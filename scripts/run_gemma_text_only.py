#!/usr/bin/env python3
"""
Custom script to run Gemma 3 4B evaluation on text-only questions in batches.
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
    print("Gemma 3 4B Evaluation on Text-Only Questions (Batched)")
    print("="*70)

    # Load text-only questions
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"

    print(f"\nLoading questions from: {questions_path}")
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # Verification: Strip correct answers before sending to model
    model_questions = []
    for q in questions:
        q_copy = q.copy()
        if 'correct_answer' in q_copy:
            del q_copy['correct_answer']
        model_questions.append(q_copy)

    total_questions = len(model_questions)
    print(f"Loaded {total_questions} text-only questions.")

    # Initialize components
    client = OpenRouterClient()
    builder = PromptBuilder()

    # Model config - Using the prompt from docs/prompt.txt
    model_id = "google/gemma-3-4b-it"  # Paid version to avoid rate limits
    model_name = "Gemma 3 4B"
    temperature = 0.7
    batch_size = 50  # Reduced from 200 to avoid context window issues

    all_answers = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # Process in batches
    for i in range(0, total_questions, batch_size):
        batch = model_questions[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_questions + batch_size - 1) // batch_size

        print(f"\n--- Processing Batch {batch_num}/{total_batches} ({len(batch)} questions) ---")

        question_ids = [q['id'] for q in batch]
        message = builder.build_message(batch)

        print("Sending request to OpenRouter...")
        try:
            response = client.call_model(
                model=model_id,
                messages=[message],
                temperature=temperature,
                max_tokens=10000 # reduced max_tokens per batch
            )

            if 'choices' not in response:
                print(f"❌ Error in batch {batch_num}: Unexpected response format")
                print(json.dumps(response, indent=2))
                continue

            response_text = response['choices'][0]['message']['content']

            # Parse response
            parser = ResponseParser(expected_question_ids=question_ids)
            batch_answers = parser.parse_response(response_text)
            print(f"Successfully parsed {len(batch_answers)} answers from batch {batch_num}")

            all_answers.update(batch_answers)

            # Update usage
            usage = response.get('usage', {})
            total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
            total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
            total_usage["total_tokens"] += usage.get('total_tokens', 0)

            # Small delay between batches
            if i + batch_size < total_questions:
                time.sleep(2)

        except Exception as e:
            print(f"❌ Exception in batch {batch_num}: {e}")
            continue

    print(f"\nFinal evaluation complete. Total parsed answers: {len(all_answers)}/{total_questions}")

    # Format results
    results = {
        "model": "gemma",
        "model_id": model_id,
        "model_name": model_name,
        "timestamp": datetime.now().isoformat(),
        "num_questions": total_questions,
        "num_answered": len(all_answers),
        "usage": total_usage,
        "answers": ResponseParser().format_for_evaluation(all_answers)
    }

    # Save results
    output_dir = repo_root / "results" / "openrouter"
    output_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"gemma_text_only_batched_{timestamp}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_path}")
    return str(output_path)

if __name__ == "__main__":
    main()
