#!/usr/bin/env python3
"""
Generate mock evaluation results for the Medical AI Leaderboard.

This script creates realistic-looking evaluation result files that match
the expected JSON schema. The data engineering team should produce files
in this exact format when running actual model evaluations.

USAGE:
    python scripts/generate_mock_results.py

OUTPUT:
    results/openrouter/<model>_<timestamp>.json files
    results/leaderboard_data.json (aggregated for the frontend)
"""

import json
import os
import random
import hashlib
from datetime import datetime, timezone
from pathlib import Path

SEED = 42
random.seed(SEED)

# ─── Models to evaluate ───────────────────────────────────────────────
MODELS = [
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "OpenAI",
        "provider_logo": "openai",
        "model_id": "openai/gpt-4o",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.78,
        "specialty_variance": 0.08,
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o mini",
        "provider": "OpenAI",
        "provider_logo": "openai",
        "model_id": "openai/gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.68,
        "specialty_variance": 0.10,
    },
    {
        "id": "claude-sonnet-4",
        "name": "Claude Sonnet 4",
        "provider": "Anthropic",
        "provider_logo": "anthropic",
        "model_id": "anthropic/claude-sonnet-4",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.82,
        "specialty_variance": 0.07,
    },
    {
        "id": "claude-haiku-3.5",
        "name": "Claude 3.5 Haiku",
        "provider": "Anthropic",
        "provider_logo": "anthropic",
        "model_id": "anthropic/claude-3-5-haiku",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.71,
        "specialty_variance": 0.09,
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "provider": "Google",
        "provider_logo": "google",
        "model_id": "google/gemini-2.5-pro",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.80,
        "specialty_variance": 0.06,
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "Google",
        "provider_logo": "google",
        "model_id": "google/gemini-2.5-flash",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.72,
        "specialty_variance": 0.09,
    },
    {
        "id": "llama-3.3-70b",
        "name": "Llama 3.3 70B",
        "provider": "Meta",
        "provider_logo": "meta",
        "model_id": "meta-llama/llama-3.3-70b-instruct",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.65,
        "specialty_variance": 0.11,
    },
    {
        "id": "qwen3-235b",
        "name": "Qwen3 235B",
        "provider": "Alibaba",
        "provider_logo": "alibaba",
        "model_id": "qwen/qwen3-235b-a22b",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.74,
        "specialty_variance": 0.09,
    },
    {
        "id": "mistral-large",
        "name": "Mistral Large",
        "provider": "Mistral AI",
        "provider_logo": "mistral",
        "model_id": "mistralai/mistral-large",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.70,
        "specialty_variance": 0.10,
    },
    {
        "id": "deepseek-r1",
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "provider_logo": "deepseek",
        "model_id": "deepseek/deepseek-r1",
        "temperature": 0.0,
        "max_tokens": 4096,
        "base_accuracy": 0.76,
        "specialty_variance": 0.08,
    },
]

# ─── Datasets (sources) ───────────────────────────────────────────────
# Present datasets have questions; upcoming ones are mentioned in SOURCES.md
DATASETS = {
    "italian_ssm": {
        "name": "Italian SSM",
        "full_name": "Selezione Specializzazioni in Medicina",
        "language": "Italian",
        "country": "Italy 🇮🇹",
        "status": "active",
        "description": "Italian National Medical Residency Examination",
        "question_count": 1120,
    },
    "spanish_mir": {
        "name": "Spanish MIR",
        "full_name": "Médico Interno Residente",
        "language": "Spanish",
        "country": "Spain 🇪🇸",
        "status": "upcoming",
        "description": "Spanish Medical Residency Examination",
        "question_count": 0,
    },
    "portuguese": {
        "name": "Portuguese Exam",
        "full_name": "Prova de Acesso à Especialização",
        "language": "Portuguese",
        "country": "Portugal 🇵🇹",
        "status": "upcoming",
        "description": "Portuguese Medical Residency Examination",
        "question_count": 0,
    },
    "french": {
        "name": "French Exam",
        "full_name": "Concours d'Internat",
        "language": "French",
        "country": "France 🇫🇷",
        "status": "upcoming",
        "description": "French Medical Residency Examination",
        "question_count": 0,
    },
}


def load_questions():
    """Load the actual question data from the repo."""
    path = Path("data/ssm_questions_with_solution.json")
    if not path.exists():
        raise FileNotFoundError(f"Questions file not found: {path}")
    with open(path) as f:
        return json.load(f)


def generate_model_results(model, questions):
    """
    Generate realistic evaluation results for a single model.
    
    This produces output in the EXACT format that the data engineering
    pipeline should produce when running real evaluations.
    """
    # Per-specialty accuracy modifiers (some models are better at certain specialties)
    specialty_mods = {}
    for q in questions:
        spec = q.get("specialty", "Unknown")
        if spec not in specialty_mods:
            specialty_mods[spec] = random.gauss(0, model["specialty_variance"])

    responses = []
    correct_count = 0

    for q in questions:
        spec = q.get("specialty", "Unknown")
        correct_letter = q["correct_answer"]["letter"]
        options = [o["letter"] for o in q["options"]]

        # Compute probability of correct answer
        accuracy = model["base_accuracy"] + specialty_mods.get(spec, 0)
        accuracy = max(0.2, min(0.95, accuracy))

        if random.random() < accuracy:
            answer = correct_letter
            correct_count += 1
        else:
            # Pick a wrong answer
            wrong_options = [o for o in options if o != correct_letter]
            answer = random.choice(wrong_options)

        confidence = random.randint(55, 98) if answer == correct_letter else random.randint(30, 75)

        responses.append({
            "question_id": q["id"],
            "answer": answer,
            "confidence": confidence,
            "explanation": "",  # Filled in real evaluation
            "reasoning": "",    # Filled in real evaluation
            "tokens_used": random.randint(120, 600),
            "time_to_response": round(random.uniform(0.8, 5.5), 2),
            "refusal": False,
            "notes": "",
        })

    total = len(questions)
    accuracy_pct = round(correct_count / total * 100, 2)

    # Compute per-specialty breakdown
    specialty_breakdown = {}
    for q, r in zip(questions, responses):
        spec = q.get("specialty", "Unknown")
        if spec not in specialty_breakdown:
            specialty_breakdown[spec] = {"correct": 0, "total": 0}
        specialty_breakdown[spec]["total"] += 1
        if r["answer"] == q["correct_answer"]["letter"]:
            specialty_breakdown[spec]["correct"] += 1

    specialty_scores = {}
    for spec, data in specialty_breakdown.items():
        specialty_scores[spec] = round(data["correct"] / data["total"] * 100, 2)

    # Year breakdown
    year_breakdown = {}
    for q, r in zip(questions, responses):
        year = str(q.get("metadata", {}).get("test_year", "unknown"))
        if year not in year_breakdown:
            year_breakdown[year] = {"correct": 0, "total": 0}
        year_breakdown[year]["total"] += 1
        if r["answer"] == q["correct_answer"]["letter"]:
            year_breakdown[year]["correct"] += 1

    year_scores = {}
    for year, data in year_breakdown.items():
        year_scores[year] = round(data["correct"] / data["total"] * 100, 2)

    result = {
        "model_name": model["name"],
        "model_id": model["id"],
        "provider": model["provider"],
        "provider_logo": model["provider_logo"],
        "openrouter_model_id": model["model_id"],
        "test_date": "2025-05-15",
        "test_date_iso": "2025-05-15T14:30:00Z",
        "dataset": "italian_ssm",
        "temperature": model["temperature"],
        "top_p": 1.0,
        "max_tokens": model["max_tokens"],
        "prompt_template": "zero_shot_cot_medical",
        "total_questions_attempted": total,
        "total_questions_answered": total,
        "total_correct": correct_count,
        "overall_accuracy": accuracy_pct,
        "specialty_scores": specialty_scores,
        "year_scores": year_scores,
        "responses": responses,
        "metadata": {
            "generated_by": "mock_generator",
            "generation_method": "openrouter_api",
            "evaluation_pipeline_version": "1.0.0",
            "note": "MOCK DATA - generated for frontend development. Replace with real evaluation results.",
        },
    }
    return result


def generate_leaderboard_data(all_results, questions):
    """Generate the aggregated leaderboard JSON consumed by the frontend."""
    from collections import Counter

    # Compute specialty counts from actual data
    spec_counts = Counter(q.get("specialty", "") for q in questions)

    # Models ranked by accuracy
    models_ranked = sorted(all_results, key=lambda x: x["overall_accuracy"], reverse=True)

    models = []
    for rank, r in enumerate(models_ranked, 1):
        models.append({
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
        })

    # Get year range from actual data
    years = sorted(set(str(q.get("metadata", {}).get("test_year", "")) for q in questions))

    leaderboard = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "datasets": DATASETS,
        "specialties": dict(spec_counts),
        "years": years,
        "models": models,
    }
    return leaderboard


def main():
    base_dir = Path(__file__).parent.parent
    os.chdir(base_dir)

    questions = load_questions()
    print(f"Loaded {len(questions)} questions")

    results_dir = base_dir / "results" / "openrouter"
    results_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    for model in MODELS:
        result = generate_model_results(model, questions)
        all_results.append(result)

        # Save individual model result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model['id']}_{timestamp}.json"
        filepath = results_dir / filename
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  → {filename} (accuracy: {result['overall_accuracy']}%)")

    # Save aggregated leaderboard data
    leaderboard_data = generate_leaderboard_data(all_results, questions)
    leaderboard_path = base_dir / "results" / "leaderboard_data.json"
    with open(leaderboard_path, "w") as f:
        json.dump(leaderboard_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Leaderboard data saved to {leaderboard_path}")
    print(f"  {len(all_results)} models, {len(leaderboard_data['specialties'])} specialties")


if __name__ == "__main__":
    main()
