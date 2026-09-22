#!/usr/bin/env python3
"""
PRIDE-style shuffled variants for bias-free SSM evaluation.

Reflects Zheng et al., "Large Language Models are Not Robust Multiple Choice
Selectors" (arXiv:2309.03882). The two ideas this machinery adopts:

  1. Randomize golden-answer placement across option positions, so models cannot
     exploit answer-position leakage (the original dataset has the correct answer
     at 'A' in ~91% of questions). This is the paper's premise that golden answers
     should be "randomly placed" for a valid selection-bias measurement.

  2. Generate SEVERAL independent option-permutation variants per question, so
     selection bias can be *measured* (recall balance across option IDs, the
     paper's Sec. 2.2 metric) and averaged out rather than relying on a single
     fixed shuffle. A model that games one fixed order cannot game all variants.

Variant 0 uses seed 42 and reproduces the letter mapping of the originally
committed shuffled set (verified 1060/1060), so existing results stay valid.
Each additional variant uses a distinct seed.

Outputs:
  data/ssm_questions_shuffled.json        variant 0 (canonical, backward-compatible)
  data/shuffle_mapping.json               variant 0 original <-> shuffled mapping
  data/ssm_questions_shuffled_v{N}.json   variant N (N >= 1)
  data/shuffle_mapping_v{N}.json          variant N mapping
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "ssm_questions_text_only.json"
OUT = BASE / "data" / "ssm_questions_shuffled.json"
MAP = BASE / "data" / "shuffle_mapping.json"

BASE_SEED = 42
LETTERS = "ABCDEF"


def build_variant(questions, seed):
    """Return (shuffled_questions, mapping) for one option-permutation variant.

    The correct answer is placed at a random letter, and the question order is
    also randomized. Deterministic given `seed`.
    """
    rng = random.Random(seed)

    shuffled = []
    mapping = {}

    for q in questions:
        options = list(q["options"])
        n = len(options)
        correct_orig = q["correct_answer"]["letter"]

        correct_idx = next(
            (i for i, o in enumerate(options) if o["letter"] == correct_orig), 0
        )

        perm = list(range(n))
        rng.shuffle(perm)

        letters = LETTERS[:n]
        new_options = []
        for new_idx, orig_idx in enumerate(perm):
            new_options.append({
                "letter": letters[new_idx],
                "text": options[orig_idx]["text"],
            })

        new_correct_idx = perm.index(correct_idx)
        new_correct_letter = new_options[new_correct_idx]["letter"]

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

    # Also randomize question order (so models don't see a fixed sequence)
    order = list(range(len(shuffled)))
    rng.shuffle(order)
    shuffled_ordered = [shuffled[i] for i in order]

    return shuffled_ordered, mapping


def write_variant(questions, mapping, out_path, map_path, seed, label):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    letters = [q["correct_answer"]["letter"] for q in questions]
    print(f"✓ {label}: wrote {len(questions)} questions -> {out_path}")
    print(f"✓ {label}: wrote mapping -> {map_path}")
    print(f"  correct-answer letter distribution (should be ~uniform): {dict(Counter(letters))}")
    print(f"  question order shuffled: yes (seed={seed})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--variants", type=int, default=3,
        help="number of independent shuffled variants to generate (default 3; variant 0 = seed 42)",
    )
    args = ap.parse_args()

    with open(SRC, encoding="utf-8") as f:
        questions = json.load(f)

    for v in range(args.variants):
        seed = BASE_SEED + v
        shuffled, mapping = build_variant(questions, seed)
        if v == 0:
            out_path, map_path, label = OUT, MAP, "variant 0"
        else:
            out_path = BASE / "data" / f"ssm_questions_shuffled_v{v}.json"
            map_path = BASE / "data" / f"shuffle_mapping_v{v}.json"
            label = f"variant {v}"
        write_variant(shuffled, mapping, out_path, map_path, seed, label)


if __name__ == "__main__":
    main()