"""Runs the eval set against the live agent and reports retrieval/routing quality.

Usage: python -m eval.run_eval
Requires GROQ_API_KEY and TAVILY_API_KEY to be set (via .env).
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from haystack.dataclasses import ChatMessage

from src.agent import build_agent, extract_tool_names

load_dotenv()

EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"
RESULTS_PATH = Path(__file__).parent / "results.json"


def check_tools(category: str, expected_tools: list[str], actual_tools: list[str]) -> bool:
    if category == "refusal":
        return True  # tool choice isn't graded for refusal cases, only the answer text
    if category == "hybrid":
        return all(t in actual_tools for t in expected_tools)
    return any(t in actual_tools for t in expected_tools)


def normalize(text: str) -> str:
    # The model sometimes emits non-ASCII spaces (e.g. U+202F) inside bolded
    # text, which breaks naive substring matching. Collapse all whitespace
    # (Unicode-aware) to a single regular space before comparing.
    return re.sub(r"\s+", " ", text, flags=re.UNICODE).lower()


def check_keywords(expected_keywords: list[str], answer: str) -> bool:
    if not expected_keywords:
        return True
    answer_norm = normalize(answer)
    for kw in expected_keywords:
        kw_norm = normalize(kw)
        if re.fullmatch(r"[\w\s]+", kw_norm):
            # Word-boundary match: a bare substring check on short words like
            # "no"/"not" gives false positives against words like "Innovation".
            if re.search(rf"\b{re.escape(kw_norm)}\b", answer_norm):
                return True
        elif kw_norm in answer_norm:
            # Symbol/punctuation keywords (e.g. "$") don't have meaningful
            # word boundaries, so fall back to a plain substring check.
            return True
    return False


def run_eval() -> None:
    cases = json.loads(EVAL_SET_PATH.read_text())
    agent = build_agent()

    results = []
    for case in cases:
        response = agent.run(messages=[ChatMessage.from_user(case["question"])])
        answer = response["last_message"].text
        tools_used = extract_tool_names(response["messages"])

        tools_ok = check_tools(case["category"], case["expected_tools"], tools_used)
        keywords_ok = check_keywords(case["expected_keywords"], answer)
        passed = tools_ok and keywords_ok

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "answer": answer,
                "tools_used": tools_used,
                "expected_tools": case["expected_tools"],
                "expected_keywords": case["expected_keywords"],
                "tools_ok": tools_ok,
                "keywords_ok": keywords_ok,
                "passed": passed,
            }
        )

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case['id']} ({case['category']}) - tools={tools_used}")
        if not passed:
            print(f"         question: {case['question']}")
            print(f"         answer:   {answer[:200]}")

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{passed_count}/{total} passed")

    RESULTS_PATH.write_text(
        json.dumps(
            {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "passed": passed_count,
                "total": total,
                "results": results,
            },
            indent=2,
        )
    )
    print(f"Full results written to {RESULTS_PATH}")


if __name__ == "__main__":
    run_eval()
