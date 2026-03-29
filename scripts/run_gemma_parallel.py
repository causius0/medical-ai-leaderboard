#!/usr/bin/env python3
"""
Parallel Gemma 3 4B evaluation - processes a specific range of questions.
Designed to be run in multiple parallel instances.
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
    # Parse command line arguments
    if len(sys.argv) != 4:
        print("Usage: python run_gemma_parallel.py <start_idx> <end_idx> <worker_id>")
        print("Example: python run_gemma_parallel.py 0 200 worker1")
        sys.exit(1)

    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    worker_id = sys.argv[3]

    print(f"="*70)
    print(f"Gemma 3 4B Worker {worker_id}")
    print(f"Processing questions {start_idx} to {end_idx-1}")
    print(f"="*70)

    # Load text-only questions
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"

    print(f"\nLoading questions from: {questions_path}")
    with open(questions_path, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)

    # Get the subset for this worker
    questions = all_questions[start_idx:end_idx]
    total_questions = len(questions)

    print(f"Worker {worker_id} assigned {total_questions} questions (indices {start_idx}-{end_idx-1})")

    # Verification: Strip correct answers before sending to model
    model_questions = []
    for q in questions:
        q_copy = q.copy()
        if 'correct_answer' in q_copy:
            del q_copy['correct_answer']
        model_questions.append(q_copy)

    # Initialize components
    client = OpenRouterClient()
    builder = PromptBuilder()

    # Model config
    model_id = "google/gemma-3-4b-it"
    model_name = "Gemma 3 4B"
    temperature = 0.7
    batch_size = 50  # Process 50 questions at a time

    all_answers = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # Process in batches
    num_batches = (total_questions + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, total_questions)
        batch = model_questions[batch_start:batch_end]

        print(f"\n[{worker_id}] Batch {batch_idx + 1}/{num_batches} ({len(batch)} questions)")

        question_ids = [q['id'] for q in batch]
        message = builder.build_message(batch)

        print(f"[{worker_id}] Sending request to OpenRouter...")
        try:
            response = client.call_model(
                model=model_id,
                messages=[message],
                temperature=temperature,
                max_tokens=10000
            )

            if 'choices' not in response:
                print(f"[{worker_id}] ❌ Error in batch {batch_idx + 1}: Unexpected response format")
                continue

            response_text = response['choices'][0]['message']['content']

            # Parse response
            parser = ResponseParser(expected_question_ids=question_ids)
            batch_answers = parser.parse_response(response_text)
            print(f"[{worker_id}] ✓ Parsed {len(batch_answers)} answers from batch {batch_idx + 1}")

            all_answers.update(batch_answers)

            # Update usage
            usage = response.get('usage', {})
            total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
            total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
            total_usage["total_tokens"] += usage.get('total_tokens', 0)

            # Small delay between batches
            if batch_idx < num_batches - 1:
                time.sleep(2)

        except Exception as e:
            print(f"[{worker_id}] ❌ Exception in batch {batch_idx + 1}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n[{worker_id}] Complete! Parsed {len(all_answers)}/{total_questions} answers")

    # Save results with worker ID
    results = {
        "worker_id": worker_id,
        "model": "gemma",
        "model_id": model_id,
        "model_name": model_name,
        "timestamp": datetime.now().isoformat(),
        "start_idx": start_idx,
        "end_idx": end_idx,
        "num_questions": total_questions,
        "num_answered": len(all_answers),
        "usage": total_usage,
        "answers": ResponseParser().format_for_evaluation(all_answers)
    }

    # Save to temp directory
    output_dir = repo_root / "results" / "openrouter" / "temp"
    output_dir.mkdir(exist_ok=True, parents=True)

    output_path = output_dir / f"gemma_{worker_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[{worker_id}] ✅ Results saved to: {output_path}")
    print(f"[{worker_id}] Coverage: {len(all_answers)}/{total_questions} ({100*len(all_answers)/total_questions:.1f}%)")
    return str(output_path)

if __name__ == "__main__":
    main()
