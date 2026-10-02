#!/usr/bin/env python3
"""
Extract Google Drive Image Links from EuropeMedQA.xlsx

The CSV export flattened the picture_link column to bare filenames
(IT0006.PNG, ...). The actual image URLs live as Excel HYPERLINKS on those
cells. This script reads the XLSX and emits data/image_drive_links.json
mapping every hyperlinked question to its Drive URL + file id.

No network calls. Safe to re-run.

Usage:
    python3 scripts/extract_drive_links.py
"""

import argparse
import json
import os
import re
from datetime import datetime
from typing import Optional

import openpyxl
from openpyxl.utils import get_column_letter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XLSX = os.path.join(REPO_ROOT, "data", "europemedqa", "EuropeMedQA.xlsx")
DEFAULT_OUT = os.path.join(REPO_ROOT, "data", "image_drive_links.json")

DRIVE_RE = re.compile(r"/file/d/([A-Za-z0-9_-]{10,})")


def find_column(header: dict, *candidates: str) -> Optional[str]:
    for col, value in header.items():
        v = (value or "").strip().lower().replace(" ", "_")
        if v in candidates:
            return col
    return None


def main():
    parser = argparse.ArgumentParser(description="Extract Drive hyperlinks for images from the XLSX")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, read_only=False, data_only=True)
    entries = []
    seen_ids = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows())
        if not rows:
            continue
        header = {get_column_letter(c.column): c.value for c in rows[0]}
        qid_col = find_column(header, "questionid", "question_id", "id")
        link_col = find_column(header, "picture_link", "picturelink")
        if not link_col:
            continue

        for row in rows[1:]:
            cells = {get_column_letter(c.column): c for c in row}
            link_cell = cells.get(link_col)
            if link_cell is None or not link_cell.hyperlink or not link_cell.hyperlink.target:
                continue
            url = link_cell.hyperlink.target
            m = DRIVE_RE.search(url)
            if not m:
                continue
            qid = cells[qid_col].value if qid_col else None
            entries.append({
                "exam": sheet_name,
                "sheet_row": link_cell.row,
                "question_id": str(qid) if qid is not None else None,
                "filename": (link_cell.value or "").strip(),
                "drive_url": url,
                "drive_file_id": m.group(1),
            })
            seen_ids[m.group(1)] = seen_ids.get(m.group(1), 0) + 1

    by_exam = {}
    for e in entries:
        by_exam[e["exam"]] = by_exam.get(e["exam"], 0) + 1
    missing_qid = sum(1 for e in entries if not e["question_id"])

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_xlsx": os.path.relpath(args.xlsx, REPO_ROOT),
        "summary": {
            "hyperlinked_questions": len(entries),
            "unique_drive_files": len(seen_ids),
            "missing_question_id": missing_qid,
            "by_exam": by_exam,
        },
        "entries": entries,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.out}")
    print(f"  hyperlinked questions : {len(entries)}")
    print(f"  unique drive files    : {len(seen_ids)}")
    for exam, n in sorted(by_exam.items()):
        print(f"    {exam:<32} {n}")
    if missing_qid:
        print(f"  WARNING: {missing_qid} entries have no question id (check sheet headers)")


if __name__ == "__main__":
    main()
