#!/usr/bin/env python3
"""
Publish a local eval run into the medbench Postgres leaderboard.

Reads a results/local/*.json produced by scripts/run_local_baseline.py, scores
it against the canonical PG-pinned shuffled key (data/ssm_questions_text_only_shuffled.json,
or pass --solutions), and inserts into medbench shuffled_* tables:

  shuffled_models    (upsert model identity)
  shuffled_runs      (one row per publish: accuracy, counts, harness metadata)
  shuffled_responses (per-question answer_letter + is_correct)

Idempotency: each publish creates a NEW run row (runs are immutable history);
re-publishing the same file duplicates — check first with:
  SELECT * FROM shuffled_runs ORDER BY run_id DESC LIMIT 5;

Usage:
    python3 scripts/publish_to_medbench.py results/local/LFM2-24B-A2B-4bit_pg_shuffled.json \
        --backend mlx --param-size "24B-A2B" --provider "Liquid AI"
"""

import argparse
import json
import os
import subprocess
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOLUTIONS = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only_shuffled.json")


def psql(db: str, sql: str, tuples: bool = False) -> str:
    cmd = ["psql", "-d", db, "-v", "ON_ERROR_STOP=1"]
    if tuples:
        cmd += ["-t", "-A", "-F", "|"]
    cmd += ["-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def sql_str(v: str) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def main():
    parser = argparse.ArgumentParser(description="Insert an eval run into medbench")
    parser.add_argument("results")
    parser.add_argument("--db", default="medbench")
    parser.add_argument("--solutions", default=DEFAULT_SOLUTIONS)
    parser.add_argument("--dataset", default="italian_ssm_shuffled")
    parser.add_argument("--prompt-template", default="zero_shot_medical_local")
    parser.add_argument("--provider", default="Liquid AI")
    parser.add_argument("--backend", default="mlx")
    parser.add_argument("--param-size", default="24B-A2B")
    args = parser.parse_args()

    with open(args.results, encoding="utf-8") as f:
        run = json.load(f)
    with open(args.solutions, encoding="utf-8") as f:
        key = {q["id"]: q["correct_answer"]["letter"] for q in json.load(f)}

    model_id = run["model_name"].split("/")[-1].lower().replace("_", "-")
    answers = run["answers"]

    # 1. upsert model
    psql(args.db, f"""
        INSERT INTO shuffled_models (model_id, name, provider, backend, param_size)
        VALUES ({sql_str(model_id)}, {sql_str(run['model_name'])}, {sql_str(args.provider)},
                {sql_str(args.backend)}, {sql_str(args.param_size)})
        ON CONFLICT (model_id) DO UPDATE SET name = EXCLUDED.name;
    """)

    # 2. score
    total_answered = sum(1 for a in answers if a["answer"])
    total_correct = sum(1 for a in answers if a["answer"] and a["answer"] == key.get(a["id"]))
    accuracy = round(100.0 * total_correct / len(key), 2)

    # 3. insert run, get run_id
    run_id = psql(args.db, f"""
        INSERT INTO shuffled_runs
            (model_id, dataset, prompt_template, temperature, max_tokens,
             total_questions, total_answered, total_correct, overall_accuracy)
        VALUES ({sql_str(model_id)}, {sql_str(args.dataset)}, {sql_str(args.prompt_template)},
                0, 8, {len(key)}, {total_answered}, {total_correct}, {accuracy})
        RETURNING run_id;
    """, tuples=True).split("\n")[0].strip()
    print(f"inserted shuffled_runs run_id={run_id}: {run['model_name']} {accuracy}% "
          f"({total_correct}/{len(key)}, answered={total_answered})")

    # 4. bulk insert responses
    values = []
    for a in answers:
        letter = a["answer"]
        correct = letter is not None and letter == key.get(a["id"])
        values.append(f"({run_id}, {sql_str(a['id'])}, {sql_str(letter)}, {str(bool(correct)).lower()})")
    # questions with no response row at all (harness skipped): none expected, key covers full set
    chunk = 250
    for i in range(0, len(values), chunk):
        psql(args.db, "INSERT INTO shuffled_responses (run_id, question_id, answer_letter, is_correct) VALUES "
                      + ", ".join(values[i:i + chunk]) + " ON CONFLICT DO NOTHING;")
    print(f"inserted {len(values)} shuffled_responses rows")


if __name__ == "__main__":
    main()
