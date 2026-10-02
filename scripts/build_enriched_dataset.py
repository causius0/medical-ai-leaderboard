#!/usr/bin/env python3
"""
Build Enriched Dataset with Image Descriptions

Merges vision-model image descriptions (data/image_descriptions.json) into a
question dataset, producing a new file where image questions carry:
  - image_description          the vision model's description text
  - image_description_model    which vision model produced it
  - image_description_label    localized label for prompt injection
  - image_description_missing  true when no description is available

The output file contains correct answers, so it is PRIVATE (add to .gitignore
alongside ssm_questions_with_solution.json). Public no-solution variants are
generated later by the normal publish flow.

No API calls are made. Safe to re-run.

Usage:
    python3 scripts/build_enriched_dataset.py
    python3 scripts/build_enriched_dataset.py \
        --dataset data/ssm_questions_with_solution.json \
        --descriptions data/image_descriptions.json \
        --out data/ssm_questions_enriched.json
"""

import argparse
import json
import os
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Localized label injected into prompts, per exam language
EXAM_LABEL = {
    "Italian": "Descrizione dell'immagine",
    "Spanish": "Descripción de la imagen",
    "French": "Description de l'image",
    "Portuguese": "Descrição da imagem",
    "English": "Image description",
}


def main():
    parser = argparse.ArgumentParser(description="Merge image descriptions into a question dataset")
    parser.add_argument("--dataset", default=os.path.join(REPO_ROOT, "data", "ssm_questions_with_solution.json"))
    parser.add_argument("--descriptions", default=os.path.join(REPO_ROOT, "data", "image_descriptions.json"))
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "data", "ssm_questions_enriched.json"))
    args = parser.parse_args()

    with open(args.dataset, encoding="utf-8") as f:
        questions = json.load(f)

    descriptions = {}
    if os.path.isfile(args.descriptions):
        with open(args.descriptions, encoding="utf-8") as f:
            descriptions = json.load(f)
    else:
        print(f"Warning: descriptions cache not found ({args.descriptions}); "
              f"all image questions will be marked missing.")

    enriched = 0
    missing = 0
    not_image = 0
    leaks = 0
    for q in questions:
        if not q.get("has_image"):
            not_image += 1
            continue
        entry = descriptions.get(q["id"])
        if entry and entry.get("status") == "ok":
            q["image_description"] = entry["description"]
            q["image_description_model"] = entry.get("model")
            q["image_description_label"] = EXAM_LABEL.get(entry.get("language"), EXAM_LABEL["English"])
            q["image_description_generated_at"] = entry.get("generated_at")
            enriched += 1
            # leakage sanity check: a description that contains an option's text
            # verbatim makes that question near-free for text-only models
            desc_lower = entry["description"].lower()
            for opt in q.get("options", []):
                text = (opt.get("text") or "").strip()
                if len(text) >= 12 and text.lower() in desc_lower:
                    q["description_reveals_option"] = True
                    leaks += 1
                    break
        else:
            q["image_description_missing"] = True
            missing += 1

    header_comment = {
        "_enriched_at": datetime.now().isoformat(timespec="seconds"),
        "_source_dataset": os.path.relpath(args.dataset, REPO_ROOT),
        "_descriptions_cache": os.path.relpath(args.descriptions, REPO_ROOT),
        "_counts": {
            "total": len(questions),
            "not_image": not_image,
            "image_with_description": enriched,
            "image_missing_description": missing,
        },
    }
    output = [header_comment] + questions

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Enriched dataset written to {args.out}")
    print(f"  total questions            : {len(questions)}")
    print(f"  not image questions        : {not_image}")
    print(f"  image, with description    : {enriched}")
    print(f"  image, MISSING description : {missing}")
    print(f"  description reveals option : {leaks} (flagged via description_reveals_option)")
    if missing:
        print("  -> run scripts/generate_image_descriptions.py again after adding missing images")


if __name__ == "__main__":
    main()
