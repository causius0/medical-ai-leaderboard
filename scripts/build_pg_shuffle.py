#!/usr/bin/env python3
"""
Build the canonical SSM eval set from the medbench Postgres shuffle.

The medbench DB (shuffled_questions.correct_letter) is the source of truth for
the leaderboard: 1,060 text-only SSM questions whose correct answers are at
DB-pinned letters. This script regenerates the eval files so every run scores
against exactly those letters:

  - data/ssm_questions_shuffled_with_solution.json        (PRIVATE, 1060, answers)
  - data/ssm_questions_text_only_shuffled.json            (PRIVATE, 1060, answers)
  - data/ssm_questions_text_only_shuffled_no_answers.json (public, for models)
  - data/shuffle_mapping.json                             (provenance + letters)

Wrong-option order is seeded-random (unobservable in the DB, irrelevant to
scoring). Requires psql access to the medbench database.

Usage:
    python3 scripts/build_pg_shuffle.py [--seed 42] [--db medbench]
"""

import argparse
import json
import os
import random
import subprocess
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IN = os.path.join(REPO_ROOT, "data", "ssm_questions_with_solution.json")
LETTERS = ["A", "B", "C", "D", "E"]


def load_db_letters(db: str) -> dict:
    out = subprocess.run(
        ["psql", "-d", db, "-t", "-A", "-F", "|", "-c",
         "SELECT question_id, correct_letter FROM shuffled_questions WHERE correct_letter IS NOT NULL"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    letters = {}
    for line in out.split("\n"):
        qid, letter = line.split("|")
        letters[qid.strip()] = letter.strip()
    return letters


def main():
    parser = argparse.ArgumentParser(description="Rebuild eval set from medbench shuffle")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--db", default="medbench")
    parser.add_argument("--infile", default=DEFAULT_IN)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    db_letters = load_db_letters(args.db)
    print(f"medbench shuffled_questions: {len(db_letters)} pinned letters")

    with open(args.infile, encoding="utf-8") as f:
        questions = {q["id"]: q for q in json.load(f)}

    missing = [qid for qid in db_letters if qid not in questions]
    if missing:
        raise SystemExit(f"{len(missing)} DB questions not found in source: {missing[:5]}")

    shuffled = []
    for qid, target in db_letters.items():
        q = questions[qid]
        correct_index = q["correct_answer"]["index"]
        correct_text = str(q["options"][correct_index]["text"])
        others = [str(o["text"]) for i, o in enumerate(q["options"]) if i != correct_index]
        rng.shuffle(others)
        pos = LETTERS.index(target)
        texts = others[:pos] + [correct_text] + others[pos:]
        q2 = dict(q)
        q2["options"] = [{"letter": LETTERS[i], "text": t} for i, t in enumerate(texts)]
        q2["correct_answer"] = {"letter": target, "index": pos}
        shuffled.append(q2)
    shuffled.sort(key=lambda x: x["id"])

    no_answers = [{k: v for k, v in q.items() if k != "correct_answer"} for q in shuffled]

    mapping = {
        "source": f"medbench.{args.db}.shuffled_questions.correct_letter",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "wrong_option_seed": args.seed,
        "questions": {q["id"]: q["correct_answer"]["letter"] for q in shuffled},
    }

    out_all = os.path.join(REPO_ROOT, "data", "ssm_questions_shuffled_with_solution.json")
    out_to = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only_shuffled.json")
    out_na = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only_shuffled_no_answers.json")
    out_map = os.path.join(REPO_ROOT, "data", "shuffle_mapping.json")
    for path, data in [(out_all, shuffled), (out_to, shuffled), (out_na, no_answers), (out_map, mapping)]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # verify round-trip against the DB
    letters = {q["id"]: q["correct_answer"]["letter"] for q in shuffled}
    assert letters == db_letters, "pinned letters do not match DB"
    print(f"wrote {len(shuffled)} questions; letters verified identical to DB")
    print(f"  {out_na}\n  {out_map} (+ private with-answer variants)")


if __name__ == "__main__":
    main()
