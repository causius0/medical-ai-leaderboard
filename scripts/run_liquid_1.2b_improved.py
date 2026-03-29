#!/usr/bin/env python3
"""
Improved Liquid LFM-2.5 1.2B evaluation with enhanced prompt engineering
"""

import os
import sys
import json
import time
import re
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

def build_enhanced_prompt(questions):
    """
    Build an enhanced prompt with explicit format instructions and few-shot examples
    """
    # Few-shot examples at the start
    examples = '''You are a medical expert answering multiple-choice questions.

EXAMPLE FORMAT (you MUST follow this exactly):
```json
{
  "answers": [
    {"id": "IT0001", "answer": "A"},
    {"id": "IT0002", "answer": "C"},
    {"id": "IT0003", "answer": "B"}
  ]
}
```

CRITICAL RULES:
1. Return ONLY valid JSON, no other text
2. Use exactly this format: {"answers": [{"id": "QUESTION_ID", "answer": "LETTER"}]}
3. Answer letter must be one of: A, B, C, D, E
4. Do NOT include explanations, commentary, or additional fields
5. Do NOT use function call format
6. Every question must have exactly one answer

'''

    # Build questions section
    questions_text = "QUESTIONS:\\n\\n"
    for i, q in enumerate(questions, 1):
        questions_text += f"{i}. ID: {q['id']}\\n"
        questions_text += f"{q['question']}\\n\\n"
        for opt in q['options']:
            questions_text += f"{opt['letter']}) {opt['text']}\\n"
        questions_text += "\\n"

    return examples + questions_text + "\\n\\nNow provide your answers in the exact JSON format shown above:"

def extract_answers_from_response(response_text, expected_ids):
    """
    Robust answer extraction that handles multiple formats
    """
    answers = {}

    # Try 1: Parse as JSON directly
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and 'answers' in data:
            for item in data['answers']:
                if 'id' in item and 'answer' in item:
                    answers[item['id']] = item['answer']
        if answers:
            return answers
    except:
        pass

    # Try 2: Extract JSON from code blocks
    json_pattern = r'```(?:json)?\\s*([\\s\\S]*?)\\s*```'
    matches = re.findall(json_pattern, response_text)
    for match in matches:
        try:
            data = json.loads(match.strip())
            if isinstance(data, dict) and 'answers' in data:
                for item in data['answers']:
                    if 'id' in item and 'answer' in item:
                        answers[item['id']] = item['answer']
            if answers:
                return answers
        except:
            continue

    # Try 3: Parse answer pairs from free text (fallback)
    # Look for patterns like "IT0001: A" or "IT0001 - A" or "IT0001 A"
    answer_pattern = r'(IT\\d+)\\s*[:\\-]?\\s*([ABCDE])'
    matches = re.findall(answer_pattern, response_text)
    for qid, answer in matches:
        if qid in expected_ids:
            answers[qid] = answer

    return answers

def main():
    print("="*70)
    print("Liquid LFM-2.5 1.2B Instruct - Improved Evaluation")
    print("="*70)

    # Load text-only questions
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"
    print(f"\\nLoading questions from: {questions_path}")
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # Strip correct answers
    model_questions = []
    for q in questions:
        q_copy = q.copy()
        if 'correct_answer' in q_copy:
            del q_copy['correct_answer']
        model_questions.append(q_copy)

    total_questions = len(model_questions)
    print(f"Loaded {total_questions} text-only questions.")

    # Initialize client
    client = OpenRouterClient()

    # Model config - smaller model, lower temperature, smaller batches
    model_id = "liquid/lfm-2.5-1.2b-instruct:free"
    model_name = "Liquid LFM-2.5 1.2B Instruct"
    temperature = 0.3  # Lower for more deterministic output
    batch_size = 25    # Smaller batches for better control

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

        print(f"\\n--- Processing Batch {batch_num}/{total_batches} ({len(batch)} questions) ---")

        question_ids = [q['id'] for q in batch]

        # Build enhanced prompt
        prompt = build_enhanced_prompt(batch)

        print("Sending request to OpenRouter...")
        try:
            response = client.call_model(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=8000
            )

            if 'choices' not in response:
                print(f"❌ Error in batch {batch_num}: Unexpected response format")
                continue

            response_text = response['choices'][0]['message']['content']

            # Extract answers with robust parsing
            batch_answers = extract_answers_from_response(response_text, set(question_ids))
            print(f"Extracted {len(batch_answers)} answers from batch {batch_num}")

            all_answers.update(batch_answers)

            # Update usage
            usage = response.get('usage', {})
            total_usage["prompt_tokens"] += usage.get('prompt_tokens', 0)
            total_usage["completion_tokens"] += usage.get('completion_tokens', 0)
            total_usage["total_tokens"] += usage.get('total_tokens', 0)

            # Progress update
            print(f"Progress: {len(all_answers)}/{total_questions} ({100*len(all_answers)/total_questions:.1f}%)")

            # Delay between batches
            if i + batch_size < total_questions:
                time.sleep(2)

        except Exception as e:
            print(f"❌ Exception in batch {batch_num}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\\nFinal evaluation complete. Total answers: {len(all_answers)}/{total_questions}")

    # Format results
    results = {
        "model": "liquid",
        "model_id": model_id,
        "model_name": model_name,
        "timestamp": datetime.now().isoformat(),
        "num_questions": total_questions,
        "num_answered": len(all_answers),
        "usage": total_usage,
        "answers": [
            {"id": q_id, "answer": answer}
            for q_id, answer in sorted(all_answers.items())
        ]
    }

    # Save results
    output_dir = repo_root / "results" / "openrouter"
    output_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"liquid_1.2b_improved_{timestamp}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\\n✅ Results saved to: {output_path}")

    if len(all_answers) == total_questions:
        print(f"\\n🎉 SUCCESS! All {total_questions} questions answered!")
    else:
        missing = total_questions - len(all_answers)
        print(f"\\n⚠️  Missing {missing} questions ({100*missing/total_questions:.1f}%)")

    return str(output_path)

if __name__ == "__main__":
    main()
