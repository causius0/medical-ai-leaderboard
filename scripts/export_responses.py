#!/usr/bin/env python3
"""
Export per-question model correctness from the shuffled_* Postgres relation to a
publishable JSON that the frontend can display. Each model's answer to each
question is recorded as correct/incorrect (scored against the shuffled
correct-answer positions).

Usage:
    python3 scripts/export_responses.py [--output frontend/public/question_responses.json]
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg

BASE = Path(__file__).resolve().parent.parent
DSN = "dbname=medbench"


def export():
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # Latest shuffled run per model
            cur.execute("SELECT model_id FROM shuffled_models ORDER BY model_id")
            model_ids = [r[0] for r in cur.fetchall()]

            # Questions with their shuffled correct letter
            cur.execute(
                "SELECT question_id, specialty, test_year, correct_letter FROM shuffled_questions ORDER BY question_id"
            )
            qs = cur.fetchall()

            # Per question, per model correctness (from each model's latest shuffled run)
            responses = {}
            for mid in model_ids:
                cur.execute(
                    """
                    SELECT r.question_id, r.is_correct, r.answer_letter
                    FROM shuffled_responses r
                    WHERE r.run_id = (SELECT MAX(run_id) FROM shuffled_runs WHERE model_id=%s)
                    """,
                    (mid,),
                )
                for qid, is_correct, answer in cur.fetchall():
                    responses.setdefault(qid, {})[mid] = {
                        "correct": bool(is_correct) if is_correct is not None else None,
                        "answer": answer,
                    }

    # Build a question-centric structure
    data = {
        "exported_at": "",
        "models": model_ids,
        "questions": [],
    }
    for qid, specialty, year, correct_letter in qs:
        data["questions"].append({
            "question_id": qid,
            "specialty": specialty,
            "test_year": year,
            "correct_letter": correct_letter,
            "models": responses.get(qid, {}),
        })
    data["exported_at"] = datetime.now(timezone.utc).isoformat()
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="frontend/public/question_responses.json")
    args = ap.parse_args()
    data = export()
    out = BASE / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✓ exported {len(data['questions'])} questions, {len(data['models'])} models → {out}")


if __name__ == "__main__":
    main()
