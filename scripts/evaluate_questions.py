#!/usr/bin/env python3
"""Test harness: generate sample assessment questions and LLM-evaluate them.

Usage:
    python3 scripts/evaluate_questions.py              # Generate + evaluate
    python3 scripts/evaluate_questions.py --count 20   # More questions
    python3 scripts/evaluate_questions.py --skip-llm   # Just generate, no eval
"""
import json
import os
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = Path(__file__).parent.parent
DB = BASE / "data" / "processed" / "scripture.db"

from lib.assessment.items import DeepQuestionGenerator


def generate_sample(count=10):
    """Generate sample questions from each tier."""
    conn = sqlite3.connect(str(DB))
    gen = DeepQuestionGenerator(conn)

    # Generate extra to get diverse samples
    items = []
    target_tiers = {"text": 0, "analysis": 0, "consistency": 0}

    for _ in range(count * 10):
        if all(target_tiers[t] >= count // 3 for t in target_tiers):
            break

        # Try each generator type
        for g in [gen._gen_cross_reference, gen._gen_structural,
                  gen._gen_thematic_group, gen._gen_passage_comprehension,
                  gen._gen_consistency]:
            try:
                item = g()
                if item:
                    # Assign tier
                    if "tier" in item and item["tier"]:
                        item["tier"] = item["tier"]
                    elif "share a theme" in item.get("question","").lower() or "develop" in item.get("question","").lower():
                        item["tier"] = "analysis"
                    elif item.get("bloom_level") == "understand":
                        item["tier"] = "text"
                    else:
                        item["tier"] = "analysis"

                    if target_tiers.get(item["tier"], 0) < count // 3:
                        target_tiers[item["tier"]] = target_tiers.get(item["tier"], 0) + 1
                        items.append(item)
            except Exception:
                continue

    conn.close()
    random.shuffle(items)
    return items[:count]


def evaluate_with_llm(items):
    """Send sample questions to the LLM for evaluation."""
    import urllib.error
    import urllib.request

    # Build an evaluation prompt
    prompt_parts = [
        "You are evaluating scripture learning questions for quality. Rate each question from 1-10 on:\n",
        "- CLARITY: Is the question clearly worded and easy to understand?\n",
        "- PEDAGOGICAL VALUE: Does it teach something meaningful about scripture?\n",
        "- FAIRNESS: Is the correct answer actually discernible from the information given?\n",
        "- DEPTH: Does it test understanding/analysis, not just recall?\n\n",
        "Here are the questions:\n\n"
    ]

    for i, item in enumerate(items):
        q = item.get("question", "")
        opts = item.get("options", [])
        ans = item.get("correct_answer", "")
        tier = item.get("tier", "?")
        prompt_parts.append(f"Question {i+1} [{tier}]:")
        prompt_parts.append(q[:200])
        prompt_parts.append(f"Options: {opts}")
        prompt_parts.append(f"Correct: {str(ans)[:80]}")
        prompt_parts.append("")

    prompt_parts.append(
        "\nRespond with a JSON array of evaluations:\n"
        '[{"q": 1, "clarity": N, "pedagogical": N, "fairness": N, "depth": N, '
        '"issues": "any problems", "strengths": "what works well"}, ...]'
    )

    prompt = "\n".join(prompt_parts)

    # Call the local chat endpoint
    api_url = os.environ.get("SCRIPTURE_API_URL", "http://localhost:8002") + "/api/v1/chat"
    req_data = json.dumps({"message": prompt, "model": "default"}).encode()
    req = urllib.request.Request(api_url, data=req_data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            raw = result.get("data", {}).get("response", "{}")
            # Extract JSON
            import re
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            return [{"raw": raw}]
        return [{"error": result.get("error", "unknown")}]
    except Exception as e:
        return [{"error": str(e)}]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate and evaluate assessment questions")
    parser.add_argument("--count", type=int, default=10, help="Number of questions")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM evaluation")
    args = parser.parse_args()

    print(f"Generating {args.count} sample questions...\n")
    items = generate_sample(args.count)

    if not items:
        print("❌ No questions generated")
        return

    print(f"Generated {len(items)} questions:")
    for i, item in enumerate(items):
        tier = item.get("tier", "?")
        q = item.get("question", "")
        ans = item.get("correct_answer", "")
        print(f"\n{'='*60}")
        print(f"Q{i+1} [{tier}] Bloom: {item.get('bloom_level','?')}")
        print(f"{q[:250]}...")
        print(f"Options: {item.get('options', [])[:4]}")
        print(f"Answer: {str(ans)[:80]}")

    if args.skip_llm:
        return

    print(f"\n{'='*60}")
    print("Sending to LLM for evaluation...")
    evaluations = evaluate_with_llm(items)
    print(f"\nReceived {len(evaluations)} evaluations:\n")

    for ev in evaluations:
        if isinstance(ev, dict):
            qnum = ev.get("q", "?")
            clarity = ev.get("clarity", "?")
            ped = ev.get("pedagogical", "?")
            fair = ev.get("fairness", "?")
            depth = ev.get("depth", "?")
            issues = ev.get("issues", "")
            strengths = ev.get("strengths", "")
            print(f"  Q{qnum}: Clarity={clarity} Pedagogy={ped} Fairness={fair} Depth={depth}")
            if strengths:
                print(f"    ✅ {strengths}")
            if issues:
                print(f"    ⚠️  {issues}")
        else:
            print(f"  Raw: {str(ev)[:200]}")

    # Summary
    scores = [e for e in evaluations if isinstance(e, dict) and isinstance(e.get("clarity"), (int, float))]
    if scores:
        def avg(k):
            return sum(s.get(k, 0) for s in scores) / len(scores)
        print(f"\n{'='*60}")
        print(f"AVERAGES: Clarity={avg('clarity'):.1f} Pedagogy={avg('pedagogical'):.1f} "
              f"Fairness={avg('fairness'):.1f} Depth={avg('depth'):.1f}")
        print(f"TOTAL SCORE: {avg('clarity') + avg('pedagogical') + avg('fairness') + avg('depth'):.1f}/40")


if __name__ == "__main__":
    main()
