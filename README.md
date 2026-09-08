# Medical AI Leaderboard

**Benchmark local LLMs on real European medical residency examinations — with a live, interactive leaderboard.**

> 🚀 **Live demo:** [causius0.github.io/medical-ai-leaderboard](https://causius0.github.io/medical-ai-leaderboard/)
>
> Real models, real questions, real results — run locally on an Apple Silicon Mac.

## What this is

A full-stack benchmark that runs **open-weight LLMs locally** (via Ollama / llama.cpp on Apple Silicon) against **1,060 real questions** from the **Italian national medical residency exam (SSM)**, sourced from the [EuropeMedQA](https://github.com/causius0/SIIAM) dataset. It scores each model across **54 medical specialties** and **8 exam years**, then publishes the results to a polished, interactive leaderboard.

## Key results (local models, zero-shot, temperature 0, **shuffled answers**)

> **Methodology note:** The correct answers are **randomized across option positions** (the original SSM dataset has the correct answer at letter "A" in ~91% of questions — an answer-position leak). Every model is re-scored on a shuffled version where correct answers are uniformly distributed (A–E), so scores reflect genuine medical knowledge, not format exploitation.

| Model | Accuracy |
|---|---|
| qwen3:8b (thinking) | **89.0%** |
| gemma3:12b | **81.6%** |
| qwen3:8b | 79.3% |
| llama3.1:8b | 69.0% |
| mistral:7b | 54.6% |
| LFM2.5-8B-A1B (Liquid) | 23.2% |

Notably, **enabling chain-of-thought reasoning lifted Qwen3-8B from 79.3% → 89.0%** on the shuffled set — a ~10-point gain purely from reasoning. Reassuringly, models that had leaned on the "answer is A" shortcut (e.g. mistral, dropping 67.6% → 54.6%) were exposed, while genuinely capable models (gemma) held or improved.

## Features

- **Bias-free evaluation** — `scripts/shuffle_answers.py` randomizes correct-answer positions (seed 42, reproducible), so results aren't inflated by answer-position leakage.
- **Real local evaluation** — `scripts/run_evaluation.py` runs Ollama / llama.cpp models against the shuffled dataset, parses answer letters, and scores by specialty + year. (No fabricated/mock results.)
- **PostgreSQL persistence** — `scripts/db_load.py` stores questions, runs, responses, and derived per-specialty/year scores in a local Postgres DB (`medbench`), which is the source of truth. Shuffled results live in a **separate `shuffled_*` relation** so the original dataset is preserved.
- **Interactive leaderboard** — Next.js static site with:
  - Live ranking with per-model brand logos
  - **Filter by medical specialty** (rank models by accuracy in e.g. Cardiology)
  - Per-model detail with full specialty breakdown (correct/total per specialty)
  - Performance heatmap, year-over-year trends, and side-by-side model comparison
  - Dark **and** light themes
- **Real data discipline** — answer keys are never committed; only scored results are published.

## Architecture

```
EuropeMedQA SSM (1060 Q) ──▶ run_evaluation.py ──▶ result JSONs
                              (Ollama/llama.cpp)        │
                                                       ▼
                                PostgreSQL (medbench) ◀── db_load.py (ingest)
                                                       │
                                                       ▼
                                frontend/public/leaderboard_data.json ──▶ GitHub Pages
```

## Tech stack

- **Python** — evaluation pipeline, Postgres ingestion/export (psycopg)
- **Ollama / llama.cpp** — local model inference (Metal-accelerated on Apple Silicon)
- **PostgreSQL 16** — schema, ingestion, derived scores
- **Next.js 16 / React 19 / TypeScript** — static leaderboard site
- **GitHub Actions + Pages** — CI build and deployment

## Running it yourself

```bash
# 1. Pull models locally
ollama pull qwen3:8b
ollama pull gemma3:12b
ollama pull llama3.1:8b

# 2. Run a real evaluation (full SSM set)
python3 scripts/run_evaluation.py --models qwen3:8b,gemma3:12b,llama3.1:8b

# 3. Persist to PostgreSQL (requires local Postgres 16 + psycopg)
createdb medbench
python3 scripts/db_load.py --init    # schema + load 1060 questions
python3 scripts/db_load.py --ingest  # ingest results
python3 scripts/db_load.py --export  # rebuild leaderboard JSON

# 4. Serve the site
cd frontend && npm install && npm run build
```

See [`docs/REAL_EVALUATION.md`](docs/REAL_EVALUATION.md) for the full pipeline, Postgres schema, and example queries.

## Roadmap

- Add Spanish (MIR), Portuguese, and French residency exams from EuropeMedQA
- Run vision-language models on image-based questions
- Calibrated confidence scores and position-bias analysis

## Related

- [SIIAM](https://github.com/causius0/SIIAM) — EuropeMedQA dataset + medical vision-language research

## License

MIT
