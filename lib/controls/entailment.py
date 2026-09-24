"""Stage-2 entailment verifier (plan hebrew-tutor-phase2, Track P2-D).

Sits BEHIND the deterministic stage-1 checker (lib/controls/claims.py):
stage 1 flags mechanical mismatches; this module asks an LLM whether the
cited verse text actually supports the quotation — catching stage-1 false
positives (paraphrase judged as misquote) and confirming real ones.

In/out are pure data; the caller injects llm_fn(prompt)->text and decides
what to do with verdicts. Fail-open by contract: anything unparseable or
missing becomes 'abstain', never 'supported'. The caller keeps stage-1
flags on abstain.
"""
import json

MAX_ITEMS = 4
MAX_PROMPT_CHARS = 1500


def entailment_prompt(quote: str, ref: str, verse_text: str) -> str:
    return (
        "You verify scripture citations. Reply with JSON only, no other text.\n"
        f"Quotation: {quote[:400]}\n"
        f"Cited as: {ref}\n"
        f"Actual verse text: {(verse_text or '')[:800]}\n"
        "Does the verse text contain or directly entail the quotation"
        " (minor wording differences allowed, dropped qualifiers not)?\n"
        '{"verdict": "supported" | "unsupported" | "abstain",'
        ' "reason": "<one short sentence>"}'
    )[:MAX_PROMPT_CHARS]


def parse_verdict(raw: str) -> dict:
    """Strict JSON verdict; anything else is abstain (fail-open)."""
    try:
        data = json.loads((raw or "").strip())
    except (ValueError, AttributeError):
        return {"verdict": "abstain", "reason": "unparseable verifier reply"}
    if not isinstance(data, dict):
        return {"verdict": "abstain", "reason": "verifier reply not an object"}
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in ("supported", "unsupported", "abstain"):
        return {"verdict": "abstain", "reason": "unknown verdict value"}
    reason = str(data.get("reason", "")).strip()[:280]
    return {"verdict": verdict, "reason": reason or "no reason given"}


def second_opinion(unsupported: list, verse_texts: dict,
                   llm_fn) -> list:
    """Chain-of-verification pass over stage-1 flags.

    unsupported: [{quote, ref}, ...] from check_quotations.
    verse_texts: {ref: actual verse text} (missing text → abstain).
    llm_fn: callable(prompt)->str; exceptions per item → abstain.
    Returns [{quote, ref, verdict, reason}], bounded at MAX_ITEMS.
    """
    out = []
    for item in (unsupported or [])[:MAX_ITEMS]:
        quote = (item or {}).get("quote", "")
        ref = (item or {}).get("ref", "")
        text = (verse_texts or {}).get(ref, "")
        if not quote or not text:
            out.append({"quote": quote, "ref": ref,
                        "verdict": "abstain", "reason": "no verse text"})
            continue
        try:
            parsed = parse_verdict(llm_fn(entailment_prompt(quote, ref, text)))
        except Exception:
            parsed = {"verdict": "abstain", "reason": "verifier call failed"}
        out.append({"quote": quote, "ref": ref, **parsed})
    return out
