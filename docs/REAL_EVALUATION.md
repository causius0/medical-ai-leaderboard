# Real Local Evaluation & Postgres Storage

This documents the **real** evaluation pipeline (replacing the mock generator) and
the PostgreSQL persistence layer for the Medical AI Leaderboard.

## Why this exists

The original repo shipped `generate_mock_results.py`, which fabricated leaderboard
numbers (every committed result file has `"generated_by": "mock_generator"`). The
frontend (leaderboard, heatmap, year trends, compare) is real and excellent — but
the numbers were fake. This replaces them with **real, reproducible, locally-run**
model evaluations.

## Hardware

Apple Silicon (Metal 4), 24 GB unified memory. Runs quantized 8–12B models via
Ollama (Metal-accelerated). ~2.5 questions/sec → a full 1060-question set takes
~7 minutes per model.

## Running a real evaluation

```bash
# 1. Pull models (one-time)
ollama pull qwen3:8b
ollama pull gemma3:12b
ollama pull llama3.1:8b

# 2. Run the full EuropeMedQA SSM (Italian) set through one or more models
python3 scripts/run_evaluation.py --models qwen3:8b,gemma3:12b,llama3.1:8b

# smoke test (8 questions)
python3 scripts/run_evaluation.py --models qwen3:8b --limit 8
```

The script:
- Loads the 1060 non-nullified text questions from `data/ssm_questions_text_only.json`
  (sourced from EuropeMedQA `SSM_Q_ITA`, answers embedded for scoring).
- Sends each question to the local model (zero-shot, temperature 0, `think:false`
  to bypass Qwen3's hidden reasoning which otherwise eats the token budget).
- Parses the answer letter, scores against the key, and emits per-specialty and
  per-year accuracy.
- Writes `results/openrouter/<model>_<ts>.json` in the exact schema the frontend
  consumes, then rebuilds `frontend/public/leaderboard_data.json`.

## PostgreSQL persistence

Results are stored in a local Postgres database `medbench`, which is the source of
truth (the JSON files are a cache/export for the static frontend).

```bash
brew install postgresql@16
brew services start postgresql@16
createdb medbench

uv pip install --python /path/to/venv psycopg[binary]

# create schema + load the 1060 EuropeMedQA questions
python3 scripts/db_load.py --init

# ingest all real evaluation result JSONs into runs/responses/scores
python3 scripts/db_load.py --ingest

# rebuild leaderboard_data.json straight from Postgres
python3 scripts/db_load.py --export
```

### Schema

| Table | Purpose |
|---|---|
| `questions` | EuropeMedQA SSM questions (with correct letter + specialty + year) |
| `models` | Model registry |
| `runs` | One row per evaluation run (model × dataset × timestamp) |
| `responses` | Per-question answer, reasoning, correctness |
| `specialty_scores` | Derived accuracy per specialty per run |
| `year_scores` | Derived accuracy per exam year per run |

### Useful queries

```sql
-- Current leaderboard (latest run per model)
SELECT m.name, r.overall_accuracy, r.total_correct, r.total_answered,
       r.started_at::date AS date
FROM runs r JOIN models m USING (model_id)
WHERE r.run_id = (SELECT MAX(run_id) FROM runs r2 WHERE r2.model_id = m.model_id)
ORDER BY r.overall_accuracy DESC;

-- Head-to-head per specialty
SELECT q.specialty,
       ROUND(100.0*AVG(CASE WHEN r2.model_id='qwen3-8b' AND r.is_correct THEN 1 END),1),
       ROUND(100.0*AVG(CASE WHEN r2.model_id='gemma3-12b' AND r.is_correct THEN 1 END),1)
FROM responses r
JOIN questions q USING (question_id)
JOIN runs r2 USING (run_id)
WHERE r2.model_id IN ('qwen3-8b','gemma3-12b')
GROUP BY q.specialty ORDER BY 2 DESC NULLS LAST;

-- Which questions does every model get wrong?
SELECT q.question_id, q.specialty, COUNT(DISTINCT r.run_id) AS models_wrong
FROM responses r JOIN questions q USING (question_id)
WHERE NOT r.is_correct
GROUP BY q.question_id, q.specialty
HAVING COUNT(DISTINCT r.run_id) >= 3;
```

## Adding a new local model

```bash
ollama pull <new-model>
python3 scripts/run_evaluation.py --models <new-model>
python3 scripts/db_load.py --ingest --export
```

## Notes / pitfalls

- **Qwen3 thinking mode** burns the whole token budget on hidden reasoning and
  returns an empty answer at low `num_predict`. Fix: `think:false` in the API payload.
- **Solutions must never be committed.** The committed `ssm_questions_text_only.json`
  includes `correct_answer` for scoring; the `.gitignore` already blocks
  `ssm_questions_with_solution.json`. Keep it that way.
