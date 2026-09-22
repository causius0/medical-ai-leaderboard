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
# Shuffled dataset: correct answers randomized across positions (bias-free).
# The original had the correct answer at 'A' in ~91% of questions, which leaked
# position and inflated scores. Use shuffled for valid results.
# Multiple independent variants exist (see scripts/shuffle_answers.py); the
# default is variant 0 (seed 42, backward-compatible with committed data).
QUESTIONS_FILE = BASE / "data" / "ssm_questions_shuffled.json"
RESULTS_DIR = BASE / "results" / "openrouter"
LEADERBOARD_FILE = BASE / "frontend" / "public" / "leaderboard_data.json"
DATASET_NAME = "italian_ssm_shuffled"  # overridable via --dataset
VARIANT = 0

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


def _write_checkpoint(path, resumed_ids, responses):
    """Persist current responses to a checkpoint file (combined with any resumed)."""
    try:
        combined = []
        seen = set()
        if Path(path).exists():
            with open(path, encoding="utf-8") as f:
                combined = json.load(f)
            seen = {r["question_id"] for r in combined}
        for r in responses:
            if r["question_id"] not in seen:
                combined.append(r)
                seen.add(r["question_id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(combined, f)
    except Exception as e:
        print(f"    ⚠ checkpoint write failed: {e}")


def _correct_for(questions, qid):
    for q in questions:
        if q["id"] == qid:
            return q["correct_answer"]["letter"]
    return None


def run_model(model, questions, limit=None, progress_every=50, think=False, endpoint=None, checkpoint_path=None):
    """Run one model over the questions. Returns result dict in frontend schema."""
    # Resume: load partial responses already computed from a prior attempt
    resumed = set()
    if checkpoint_path and Path(checkpoint_path).exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            partial = json.load(f)
        resumed = {r["question_id"] for r in partial}
        print(f"    ↻ resuming: {len(resumed)} questions already answered")
    # keep original order; filter out resumed questions
    ordered = [q for q in questions]
    if resumed:
        questions = [q for q in questions if q["id"] not in resumed]
        if not questions:
            print("    ↻ all questions already answered in checkpoint")

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

        # Live terminal progress line (overwrites in place)
        done = i + 1
        elapsed_now = time.time() - t0
        rate_now = done / elapsed_now if elapsed_now > 0 else 0
        eta_min = (len(questions) - done) / rate_now / 60 if rate_now > 0 else 0
        acc_now = correct_count / done * 100 if done > 0 else 0
        bar_w = 28
        filled = int(bar_w * done / len(questions))
        bar = "█" * filled + "░" * (bar_w - filled)
        sys.stdout.write(
            f"\r  [{model}] {bar} {done}/{len(questions)} ({done/len(questions)*100:5.1f}%)  "
            f"acc={acc_now:5.1f}%  {rate_now:4.1f} q/s  ETA {eta_min:5.0f} min"
        )
        sys.stdout.flush()

        if (i + 1) % progress_every == 0:
            print()  # finalize the progress line at each milestone
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(
                f"  [{model}] {i+1}/{len(questions)}  acc={correct_count/(i+1)*100:.1f}%  "
                f"({rate:.1f} q/s)"
            )
            # Checkpoint partial progress so a crash can resume
            if checkpoint_path:
                _write_checkpoint(checkpoint_path, resumed, responses)

    # Merge resumed responses back in original question order
    if resumed and checkpoint_path and Path(checkpoint_path).exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            partial = json.load(f)
        by_id = {r["question_id"]: r for r in partial}
        merged = []
        for q in ordered:
            if q["id"] in by_id:
                merged.append(by_id[q["id"]])
        # append the newly computed ones (skip if already in partial)
        for r in responses:
            if r["question_id"] not in by_id:
                merged.append(r)
        responses = merged
        correct_count = sum(1 for r in responses if r["answer"] == _correct_for(ordered, r["question_id"]))

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
        "dataset": DATASET_NAME,
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
        "selection_bias": compute_selection_bias(responses, ordered),
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


def compute_selection_bias(responses, questions):
    """Selection-bias metrics per Zheng et al. arXiv:2309.03882 (Sec 2.2).

    Selection bias = a model's preference for certain option IDs regardless of
    content. The paper measures it as the *imbalance of recalls across option
    IDs*: for each option ID (letter), recall is the fraction of questions whose
    correct answer is at that letter that the model got right. Low spread (std)
    across letters -> unbiased; high spread -> the model systematically wins or
    loses depending on where the answer sits.

    Also reports a chi-square uniformity test on the letter distribution of the
    model's *picks*, which surfaces the raw "always answers A/B..." token bias.
    Requires matching responses <-> questions (by question_id).
    """
    from statistics import pstdev
    from scipy import stats

    by_id = {r["question_id"]: r for r in responses}
    n_letters = 5
    letters = ["A", "B", "C", "D", "E"]

    recall_correct = {L: 0 for L in letters}
    recall_total = {L: 0 for L in letters}
    pick_counts = {L: 0 for L in letters}

    for q in questions:
        ans_l = (q.get("correct_answer") or {}).get("letter", "")
        r = by_id.get(q["id"])
        if not r or ans_l not in recall_total:
            continue
        recall_total[ans_l] += 1
        if r.get("answer") == ans_l:
            recall_correct[ans_l] += 1
        if r.get("answer") in pick_counts:
            pick_counts[r["answer"]] += 1

    recall = {L: (recall_correct[L] / recall_total[L]) if recall_total[L] else None
              for L in letters}
    recall_vals = [recall[L] for L in letters if recall[L] is not None]

    picked = [pick_counts[L] for L in letters]
    total_picked = sum(picked)
    expected = total_picked / n_letters if total_picked else 0
    chi2 = (sum((o - expected) ** 2 / expected for o in picked)
            if expected else 0.0)
    p_value = stats.chi2.sf(chi2, df=n_letters - 1) if total_picked else None

    return {
        "per_letter_recall": {L: (round(v, 4) if v is not None else None) for L, v in recall.items()},
        "recall_std": round(pstdev(recall_vals), 4) if recall_vals else None,
        "recall_max_minus_min": round(max(recall_vals) - min(recall_vals), 4) if len(recall_vals) > 1 else None,
        "pick_distribution": {L: pick_counts[L] for L in letters},
        "pick_chi2": round(chi2, 4),
        "pick_chi2_pvalue": (round(p_value, 6) if p_value is not None else None),
        "method": "Zheng et al. 2023 (arXiv:2309.03882) Sec 2.2; std of per-letter recall",
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
    ap.add_argument("--dataset", default=None, help="dataset label stored in results (default: italian_ssm_shuffled)")
    ap.add_argument("--variant", type=int, default=0,
                    help="which shuffled variant to evaluate (0 = seed 42, backward-compatible). "
                         "Higher variants are independent option-permutations for selection-bias measurement.")
    args = ap.parse_args()

    # dataset label (module-level constant, read by run_model)
    if args.dataset:
        globals()["DATASET_NAME"] = args.dataset

    # select the shuffled variant file + dataset label
    if args.variant != 0:
        vfile = BASE / "data" / f"ssm_questions_shuffled_v{args.variant}.json"
        if not vfile.exists():
            print(f"Variant {args.variant} file not found: {vfile}. "
                  f"Generate it first: python3 scripts/shuffle_answers.py --variants {args.variant+1}")
            sys.exit(1)
        globals()["QUESTIONS_FILE"] = vfile
        globals()["DATASET_NAME"] = f"italian_ssm_shuffled_v{args.variant}"
    else:
        globals()["VARIANT"] = 0

    questions = load_questions()
    print(f"Loaded {len(questions)} questions from EuropeMedQA SSM (Italian) — variant {args.variant}")

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
            # checkpoint file allows crash-resume; deleted once the run completes
            ckpt = RESULTS_DIR / f"{model.replace(':','-')}_checkpoint.json"
            result = run_model(model, questions, limit=args.limit, think=args.thinking,
                               endpoint=args.endpoint, checkpoint_path=str(ckpt))
            # clean up checkpoint on success
            if ckpt.exists():
                ckpt.unlink()
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
