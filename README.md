# Medical AI Leaderboard

Benchmarking local LLMs on real European medical residency exams. The canonical
leaderboard lives in a local **Postgres database (`medbench`)**; models are
evaluated locally with **MLX** on Apple Silicon.

Companion repos: [europemedqa](https://github.com/causius0/europemedqa) — the
12,340-question multilingual dataset (IT/ES/FR/PT) that powers both evaluation
and LoRA training.

## What is being measured

- **Eval set**: 1,060 text-only questions from the Italian SSM exam
  (2017–2024), with answer positions **shuffled to uniform A–E** so scores are
  not confounded by position priors (the original exam is 91% "A").
- **Harness**: single-question, greedy decoding, Italian chat prompt, letter
  answer. Reasoning models are scored on the text after `</think>` only.
- **Token budget is part of the score.** A reasoning model given too few
  tokens refuses by truncation — see the cautionary tale in
  `docs/TRAINING_PLAN.md`: LFM2.5-8B-A1B scored 23.21% at a 256-token budget
  and 72.64% on a 1024/2048/4096 budget ladder. Every run records its budget
  in `shuffled_runs.notes`.

## Current leaderboard (medbench.shuffled_runs)

| Model | Accuracy | Budget |
|---|---|---|
| qwen3:8b (thinking) | 88.96% | 256 |
| gemma3:12b | 81.60% | 256 |
| qwen3:8b | 79.34% | 256 |
| LFM2.5-8B-A1B 4-bit | 72.64% | 1024→4096 ladder |
| llama3.1:8b | 68.96% | 256 |
| LFM2-24B-A2B 4-bit | 60.38% | 8 (non-thinking) |
| mistral:7b | 54.62% | 256 |

## How to run an evaluation

```bash
# 1. (once) canonical eval set, reconstructed from the DB's pinned letters
python3 scripts/build_pg_shuffle.py

# 2. answer the 1,060 questions with a local model
.venv/bin/python scripts/run_local_baseline.py \
    --model models/LFM2.5-8B-A1B-4bit \
    --questions data/ssm_questions_text_only_shuffled_no_answers.json \
    --tag my_run --max-tokens 1024        # raise budget for thinking models

# 3. score + publish to the leaderboard
.venv/bin/python scripts/evaluate_ssm_results.py \
    results/local/<model>_<tag>.json data/ssm_questions_text_only_shuffled.json
python3 scripts/publish_to_medbench.py results/local/<model>_<tag>.json \
    --param-size 8B-A1B --notes-extra "anything that matters"
```

Runs are resumeable (answered questions are skipped) and every publish
records model repo, quantization, budget, and parse rate alongside the score.

## LoRA fine-tuning project

Can LoRA teach LFM2.5-8B to answer directly (no reasoning spiral) at an
8-token budget, matching its own thinking-mode ceiling? Staged plan with
review gates and decision rules: **[docs/TRAINING_PLAN.md](docs/TRAINING_PLAN.md)**.
Training data (9,401 examples, contamination-guarded, position-balanced):
**[docs/LoRA_DATA_PREP.md](docs/LoRA_DATA_PREP.md)**.

## Image questions

The 60 image-dependent SSM questions (and ~440 more in other exams) are
described by a vision model and injected as text at test time:
**[docs/IMAGE_DESCRIPTIONS.md](docs/IMAGE_DESCRIPTIONS.md)**.

## Repo layout

```
scripts/
  build_pg_shuffle.py        # eval set from medbench's pinned letters
  run_local_baseline.py      # local MLX eval harness (base or +LoRA adapter)
  evaluate_ssm_results.py    # score a results file
  publish_to_medbench.py     # insert runs into the Postgres leaderboard
  prepare_lora_data.py       # build data/lora/ train/dev JSONL
  shuffle_answer_keys.py     # standalone position-shuffler (legacy of eval set)
  extract_drive_links.py / download_images.py /
  generate_image_descriptions.py / build_enriched_dataset.py   # image pipeline
  openrouter_client.py, run_*_text_only.py, ...               # legacy batch path (dead scale)
data/                        # gitignored where answers live — see SECURITY
models/                      # patched local MLX snapshots (4-bit)
.venv/                       # MLX environment (python3.9)
results/local/               # harness outputs (committed)
```

## Security

Files containing correct answers are gitignored and must never be committed:
`data/ssm_questions_with_solution.json`, `data/ssm_questions_*shuffled*.json`
(with answers), `data/shuffle_mapping.json`, `data/ssm_questions_enriched.json`,
`data/lora/` (contains answers in targets), `data/images/` (copyright).
Questions sent to models must not contain `correct_answer`.
