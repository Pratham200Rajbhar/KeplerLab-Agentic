from __future__ import annotations

from typing import Any, Dict, Iterable


def evaluate_game(content: Dict[str, Any], moves: Iterable[dict]) -> Dict[str, Any]:
    """Evaluate game moves against generated rounds."""
    game = (content or {}).get("game") or {}
    rounds = game.get("rounds") or []

    submitted = {
        str(m.get("round_id") or ""): str(m.get("answer") or "").strip().upper()
        for m in (moves or [])
    }

    if not rounds:
        return {
            "passed": True,
            "score": 1.0,
            "xp_awarded": 10,
            "feedback": "No game rounds were generated for this day.",
        }

    correct = 0
    for round_item in rounds:
        rid = str(round_item.get("id") or "")
        expected = str(round_item.get("correct_choice") or "").strip().upper()
        selected = submitted.get(rid, "")
        if selected == expected:
            correct += 1

    total = len(rounds)
    score = (correct / total) if total else 0.0
    passed = score >= 0.67
    xp_awarded = int(20 + (score * 30)) if passed else int(score * 10)

    if passed:
        feedback = f"Challenge complete. You got {correct}/{total} rounds right."
    else:
        feedback = f"You got {correct}/{total} rounds right. Retry to unlock completion."

    return {
        "passed": passed,
        "score": round(score, 4),
        "xp_awarded": xp_awarded,
        "feedback": feedback,
    }
