#!/usr/bin/env python3
"""
Shuffle Answer Keys for SSM Position-Bias Testing

The SSM exam's correct answers are heavily position-skewed (91% 'A' in the
source data), so accuracy measured on original positions is confounded by
answer-position priors. This script deterministically permutes each question's
options so correct answers are uniformly distributed across A-E, producing the
artifacts documented in CLAUDE.md:

  - data/ssm_questions_shuffled_with_solution.json        (private, 1120, answers)
  - data/s sm_questions_text_only_shuffled.json           (private, 1060, answers)
  - data/ssm_questions_text_only_shuffled_no_answers.json (public, 1060, for models)
  - data/shuffle_mapping.json                             (original -> shuffled)

Seeded and reproducible. The same balancing rule is used by
scripts/prepare_lora_data.py for the training data, so training and eval are
position-consistent.

Usage:
    python3 scripts/shuffle_answer_keys.py [--seed 42]
"""

import argparse
import json
import os
import random
from collections import Counter
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IN = os.path.join(REPO_ROOT, "data", "ssm_questions_with_solution.json")
LETTERS = ["A", "B", "C", "D", "E"]


def strip_answers(q):
    return {k: v for k, v in q.items() if k not in ("correct_answer",)}


def main():
    parser = argparse.ArgumentParser(description="Shuffle SSM answer keys (position balancing)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--infile", default=DEFAULT_IN)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    with open(args.infile, encoding="utf-8") as f:
        questions = json.load(f)

    before = Counter()
    after = Counter()
    mapping = {"seed": args.seed, "generated_at": datetime.now().isoformat(timespec="seconds"), "questions": {}}
    shuffled_all = []

    dist = Counter()  # running counts for least-used-letter assignment
    for q in questions:
        before[q["correct_answer"]["letter"]] += 1
        options = q["options"]  # [{letter, text}] in original order
        correct_index = q["correct_answer"]["index"]
        correct_text = options[correct_index]["text"]
        orig_letter = q["correct_answer"]["letter"]

        # place correct option at the globally least-used letter slot
        slots = LETTERS[: len(options)]
        target = min(slots, key=lambda L: (dist[L], rng.random()))
        others = [o["text"] for i, o in enumerate(options) if i != correct_index]
        rng.shuffle(others)
        target_index = LETTERS.index(target)
        new_options_texts = others[:target_index] + [correct_text] + others[target_index:]
        new_options = [{"letter": LETTERS[i], "text": t} for i, t in enumerate(new_options_texts)]

        q2 = dict(q)
        q2["options"] = new_options
        q2["correct_answer"] = {"letter": target, "index": LETTERS.index(target)}
        shuffled_all.append(q2)

        after[target] += 1
        dist[target] += 1
        mapping["questions"][q["id"]] = {
            "orig_letter": orig_letter,
            "shuffled_letter": target,
        }

    text_only = [q for q in shuffled_all if not q.get("has_image")]
    no_answers = [strip_answers(q) for q in text_only]

    out_all = os.path.join(REPO_ROOT, "data", "ssm_questions_shuffled_with_solution.json")
    out_to = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only_shuffled.json")
    out_na = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only_shuffled_no_answers.json")
    out_map = os.path.join(REPO_ROOT, "data", "shuffle_mapping.json")

    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(shuffled_all, f, ensure_ascii=False, indent=2)
    with open(out_to, "w", encoding="utf-8") as f:
        json.dump(text_only, f, ensure_ascii=False, indent=2)
    with open(out_na, "w", encoding="utf-8") as f:
        json.dump(no_answers, f, ensure_ascii=False, indent=2)
    with open(out_map, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"shuffled {len(questions)} questions (seed {args.seed})")
    print(f"  letters before: {dict(sorted(before.items()))}")
    print(f"  letters after : {dict(sorted(after.items()))}")
    print(f"  text-only     : {len(text_only)}")
    print(f"wrote: {out_all}")
    print(f"wrote: {out_to} (PRIVATE - contains answers)")
    print(f"wrote: {out_na}")
    print(f"wrote: {out_map}")


if __name__ == "__main__":
    main()
