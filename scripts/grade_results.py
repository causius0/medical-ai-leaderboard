#!/usr/bin/env python3
"""
Medical AI Leaderboard - Grading Script

This script grades AI model answers against the solution key and updates
the leaderboard with the results.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file with error handling."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def validate_answers_format(answers_data: Dict[str, Any]) -> None:
    """Validate the answers JSON format."""
    required_fields = ['model_name', 'answers']

    for field in required_fields:
        if field not in answers_data:
            raise ValueError(f"Missing required field in answers: {field}")

    if not isinstance(answers_data['answers'], list):
        raise ValueError("'answers' must be a list")

    for idx, answer in enumerate(answers_data['answers']):
        if not isinstance(answer, dict):
            raise ValueError(f"Answer {idx} must be a dictionary")

        if 'question_id' not in answer:
            raise ValueError(f"Answer {idx} missing 'question_id'")

        if 'chosen_answer' not in answer:
            raise ValueError(f"Answer {idx} missing 'chosen_answer'")


def validate_solutions_format(solutions_data: Dict[str, Any]) -> None:
    """Validate the solutions JSON format."""
    if 'questions' not in solutions_data:
        raise ValueError("Missing 'questions' field in solutions")

    if not isinstance(solutions_data['questions'], list):
        raise ValueError("'questions' must be a list")

    for idx, question in enumerate(solutions_data['questions']):
        if not isinstance(question, dict):
            raise ValueError(f"Question {idx} must be a dictionary")

        if 'id' not in question:
            raise ValueError(f"Question {idx} missing 'id'")

        if 'correct_answer' not in question:
            raise ValueError(f"Question {idx} missing 'correct_answer'")


def grade_answers(
    answers_data: Dict[str, Any],
    solutions_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Grade the answers against the solutions.

    Returns a dictionary with grading results including:
    - total_correct: total number of correct answers
    - total_questions: total number of questions
    - accuracy: overall accuracy percentage
    - specialty_breakdown: performance per specialty
    - source_breakdown: performance per source
    """
    # Create a lookup dictionary for solutions
    solutions_lookup = {}
    specialties = {}
    sources = {}

    for question in solutions_data['questions']:
        qid = question['id']
        solutions_lookup[qid] = question['correct_answer']
        specialties[qid] = question.get('specialty', 'Unknown')
        sources[qid] = question.get('source', 'Unknown')

    # Track results
    total_correct = 0
    total_questions = len(answers_data['answers'])
    specialty_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    source_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    unknown_question_ids = []

    # Grade each answer
    for answer in answers_data['answers']:
        qid = answer['question_id']
        chosen = answer['chosen_answer']

        if qid not in solutions_lookup:
            unknown_question_ids.append(qid)
            continue

        correct_answer = solutions_lookup[qid]
        specialty = specialties[qid]
        source = sources[qid]

        # Update specialty stats
        specialty_stats[specialty]['total'] += 1

        # Update source stats
        source_stats[source]['total'] += 1

        # Check if correct
        if chosen == correct_answer:
            total_correct += 1
            specialty_stats[specialty]['correct'] += 1
            source_stats[source]['correct'] += 1

    # Warn about unknown question IDs
    if unknown_question_ids:
        print(f"Warning: Unknown question IDs: {unknown_question_ids}", file=sys.stderr)

    # Calculate accuracy
    accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0

    # Build specialty breakdown
    specialty_breakdown = {}
    for specialty, stats in specialty_stats.items():
        specialty_breakdown[specialty] = {
            'correct': stats['correct'],
            'total': stats['total'],
            'accuracy': round(stats['correct'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0.0
        }

    # Build source breakdown
    source_breakdown = {}
    for source, stats in source_stats.items():
        source_breakdown[source] = {
            'correct': stats['correct'],
            'total': stats['total'],
            'accuracy': round(stats['correct'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0.0
        }

    return {
        'total_correct': total_correct,
        'total_questions': total_questions,
        'accuracy': round(accuracy, 1),
        'specialty_breakdown': specialty_breakdown,
        'source_breakdown': source_breakdown
    }


def create_model_entry(
    answers_data: Dict[str, Any],
    grading_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a model entry for the leaderboard."""
    return {
        'name': answers_data['model_name'],
        'version': answers_data.get('model_version', 'unknown'),
        'timestamp': answers_data.get('timestamp', datetime.now().isoformat() + 'Z'),
        'total_correct': grading_results['total_correct'],
        'total_questions': grading_results['total_questions'],
        'accuracy': grading_results['accuracy'],
        'specialty_breakdown': grading_results['specialty_breakdown'],
        'source_breakdown': grading_results['source_breakdown']
    }


def load_or_create_leaderboard(leaderboard_path: str) -> Dict[str, Any]:
    """Load existing leaderboard or create a new one."""
    path = Path(leaderboard_path)

    if path.exists():
        try:
            return load_json_file(leaderboard_path)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load existing leaderboard: {e}", file=sys.stderr)
            print("Creating new leaderboard...", file=sys.stderr)

    return {'models': []}


def merge_model_into_leaderboard(
    leaderboard: Dict[str, Any],
    new_model: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge a new model entry into the leaderboard.
    If the model already exists, update it. Otherwise, add it.
    """
    models = leaderboard.get('models', [])
    model_name = new_model['name']

    # Check if model already exists
    updated = False
    for idx, model in enumerate(models):
        if model['name'] == model_name:
            # Update existing model
            models[idx] = new_model
            updated = True
            print(f"Updated existing model: {model_name}")
            break

    if not updated:
        # Add new model
        models.append(new_model)
        print(f"Added new model: {model_name}")

    # Sort models by accuracy (descending)
    models.sort(key=lambda x: x['accuracy'], reverse=True)

    leaderboard['models'] = models
    leaderboard['last_updated'] = datetime.now().isoformat() + 'Z'

    return leaderboard


def save_leaderboard(leaderboard: Dict[str, Any], output_path: str) -> None:
    """Save the leaderboard to a JSON file."""
    path = Path(output_path)

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(leaderboard, f, indent=2, ensure_ascii=False)

    print(f"Leaderboard saved to: {output_path}")


def print_summary(model_entry: Dict[str, Any]) -> None:
    """Print a summary of the grading results to console."""
    print("\n" + "="*60)
    print("GRADING SUMMARY")
    print("="*60)
    print(f"Model: {model_entry['name']}")
    if model_entry.get('version') and model_entry['version'] != 'unknown':
        print(f"Version: {model_entry['version']}")
    print(f"\nOverall Performance:")
    print(f"  Score: {model_entry['total_correct']}/{model_entry['total_questions']}")
    print(f"  Accuracy: {model_entry['accuracy']}%")

    if model_entry['specialty_breakdown']:
        print(f"\nSpecialty Breakdown:")
        for specialty, stats in sorted(model_entry['specialty_breakdown'].items()):
            print(f"  {specialty}: {stats['correct']}/{stats['total']} ({stats['accuracy']}%)")

    if model_entry['source_breakdown']:
        print(f"\nSource Breakdown:")
        for source, stats in sorted(model_entry['source_breakdown'].items()):
            print(f"  {source}: {stats['correct']}/{stats['total']} ({stats['accuracy']}%)")

    print("="*60 + "\n")


def main():
    """Main entry point for the grading script."""
    parser = argparse.ArgumentParser(
        description='Grade AI model answers and update the leaderboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --answers results/llama3-70b.json
  %(prog)s --answers results/gpt4.json --solutions data/solutions.json
  %(prog)s --answers results/claude.json --output custom/leaderboard.json
        """
    )

    parser.add_argument(
        '--answers',
        required=True,
        help='Path to AI answers JSON file'
    )

    parser.add_argument(
        '--solutions',
        default='data/solutions.json',
        help='Path to solutions JSON file (default: data/solutions.json)'
    )

    parser.add_argument(
        '--output',
        default='frontend/public/leaderboard.json',
        help='Path to output leaderboard JSON file (default: frontend/public/leaderboard.json)'
    )

    args = parser.parse_args()

    try:
        # Load input files
        print(f"Loading answers from: {args.answers}")
        answers_data = load_json_file(args.answers)
        validate_answers_format(answers_data)

        print(f"Loading solutions from: {args.solutions}")
        solutions_data = load_json_file(args.solutions)
        validate_solutions_format(solutions_data)

        # Grade the answers
        print("Grading answers...")
        grading_results = grade_answers(answers_data, solutions_data)

        # Create model entry
        model_entry = create_model_entry(answers_data, grading_results)

        # Load or create leaderboard
        print(f"Loading leaderboard from: {args.output}")
        leaderboard = load_or_create_leaderboard(args.output)

        # Merge model into leaderboard
        leaderboard = merge_model_into_leaderboard(leaderboard, model_entry)

        # Save updated leaderboard
        save_leaderboard(leaderboard, args.output)

        # Print summary
        print_summary(model_entry)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
