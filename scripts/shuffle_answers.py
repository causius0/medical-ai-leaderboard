#!/usr/bin/env python3
"""
Create a shuffled version of the SSM (Italian) exam questions for bias-free
evaluation. The correct answer is randomized across option positions so models
cannot exploit answer-position leakage (the original dataset has the correct
answer at 'A' in ~91% of questions).

Output: data/ssm_questions_shuffled.json  (used for evaluation)
        data/shuffle_mapping.json         (original <-> shuffled position, for scoring)
"""
import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "ssm_questions_text_only.json"
OUT = BASE / "data" / "ssm_questions_shuffled.json"
MAP = BASE / "data" / "shuffle_mapping.json"

SEED = 42


def main():
    random.seed(SEED)
    with open(SRC, encoding="utf-8") as f:
        questions = json.load(f)

    shuffled = []
    mapping = {}

    for q in questions:
        options = list(q["options"])
        n = len(options)
        correct_orig = q["correct_answer"]["letter"]

        # Find index of the correct option
        correct_idx = next(
            (i for i, o in enumerate(options) if o["letter"] == correct_orig), 0
        )

        # Randomly permute option positions
        perm = list(range(n))
        random.shuffle(perm)

        # Reassign letter labels A..E to the new positions (so the correct
        # answer lands on a RANDOM letter, not its original one)
        letters = ["A", "B", "C", "D", "E", "F"][:n]
        new_options = []
        for new_idx, orig_idx in enumerate(perm):
            new_options.append({
                "letter": letters[new_idx],
                "text": options[orig_idx]["text"],
            })

        # New position of the correct answer = where the correct option text landed
        new_correct_idx = perm.index(correct_idx)
        new_correct_letter = new_options[new_correct_idx]["letter"]

        # Build the new question (question order also shuffled later)
        new_q = {
            "id": q["id"],
            "question": q["question"],
            "options": new_options,
            "correct_answer": {
                "letter": new_correct_letter,
                "index": new_correct_idx,
            },
            "specialty": q["specialty"],
            "has_image": q.get("has_image", False),
            "metadata": q.get("metadata", {}),
        }
        shuffled.append(new_q)
        mapping[q["id"]] = {
            "original_letter": correct_orig,
            "shuffled_letter": new_correct_letter,
            "permutation": perm,
        }

    # Also shuffle question order (so models don't see a fixed order)
    order = list(range(len(shuffled)))
    random.shuffle(order)
    shuffled_ordered = [shuffled[i] for i in order]

    # Write
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(shuffled_ordered, f, ensure_ascii=False, indent=2)
    with open(MAP, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    # Verify distribution
    letters = [q["correct_answer"]["letter"] for q in shuffled_ordered]
    from collections import Counter
    print(f"✓ Wrote {len(shuffled_ordered)} shuffled questions → {OUT}")
    print(f"✓ Wrote mapping → {MAP}")
    print(f"Correct-answer letter distribution (should be ~uniform): {dict(Counter(letters))}")
    print(f"Question order shuffled: yes (seed={SEED})")


if __name__ == "__main__":
    main()
