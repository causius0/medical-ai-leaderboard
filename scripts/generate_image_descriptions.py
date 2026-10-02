#!/usr/bin/env python3
"""
Generate Image Descriptions via a Vision Model (OpenRouter)

For every image question in the manifest (data/image_questions_manifest.json)
that has a locally available image, send ONLY the image to a vision model and
ask for an objective description. The description is cached in
data/image_descriptions.json and later merged into the question datasets by
scripts/build_enriched_dataset.py.

ANTI-LEAKAGE DESIGN: the vision model sees the image alone — never the question
text, options, or answer. It cannot leak the correct answer into the
description.

By default this script does a DRY RUN (plans and reports only). API calls
cost money and require --execute.

Usage:
    # Plan only (default): shows what would be described and rough cost
    python3 scripts/generate_image_descriptions.py

    # Describe the 60 SSM images (the leaderboard eval set)
    python3 scripts/generate_image_descriptions.py --exam SSM_Italy --execute

    # Use a specific model, retry previous failures
    python3 scripts/generate_image_descriptions.py --execute --model google/gemini-2.5-flash --retry-failed
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openrouter_client import OpenRouterClient
from extract_image_manifest import resolve_local_image

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(REPO_ROOT, "data", "image_questions_manifest.json")
DEFAULT_CACHE = os.path.join(REPO_ROOT, "data", "image_descriptions.json")
DEFAULT_MODEL = "google/gemini-2.5-flash"

# Description language matches the exam language so the downstream model sees
# one consistent language per question.
EXAM_LANGUAGE = {
    "SSM_Italy": "Italian",
    "Abilitazione_Italy_clinical": "Italian",
    "Abilitazione_Italy_preclinical": "Italian",
    "MIR_Spain": "Spanish",
    "ECN_France": "French",
    "PNA_Portugal": "Portuguese",
}

DESCRIPTION_PROMPT = """You are describing a medical image for a medical examination context. Describe ONLY what is visibly present in the image. Include:
- Image type/modality (e.g. ECG trace, chest X-ray, dermatology photo, chart/table, diagram, endoscopy view)
- Anatomical region or body system shown
- Key visible findings: abnormalities, measurements, tracing patterns, colors, lesions, devices
- Any text, labels, numbers, calibration marks, or captions visible in the image (transcribe them)
- Layout if multiple panels are present

Rules:
- Be factual and precise; do not speculate about a diagnosis beyond what is directly visible
- Do not invent details you cannot see
- If the image quality is poor, say so
- Write the description in {language}
- Keep it under 200 words"""


def load_env():
    env_file = os.path.join(REPO_ROOT, ".env")
    if os.path.isfile(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def image_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def save_json_atomic(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description="Draft image descriptions with a vision model (OpenRouter)")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", default=DEFAULT_CACHE)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Vision model id on OpenRouter")
    parser.add_argument("--exam", action="append", help="Restrict to one exam (repeatable), e.g. --exam SSM_Italy")
    parser.add_argument("--only-clean", action="store_true",
                        help="Skip records flagged for data-quality issues (duplicates, PDFs, malformed links)")
    parser.add_argument("--limit", type=int, help="Max images to describe this run")
    parser.add_argument("--execute", action="store_true",
                        help="Actually call the API (default: dry run)")
    parser.add_argument("--retry-failed", action="store_true", help="Re-attempt questions that previously errored")
    parser.add_argument("--retry-truncated", action="store_true",
                        help="Re-attempt ok entries that hit the max-token cap (finish_reason=length)")
    parser.add_argument("--qid", action="append", help="Restrict to specific question id(s), repeatable")
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--sleep", type=float, default=0.5, help="Seconds between API calls")
    args = parser.parse_args()

    load_env()

    if not os.path.isfile(args.manifest):
        raise SystemExit(f"Manifest not found: {args.manifest}. Run scripts/extract_image_manifest.py first.")

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)

    cache = {}
    if os.path.isfile(args.cache):
        with open(args.cache, encoding="utf-8") as f:
            cache = json.load(f)

    # Select work items. Image availability is checked live (files may have been
    # added after the manifest was generated).
    image_dir = os.path.join(REPO_ROOT, "data", "images")
    todo = []
    for q in manifest["questions"]:
        if args.exam and q["exam"] not in args.exam:
            continue
        if args.qid and q["question_id"] not in args.qid:
            continue
        if args.only_clean and q["flags"]:
            continue
        if not q.get("picture_link"):
            continue
        if not q.get("local_image"):
            q["local_image"] = resolve_local_image(q["picture_link"], image_dir)
            if not q["local_image"]:
                continue
        if q["flags"]:
            # hard skip for non-image payloads regardless of --only-clean
            if any(f.startswith("pdf_not_image") or f.startswith("malformed_ext") for f in q["flags"]):
                continue
        prior = cache.get(q["question_id"])
        was_truncated = bool(prior) and prior.get("status") == "ok" and (
            prior.get("finish_reason") == "length"
            or (not prior.get("finish_reason")
                and (prior.get("completion_tokens") or 0) >= (prior.get("max_tokens") or 600))
        )
        if prior and prior.get("status") == "ok" and not (args.retry_truncated and was_truncated):
            continue  # never re-bill successes unless explicitly targeted
        if prior and prior.get("status") == "error" and not (args.retry_failed or args.retry_truncated):
            continue
        todo.append(q)

    if args.limit:
        todo = todo[: args.limit]

    total_in_manifest = manifest["summary"]["total_image_questions"]
    with_image = sum(
        1 for q in manifest["questions"]
        if q.get("local_image") or (q.get("picture_link") and resolve_local_image(q["picture_link"], image_dir))
    )
    print(f"Manifest: {total_in_manifest} image questions, {with_image} with local image file available")
    print(f"To describe now: {len(todo)}" + (f"  (exams: {', '.join(args.exam)})" if args.exam else ""))
    if not todo:
        print("Nothing to do. Place image files in data/images/ (filenames from picture_link) and re-run.")
        return

    if not args.execute:
        print("\nDRY RUN (no API calls). Add --execute to generate descriptions.")
        print(f"Model: {args.model}")
        for q in todo[:10]:
            print(f"  would describe: {q['question_id']}  {q['picture_link']}  [{q['exam']}]")
        if len(todo) > 10:
            print(f"  ... and {len(todo) - 10} more")
        return

    client = OpenRouterClient()
    ok = 0
    failed = 0
    reused = 0
    # Multiple questions can reference the same image file; describe each
    # unique image once per run and reuse the description for its siblings.
    memo = {}  # picture_link (lower) -> cache entry with status ok
    for i, q in enumerate(todo, 1):
        qid = q["question_id"]
        image_path = os.path.join(REPO_ROOT, q["local_image"])
        language = EXAM_LANGUAGE.get(q["exam"], "English")
        memo_key = (q.get("picture_link") or "").lower()
        if memo_key in memo:
            cache[qid] = dict(memo[memo_key])
            ok += 1
            reused += 1
            print(f"[{i}/{len(todo)}] {qid} ({q['exam']}) ... ok (shared image, reused)")
            continue
        content = [
            {"type": "text", "text": DESCRIPTION_PROMPT.format(language=language)},
            {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
        ]
        print(f"[{i}/{len(todo)}] {qid} ({q['exam']}) ...", end=" ", flush=True)
        try:
            response = client.call_model(
                model=args.model,
                messages=[{"role": "user", "content": content}],
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
            description = response["choices"][0]["message"]["content"].strip()
            usage = response.get("usage", {})
            cache[qid] = {
                "exam": q["exam"],
                "image_ref": q["picture_link"],
                "model": args.model,
                "language": language,
                "status": "ok",
                "description": description,
                "finish_reason": response["choices"][0].get("finish_reason"),
                "max_tokens": args.max_tokens,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            ok += 1
            memo[memo_key] = cache[qid]
            print("ok")
        except Exception as e:
            cache[qid] = {
                "exam": q["exam"],
                "image_ref": q["picture_link"],
                "model": args.model,
                "language": language,
                "status": "error",
                "error": str(e),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            failed += 1
            print(f"FAILED: {e}")

        # persist after every question so a crash loses nothing (atomic replace)
        save_json_atomic(args.cache, cache)
        time.sleep(args.sleep)

    print(f"\nDone. described={ok} (of which reused={reused}, unique api calls={ok - reused}) failed={failed} cache={args.cache}")
    total_prompt = sum(v.get("prompt_tokens") or 0 for v in cache.values() if v.get("status") == "ok")
    total_completion = sum(v.get("completion_tokens") or 0 for v in cache.values() if v.get("status") == "ok")
    print(f"Token totals in cache: prompt={total_prompt} completion={total_completion}")
    print("Next: python3 scripts/build_enriched_dataset.py")


if __name__ == "__main__":
    main()
