#!/usr/bin/env python3
"""
Final retry: Process remaining questions individually for maximum reliability.
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
from response_parser import ResponseParser

def main():
    print("="*70)
    print("Gemma 3 4B: Final Retry (Individual Questions)")
    print("="*70)

    # Load latest results
    result_files = list((repo_root / "results" / "openrouter").glob("gemma_3_4b_final_*.json"))
    if not result_files:
        print("❌ No results found!")
        return

    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"\nLoading: {latest_file.name}")

    with open(latest_file, 'r') as f:
        data = json.load(f)

    existing_answers = {a['id']: a['answer'] for a in data.get('answers', [])}

    # Load all questions
    with open(repo_root / "data" / "ssm_questions_text_only.json") as f:
        all_questions = json.load(f)

    # Find missing questions
    missing = []
    for q in all_questions:
        if q['id'] not in existing_answers:
            q_copy = q.copy()
            if 'correct_answer' in q_copy:
                del q_copy['correct_answer']
            missing.append(q_copy)

    print(f"\nMissing questions: {len(missing)}")

    if not missing:
        print("✅ All questions answered!")
        return

    # Initialize client
    client = OpenRouterClient()
    model_id = "google/gemma-3-4b-it"

    new_answers = {}
    parser = ResponseParser()

    # Process each question individually with simpler prompt
    for idx, question in enumerate(missing, 1):
        qid = question['id']
        print(f"\n[{idx}/{len(missing)}] Question {qid}")

        # Build simple prompt
        prompt = f"""You are a medical expert answering a multiple-choice question.

Question ID: {question['id']}
Question: {question['question']}

Options:
A) {question['options'][0]['text']}
B) {question['options'][1]['text']}
C) {question['options'][2]['text']}
D) {question['options'][3]['text']}
E) {question['options'][4]['text']}

Select the single best answer (A, B, C, D, or E). Reply with ONLY the letter."""

        try:
            response = client.call_model(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=10
            )

            if 'choices' in response:
                answer_text = response['choices'][0]['message']['content'].strip().upper()

                # Extract single letter
                for letter in ['A', 'B', 'C', 'D', 'E']:
                    if letter in answer_text:
                        new_answers[qid] = letter
                        print(f"  ✓ Answer: {letter}")
                        break
                else:
                    print(f"  ⚠️  Could not parse: {answer_text}")

                time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'='*70}")
    print(f"FINAL RETRY SUMMARY")
    print(f"{'='*70}")
    print(f"Questions retried: {len(missing)}")
    print(f"New answers: {len(new_answers)}")

    # Merge answers
    all_answers = {**existing_answers, **new_answers}
    total = len(all_questions)
    coverage = 100 * len(all_answers) / total

    print(f"Total answers: {len(all_answers)}/{total}")
    print(f"Coverage: {coverage:.1f}%")

    # Check remaining missing
    still_missing = [q['id'] for q in all_questions if q['id'] not in all_answers]
    if still_missing:
        print(f"\nStill missing {len(still_missing)} questions:")
        for qid in still_missing:
            print(f"  - {qid}")

    # Format and save
    formatted_answers = [{"id": k, "answer": v} for k, v in sorted(all_answers.items())]

    final_result = {
        "model": "gemma",
        "model_id": "google/gemma-3-4b-it",
        "model_name": "Gemma 3 4B",
        "timestamp": datetime.now().isoformat(),
        "num_questions": total,
        "num_answered": len(all_answers),
        "coverage_percent": round(coverage, 1),
        "answers": formatted_answers
    }

    output_path = repo_root / "results" / "openrouter" / f"gemma_3_4b_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    main()
