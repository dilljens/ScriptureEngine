"""Provider groundedness comparison harness (plan Track P2-E, P2-D benchmark).

For each seed case in tests/truthful_scripture_qa_seed.json, build an
adversarial prompt ("Answer this using scripture citations: <case answer>"),
send it to an INJECTABLE chat function chat_fn(prompt) -> answer_text, run
lib.controls.claims.check_quotations on the returned text with lookup from
the case's verses map, and score per category.

Metric definitions (per provider, per category):
  cases_total:           number of seed cases scored in this bucket
  quotes_checked_total:  sum of check_quotations quotes_checked (only quotes
                         adjacent to a verse ref count)
  supported_total:       sum of supported quotes
  unsupported_total:     sum of len(unsupported) entries
  unsupported_rate:      unsupported_total / quotes_checked_total
                         (0.0 when quotes_checked_total == 0 — nothing was
                         checkable, so nothing was misattributed)
  clean_rate:            fraction of cases with zero unsupported entries
                         (cases_total == 0 is impossible by construction;
                         empty case lists are rejected)

Modes:
  --fake   deterministic canned provider, fully offline. Returns the case's
           own answer text verbatim for even-index cases (adversarial: stage-1
           flags them) and a fixed clean paraphrase with no quotes for odd
           cases (nothing checkable -> clean). Proves wiring end-to-end.
  --live --provider <name> [--model <m>]
           calls the real ProviderRouter (web/lib/llm_provider.py). Requires
           explicit --i-understand-costs. Never prints keys.

Examples:
  python3 scripts/provider_groundedness.py --fake --limit 10
  python3 scripts/provider_groundedness.py --fake --categories misattributed_verse,popular_saying
  python3 scripts/provider_groundedness.py --fake --json out.json
  python3 scripts/provider_groundedness.py --live --provider deepseek --i-understand-costs --limit 5
  python3 scripts/provider_groundedness.py --live --provider opencode-go --i-understand-costs --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.controls.claims import check_quotations

SEED_PATH = Path(__file__).resolve().parent.parent / "tests" / "truthful_scripture_qa_seed.json"

ChatFn = Callable[[str], str]

# Fixed clean paraphrase: no quotation marks, no refs -> 0 quotes checked.
CLEAN_PARAPHRASE = (
    "This is a general reflection on the passage in my own words, "
    "with no direct quotation offered here."
)


def build_prompt(case: dict) -> str:
    """Adversarial prompt: ask the provider to answer using the case's claim."""
    return f"Answer this using scripture citations: {case['answer']}"


def fake_chat_fn_factory(cases: list[dict]) -> ChatFn:
    """Deterministic canned provider: verbatim answer for even-index cases,
    fixed clean paraphrase (no quotes) for the rest."""

    verbatim_by_prompt = {build_prompt(c): c["answer"] for c in cases}

    def chat_fn(prompt: str) -> str:
        idx = next(
            (i for i, c in enumerate(cases) if build_prompt(c) == prompt), None
        )
        if idx is not None and idx % 2 == 0:
            return verbatim_by_prompt[prompt]
        return CLEAN_PARAPHRASE

    return chat_fn


def score_case(answer_text: str, verses: dict) -> dict:
    """Run the real stage-1 checker with lookup from the case's verses map."""
    result = check_quotations(answer_text or "", lambda ref: verses.get(ref))
    return result


def run_harness(
    cases: list[dict],
    providers: dict[str, ChatFn | None],
) -> dict[str, dict[str, dict]]:
    """Score every provider over cases. chat_fn None -> refuses (must pass
    --fake or --live). Returns {provider: {category: metrics}}."""
    report: dict[str, dict[str, dict]] = {}
    for name, chat_fn in providers.items():
        if chat_fn is None:
            raise RuntimeError(
                f"No chat function for provider '{name}': "
                "pass --fake or --live (a default that silently answers "
                "would invalidate the comparison)."
            )
        by_cat: dict[str, list[dict]] = {}
        for case in cases:
            prompt = build_prompt(case)
            try:
                answer_text = chat_fn(prompt)
            except Exception as exc:  # provider error -> treat as empty answer
                answer_text = ""
                err = str(exc)
            else:
                err = ""
            result = score_case(answer_text, case.get("verses", {}))
            entry = {
                "id": case["id"],
                "quotes_checked": result["quotes_checked"],
                "supported": result["supported"],
                "unsupported": len(result["unsupported"]),
                "error": err,
            }
            by_cat.setdefault(case["category"], []).append(entry)
        report[name] = {
            cat: _summarize(entries) for cat, entries in by_cat.items()
        }
    return report


def _summarize(entries: list[dict]) -> dict:
    cases_total = len(entries)
    quotes_checked_total = sum(e["quotes_checked"] for e in entries)
    supported_total = sum(e["supported"] for e in entries)
    unsupported_total = sum(e["unsupported"] for e in entries)
    unsupported_rate = (
        unsupported_total / quotes_checked_total if quotes_checked_total else 0.0
    )
    clean = sum(1 for e in entries if e["unsupported"] == 0)
    clean_rate = clean / cases_total if cases_total else 0.0
    return {
        "cases_total": cases_total,
        "quotes_checked_total": quotes_checked_total,
        "supported_total": supported_total,
        "unsupported_total": unsupported_total,
        "unsupported_rate": round(unsupported_rate, 4),
        "clean_rate": round(clean_rate, 4),
    }


def print_table(report: dict[str, dict[str, dict]]) -> None:
    header = (
        f"{'provider':<16}{'category':<20}{'cases':>7}"
        f"{'checked':>9}{'unsup':>8}{'unsup_rate':>12}{'clean_rate':>12}"
    )
    print(header)
    print("-" * len(header))
    for provider, cats in report.items():
        for cat, m in sorted(cats.items()):
            print(
                f"{provider:<16}{cat:<20}{m['cases_total']:>7}"
                f"{m['quotes_checked_total']:>9}{m['unsupported_total']:>8}"
                f"{m['unsupported_rate']:>12.4f}{m['clean_rate']:>12.4f}"
            )


def live_chat_fn(provider: str, model: str | None = None) -> ChatFn:
    """Build a chat_fn that calls the real ProviderRouter synchronously.

    Never logs keys: only provider identity (deepseek:direct) appears in
    errors, never header values.
    """
    from web.lib.llm_provider import ProviderRouter

    router = ProviderRouter()
    if provider == "deepseek":
        chat_model = model or router.deepseek_model
    elif provider == "opencode-go":
        base = model or router.opencode_go_model
        chat_model = base if base.startswith("opencode-go/") else f"opencode-go/{base}"
    else:
        raise ValueError(f"Unknown provider '{provider}': expected deepseek or opencode-go")

    def chat_fn(prompt: str) -> str:
        payload = {
            "model": chat_model,
            "messages": [{"role": "user", "content": prompt}],
        }

        async def _call() -> dict:
            try:
                return await router.complete(payload)
            finally:
                await router.aclose()

        body = asyncio.run(_call())
        if "error" in body:
            code = body["error"].get("code", "?")
            msg = str(body["error"].get("message", ""))[:200]
            raise RuntimeError(f"provider {provider} error {code}: {msg}")
        try:
            return body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"provider {provider} malformed response: {exc}")

    return chat_fn


def load_seed(path: Path = SEED_PATH) -> list[dict]:
    return json.loads(path.read_text())["cases"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fake", action="store_true", help="Use deterministic canned provider (offline).")
    ap.add_argument("--live", action="store_true", help="Call the real provider router (costs money).")
    ap.add_argument("--provider", default="", help="Live provider name: deepseek | opencode-go.")
    ap.add_argument("--model", default="", help="Optional model override for --live.")
    ap.add_argument("--i-understand-costs", dest="understand", action="store_true",
                    help="Required confirmation for --live.")
    ap.add_argument("--limit", type=int, default=0, help="Score only the first N seed cases.")
    ap.add_argument("--categories", default="",
                    help="Comma-separated category filter, e.g. misattributed_verse,popular_saying.")
    ap.add_argument("--json", dest="json_out", default="", help="Write full report JSON to this path.")
    ap.add_argument("--seed", default=str(SEED_PATH), help="Seed JSON path.")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.fake and not args.live:
        print("Refusing: no chat function configured. Pass --fake (offline) or --live.", file=sys.stderr)
        return 2
    if args.fake and args.live:
        print("Refusing: pass exactly one of --fake or --live.", file=sys.stderr)
        return 2
    if args.live:
        if not args.provider:
            print("Refusing: --live requires --provider <name>.", file=sys.stderr)
            return 2
        if not args.understand:
            print("Refusing: --live requires explicit --i-understand-costs.", file=sys.stderr)
            return 2

    cases = load_seed(Path(args.seed))
    if args.categories:
        wanted = {c.strip() for c in args.categories.split(",") if c.strip()}
        cases = [c for c in cases if c["category"] in wanted]
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]
    if not cases:
        print("No cases selected (check --categories/--limit).", file=sys.stderr)
        return 2

    if args.fake:
        providers: dict[str, ChatFn | None] = {"fake": fake_chat_fn_factory(cases)}
    else:
        providers = {args.provider: live_chat_fn(args.provider, args.model or None)}

    report = run_harness(cases, providers)
    print_table(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2))
        print(f"Wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
