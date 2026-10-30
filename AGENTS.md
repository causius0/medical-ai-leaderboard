# AGENTS.md — Expanded Exam Corpus (added Oct 2026)

Working guide for the 2023–2026 exam corpus **beyond** the original SSM
benchmark. The SSM leaderboard, DB conventions, LoRA experiment and security
rules are documented in `CLAUDE.md` — read that first; everything below
extends it, nothing replaces it.

## What this corpus is

58 exams / **7,812 questions** downloaded and parsed in Oct 2026, none of
which exist in `data/europemedqa/` (upstream repo `causius0/europemedqa` is
frozen at commit 155a342 — don't re-clone expecting updates):

| family | exams | questions | keys |
|---|---|---|---|
| ssm_italy 2025 + 2026 | 2 | 280 | official MUR paper — correct answer is **always A** (position leak, must shuffle before eval) |
| mir_spain 2025 + 2026 | 2 | 420 | official plantillas; 4 options; 7 annulled in 2026 (13,50,64,139,142,161,208) |
| edn_france 2023–2025 | 3 | 962 | **NO keys exist** (CNG publishes questions only); mixed types: QCM, QRP (multi-answer, A–E kept), QROC/QZP (no choices), TCS (Likert A–E); 143 rows legitimately have no options |
| pna_portugal 2025 | 1 | 150 | official chave (Prova A) |
| pes_poland 2018–2022 | 50 | 6,000 | official CEM klucz; 5 specialties × 10 sessions (wiosna/jesien), 120 Q each, Polish language |

PES caveats: 2021–2022 sessions are OCR'd scans (text noise; ~44 rows lost
all options to OCR — stems and keys preserved). Three scanned 2022 papers
(psychiatria jesien, choroby wewnetrzne wiosna, medycyna rodzinna jesien)
**print the same question number on two different questions** — the second
occurrence gets an `_b` id suffix (e.g. `..._q066_b`). Don't "fix" this; it
reflects the source papers.

## Pipeline (how the data flows)

```
data/processed_csv/*.csv   (delivered parse; correct_answer column)
        │  python3 scripts/convert_processed_csvs.py
        ▼
data/new_exams/*.json      (canonical schema, same shape as
        │                   ssm_questions_with_solution.json)
        │  .venv/bin/python scripts/db_load.py --load-exams
        ▼
medbench.exam_questions    (queryable corpus: options JSONB,
                            correct_letter, language, country, provenance)
```

- `--load-exams` is idempotent (upsert on question_id). `--exam-stats`
  prints per-family reconciliation — after any reload it must show exactly
  7,812 questions / 6,810 keyed / 40 annulled / 58 exams.
- ID conventions: SSM uses the printed codice (`ssm2025861`), EDN/PES are
  constructed (`<exam_id>_qNNN`), MIR/PNA have no source codes.
- Specialty labels exist only for PES (English: Pediatrics, Internal
  Medicine, General Surgery, Psychiatry, Family Medicine — 1,200 each);
  all other families have `specialty = NULL`.

## Verification (how to check the keys)

1. **Structural**: rerun the converter — it asserts totals, key-in-options,
   and global ID uniqueness. Any change to `processed_csv/` must pass it.
2. **Statistical**: key-letter distribution per family should be roughly
   balanced (MIR/PNA/PES are 15–32%); per-exam, no letter >40% — the ONLY
   sanctioned exception is SSM 2025/26 at 100% A. A new exam violating this
   means a misparsed/misaligned key.
3. **End-to-end** (not yet wired): run a known-strength model on a sample;
   SSM-band accuracy (~80%+ for qwen3:8b) confirms alignment, chance-level
   means broken keys. Requires shuffling SSM first and extending
   `run_evaluation.py` past its SSM-only hardcode.

## Status / known limits (as of 2026-10-30)

- **Raw source PDFs are NOT in the repo** — only the parsed CSVs + extracted
  images. They live in the download agent's VM (`~/workspace/pes_parse/`
  there, incl. hand-transcribed PES key JSONs). Re-delivery of
  `data/updates_raw/` would enable byte-level key spot-checks; until then
  verification rests on levels 1–2 above.
- `data/processed_csv/SUMMARY.md` (trackable, no keys) is the parse provenance
  record — read its "Issues" section before trusting any individual exam.
- EDN cannot be scored until keys are sourced (they exist only inside
  login-gated prep platforms: edn.chat, refoua.fr, oreille-externe.fr).
- Not yet integrated into any leaderboard scale — `exam_questions` is a
  corpus, not a run. SSM 2025/26 need `shuffle_answers.py`-style
  randomization + a canonical shuffled set before first eval.
- Future drops to watch: PNA 2026 (held 25 Nov 2026), EDN 2026 annales
  (session ~mid-Oct 2026), SSM 2027 (July 2027), PES jesien 2026 (CEM
  publishes questions + answers ~7 days per session, spring 2023 onward).

## Git discipline (extends CLAUDE.md security rules)

`data/processed_csv/**` and `data/new_exams/**` are gitignored (they carry
answer keys); only the three provenance docs are trackable:
`data/processed_csv/SUMMARY.md`, `build_edn_csvs.py`,
`edn_france_build_issues.log`. Images under `data/processed_csv/images/` are
exam-copyright material — same rule as `data/images/`. Never commit or
redistribute.
