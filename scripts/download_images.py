#!/usr/bin/env python3
"""
Download Exam Images from Google Drive

Downloads every unique Drive file referenced in data/image_drive_links.json
(embedded hyperlinks in EuropeMedQA.xlsx) into data/images/, named by the
picture_link filename from the source sheet. These filenames are what the
manifest and description pipeline expect.

Notes
- Files are deduplicated by Drive file id; each file is fetched once.
- Content magic bytes are sniffed; non-image payloads (Drive error pages,
  PDFs) are recorded in the report. PDFs are saved as <name>.pdf and flagged.
- Existing valid files are skipped; use --force to re-download.
- Interrupt-safe: the report is written after every file.

Usage:
    python3 scripts/download_images.py                 # all exams
    python3 scripts/download_images.py --exam SSM_Q_ITA
    python3 scripts/download_images.py --force --exam SSM_Q_ITA
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LINKS = os.path.join(REPO_ROOT, "data", "image_drive_links.json")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "images")
DEFAULT_REPORT = os.path.join(REPO_ROOT, "data", "image_download_report.json")

DOWNLOAD_URL = "https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"

MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF8", "gif"),
    (b"BM", "bmp"),
    (b"%PDF", "pdf"),
]


def sniff(data: bytes) -> str:
    for prefix, kind in MAGIC:
        if data.startswith(prefix):
            return kind
    if data.lstrip()[:1] == b"<" or b"<html" in data[:512].lower():
        return "html"
    return "unknown"


def download_one(fid: str, timeout: float = 60.0) -> dict:
    url = DOWNLOAD_URL.format(fid=fid)
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return {"data": resp.content, "status_code": resp.status_code}


def save_json_atomic(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description="Download exam images from Google Drive")
    parser.add_argument("--links", default=DEFAULT_LINKS)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--exam", action="append", help="Restrict to sheet name(s), e.g. --exam SSM_Q_ITA")
    parser.add_argument("--force", action="store_true", help="Re-download even if the file exists")
    parser.add_argument("--sleep", type=float, default=0.3, help="Seconds between downloads")
    args = parser.parse_args()

    if not os.path.isfile(args.links):
        raise SystemExit(f"Links file not found: {args.links}. Run scripts/extract_drive_links.py first.")
    with open(args.links, encoding="utf-8") as f:
        links = json.load(f)

    entries = links["entries"]
    if args.exam:
        entries = [e for e in entries if e["exam"] in args.exam]

    # filename -> drive id (verified 1:1 upstream); dedupe files by drive id.
    # One Drive file can be referenced under several filename spellings in the
    # source sheet (e.g. IT063.png vs IT0063.png); collect every variant so an
    # alias can be created for each after download.
    by_file_id = {}
    names_for_id = {}
    for e in entries:
        fid = e["drive_file_id"]
        by_file_id[fid] = e["filename"]
        variants = names_for_id.setdefault(fid, [])
        if e["filename"].lower() not in [v.lower() for v in variants]:
            variants.append(e["filename"])
    filename_for = {fid: variants[0] for fid, variants in names_for_id.items()}

    report = {}
    if os.path.isfile(args.report):
        with open(args.report, encoding="utf-8") as f:
            report = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    # case-insensitive filename map of what is already on disk
    existing = {}
    if os.path.isdir(args.out_dir):
        for name in os.listdir(args.out_dir):
            existing[name.lower()] = name

    def existing_ok(filename: str, fid: str = None) -> bool:
        name = existing.get(filename.lower())
        if not name:
            return False
        path = os.path.join(args.out_dir, name)
        with open(path, "rb") as fh:
            kind = sniff(fh.read(16))
        if kind in ("png", "jpeg", "gif", "bmp"):
            return True
        # non-image payloads (e.g. the ECN PDFs) count as done when the report
        # recorded them, so they are not re-downloaded on every run
        if kind == "pdf" and fid and report.get(fid, {}).get("status") == "not_image":
            return True
        return False

    # Alias pre-pass: files downloaded in earlier runs may be referenced under
    # other filename spellings; create those aliases before computing the todo list.
    aliases_made = 0
    for fid, variants in names_for_id.items():
        if not existing_ok(variants[0]):
            continue
        primary_path = os.path.join(args.out_dir, existing[variants[0].lower()])
        with open(primary_path, "rb") as fh:
            data = fh.read()
        for variant in variants[1:]:
            if variant.lower() not in existing:
                with open(os.path.join(args.out_dir, variant), "wb") as fh:
                    fh.write(data)
                existing[variant.lower()] = variant
                aliases_made += 1
    if aliases_made:
        print(f"Created {aliases_made} filename alias(es) for already-downloaded files")

    todo = [fid for fid, fn in filename_for.items()
            if args.force or not existing_ok(fn, fid)]
    exam_scope = ", ".join(args.exam) if args.exam else "all"
    print(f"Scope: {exam_scope} | unique files: {len(filename_for)} | to download: {len(todo)}")

    ok = failed = skipped_type = 0
    for i, fid in enumerate(todo, 1):
        filename = filename_for[fid]
        try:
            result = download_one(fid)
            data = result["data"]
            kind = sniff(data)
            if kind == "html":
                raise RuntimeError("got HTML page (permission/consent wall?), not a file")
            out_name = filename
            if kind == "pdf" and not out_name.lower().endswith(".pdf"):
                out_name += ".pdf"
            path = os.path.join(args.out_dir, out_name)
            with open(path, "wb") as fh:
                fh.write(data)
            existing[out_name.lower()] = out_name
            # alias every other filename spelling of this Drive file
            for variant in names_for_id[fid]:
                if variant.lower() not in existing:
                    alias_path = os.path.join(args.out_dir, variant)
                    with open(alias_path, "wb") as fh:
                        fh.write(data)
                    existing[variant.lower()] = variant
            report[fid] = {
                "filename": out_name,
                "sniffed_type": kind,
                "bytes": len(data),
                "status": "ok" if kind in ("png", "jpeg", "gif", "bmp") else "not_image",
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
            }
            if kind in ("png", "jpeg", "gif", "bmp"):
                ok += 1
            else:
                skipped_type += 1
        except Exception as e:
            report[fid] = {
                "filename": filename,
                "status": "error",
                "error": str(e),
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
            }
            failed += 1
            print(f"[{i}/{len(todo)}] {filename} FAILED: {e}")

        if i % 20 == 0 or i == len(todo):
            print(f"[{i}/{len(todo)}] ok={ok} not_image={skipped_type} failed={failed}")
            save_json_atomic(args.report, report)
        time.sleep(args.sleep)

    save_json_atomic(args.report, report)
    print(f"\nDone. images={ok} not_image={skipped_type} failed={failed}")
    print(f"Report: {args.report}")
    if failed or skipped_type:
        print("Re-run with --force to retry failures (after checking Drive permissions).")


if __name__ == "__main__":
    main()
