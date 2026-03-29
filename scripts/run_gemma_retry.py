#!/usr/bin/env python3
"""
Re-run Gemma 3 4B on missing questions to achieve 100% coverage.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Load environment variables
repo_root = Path(__file__).parent.parent
env_file = repo_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from openrouter_client import OpenRouterClient
from prompt_builder import PromptBuilder
from response_parser import ResponseParser

def main():
    print("="*70)
    print("Gemma 3 4B: Re-running Missing Questions")
    print("="*70)

    # Load missing questions
    missing_file = repo_root / "results" / "openrouter" / "temp" / "missing_questions.json"

    if not missing_file.exists():
        print("❌ No missing questions file found!")
        return

    with open(missing_file, 'r') as f:
        questions = json.load(f)

    print(f"\nFound {len(questions)} missing questions")
    print(f"Questions: {[q['id'] for q in questions[:10]]}...")

    # Load existing merged results
    merged_files = list((repo_root / "results" / "openrouter").glob("gemma_merged_*.json"))
    if not merged_files:
        print("❌ No merged results found!")
        return

    latest_merged = max(merged_files, key=lambda p: p.stat().st_mtime)
    print(f"\nLoading existing merged results from: {latest_merged.name}")

    with open(latest_merged, 'r') as f:
        merged_data = json.load(f)

    existing_answers = {a['id']: a['answer'] for a in merged_data.get('answers', [])}
    print(f"Existing answers: {len(existing_answers)}")

    # Initialize components
    client = OpenRouterClient()
    builder = PromptBuilder()

    # Model config
    model_id = "google/gemma-3-4b-it"
    temperature = 0.7
    batch_size = 50  # All questions fit in one batch

    print(f"\nProcessing {len(questions)} questions in batches of {batch_size}...")

    new_answers = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # Process in batches
    num_batches = (len(questions) + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(questions))
        batch = questions[batch_start:batch_end]

        print(f"\n--- Batch {batch_idx + 1}/{num_batches} ({len(batch)} questions) ---")

        question_ids = [q['id'] for q in batch]
        message = builder.build_message(batch)

        print("Sending request to OpenRouter...")
        try:
            response = client.call_model(
                model=model_id,
                messages=[message],
                temperature=temperature,
                max_tokens=10000
            )

            if 'choices' not in response:
                print(f"❌ Error: Unexpected response format")
                print(json.dumps(response, indent=2))
                continue

            response_text = response['choices'][0]['message']['content']

            # Parse response
            parser = ResponseParser(expected_question_ids=question_ids)
            batch_answers = parser.parse_response(response_text)
            print(f"✓ Parsed {len(batch_answers)} answers")

            new_answers.update(batch_answers)

            # Update usage
            usage = response.get('usage', {})
            total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
            total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
            total_usage["total_tokens"] += usage.get('total_tokens', 0)

            # Small delay
            if batch_idx < num_batches - 1:
                time.sleep(2)

        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*70}")
    print(f"RETRY SUMMARY")
    print(f"{'='*70}")
    print(f"Questions to retry: {len(questions)}")
    print(f"New answers obtained: {len(new_answers)}")

    # Merge with existing answers
    all_answers = {**existing_answers, **new_answers}
    total_questions = merged_data.get('num_questions', 1060)

    print(f"Total unique answers: {len(all_answers)}")
    print(f"Coverage: {100*len(all_answers)/total_questions:.1f}%")

    # Check for any still-missing questions
    all_ids = {q['id'] for q in questions}
    answered_ids = set(all_answers.keys())
    still_missing = all_ids - answered_ids

    if still_missing:
        print(f"\n⚠️  Still missing {len(still_missing)} questions:")
        for qid in sorted(still_missing):
            print(f"  - {qid}")

    # Format answers
    formatted_answers = []
    for qid, answer in sorted(all_answers.items()):
        formatted_answers.append({
            "id": qid,
            "answer": answer
        })

    # Create final merged result
    final_result = {
        "model": "gemma",
        "model_id": "google/gemma-3-4b-it",
        "model_name": "Gemma 3 4B",
        "timestamp": datetime.now().isoformat(),
        "num_questions": total_questions,
        "num_answered": len(all_answers),
        "coverage_percent": round(100 * len(all_answers) / total_questions, 1),
        "usage": {
            "prompt_tokens": merged_data.get('usage', {}).get('prompt_tokens', 0) + total_usage["prompt_tokens"],
            "completion_tokens": merged_data.get('usage', {}).get('completion_tokens', 0) + total_usage["completion_tokens"],
            "total_tokens": merged_data.get('usage', {}).get('total_tokens', 0) + total_usage["total_tokens"]
        },
        "retry_stats": {
            "questions_retried": len(questions),
            "new_answers_obtained": len(new_answers),
            "retry_success_rate": round(100 * len(new_answers) / len(questions), 1) if questions else 0
        },
        "answers": formatted_answers
    }

    # Save final result
    output_path = repo_root / "results" / "openrouter" / f"gemma_3_4b_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Final results saved to: {output_path}")
    print(f"📊 Final coverage: {len(all_answers)}/{total_questions} ({100*len(all_answers)/total_questions:.1f}%)")

    return output_path

if __name__ == "__main__":
    main()
