# Image Descriptions Pipeline (Vision → Text Proxy)

**Status: COMPLETE (2026-10-02).** 502/502 descriptions generated with `google/gemini-2.5-flash` (image-only calls, exam-language output, 0 errors). Independently audited: extraction reproduced byte-for-byte from the XLSX, all 459 Drive files verified on disk, 8-image visual spot-check found zero factual mismatches, and the anti-leakage property was confirmed structurally and empirically (1 description verbatim-contains its correct option — flagged `description_reveals_option` on IT1113 in the enriched dataset).

## Purpose

The leaderboard's eval set (1,060 SSM text-only questions) excludes 60 SSM questions that depend on images, because text-only models cannot see them. This pipeline lets any text-only model attempt image questions: a **vision model drafts a text description of each image**, and that description is injected into the question at test time. The same enriched data can later add image questions for MIR, ECN and PNA (see data-quality notes).

## Design decisions

1. **Anti-leakage**: the vision model receives *only the image* — never the question text, options, or answer key. It cannot leak the correct answer into the description.
2. **Description language matches the exam language** (Italian for SSM, Spanish for MIR, French for ECN, Portuguese for PNA) so the downstream model sees one consistent language per question.
3. **Descriptions are cached and reusable** in `data/image_descriptions.json`, keyed by question id. Re-runs skip anything already described; failures are recorded and retryable.
4. **Cost-gated**: the generator does a dry run by default; API spend requires `--execute`.
5. **Attribution**: every description records the vision model and timestamp, so a description quality problem is traceable.

## Pipeline steps

```
EuropeMedQA.csv ──► extract_image_manifest.py ──► data/image_questions_manifest.json
                                                        │
data/images/*.png (you supply files)                    │
        └──────────► generate_image_descriptions.py ◄───┘   (OpenRouter vision, --execute)
                                │
                                ▼
                  data/image_descriptions.json  (cache, resumable)
                                │
        ssm_questions_with_solution.json
                                └──► build_enriched_dataset.py
                                        │
                                        ▼
                          data/ssm_questions_enriched.json  (PRIVATE, gitignored)
                                        │
                          prompt_builder.apply_image_descriptions()
                                        │
                                        ▼
                          eval pipeline (test-time injection)
```

### Step 1 — Manifest (already run)

```bash
python3 scripts/extract_image_manifest.py
```

Scans the CSV, records every image question with data-quality flags, and checks `data/images/` for the actual files. Result (after the manifest was fixed to ignore MIR's literal `"no"`/`"link"` junk link values): **622 image-question candidates**, of which **376 are clean records**. The XLSX hyperlinks (537 questions / 459 unique files) are the authoritative set; the CSV's link column adds only noise beyond that.

| Exam | Candidates | Notes |
|------|-----------|-------|
| MIR_Spain | 327 | Real image questions: 323 (all downloaded + described). 2 (ES0264/ES0265) reference `ES14_15.png` but have **no Drive hyperlink** — flagged `no_drive_link`, currently no image available. |
| ECN_France | 225 | 144 real links; **32 are PDFs, not images**; 3 double-name links (`FR1078.1 FR1078.2`) hard-skipped; 81 further ECN questions embed image references inside `question_text` only (no Drive link) — not describable by this pipeline. |
| SSM_Italy | 60 | Clean. Verified 1:1 against `ssm_questions_with_solution.json` (`has_image=true`). |
| PNA_Portugal | 10 | Clean. |

### Step 2 — Fetch image files (DONE for all exams, 2026-10-02)

The images are **not** in the `europemedqa` repo. Their URLs live as **Excel hyperlinks embedded on the `picture_link` cells of `EuropeMedQA.xlsx`** (the CSV export flattened them to bare filenames). Two scripts handle this:

```bash
# 1. extract question -> Drive URL mapping from the XLSX (done)
python3 scripts/extract_drive_links.py
#    -> data/image_drive_links.json : 537 hyperlinked questions, 459 unique Drive files
#       (SSM 60, MIR 323, ECN 144, PNA 10)

# 2. download into data/images/ (done; re-run any time for new files)
python3 scripts/download_images.py                 # all exams
python3 scripts/download_images.py --exam SSM_Q_ITA
```

The downloader dedupes by Drive file id, sniffs magic bytes (Drive error pages and PDFs are caught and reported in `data/image_download_report.json`), and is interrupt-safe. Note: the source sheet sometimes spells the same image's filename inconsistently (e.g. `IT063.png` vs `IT0063.png` for the same Drive file) — the downloader creates filename aliases so every question reference resolves. After downloading, re-run `extract_image_manifest.py` so availability is baked into the manifest.

Result: **all 60/60 SSM image questions resolve to local files.** `data/images/` is gitignored (exam images are copyright-sensitive). Filenames are case-insensitively matched (source data mixes `.PNG`/`.png`).

### Step 3 — Generate descriptions (DONE)

```bash
python3 scripts/generate_image_descriptions.py --exam SSM_Italy   # per-exam
python3 scripts/generate_image_descriptions.py                    # all
```

502 ok / 0 errors (SSM 60, MIR 323, ECN 109, PNA 10; 455 unique images, shared images described once and reused). Entries record `finish_reason` and the token cap; 12 chart-heavy descriptions that hit the original 600-token cap were re-generated at 1200 (`--retry-truncated` targets only truncated entries — successes are never re-billed). Non-image payloads (PDFs, malformed links) are always skipped. The cache is written atomically after every question, so an interrupted run loses nothing.

### Step 4 — Build the enriched dataset

```bash
python3 scripts/build_enriched_dataset.py
```

Merges the cache into the SSM dataset → `data/ssm_questions_enriched.json`. Every image question either carries `image_description` (+ model + timestamp) or is explicitly marked `image_description_missing: true` so nothing silently drops. **The output contains correct answers and is gitignored.**

### Step 5 — Test-time injection

`scripts/prompt_builder.py` now exposes:

```python
from prompt_builder import apply_image_descriptions

questions = json.load(open("data/ssm_questions_enriched.json"))
questions = apply_image_descriptions(questions)   # appends "[Descrizione dell'immagine: ...]" to matching stems
```

Labels are localized per exam language (stamped in step 4). Questions without descriptions pass through untouched, so the same code path serves both the 1,060 text-only set and any image-augmented run.

## Evaluation implications

- The standard leaderboard run remains the **1,060 text-only questions** — untouched, comparable to all existing results.
- The enriched set enables a **separate "image-augmented" track**: the 60 SSM image questions answered *with* descriptions. Report it as its own column; never mix it into the text-only accuracy.
- Expect the vision proxy to add noise: a description is a lossy, model-dependent rendering of the image. Compare a strong vision model answering the raw images directly (upper bound) against text-only models answering descriptions (proxy) when interpreting results.

## Data-quality caveats carried in the manifest

- `duplicate_link` — same filename on multiple questions (mostly MIR): the link column there looks shifted; verify against the source XLSX sheet before trusting any MIR image.
- `pdf_not_image` — ECN "images" that are PDFs; either convert pages to PNG or exclude.
- `link_but_not_marked_provided` / `marked_provided_but_no_link` — the two source signals disagree; manifest keeps both so you can choose a policy per exam.

## Cost estimate (SSM 60, default model)

60 images × (~1,500 image tokens + ~300 text tokens in, ~200 tokens out) — a few cents on a flash-class model. Even the full clean set (376) stays well under a dollar.
