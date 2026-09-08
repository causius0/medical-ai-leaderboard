#!/usr/bin/env python3
"""
Load EuropeMedQA questions + local LLM evaluation results into PostgreSQL
(medbench) so the DB is the source of truth for the leaderboard.

Uses psycopg (PostgreSQL driver). Install:  uv pip install psycopg[binary]

Usage:
    python3 scripts/db_load.py --init          # create schema + load questions
    python3 scripts/db_load.py --ingest        # ingest result JSONs into runs/responses/scores
    python3 scripts/db_load.py --export        # rebuild leaderboard_data.json from DB
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg

BASE = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE / "data" / "ssm_questions_shuffled.json"
RESULTS_DIR = BASE / "results" / "openrouter"
LEADERBOARD_FILE = BASE / "frontend" / "public" / "leaderboard_data.json"

DSN = "dbname=medbench"

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    question_id   TEXT PRIMARY KEY,
    test_year     INT,
    number_in_test INT,
    question_text TEXT NOT NULL,
    specialty     TEXT NOT NULL,
    has_image     BOOLEAN DEFAULT FALSE,
    nullified     BOOLEAN DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS models (
    model_id   TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    provider   TEXT,
    provider_logo TEXT,
    backend    TEXT,
    param_size TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    run_id        SERIAL PRIMARY KEY,
    model_id      TEXT NOT NULL REFERENCES models(model_id),
    dataset       TEXT NOT NULL DEFAULT 'italian_ssm',
    prompt_template TEXT,
    temperature   REAL,
    max_tokens    INT,
    started_at    TIMESTAMPTZ DEFAULT now(),
    elapsed_seconds REAL,
    total_questions INT,
    total_answered INT,
    total_correct INT,
    overall_accuracy REAL,
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);
CREATE TABLE IF NOT EXISTS responses (
    run_id        INT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    question_id   TEXT NOT NULL REFERENCES questions(question_id),
    answer_letter CHAR(1),
    reasoning     TEXT,
    refusal       BOOLEAN DEFAULT FALSE,
    is_correct    BOOLEAN,
    PRIMARY KEY (run_id, question_id)
);
CREATE TABLE IF NOT EXISTS specialty_scores (
    run_id       INT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    specialty    TEXT NOT NULL,
    correct      INT,
    total        INT,
    accuracy     REAL,
    PRIMARY KEY (run_id, specialty)
);
CREATE TABLE IF NOT EXISTS year_scores (
    run_id     INT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    test_year  INT NOT NULL,
    correct    INT,
    total      INT,
    accuracy   REAL,
    PRIMARY KEY (run_id, test_year)
);
"""

# Separate relation for the shuffled (bias-free) evaluation. Uses prefixed
# table names so it never overwrites the original 'italian_ssm' dataset.
SCHEMA_SHUFFLED = """
CREATE TABLE IF NOT EXISTS shuffled_questions (
    question_id   TEXT PRIMARY KEY,
    test_year     INT,
    number_in_test INT,
    question_text TEXT NOT NULL,
    specialty     TEXT NOT NULL,
    has_image     BOOLEAN DEFAULT FALSE,
    nullified     BOOLEAN DEFAULT FALSE,
    correct_letter CHAR(1)
);
CREATE TABLE IF NOT EXISTS shuffled_models (
    model_id   TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    provider   TEXT,
    provider_logo TEXT,
    backend    TEXT,
    param_size TEXT
);
CREATE TABLE IF NOT EXISTS shuffled_runs (
    run_id        SERIAL PRIMARY KEY,
    model_id      TEXT NOT NULL REFERENCES shuffled_models(model_id),
    dataset       TEXT NOT NULL DEFAULT 'italian_ssm_shuffled',
    prompt_template TEXT,
    temperature   REAL,
    max_tokens    INT,
    started_at    TIMESTAMPTZ DEFAULT now(),
    elapsed_seconds REAL,
    total_questions INT,
    total_answered INT,
    total_correct INT,
    overall_accuracy REAL
);
CREATE TABLE IF NOT EXISTS shuffled_responses (
    run_id        INT NOT NULL REFERENCES shuffled_runs(run_id) ON DELETE CASCADE,
    question_id   TEXT NOT NULL REFERENCES shuffled_questions(question_id),
    answer_letter CHAR(1),
    reasoning     TEXT,
    refusal       BOOLEAN DEFAULT FALSE,
    is_correct    BOOLEAN,
    PRIMARY KEY (run_id, question_id)
);
CREATE TABLE IF NOT EXISTS shuffled_specialty_scores (
    run_id       INT NOT NULL REFERENCES shuffled_runs(run_id) ON DELETE CASCADE,
    specialty    TEXT NOT NULL,
    correct      INT,
    total        INT,
    accuracy     REAL,
    PRIMARY KEY (run_id, specialty)
);
CREATE TABLE IF NOT EXISTS shuffled_year_scores (
    run_id     INT NOT NULL REFERENCES shuffled_runs(run_id) ON DELETE CASCADE,
    test_year  INT NOT NULL,
    correct    INT,
    total      INT,
    accuracy   REAL,
    PRIMARY KEY (run_id, test_year)
);
"""


def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def shuffled_correct_map():
    """question_id -> correct letter from the shuffled evaluation dataset."""
    return {q["id"]: q["correct_answer"]["letter"] for q in load_questions()}


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        # Load questions (correct letter no longer stored — it varies per dataset)
        qs = load_questions()
        for q in qs:
            cur.execute(
                """
                INSERT INTO questions (question_id, test_year, number_in_test,
                    question_text, specialty, has_image, nullified)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (question_id) DO NOTHING
                """,
                (
                    q["id"],
                    q["metadata"].get("test_year"),
                    q["metadata"].get("number_in_test"),
                    q["question"],
                    q["specialty"],
                    q.get("has_image", False),
                    q["metadata"].get("nullified", False),
                ),
            )
    conn.commit()
    print(f"Loaded {len(qs)} questions")


def ingest_result(conn, path: Path):
    with open(path, encoding="utf-8") as f:
        r = json.load(f)

    if r.get("metadata", {}).get("generated_by") == "mock_generator":
        print(f"  skip mock: {path.name}")
        return

    model_id = r["model_id"]
    # Distinguish thinking-mode runs so they appear as separate rows (not collapsed
    # with the same model's direct run by the 'latest per model' export)
    think = r.get("metadata", {}).get("think", False)
    if think:
        model_id = f"{model_id}-thinking"
    # upsert model
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO models (model_id, name, provider, provider_logo, backend)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (model_id) DO UPDATE SET name=EXCLUDED.name
            """,
            (model_id, r["model_name"], r["provider"], r["provider_logo"], "ollama"),
        )
        # insert run
        cur.execute(
            """
            INSERT INTO runs (model_id, dataset, prompt_template, temperature, max_tokens,
                started_at, elapsed_seconds, total_questions, total_answered,
                total_correct, overall_accuracy)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING run_id
            """,
            (
                model_id,
                r["dataset"],
                r["prompt_template"],
                r["temperature"],
                r["max_tokens"],
                datetime.now(timezone.utc),
                r["metadata"].get("elapsed_seconds"),
                r["total_questions_attempted"],
                r["total_questions_answered"],
                r["total_correct"],
                r["overall_accuracy"],
            ),
        )
        run_id = cur.fetchone()[0]

        # responses
        # map correct letters from the shuffled dataset (correctness varies per dataset)
        correct_map = shuffled_correct_map()
        for resp in r["responses"]:
            ans = resp["answer"]
            correct = correct_map.get(resp["question_id"])
            is_correct = None if ans is None else (ans == correct)
            cur.execute(
                """
                INSERT INTO responses (run_id, question_id, answer_letter, reasoning,
                    refusal, is_correct)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id, question_id) DO UPDATE
                  SET answer_letter=EXCLUDED.answer_letter,
                      is_correct=EXCLUDED.is_correct
                """,
                (
                    run_id,
                    resp["question_id"],
                    ans,
                    (resp.get("reasoning") or "")[:2000],
                    resp.get("refusal", False),
                    is_correct,
                ),
            )

        # specialty + year scores computed from responses
        cur.execute(
            """
            DELETE FROM specialty_scores WHERE run_id=%s
            """,
            (run_id,),
        )
        cur.execute(
            """
            INSERT INTO specialty_scores (run_id, specialty, correct, total, accuracy)
            SELECT %s, q.specialty,
                   COUNT(*) FILTER (WHERE r.is_correct),
                   COUNT(*),
                   ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2)
            FROM responses r JOIN questions q USING (question_id)
            WHERE r.run_id=%s GROUP BY q.specialty
            """,
            (run_id, run_id),
        )
        cur.execute("DELETE FROM year_scores WHERE run_id=%s", (run_id,))
        cur.execute(
            """
            INSERT INTO year_scores (run_id, test_year, correct, total, accuracy)
            SELECT %s, q.test_year,
                   COUNT(*) FILTER (WHERE r.is_correct),
                   COUNT(*),
                   ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2)
            FROM responses r JOIN questions q USING (question_id)
            WHERE r.run_id=%s GROUP BY q.test_year
            """,
            (run_id, run_id),
        )
    conn.commit()
    print(f"  ✓ {path.name} → run_id={run_id} acc={r['overall_accuracy']}%")


def _logo_for_id(model_id):
    """Map a model_id to its brand logo key for the frontend."""
    mid = (model_id or "").lower()
    if "gemma" in mid:
        return "google"
    if "qwen" in mid:
        return "alibaba"
    if "llama" in mid:
        return "meta"
    if "mistral" in mid:
        return "mistral"
    if "lfm" in mid or "liquid" in mid:
        return "liquid"
    if "deepseek" in mid:
        return "deepseek"
    return "meta"


def export_shuffled_leaderboard(conn):
    """Rebuild leaderboard_data.json from the shuffled_* (bias-free) relation."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.model_id, m.name, m.provider, m.provider_logo,
                   r.overall_accuracy, r.total_correct, r.total_answered,
                   r.started_at::date::text
            FROM shuffled_runs r JOIN shuffled_models m USING (model_id)
            WHERE r.run_id = (SELECT MAX(run_id) FROM shuffled_runs r2 WHERE r2.model_id = m.model_id)
            ORDER BY r.overall_accuracy DESC
            """
        )
        rows = cur.fetchall()

        models = []
        for rank, (mid, name, prov, logo, acc, correct, total, date) in enumerate(rows, 1):
            cur.execute(
                "SELECT specialty, accuracy FROM shuffled_specialty_scores WHERE run_id = "
                "(SELECT MAX(run_id) FROM shuffled_runs WHERE model_id=%s) ORDER BY specialty",
                (mid,),
            )
            spec = {s: float(a) for s, a in cur.fetchall()}
            cur.execute(
                "SELECT test_year, accuracy FROM shuffled_year_scores WHERE run_id = "
                "(SELECT MAX(run_id) FROM shuffled_runs WHERE model_id=%s) ORDER BY test_year",
                (mid,),
            )
            yrs = {str(y): float(a) for y, a in cur.fetchall()}
            cur.execute(
                """
                SELECT q.specialty, COUNT(*) AS answered,
                       COUNT(*) FILTER (WHERE r.is_correct) AS correct,
                       ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2) AS acc
                FROM shuffled_responses r JOIN shuffled_questions q USING (question_id)
                WHERE r.run_id = (SELECT MAX(run_id) FROM shuffled_runs WHERE model_id=%s)
                GROUP BY q.specialty ORDER BY answered DESC
                """,
                (mid,),
            )
            specialty_breakdown = {}
            for s, answered, corr, acc_spec in cur.fetchall():
                specialty_breakdown[s] = {
                    "answered": int(answered),
                    "correct": int(corr),
                    "accuracy": float(acc_spec),
                }
            display_name = name
            if mid.endswith("-thinking"):
                display_name = f"{name} (thinking)"
            models.append({
                "id": mid, "name": display_name, "provider": prov, "provider_logo": _logo_for_id(mid),
                "overall_accuracy": acc, "total_correct": correct,
                "total_questions": total, "rank": rank,
                "specialty_scores": spec, "year_scores": yrs, "test_date": date,
                "specialty_breakdown": specialty_breakdown,
            })

        cur.execute("SELECT specialty, COUNT(*) FROM shuffled_questions GROUP BY specialty")
        specialties = dict(cur.fetchall())
        cur.execute("SELECT DISTINCT test_year FROM shuffled_questions ORDER BY test_year")
        years = [str(y[0]) for y in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM shuffled_questions")
        n_q = cur.fetchone()[0]

    datasets = {
        "italian_ssm": {"name": "Italian SSM (shuffled)", "full_name": "Selezione Specializzazioni in Medicina", "language": "Italian", "country": "Italy 🇮🇹", "status": "active", "description": "Italian National Medical Residency Examination — correct answers randomized to remove position bias", "question_count": n_q},
        "spanish_mir": {"name": "Spanish MIR", "full_name": "Médico Interno Residente", "language": "Spanish", "country": "Spain 🇪🇸", "status": "upcoming", "description": "Spanish Medical Residency Examination", "question_count": 0},
        "portuguese": {"name": "Portuguese Exam", "full_name": "Prova de Acesso à Especialização", "language": "Portuguese", "country": "Portugal 🇵🇹", "status": "upcoming", "description": "Portuguese Medical Residency Examination", "question_count": 0},
        "french": {"name": "French Exam", "full_name": "Concours d'Internat", "language": "French", "country": "France 🇫🇷", "status": "upcoming", "description": "French Medical Residency Examination", "question_count": 0},
    }

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "2.2.0",
        "datasets": datasets,
        "specialties": specialties,
        "years": years,
        "models": models,
    }
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=_json_default)
    print(f"✓ leaderboard_data.json rebuilt from shuffled relation: {len(models)} models")


def export_leaderboard(conn):
    """Rebuild leaderboard_data.json straight from Postgres."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.model_id, m.name, m.provider, m.provider_logo,
                   r.overall_accuracy, r.total_correct, r.total_answered,
                   r.started_at::date::text
            FROM runs r JOIN models m USING (model_id)
            WHERE r.run_id = (SELECT MAX(run_id) FROM runs r2 WHERE r2.model_id = m.model_id)
            ORDER BY r.overall_accuracy DESC
            """
        )
        rows = cur.fetchall()

        models = []
        for rank, (mid, name, prov, logo, acc, correct, total, date) in enumerate(rows, 1):
            cur.execute(
                "SELECT specialty, accuracy FROM specialty_scores WHERE run_id = "
                "(SELECT MAX(run_id) FROM runs WHERE model_id=%s) ORDER BY specialty",
                (mid,),
            )
            spec = {s: float(a) for s, a in cur.fetchall()}
            cur.execute(
                "SELECT test_year, accuracy FROM year_scores WHERE run_id = "
                "(SELECT MAX(run_id) FROM runs WHERE model_id=%s) ORDER BY test_year",
                (mid,),
            )
            yrs = {str(y): float(a) for y, a in cur.fetchall()}
            # per-specialty breakdown of questions the model ANSWERED (correct/total/accuracy)
            cur.execute(
                """
                SELECT q.specialty, COUNT(*) AS answered,
                       COUNT(*) FILTER (WHERE r.is_correct) AS correct,
                       ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2) AS acc
                FROM responses r JOIN questions q USING (question_id)
                WHERE r.run_id = (SELECT MAX(run_id) FROM runs WHERE model_id=%s)
                GROUP BY q.specialty ORDER BY answered DESC
                """,
                (mid,),
            )
            specialty_breakdown = {}
            for s, answered, corr, acc_spec in cur.fetchall():
                specialty_breakdown[s] = {
                    "answered": int(answered),
                    "correct": int(corr),
                    "accuracy": float(acc_spec),
                }
            # label thinking-mode rows distinctly
            display_name = name
            if mid.endswith("-thinking"):
                display_name = f"{name} (thinking)"
            models.append({
                "id": mid, "name": display_name, "provider": prov, "provider_logo": _logo_for_id(mid),
                "overall_accuracy": acc, "total_correct": correct,
                "total_questions": total, "rank": rank,
                "specialty_scores": spec, "year_scores": yrs, "test_date": date,
                "specialty_breakdown": specialty_breakdown,
            })

        cur.execute("SELECT specialty, COUNT(*) FROM questions GROUP BY specialty")
        specialties = dict(cur.fetchall())
        cur.execute("SELECT DISTINCT test_year FROM questions ORDER BY test_year")
        years = [str(y[0]) for y in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM questions")
        n_q = cur.fetchone()[0]

    datasets = {
        "italian_ssm": {"name": "Italian SSM", "full_name": "Selezione Specializzazioni in Medicina", "language": "Italian", "country": "Italy 🇮🇹", "status": "active", "description": "Italian National Medical Residency Examination", "question_count": n_q},
        "spanish_mir": {"name": "Spanish MIR", "full_name": "Médico Interno Residente", "language": "Spanish", "country": "Spain 🇪🇸", "status": "upcoming", "description": "Spanish Medical Residency Examination", "question_count": 0},
        "portuguese": {"name": "Portuguese Exam", "full_name": "Prova de Acesso à Especialização", "language": "Portuguese", "country": "Portugal 🇵🇹", "status": "upcoming", "description": "Portuguese Medical Residency Examination", "question_count": 0},
        "french": {"name": "French Exam", "full_name": "Concours d'Internat", "language": "French", "country": "France 🇫🇷", "status": "upcoming", "description": "French Medical Residency Examination", "question_count": 0},
    }

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "2.1.0",
        "datasets": datasets,
        "specialties": specialties,
        "years": years,
        "models": models,
    }
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=_json_default)
    print(f"✓ leaderboard_data.json rebuilt from Postgres: {len(models)} models")


def _json_default(o):
    """Serialize Decimals (Postgres numeric) as floats for JSON."""
    from decimal import Decimal
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


def ingest_shuffled_result(conn, path: Path):
    """Ingest a shuffled-dataset result into the shuffled_* relation."""
    with open(path, encoding="utf-8") as f:
        r = json.load(f)
    if r.get("metadata", {}).get("generated_by") == "mock_generator":
        print(f"  skip mock: {path.name}")
        return
    model_id = r["model_id"]
    think = r.get("metadata", {}).get("think", False)
    if think:
        model_id = f"{model_id}-thinking"
    # Idempotent: skip if this model already has a shuffled run
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM shuffled_runs WHERE model_id=%s LIMIT 1", (model_id,))
        if cur.fetchone():
            print(f"  ✓ already ingested (skip): {path.name} ({model_id})")
            return
        cur.execute(
            """
            INSERT INTO shuffled_models (model_id, name, provider, provider_logo, backend)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (model_id) DO UPDATE SET name=EXCLUDED.name
            """,
            (model_id, r["model_name"], r["provider"], r["provider_logo"], "ollama"),
        )
        cur.execute(
            """
            INSERT INTO shuffled_runs (model_id, dataset, prompt_template, temperature, max_tokens,
                started_at, elapsed_seconds, total_questions, total_answered,
                total_correct, overall_accuracy)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING run_id
            """,
            (model_id, r["dataset"], r["prompt_template"], r["temperature"], r["max_tokens"],
             datetime.now(timezone.utc), r["metadata"].get("elapsed_seconds"),
             r["total_questions_attempted"], r["total_questions_answered"],
             r["total_correct"], r["overall_accuracy"]),
        )
        run_id = cur.fetchone()[0]
        correct_map = shuffled_correct_map()
        for resp in r["responses"]:
            ans = resp["answer"]
            correct = correct_map.get(resp["question_id"])
            is_correct = None if ans is None else (ans == correct)
            cur.execute(
                """
                INSERT INTO shuffled_responses (run_id, question_id, answer_letter, reasoning,
                    refusal, is_correct)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id, question_id) DO UPDATE
                  SET answer_letter=EXCLUDED.answer_letter, is_correct=EXCLUDED.is_correct
                """,
                (run_id, resp["question_id"], ans, (resp.get("reasoning") or "")[:2000],
                 resp.get("refusal", False), is_correct),
            )
        # specialty + year scores
        cur.execute("DELETE FROM shuffled_specialty_scores WHERE run_id=%s", (run_id,))
        cur.execute(
            """
            INSERT INTO shuffled_specialty_scores (run_id, specialty, correct, total, accuracy)
            SELECT %s, q.specialty, COUNT(*) FILTER (WHERE r.is_correct), COUNT(*),
                   ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2)
            FROM shuffled_responses r JOIN shuffled_questions q USING (question_id)
            WHERE r.run_id=%s GROUP BY q.specialty
            """,
            (run_id, run_id),
        )
        cur.execute("DELETE FROM shuffled_year_scores WHERE run_id=%s", (run_id,))
        cur.execute(
            """
            INSERT INTO shuffled_year_scores (run_id, test_year, correct, total, accuracy)
            SELECT %s, q.test_year, COUNT(*) FILTER (WHERE r.is_correct), COUNT(*),
                   ROUND(100.0 * COUNT(*) FILTER (WHERE r.is_correct) / COUNT(*), 2)
            FROM shuffled_responses r JOIN shuffled_questions q USING (question_id)
            WHERE r.run_id=%s GROUP BY q.test_year
            """,
            (run_id, run_id),
        )
    conn.commit()
    print(f"  ✓ shuffled: {path.name} → run_id={run_id} acc={r['overall_accuracy']}%")


def init_shuffled_db(conn):
    """Create shuffled_* tables and load shuffled questions."""
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SHUFFLED)
        qs = load_questions()
        for q in qs:
            cur.execute(
                """
                INSERT INTO shuffled_questions (question_id, test_year, number_in_test,
                    question_text, specialty, has_image, nullified, correct_letter)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (question_id) DO NOTHING
                """,
                (q["id"], q["metadata"].get("test_year"), q["metadata"].get("number_in_test"),
                 q["question"], q["specialty"], q.get("has_image", False),
                 q["metadata"].get("nullified", False), q["correct_answer"]["letter"]),
            )
    conn.commit()
    print(f"Loaded {len(qs)} shuffled questions")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--shuffled", action="store_true", help="operate on the shuffled_* relation (separate from original)")
    ap.add_argument("--export-shuffled", action="store_true", help="rebuild leaderboard_data.json from the shuffled relation")
    args = ap.parse_args()

    with psycopg.connect(DSN) as conn:
        if args.export_shuffled:
            export_shuffled_leaderboard(conn)
            return
        if args.shuffled:
            if args.init:
                init_shuffled_db(conn)
            if args.ingest:
                for f in sorted(RESULTS_DIR.glob("*.json")):
                    if "checkpoint" in f.name:
                        continue
                    ingest_shuffled_result(conn, f)
            print("done")
            return
        if args.init:
            init_db(conn)
        if args.ingest:
            for f in sorted(RESULTS_DIR.glob("*.json")):
                if "checkpoint" in f.name:
                    continue
                ingest_result(conn, f)
        if args.export:
            export_leaderboard(conn)
    print("done")


if __name__ == "__main__":
    main()
