#!/usr/bin/env python3
"""
Extract Image Question Manifest for Medical AI Leaderboard

Scans the EuropeMedQA dataset and builds a manifest of every image-dependent
question. The manifest is the input for the vision-description pipeline
(scripts/generate_image_descriptions.py).

For each image question the manifest records:
  - exam, question_id, picture_link, picture_provided (as found in the CSV)
  - flags for data-quality problems (PDF "images", malformed links,
    duplicate links, link/provided mismatches)
  - whether the image file is available locally (data/images/<filename>)

No API calls are made. Safe to re-run (regenerates the manifest).

Usage:
    python3 scripts/extract_image_manifest.py
    python3 scripts/extract_image_manifest.py --csv data/europemedqa/EuropeMedQA.csv
"""

import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "europemedqa", "EuropeMedQA.csv")
DEFAULT_OUT = os.path.join(REPO_ROOT, "data", "image_questions_manifest.json")
DEFAULT_IMAGE_DIR = os.path.join(REPO_ROOT, "data", "images")

NA_VALUES = {"", "n/a", "na", "null", "-", "none", "no", "link"}
YES_VALUES = {"yes", "si", "sí", "true", "1", "y"}
KNOWN_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff"}


def _clean(value: str) -> str:
    return (value or "").strip()


def is_real_link(value: str) -> bool:
    return _clean(value).lower() not in NA_VALUES and _clean(value) != ""


def is_yes(value: str) -> bool:
    return _clean(value).lower() in YES_VALUES


def link_extension(link: str) -> str:
    base = link.split("?")[0]
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def resolve_local_image(link: str, image_dir: str) -> Optional[str]:
    """Images are expected in data/images/ (flat). Filenames are exam-prefixed
    (IT0006.PNG, ES13_1.png, FR_D02_03.png, PO175.png) so no per-exam subdirs needed."""
    candidate = os.path.join(image_dir, link)
    if os.path.isfile(candidate):
        return candidate
    # case-insensitive fallback (source data mixes .PNG/.png)
    if os.path.isdir(image_dir):
        for name in os.listdir(image_dir):
            if name.lower() == link.lower():
                return os.path.join(image_dir, name)
    return None


def main():
    parser = argparse.ArgumentParser(description="Build image-question manifest from EuropeMedQA")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to EuropeMedQA.csv")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output manifest path")
    parser.add_argument("--image-dir", default=DEFAULT_IMAGE_DIR, help="Directory to check for local image files")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        raise SystemExit(f"CSV not found: {args.csv}. Clone the dataset: git clone https://github.com/causius0/europemedqa data/europemedqa")

    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    questions = []
    link_use_count = Counter()

    # First pass: count duplicate links within each exam
    for row in rows:
        if is_real_link(row.get("picture_link")):
            key = (row["exam"], _clean(row["picture_link"]).lower())
            link_use_count[key] += 1

    for row in rows:
        exam = row["exam"]
        qid = row["questionID"]
        link = _clean(row.get("picture_link"))
        provided = _clean(row.get("picture_provided"))

        has_link = is_real_link(link)
        has_provided = is_yes(provided)

        # A question is an image candidate if either signal fires. Conflicts are flagged.
        if not has_link and not has_provided:
            continue

        flags = []
        if has_link and not has_provided:
            flags.append("link_but_not_marked_provided")
        if has_provided and not has_link:
            flags.append("marked_provided_but_no_link")
        if has_link:
            ext = link_extension(link)
            if ext == "pdf":
                flags.append("pdf_not_image")
            elif ext and ext not in KNOWN_IMAGE_EXTS:
                flags.append(f"malformed_ext:{ext}")
            elif not ext:
                flags.append("no_extension")
            if link_use_count[(exam, link.lower())] > 1:
                flags.append("duplicate_link")

        local_path = resolve_local_image(link, args.image_dir) if has_link else None

        questions.append({
            "exam": exam,
            "question_id": qid,
            "picture_link": link if has_link else None,
            "picture_provided_raw": provided,
            "flags": flags,
            "local_image": os.path.relpath(local_path, REPO_ROOT) if local_path else None,
        })

    # Flag rows whose link is a real image filename but which have no Drive
    # hyperlink in image_drive_links.json (hyperlink extraction missed them).
    links_path = os.path.join(REPO_ROOT, "data", "image_drive_links.json")
    if os.path.isfile(links_path):
        with open(links_path, encoding="utf-8") as f:
            drive_qids = {e["question_id"] for e in json.load(f)["entries"]}
        for q in questions:
            link = q.get("picture_link") or ""
            if (link and link_extension(link) in KNOWN_IMAGE_EXTS
                    and q["question_id"] not in drive_qids):
                q["flags"].append("no_drive_link")

    by_exam = Counter(q["exam"] for q in questions)
    available = sum(1 for q in questions if q["local_image"])
    clean = sum(1 for q in questions if not q["flags"])

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_csv": os.path.relpath(args.csv, REPO_ROOT),
        "image_dir": os.path.relpath(args.image_dir, REPO_ROOT),
        "summary": {
            "total_image_questions": len(questions),
            "by_exam": dict(by_exam),
            "with_local_image_available": available,
            "clean_records": clean,
            "with_flags": len(questions) - clean,
        },
        "questions": questions,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Manifest written to {args.out}")
    print(f"  total image questions : {len(questions)}")
    for exam, n in sorted(by_exam.items()):
        print(f"    {exam:<32} {n}")
    print(f"  local image available : {available}/{len(questions)}")
    print(f"  clean records         : {clean}/{len(questions)}")
    flag_counter = Counter(flag for q in questions for flag in q["flags"])
    if flag_counter:
        print("  flags:")
        for flag, n in flag_counter.most_common():
            print(f"    {flag:<36} {n}")


if __name__ == "__main__":
    main()
