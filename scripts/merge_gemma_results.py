#!/usr/bin/env python3
"""
Merge results from multiple Gemma workers into a single comprehensive result file.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def main():
    repo_root = Path(__file__).parent.parent
    temp_dir = repo_root / "results" / "openrouter" / "temp"

    print("="*70)
    print("Merging Gemma 3 4B Results from All Workers")
    print("="*70)

    # Find all temp result files
    temp_files = sorted(temp_dir.glob("gemma_worker*_*.json"))
    print(f"\nFound {len(temp_files)} worker result files")

    if not temp_files:
        print("❌ No temp files found!")
        return

    # Load all results
    all_results = []
    all_answers = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    for temp_file in temp_files:
        print(f"\nLoading: {temp_file.name}")
        with open(temp_file, 'r') as f:
            data = json.load(f)
            all_results.append(data)

            # Merge answers
            for answer in data.get('answers', []):
                qid = answer['id']
                # Skip duplicates (keep first occurrence)
                if qid not in all_answers:
                    all_answers[qid] = answer['answer']

            # Accumulate usage
            usage = data.get('usage', {})
            total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
            total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
            total_usage["total_tokens"] += usage.get('total_tokens', 0)

            print(f"  - Worker {data.get('worker_id', 'unknown')}: {len(data.get('answers', []))} answers")

    # Load original questions to get total count
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"
    with open(questions_path, 'r') as f:
        all_questions = json.load(f)

    total_questions = len(all_questions)
    answered_questions = len(all_answers)

    print(f"\n{'='*70}")
    print(f"MERGE SUMMARY")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Questions answered: {answered_questions}")
    print(f"Coverage: {100*answered_questions/total_questions:.1f}%")
    print(f"Missing: {total_questions - answered_questions}")

    # Find missing question IDs
    answered_ids = set(all_answers.keys())
    all_ids = {q['id'] for q in all_questions}
    missing_ids = sorted(all_ids - answered_ids)

    if missing_ids:
        print(f"\nMissing question IDs ({len(missing_ids)}):")
        for i, qid in enumerate(missing_ids[:20], 1):  # Show first 20
            print(f"  {i}. {qid}")
        if len(missing_ids) > 20:
            print(f"  ... and {len(missing_ids) - 20} more")

    # Format results for evaluation
    formatted_answers = []
    for qid, answer in all_answers.items():
        formatted_answers.append({
            "id": qid,
            "answer": answer
        })

    # Create merged result
    merged_result = {
        "model": "gemma",
        "model_id": "google/gemma-3-4b-it",
        "model_name": "Gemma 3 4B",
        "timestamp": datetime.now().isoformat(),
        "num_workers": len(all_results),
        "num_questions": total_questions,
        "num_answered": answered_questions,
        "coverage_percent": round(100 * answered_questions / total_questions, 1),
        "usage": total_usage,
        "worker_files": [str(f.name) for f in temp_files],
        "missing_question_ids": missing_ids,
        "answers": formatted_answers
    }

    # Save merged result
    output_path = repo_root / "results" / "openrouter" / f"gemma_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Merged results saved to: {output_path}")

    # Also save missing questions for re-running
    if missing_ids:
        missing_file = repo_root / "results" / "openrouter" / "temp" / "missing_questions.json"
        missing_questions = [q for q in all_questions if q['id'] in missing_ids]

        # Strip correct answers
        for q in missing_questions:
            if 'correct_answer' in q:
                del q['correct_answer']

        with open(missing_file, 'w', encoding='utf-8') as f:
            json.dump(missing_questions, f, indent=2, ensure_ascii=False)

        print(f"📝 Missing questions saved to: {missing_file}")

    return output_path, len(missing_ids) if missing_ids else 0

if __name__ == "__main__":
    main()
