#!/usr/bin/env python3
"""
Add OpenRouter model results to the leaderboard
Calculates specialty breakdowns and updates leaderboard.json
"""

import json
import os
import sys
from datetime import datetime
from collections import defaultdict
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


def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filepath):
    """Save JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def calculate_specialty_breakdown(questions, predictions):
    """
    Calculate accuracy breakdown by medical specialty

    Args:
        questions: List of question dictionaries with specialty info
        predictions: Dict mapping question IDs to answers

    Returns:
        Dict with specialty breakdown
    """
    specialty_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    for question in questions:
        q_id = question['id']
        specialty = question.get('specialty', 'Unknown')

        if q_id in predictions:
            specialty_stats[specialty]['total'] += 1

            predicted_answer = predictions[q_id]
            correct_answer = question['correct_answer']['letter']

            if predicted_answer == correct_answer:
                specialty_stats[specialty]['correct'] += 1

    # Convert to format expected by leaderboard
    breakdown = {}
    for specialty, stats in specialty_stats.items():
        breakdown[specialty] = {
            'correct': stats['correct'],
            'total': stats['total'],
            'accuracy': round((stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1)
        }

    return breakdown


def add_model_to_leaderboard(results_file, questions_file, leaderboard_file):
    """
    Add model results to leaderboard

    Args:
        results_file: Path to model results JSON
        questions_file: Path to questions with solutions
        leaderboard_file: Path to leaderboard.json
    """
    print("Loading files...")
    results = load_json(results_file)
    questions = load_json(questions_file)
    leaderboard = load_json(leaderboard_file)

    # Extract predictions
    predictions = {a['id']: a['answer'] for a in results['answers']}

    # Calculate correct answers
    correct_count = 0
    for question in questions:
        q_id = question['id']
        if q_id in predictions:
            if predictions[q_id] == question['correct_answer']['letter']:
                correct_count += 1

    total_questions = len(predictions)
    accuracy = round((correct_count / total_questions * 100) if total_questions > 0 else 0, 1)

    print(f"\nModel: {results['model_name']}")
    print(f"Correct: {correct_count}/{total_questions}")
    print(f"Accuracy: {accuracy}%")

    # Calculate specialty breakdown
    print("\nCalculating specialty breakdown...")
    specialty_breakdown = calculate_specialty_breakdown(questions, predictions)

    print("\nSpecialty Breakdown:")
    for specialty, stats in sorted(specialty_breakdown.items()):
        print(f"  {specialty}: {stats['correct']}/{stats['total']} ({stats['accuracy']}%)")

    # Create model entry
    model_entry = {
        'name': results['model_name'],
        'model_id': results['model_id'],
        'version': results['timestamp'],
        'timestamp': results['timestamp'],
        'total_correct': correct_count,
        'total_questions': total_questions,
        'accuracy': accuracy,
        'specialty_breakdown': specialty_breakdown,
        'source_breakdown': {
            'Italian SSM': {
                'correct': correct_count,
                'total': total_questions,
                'accuracy': accuracy
            }
        },
        'metadata': {
            'provider': 'Alibaba (via OpenRouter)',
            'cost': f"${results['usage'].get('cost', 0):.4f}",
            'tokens': results['usage']['total_tokens'],
            'evaluation_method': 'OpenRouter API'
        }
    }

    # Check if model already exists
    model_names = [m['name'] for m in leaderboard['models']]
    if results['model_name'] in model_names:
        # Update existing entry
        print(f"\nUpdating existing model entry...")
        for i, model in enumerate(leaderboard['models']):
            if model['name'] == results['model_name']:
                leaderboard['models'][i] = model_entry
                break
    else:
        # Add new entry
        print(f"\nAdding new model to leaderboard...")
        leaderboard['models'].append(model_entry)

    # Sort by accuracy (highest first)
    leaderboard['models'].sort(key=lambda x: x['accuracy'], reverse=True)

    # Update last_updated
    leaderboard['last_updated'] = datetime.now().isoformat()

    # Save updated leaderboard
    save_json(leaderboard, leaderboard_file)
    print(f"\n✓ Leaderboard updated: {leaderboard_file}")

    # Print ranking
    print(f"\n{'='*70}")
    print("LEADERBOARD RANKINGS")
    print(f"{'='*70}")
    for i, model in enumerate(leaderboard['models'][:10], 1):
        print(f"{i:2d}. {model['name']:30s} {model['accuracy']:5.1f}%")

    return leaderboard


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python add_to_leaderboard.py <results_file>")
        print("\nExample:")
        print("  python add_to_leaderboard.py results/openrouter/qwen_20260309_140351.json")
        sys.exit(1)

    # Get file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    results_file = sys.argv[1]
    questions_file = os.path.join(repo_root, "data", "ssm_questions_with_solution.json")
    leaderboard_file = os.path.join(repo_root, "frontend", "public", "leaderboard.json")

    # Add to leaderboard
    add_model_to_leaderboard(results_file, questions_file, leaderboard_file)


if __name__ == "__main__":
    main()
