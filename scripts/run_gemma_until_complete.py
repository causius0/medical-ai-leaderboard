#!/usr/bin/env python3
"""
Run Gemma 3 4B evaluation from scratch until ALL 1060 questions are answered.
Will keep retrying failed batches until 100% completion.
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
    print("Gemma 3 4B - COMPLETE Evaluation (Target: 1060/1060)")
    print("="*70)

    # Load text-only questions
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"
    print(f"\nLoading questions from: {questions_path}")
    with open(questions_path, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)

    # Strip correct answers
    model_questions = []
    for q in all_questions:
        q_copy = q.copy()
        if 'correct_answer' in q_copy:
            del q_copy['correct_answer']
        model_questions.append(q_copy)

    total_questions = len(model_questions)
    print(f"Loaded {total_questions} text-only questions.")
    print(f"Target: Answer ALL {total_questions} questions")

    # Initialize components
    client = OpenRouterClient()
    builder = PromptBuilder()

    # Model config
    model_id = "google/gemma-3-4b-it"
    model_name = "Gemma 3 4B"
    temperature = 0.7
    batch_size = 50

    all_answers = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # Track remaining questions
    remaining_questions = model_questions.copy()
    attempt = 1
    max_attempts = 10  # Prevent infinite loops

    while len(remaining_questions) > 0 and attempt <= max_attempts:
        print(f"\n{'='*70}")
        print(f"ATTEMPT #{attempt} - {len(remaining_questions)} questions remaining")
        print(f"{'='*70}")

        batch_answers = {}
        num_batches = (len(remaining_questions) + batch_size - 1) // batch_size

        for i in range(0, len(remaining_questions), batch_size):
            batch = remaining_questions[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            print(f"\n--- Processing Batch {batch_num}/{num_batches} ({len(batch)} questions) ---")

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
                    print(f"❌ Error in batch {batch_num}: Unexpected response format")
                    continue

                response_text = response['choices'][0]['message']['content']

                # Parse response
                parser = ResponseParser(expected_question_ids=question_ids)
                parsed_answers = parser.parse_response(response_text)
                print(f"Successfully parsed {len(parsed_answers)} answers from batch {batch_num}")

                # Merge into batch_answers
                for qid, answer in parsed_answers.items():
                    batch_answers[qid] = answer

                # Update usage
                usage = response.get('usage', {})
                total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
                total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
                total_usage["total_tokens"] += usage.get('total_tokens', 0)

                # Small delay between batches
                if i + batch_size < len(remaining_questions):
                    time.sleep(2)

            except Exception as e:
                print(f"❌ Exception in batch {batch_num}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Merge attempt answers with all_answers
        print(f"\nAttempt #{attempt} complete:")
        print(f"  Newly answered: {len(batch_answers)}")
        print(f"  Total unique: {len(all_answers) + len([k for k in batch_answers if k not in all_answers])}")

        for qid, answer in batch_answers.items():
            all_answers[qid] = answer

        # Find remaining questions
        answered_ids = set(all_answers.keys())
        remaining_questions = [q for q in model_questions if q['id'] not in answered_ids]

        completion = 100 * len(all_answers) / total_questions
        print(f"  Overall Progress: {len(all_answers)}/{total_questions} ({completion:.1f}%)")

        if len(remaining_questions) == 0:
            print(f"\n🎉 SUCCESS! All {total_questions} questions answered on attempt #{attempt}!")
            break
        else:
            print(f"  ⚠️  {len(remaining_questions)} questions still need answers")
            print(f"  Starting attempt #{attempt + 1}...")
            attempt += 1
            # Longer delay between full attempts
            time.sleep(5)

    # Final report
    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Questions answered: {len(all_answers)}")
    print(f"Questions remaining: {len(remaining_questions)}")
    print(f"Completion rate: {100*len(all_answers)/total_questions:.1f}%")
    print(f"Total attempts: {attempt}")

    if len(remaining_questions) > 0:
        print(f"\n⚠️  Could not complete {len(remaining_questions)} questions after {max_attempts} attempts")
        print(f"Missing question IDs:")
        for q in remaining_questions[:20]:
            print(f"  {q['id']}")
        if len(remaining_questions) > 20:
            print(f"  ... and {len(remaining_questions) - 20} more")

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
    output_path = output_dir / f"gemma_until_complete_{timestamp}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_path}")

    return str(output_path), len(all_answers) == total_questions

if __name__ == "__main__":
    result_path, complete = main()
    sys.exit(0 if complete else 1)
