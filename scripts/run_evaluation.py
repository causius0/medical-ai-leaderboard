#!/usr/bin/env python3
"""
Run REAL local LLM evaluations against the EuropeMedQA SSM (Italian) dataset
and emit results in the exact schema the MedBench frontend consumes.

Backend: Ollama (Metal-accelerated on Apple Silicon).

Usage:
    python3 scripts/run_evaluation.py --models qwen3:8b,gemma3:12b
    python3 scripts/run_evaluation.py --models qwen3:8b --limit 20   # quick smoke test
    python3 scripts/run_evaluation.py --rebuild                       # rebuild leaderboard_data.json
"""

import argparse
import json
import re
import signal
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE / "data" / "ssm_questions_text_only.json"
RESULTS_DIR = BASE / "results" / "openrouter"
LEADERBOARD_FILE = BASE / "frontend" / "public" / "leaderboard_data.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELS_URL = "http://localhost:11434/api/tags"

# Zero-shot CoT medical prompt (same template family as the mock generator used)
SYSTEM_PROMPT = (
    "Sei un medico esperto. Rispondi alle domande dell'esame di specializzazione "
    "medica. Fornisci SOLO la lettera della risposta corretta (A, B, C, D o E). "
    "Nessuna spiegazione, nessun testo aggiuntivo."
)

USER_TEMPLATE = (
    "Domanda: {question}\n\n"
    "Opzioni:\n{options}\n\n"
    "Rispondi con la sola lettera della risposta corretta."
)


def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def ollama_installed_models():
    try:
        with urllib.request.urlopen(OLLAMA_MODELS_URL, timeout=5) as r:
            data = json.load(r)
            return {m["name"] for m in data.get("models", [])}
    except Exception:
        return set()


def query_ollama(model, prompt, temperature=0.0, max_tokens=256, timeout=180, think=False):
    """Query a local Ollama model. Returns raw text.
    The urllib `timeout` only bounds socket-read idle time, so we ALSO enforce a
    hard wall-clock deadline with signal.alarm to kill runaway generations
    (e.g. thinking-mode token loops). Returns '' on timeout/error.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "think": think,  # Qwen3: False=fast direct answers, True=let it reason first
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    result = {"text": ""}

    def _run():
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        result["text"] = data.get("response", "").strip()

    # Hard wall-clock deadline (covers total generation, not just read idle)
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        _run()
    except TimeoutError:
        print(f"    ⚠ {model}: request exceeded {timeout}s, treating as refusal")
        result["text"] = ""
    except Exception as e:
        result["text"] = ""
    finally:
        signal.alarm(0)
    return result["text"]


def _timeout_handler(signum, frame):
    raise TimeoutError("request timed out")


def query_llamaserver(endpoint, model, prompt, temperature=0.0, max_tokens=256, timeout=300):
    """Query a llama.cpp OpenAI-compatible server (raw completions). Returns raw text."""
    url = f"{endpoint}/v1/completions"
    payload = {
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["text"].strip()


def _logo_for(model):
    """Map a model string to its brand logo key (used by the frontend Logo component)."""
    m = model.lower()
    if "gemma" in m:
        return "google"
    if "qwen" in m:
        return "alibaba"
    if "llama" in m:
        return "meta"
    if "mistral" in m:
        return "mistral"
    if "lfm" in m or "liquid" in m:
        return "liquid"
    if "deepseek" in m:
        return "deepseek"
    return "meta"


def parse_answer(text):
    """Extract the answer letter (A-E) from a model response."""
    if not text:
        return None, text
    # Strip Qwen3 thinking tags (hidden chain-of-thought)
    text_clean = re.sub(r"<\|?think\|?>|</?think>|```[a-z]*\n|```", "", text, flags=re.I)
    # 1) Explicit single letter answer
    m = re.search(r"\b([A-E])\b(?!\s*[A-E])", text_clean)
    # Prefer a letter appearing as 'A)' or 'A.' or standalone at start
    m2 = re.search(r"(?:^|\s|\)|\.|\"|')\s*([A-E])\s*(?:\)|\.|,|\s|$)", text_clean)
    if m2:
        return m2.group(1), text
    if m:
        return m.group(1), text
    return None, text


def run_model(model, questions, limit=None, progress_every=50, think=False, endpoint=None):
    """Run one model over the questions. Returns result dict in frontend schema."""
    if limit:
        questions = questions[:limit]

    responses = []
    correct_count = 0
    t0 = time.time()

    for i, q in enumerate(questions):
        opts = "\n".join(f"{o['letter']}. {o['text']}" for o in q["options"])
        prompt = USER_TEMPLATE.format(question=q["question"], options=opts)

        try:
            # thinking mode: large token budget + generous hard timeout
            # (signal.alarm kills runaway token loops so a single question
            # can never hang the whole run)
            max_tokens = 2048 if think else 256
            q_timeout = 300 if think else 60
            if endpoint:
                raw = query_llamaserver(endpoint, model, prompt, max_tokens=max_tokens, timeout=q_timeout)
            else:
                raw = query_ollama(model, prompt, max_tokens=max_tokens, think=think, timeout=q_timeout)
        except Exception as e:
            raw = ""
            # record refusal/error
        answer, reasoning = parse_answer(raw)
        correct = q["correct_answer"]["letter"]
        is_correct = answer == correct

        responses.append(
            {
                "question_id": q["id"],
                "answer": answer,
                "confidence": 0,  # local models don't output calibrated confidence
                "explanation": "",
                "reasoning": reasoning[:500],
                "tokens_used": 0,
                "time_to_response": 0.0,
                "refusal": answer is None,
                "notes": "",
            }
        )
        if is_correct:
            correct_count += 1

        if (i + 1) % progress_every == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(
                f"  [{model}] {i+1}/{len(questions)}  acc={correct_count/(i+1)*100:.1f}%  "
                f"({rate:.1f} q/s)"
            )

    elapsed = time.time() - t0
    total = len(questions)

    # Specialty breakdown
    spec_correct, spec_total = {}, {}
    for q, r in zip(questions, responses):
        spec = q["specialty"]
        spec_total[spec] = spec_total.get(spec, 0) + 1
        if r["answer"] == q["correct_answer"]["letter"]:
            spec_correct[spec] = spec_correct.get(spec, 0) + 1
    specialty_scores = {
        s: round(spec_correct.get(s, 0) / n * 100, 2) for s, n in spec_total.items()
    }

    # Year breakdown
    yr_correct, yr_total = {}, {}
    for q, r in zip(questions, responses):
        yr = str(q["metadata"].get("test_year", "unknown"))
        yr_total[yr] = yr_total.get(yr, 0) + 1
        if r["answer"] == q["correct_answer"]["letter"]:
            yr_correct[yr] = yr_correct.get(yr, 0) + 1
    year_scores = {
        y: round(yr_correct.get(y, 0) / n * 100, 2) for y, n in yr_total.items()
    }

    return {
        "model_name": model,
        "model_id": model.replace(":", "-"),
        "provider": "Local (Ollama)",
        "provider_logo": _logo_for(model),
        "openrouter_model_id": f"ollama/{model}",
        "test_date": datetime.now().strftime("%Y-%m-%d"),
        "test_date_iso": datetime.now(timezone.utc).isoformat(),
        "dataset": "italian_ssm",
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 256,
        "prompt_template": "zero_shot_medical_local",
        "total_questions_attempted": total,
        "total_questions_answered": total - sum(1 for r in responses if r["refusal"]),
        "total_correct": correct_count,
        "overall_accuracy": round(correct_count / total * 100, 2),
        "specialty_scores": specialty_scores,
        "year_scores": year_scores,
        "responses": responses,
        "metadata": {
            "generated_by": "run_evaluation.py",
            "generation_method": "llamaserver_local" if endpoint else "ollama_local",
            "evaluation_pipeline_version": "2.0.0",
            "backend": "llama.cpp" if endpoint else "Ollama (Metal)",
            "think": think,
            "note": "REAL local evaluation.",
            "elapsed_seconds": round(elapsed, 1),
        },
    }


def build_leaderboard(all_results, questions):
    """Aggregate results into the frontend's leaderboard_data.json format."""
    from collections import Counter

    spec_counts = Counter(q["specialty"] for q in questions)
    years = sorted(set(str(q["metadata"].get("test_year", "")) for q in questions))
    ranked = sorted(all_results, key=lambda x: x["overall_accuracy"], reverse=True)

    models = []
    for rank, r in enumerate(ranked, 1):
        models.append(
            {
                "id": r["model_id"],
                "name": r["model_name"],
                "provider": r["provider"],
                "provider_logo": r["provider_logo"],
                "overall_accuracy": r["overall_accuracy"],
                "total_correct": r["total_correct"],
                "total_questions": r["total_questions_answered"],
                "rank": rank,
                "specialty_scores": r["specialty_scores"],
                "year_scores": r["year_scores"],
                "test_date": r["test_date"],
            }
        )

    datasets = {
        "italian_ssm": {
            "name": "Italian SSM",
            "full_name": "Selezione Specializzazioni in Medicina",
            "language": "Italian",
            "country": "Italy 🇮🇹",
            "status": "active",
            "description": "Italian National Medical Residency Examination",
            "question_count": len(questions),
        },
        "spanish_mir": {"name": "Spanish MIR", "full_name": "Médico Interno Residente", "language": "Spanish", "country": "Spain 🇪🇸", "status": "upcoming", "description": "Spanish Medical Residency Examination", "question_count": 0},
        "portuguese": {"name": "Portuguese Exam", "full_name": "Prova de Acesso à Especialização", "language": "Portuguese", "country": "Portugal 🇵🇹", "status": "upcoming", "description": "Portuguese Medical Residency Examination", "question_count": 0},
        "french": {"name": "French Exam", "full_name": "Concours d'Internat", "language": "French", "country": "France 🇫🇷", "status": "upcoming", "description": "French Medical Residency Examination", "question_count": 0},
    }

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "datasets": datasets,
        "specialties": dict(spec_counts),
        "years": years,
        "models": models,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen3:8b")
    ap.add_argument("--limit", type=int, default=None, help="run only first N questions")
    ap.add_argument("--rebuild", action="store_true", help="only rebuild leaderboard from existing result files")
    ap.add_argument("--thinking", action="store_true", help="enable Qwen3 thinking mode (reason first, slower)")
    ap.add_argument("--endpoint", default=None, help="llama.cpp OpenAI-compatible server URL (e.g. http://127.0.0.1:8081)")
    args = ap.parse_args()

    questions = load_questions()
    print(f"Loaded {len(questions)} questions from EuropeMedQA SSM (Italian)")

    available = ollama_installed_models()
    if not args.rebuild:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
        if not args.endpoint:
            missing = [m for m in models if m not in available]
            if missing:
                print(f"Models not installed locally: {missing}. Run 'ollama pull <model>'")
                sys.exit(1)
        print(f"Local models found: {available}")
        print(f"Evaluating: {models} (endpoint={args.endpoint})\n")

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        all_results = []
        for model in models:
            print(f"▶ Running {model} on {len(questions[:args.limit])} questions... (thinking={args.thinking})")
            result = run_model(model, questions, limit=args.limit, think=args.thinking, endpoint=args.endpoint)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{result['model_id']}_{stamp}.json"
            with open(RESULTS_DIR / fname, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  → saved {fname}  (accuracy {result['overall_accuracy']}%)")
            all_results.append(result)
            print()

    # Rebuild leaderboard from ALL committed result files
    result_files = sorted(RESULTS_DIR.glob("*.json")) if not args.rebuild else sorted(RESULTS_DIR.glob("*.json"))
    print(f"Aggregating {len(result_files)} result files...")
    all_results = []
    for f in result_files:
        with open(f, encoding="utf-8") as fh:
            all_results.append(json.load(fh))
    # Only include real (non-mock) results
    real_results = [r for r in all_results if r.get("metadata", {}).get("generated_by") != "mock_generator"]
    print(f"Real results: {len(real_results)} (excluding {len(all_results)-len(real_results)} mock)")

    if real_results:
        leaderboard = build_leaderboard(real_results, questions)
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(leaderboard, f, indent=2, ensure_ascii=False)
        print(f"\n✓ leaderboard_data.json written: {len(leaderboard['models'])} models")
        for m in leaderboard["models"]:
            print(f"   #{m['rank']} {m['name']:<18} {m['overall_accuracy']}%")
    else:
        print("No real results found — run --models first.")


if __name__ == "__main__":
    main()
