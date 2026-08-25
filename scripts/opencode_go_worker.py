#!/usr/bin/env python3
"""Minimal credential-isolated OpenCode Go worker.

Run this through ``ai-secret exec`` so the worker receives exactly one
``OPENCODE_API_KEY``.  The parent chat process talks to it over a Unix socket;
the worker never logs request bodies or authorization headers.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socketserver
import sys
import threading
from contextlib import suppress
from http.server import BaseHTTPRequestHandler

import httpx

DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"


class _WorkerHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, _format, *_args):
        # Request paths can contain user-controlled data. Keep the worker quiet
        # so credentials and prompts cannot accidentally enter service logs.
        return

    def _write_json(self, status: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            ready = bool(os.environ.get("OPENCODE_API_KEY", "").strip())
            self._write_json(200 if ready else 503, {"ok": ready, "ready": ready})
            return
        self._write_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/chat/completions":
            self._write_json(404, {"error": "not found"})
            return

        api_key = os.environ.get("OPENCODE_API_KEY", "").strip()
        if not api_key:
            self._write_json(503, {"error": "worker credential unavailable"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request_body = json.loads(self.rfile.read(length))
        except (TypeError, ValueError):
            self._write_json(400, {"error": "invalid JSON request"})
            return

        base_url = os.environ.get("OPENCODE_GO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        try:
            with (
                httpx.Client(timeout=600.0) as client,
                client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                ) as upstream,
            ):
                self.send_response(upstream.status_code)
                content_type = upstream.headers.get("content-type", "application/json")
                self.send_header("Content-Type", content_type)
                self.end_headers()
                for chunk in upstream.iter_raw():
                    if chunk:
                        self.wfile.write(chunk)
                        self.wfile.flush()
        except (httpx.HTTPError, OSError) as exc:
            # Keep the message generic; upstream details belong in the parent
            # router's structured error handling, not this credential process.
            with suppress(BrokenPipeError, ConnectionResetError):
                self._write_json(503, {"error": f"upstream unavailable: {type(exc).__name__}"})


class _UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True, help="Unix socket path")
    args = parser.parse_args()

    with suppress(FileNotFoundError):
        os.unlink(args.socket)
    os.makedirs(os.path.dirname(args.socket) or ".", mode=0o700, exist_ok=True)

    server = _UnixServer(args.socket, _WorkerHandler)
    os.chmod(args.socket, 0o600)

    stop_requested = threading.Event()

    def stop(_signum, _frame):
        stop_requested.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server_thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.25},
        daemon=True,
    )
    server_thread.start()
    try:
        while server_thread.is_alive() and not stop_requested.wait(0.25):
            pass
    finally:
        server.shutdown()
        server_thread.join()
        server.server_close()
        with suppress(FileNotFoundError):
            os.unlink(args.socket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
