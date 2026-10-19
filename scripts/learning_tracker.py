#!/usr/bin/env python3
"""Opt-in, local-only course progress journal and adaptive practice hints."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import uuid
from pathlib import Path

RUBRIC = ("concept_accuracy", "explanation_clarity", "example_transfer", "error_correction")


def record(path: Path, learner_id: str, lesson: str, scores: dict[str, int], note: str = "") -> dict:
    if not learner_id.strip() or not lesson.strip():
        raise ValueError("learner_id and lesson are required; avoid real names or sensitive data")
    if set(scores) != set(RUBRIC) or any(not isinstance(v, int) or not 0 <= v <= 4 for v in scores.values()):
        raise ValueError("provide integer scores 0-4 for: " + ", ".join(RUBRIC))
    entry = {"record_id": str(uuid.uuid4()), "date": dt.date.today().isoformat(), "learner_id": learner_id, "lesson": lesson, "scores": scores, "note": note[:500]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def recommend(entries: list[dict]) -> dict:
    if not entries:
        return {"status": "no_history", "recommendation": "先完成一题闭卷费曼讲解并记录基线。"}
    latest = entries[-1]
    weak = [k for k, v in latest["scores"].items() if v < 3]
    totals = {k: round(sum(e["scores"][k] for e in entries) / len(entries), 2) for k in RUBRIC}
    if weak:
        return {"status": "practice_needed", "focus": weak, "averages": totals, "next_review_days": 1, "recommendation": "针对低分项换一个走势案例重讲；先要求学员独立解释，再给最小提示，次日间隔复测。"}
    return {"status": "ready_for_transfer", "focus": [], "averages": totals, "next_review_days": 3, "recommendation": "进入新周期/新标的迁移题，记录标注分歧；3日后无提示复测。"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--file", type=Path, required=True, help="Local JSONL file; do not put it in a public repository")
    p.add_argument("--learner-id", default="learner-local", help="Pseudonymous label; do not use a real name")
    p.add_argument("--lesson", help="Lesson identifier; omit to show recommendation")
    p.add_argument("--scores", help="Four comma-separated 0-4 scores in rubric order")
    p.add_argument("--note", default="")
    a = p.parse_args()
    try:
        if a.lesson:
            if not a.scores:
                p.error("--scores required when --lesson is specified")
            values = [int(x) for x in a.scores.split(",")]
            if len(values) != 4:
                p.error("--scores needs four comma-separated integers")
            record(a.file, a.learner_id, a.lesson, dict(zip(RUBRIC, values)), a.note)
        entries = [json.loads(line) for line in a.file.read_text(encoding="utf-8").splitlines() if line.strip()] if a.file.exists() else []
        print(json.dumps(recommend(entries), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(2, f"progress record failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
