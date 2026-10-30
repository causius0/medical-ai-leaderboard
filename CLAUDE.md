# Medical AI Leaderboard — Working Guide

Entry point for anyone (human or agent) working in this repo.
Read `docs/TRAINING_PLAN.md` for the active LoRA experiment and its session log.
For the expanded 2023–2026 exam corpus (SSM 25/26, MIR 25/26, EDN 23–25,
PNA 25, PES Poland — `exam_questions` in medbench), read `AGENTS.md`.

## Ground truth and scale discipline

1. **The canonical leaderboard is the local Postgres DB `medbench`**
   (tables `shuffled_models`, `shuffled_runs`, `shuffled_responses`,
   `shuffled_specialty_scores`, …). The old `frontend/*/leaderboard.json`
   files and `results/openrouter/` runs are a **dead scale** (batch pipeline,
   original answer positions, temperature 0.7) — never compare against them.
2. **Every eval uses the canonical shuffled set** built from the DB:
   `data/ssm_questions_text_only_shuffled_no_answers.json` (for models) and
   `..._shuffled.json` (with answers, PRIVATE). Regenerate with
   `python3 scripts/build_pg_shuffle.py` — correct letters are pinned to
   `medbench.shuffled_questions.correct_letter`.
3. **Run parameters are part of a score.** Token budget, thinking behavior,
   quantization. When publishing, `scripts/publish_to_medbench.py` stores them
   in `shuffled_runs.notes` — add `--notes-extra` for anything unusual.
   Cautionary tale: LFM2.5-8B scored 23.21% at a 256-token budget and 72.64%
   with a 1024/2048/4096 ladder (runs 7 vs 12).

## Standard eval workflow (local MLX)

```bash
# models live in models/ — patched snapshots (config: flat rope_theta;
# tokenizer_config: PreTrainedTokenizerFast). Use .venv/bin/python for MLX.
.venv/bin/python scripts/run_local_baseline.py \
    --model models/LFM2.5-8B-A1B-4bit \
    --questions data/ssm_questions_text_only_shuffled_no_answers.json \
    --tag <name> --max-tokens 1024          # thinking models need budget

# score
.venv/bin/python scripts/evaluate_ssm_results.py \
    results/local/<model>_<tag>.json data/ssm_questions_text_only_shuffled.json

# publish to medbench (creates a new immutable run row)
python3 scripts/publish_to_medbench.py results/local/<model>_<tag>.json \
    --param-size 8B-A1B --notes-extra "..."
```

Harness details: greedy decoding; Italian single-question prompt identical to
the LoRA training format; answers parsed only after `</think>` (an unclosed
think block = refusal); resumeable — safe to kill and relaunch.

## LoRA training (mlx-lm)

```bash
.venv/bin/python -m mlx_lm lora --train \
    --model models/LFM2.5-8B-A1B-4bit --data data/lora \
    --fine-tune-type lora --num-layers 16 --batch-size 4 \
    --learning-rate 1e-4 --iters 1500 --max-seq-length 1024 \
    --grad-checkpoint --mask-prompt \
    --adapter-path adapters/v2_s1 --save-every 250 \
    --steps-per-eval 250 --val-batches 20 --seed 42
```

- Data: `data/lora/{train,valid}.jsonl` via `scripts/prepare_lora_data.py`
  (no SSM questions; contamination-guarded; letters balanced A–E).
- Adapter eval: same harness with `--adapter adapters/<name>` (pass the
  DIRECTORY, not the safetensors file). Eval at `--max-tokens 8` — the
  experiment's whole point is direct answers without thinking.
- Verify "Trainable parameters: ~0.2%" in training output — 0% means the
  adapter silently attached to nothing.
- Stages, review gates, decision rules: `docs/TRAINING_PLAN.md`.

## Image-question pipeline

`docs/IMAGE_DESCRIPTIONS.md`. Vision model describes each image ALONE (never
the question/options — anti-leakage) in the exam language; descriptions are
cached in `data/image_descriptions.json` and injected at test time via
`prompt_builder.apply_image_descriptions()`.

## Security rules (non-negotiable)

- **NEVER commit files with correct answers** (all gitignored):
  `data/ssm_questions_with_solution.json`,
  `data/ssm_questions_*shuffled*.json` (answer variants),
  `data/shuffle_mapping.json`, `data/ssm_questions_enriched.json`,
  `data/lora/`, `data/ssm_questions_shuffled_with_solution.json`.
- **Questions sent to models must not include `correct_answer`.**
- `data/images/` is exam-copyright material — never commit or redistribute.
- `data/europemedqa/` is a clone of the public dataset repo (contains every
  exam's answer key) — keep it gitignored.

## Legacy (do not extend)

`scripts/openrouter_client.py`, `run_*_text_only.py`, `retry_gemma*.py`,
`merge_gemma_results.py`, `response_parser.py`, `add_to_leaderboard.py`,
`test_gemma.py` — the March OpenRouter batch pipeline (dead scale). The
Gemma/Qwen/Liquid files under it were removed from git history's HEAD.
`docs/DATASET_CONVERSION.md` documents the (uncommitted) original Excel→JSON
conversion; its data-quality stats remain the reference for the SSM dataset.

## Environment notes

- `.venv/` (python3.9) holds mlx-lm 0.29.1 + transformers; MLX work always
  via `.venv/bin/python`. Plain `python3` is fine for data scripts.
- `models/LFM2.5-8B-A1B-4bit` and `models/LFM2-24B-A2B-4bit` are patched
  local snapshots of mlx-community 4-bit builds (flat `rope_theta`,
  `PreTrainedTokenizerFast`) — symlinks into the HF cache; keep gitignored.
- Postgres: `psql -d medbench`. Frontend (Next.js in `frontend/`) currently
  renders static data and is NOT wired to the DB.
