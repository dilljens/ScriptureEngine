"""Chat background job manager.

Runs DeepSeek chat jobs as independent asyncio tasks so they survive the
client disconnecting (phone minimize, network drop, tab switch). Each job
emits seq-numbered events into an in-memory buffer AND a `chat_jobs` SQLite
row (flushed on a timer), so any uvicorn worker can serve polls and the final
state survives process death as a recoverable record.

Poll correctness across workers: events are persisted to SQLite in batches
(events_json), so a poll answered by a different worker than the one running
the job still returns the same incremental stream. The job's final content is
persisted too, so a late poller gets the complete answer even after the
in-memory buffer is evicted.

See docs/plans/chat-background-jobs.md (Track A3/A4).
"""
import asyncio
import json
import logging
import time
import uuid
from types import SimpleNamespace

from lib.db import CHAT_JOBS_SQL, get_db

logger = logging.getLogger("chat.jobs")

POLL_BUFFER = 200          # max events kept per job (memory + DB)
FLUSH_INTERVAL = 2.0       # seconds between DB flushes while streaming
FLUSH_EVENT_BATCH = 50     # or flush after this many new events
JOB_TTL_SECONDS = 3600     # done/failed jobs are evicted after 1h
STALE_RUNNING_SECONDS = 180  # a queued/running row untouched this long is dead
                             # (heartbeats update updated_at every ≤15s while live)
MAX_JOBS_PER_IP = 5


class JobLimitError(Exception):
    """Raised when an IP already has the maximum number of active jobs."""


class ChatJob:
    """State + run loop for one background chat job."""

    def __init__(self, job_id, body, messages, client_ip=""):
        self.id = job_id
        self.body = body          # dict of ChatRequest fields (minus messages)
        self.messages = messages  # prepared message list (system prompt injected)
        self.client_ip = client_ip
        self.status = "queued"
        self.seq = 0
        self.events = []          # [{"seq": n, ...event}, ...] newest-last, capped
        self.final_content = ""
        self.final_reasoning = ""
        self.usage = {}
        self.cost = None
        self.model = body.get("model") or "deepseek-v4-flash"
        self.finish_reason = ""
        self.error = ""
        self.tool_results = []
        self.created_at = time.time()
        self.updated_at = time.time()
        self.task = None

    # ── event buffer ────────────────────────────────────────────────────

    def emit(self, event: dict) -> None:
        self.seq += 1
        self.events.append({"seq": self.seq, **event})
        if len(self.events) > POLL_BUFFER:
            del self.events[: len(self.events) - POLL_BUFFER]
        self.updated_at = time.time()

    def events_since(self, after_seq: int) -> list:
        return [e for e in self.events if e["seq"] > after_seq]

    # ── persistence (SQLite chat_jobs row) ──────────────────────────────

    @staticmethod
    def _ensure_table() -> None:
        try:
            conn = get_db()
            try:
                conn.executescript(CHAT_JOBS_SQL)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat_jobs table ensure failed: %s", e)

    def _insert_row(self) -> None:
        self._ensure_table()
        try:
            conn = get_db()
            try:
                conn.execute(
                    """
                    INSERT INTO chat_jobs
                        (id, session_id, client_message_id, status, seq, model,
                         max_tokens, temperature, created_at, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, 0, ?, ?, ?, datetime('now'), datetime('now'), ?)
                    """,
                    (
                        self.id,
                        self.body.get("session_id") or "",
                        self.body.get("client_message_id") or "",
                        self.status,
                        self.model,
                        self.body.get("max_tokens") or 16384,
                        self.body.get("temperature") or 0.7,
                        time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.gmtime(time.time() + JOB_TTL_SECONDS)),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat job %s row insert failed: %s", self.id, e)

    def _persist(self) -> None:
        try:
            conn = get_db()
            try:
                conn.execute(
                    """
                    UPDATE chat_jobs SET
                        status=?, seq=?, events_json=?, tool_results_json=?,
                        usage_json=?, finish_reason=?, error=?,
                        final_content=?, final_reasoning=?,
                        updated_at=datetime('now'), expires_at=?
                    WHERE id=?
                    """,
                    (
                        self.status,
                        self.seq,
                        json.dumps(self.events, default=str, ensure_ascii=False),
                        json.dumps(self.tool_results, default=str, ensure_ascii=False),
                        json.dumps(self.usage, default=str),
                        self.finish_reason,
                        self.error,
                        self.final_content,
                        self.final_reasoning,
                        time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.gmtime(time.time() + JOB_TTL_SECONDS)),
                        self.id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat job %s persist failed: %s", self.id, e)

    # ── run loop ────────────────────────────────────────────────────────

    def _body_ns(self):
        """ChatRequest-ish namespace for _chat_pipeline (attribute access)."""
        b = dict(self.body)
        b.setdefault("tools_enabled", True)
        b.setdefault("scopes", [])
        b.setdefault("disabled_tools", [])
        b.setdefault("mode", "chat")
        b.setdefault("model", "deepseek-v4-flash")
        b.setdefault("max_tokens", 16384)
        b.setdefault("temperature", 0.7)
        return SimpleNamespace(**b)

    def _apply_event(self, event: dict) -> None:
        etype = event.get("type")
        if etype in ("text", "thinking"):
            self.status = "streaming"
            if etype == "text":
                self.final_content += event.get("content") or ""
            else:
                self.final_reasoning += event.get("content") or ""
        elif etype == "tool_progress":
            self.status = "streaming"
        elif etype == "done":
            self.status = "done"
            self.final_content = event.get("final_content") or ""
            self.final_reasoning = event.get("final_reasoning") or ""
            self.usage = event.get("usage") or {}
            self.cost = event.get("cost")
            self.model = event.get("model") or self.model
            self.finish_reason = event.get("finish_reason") or ""
            self.tool_results = event.get("tool_results") or []
        elif etype == "error":
            self.status = "failed"
            self.error = event.get("message") or ""

    async def _run(self) -> None:
        # Lazy import: web.routes.chat imports this module at load time, so we
        # cannot import it back at module level (cycle). By the time a job runs,
        # chat is fully imported.
        from web.routes.chat import _chat_pipeline

        self.status = "running"
        self._persist()
        last_flush = time.time()
        try:
            async for event in _chat_pipeline(self._body_ns(), self.messages):
                self.emit(event)
                self._apply_event(event)
                if event.get("type") in ("done", "error"):
                    break
                now = time.time()
                if now - last_flush >= FLUSH_INTERVAL or len(self.events) >= FLUSH_EVENT_BATCH:
                    self._persist()
                    last_flush = now
        except asyncio.CancelledError:
            self.status = "cancelled"
            self._persist()
            raise
        except Exception as e:
            logger.exception("chat job %s crashed", self.id)
            self.status = "failed"
            self.error = str(e)
            self.emit({"type": "error", "message": f"Chat job failed: {e}"})
        self._persist()
        if self.status == "done":
            self._save_to_conversation()

    # ── completion side-effects ─────────────────────────────────────────

    def _save_to_conversation(self) -> None:
        """Best-effort: persist the finished assistant message to the session.
        Client remains the source of truth; this survives a full app kill."""
        session_id = self.body.get("session_id") or ""
        if not session_id:
            return
        try:
            from lib.api.conversations import add_message
            conn = get_db()
            try:
                add_message(
                    conn,
                    session_id=session_id,
                    role="assistant",
                    content=self.final_content or self.final_reasoning or "(no response)",
                    metadata={
                        "client_message_id": f"job-{self.id}",
                        "source": "chat_job",
                        "finish_reason": self.finish_reason,
                        "tool_count": len(self.tool_results),
                    },
                )
                conn.commit()
                logger.info("chat job %s saved assistant message to session %s",
                            self.id, session_id)
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat job %s conversation save failed: %s", self.id, e)


class JobManager:
    def __init__(self):
        self._jobs: dict[str, ChatJob] = {}
        self._ip_active: dict[str, int] = {}

    def create(self, body: dict, messages: list, client_ip: str = "") -> str:
        """Create a job, insert its DB row, and start the detached run task."""
        if client_ip and self._ip_active.get(client_ip, 0) >= MAX_JOBS_PER_IP:
            raise JobLimitError("Too many active chat jobs — wait for one to finish.")
        job_id = uuid.uuid4().hex
        job = ChatJob(job_id, body, messages, client_ip)
        self._jobs[job_id] = job
        if client_ip:
            self._ip_active[client_ip] = self._ip_active.get(client_ip, 0) + 1
        job._insert_row()
        job.task = asyncio.create_task(self._wrap_run(job))
        return job_id

    async def _wrap_run(self, job: ChatJob) -> None:
        try:
            await job._run()
        finally:
            if job.client_ip:
                self._ip_active[job.client_ip] = max(0, self._ip_active.get(job.client_ip, 0) - 1)

    def get(self, job_id: str) -> ChatJob | None:
        """In-memory job if this worker owns it, else the SQLite record."""
        job = self._jobs.get(job_id)
        if job is not None:
            return job
        return self._load(job_id)

    def cancel(self, job_id: str) -> bool:
        """Cancel a running job (Stop button). No-op if already finished."""
        job = self._jobs.get(job_id)
        if job is not None and job.task is not None and not job.task.done():
            job.task.cancel()
            return True
        # Not running on this worker — mark the DB row cancelled if it's live.
        row = self._load(job_id)
        if row is not None and row.status in ("queued", "running", "streaming"):
            try:
                conn = get_db()
                try:
                    conn.execute("UPDATE chat_jobs SET status='cancelled', updated_at=datetime('now') WHERE id=?", (job_id,))
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass
            return True
        return False

    def sweep(self) -> None:
        """Ensure the table, evict expired finished jobs, recover stale rows."""
        ChatJob._ensure_table()
        now = time.time()
        for job_id in list(self._jobs):
            job = self._jobs[job_id]
            if job.status in ("done", "failed", "cancelled") and now - job.updated_at > JOB_TTL_SECONDS:
                del self._jobs[job_id]
                if job.client_ip:
                    self._ip_active[job.client_ip] = max(0, self._ip_active.get(job.client_ip, 0) - 1)
        self._recover_stale()

    def _recover_stale(self) -> None:
        """Mark rows that look dead (worker died mid-job) as failed."""
        cutoff = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.gmtime(time.time() - STALE_RUNNING_SECONDS))
        try:
            conn = get_db()
            try:
                rows = conn.execute(
                    "SELECT id FROM chat_jobs WHERE status IN ('queued','running','streaming') AND updated_at < ?",
                    (cutoff,),
                ).fetchall()
                for row in rows:
                    conn.execute(
                        "UPDATE chat_jobs SET status='failed', error='interrupted — retry', updated_at=datetime('now') WHERE id=?",
                        (row["id"],),
                    )
                conn.commit()
                if rows:
                    logger.warning("chat jobs recovered as interrupted: %s",
                                   [r["id"] for r in rows])
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat job recovery sweep failed: %s", e)

    def _load(self, job_id: str) -> ChatJob | None:
        """Reconstruct a job from its SQLite row (other worker / post-eviction)."""
        try:
            conn = get_db()
            try:
                row = conn.execute("SELECT * FROM chat_jobs WHERE id=?", (job_id,)).fetchone()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("chat job %s load failed: %s", job_id, e)
            return None
        if row is None:
            return None
        job = ChatJob(job_id, {}, [])
        job.status = row["status"]
        job.seq = row["seq"] or 0
        try:
            job.events = json.loads(row["events_json"] or "[]")
        except Exception:
            job.events = []
        job.final_content = row["final_content"] or ""
        job.final_reasoning = row["final_reasoning"] or ""
        job.finish_reason = row["finish_reason"] or ""
        job.error = row["error"] or ""
        try:
            job.tool_results = json.loads(row["tool_results_json"] or "[]")
        except Exception:
            job.tool_results = []
        try:
            job.usage = json.loads(row["usage_json"] or "{}")
        except Exception:
            job.usage = {}
        job.model = row["model"] or "deepseek-v4-flash"
        return job


manager = JobManager()


# ── periodic sweep ──────────────────────────────────────────────────────

async def _sweep_loop(interval: float = 600.0):
    while True:
        await asyncio.sleep(interval)
        try:
            manager.sweep()
        except Exception as e:
            logger.warning("chat job sweep failed: %s", e)


def start_sweeper() -> asyncio.Task:
    """Start the periodic sweep task (call once from app lifespan)."""
    return asyncio.create_task(_sweep_loop())
