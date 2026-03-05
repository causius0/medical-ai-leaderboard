#!/usr/bin/env python3
"""
Script to evaluate gemma-3-4b's performance on the SSM medical questions.
Compares the model's answers against the ground truth and calculates accuracy.
"""
import json
import sys
from collections import defaultdict

def load_json_file(filepath):
    """Load a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)

def evaluate_predictions(questions_with_solution, model_predictions):
    """
    Compare model predictions against ground truth.

    Args:
        questions_with_solution: List of questions with correct answers
        model_predictions: Dict or list of model predictions

    Returns:
        Dictionary with evaluation metrics
    """
    # Create a lookup dictionary for ground truth
    ground_truth = {}
    for q in questions_with_solution:
        q_id = q['id']
        correct_letter = q['correct_answer']['letter']
        ground_truth[q_id] = correct_letter

    # Convert predictions to dict if they're in list format
    if isinstance(model_predictions, list):
        predictions = {p['id']: p['answer'] for p in model_predictions}
    elif isinstance(model_predictions, dict) and 'answers' in model_predictions:
        predictions = {p['id']: p['answer'] for p in model_predictions['answers']}
    else:
        predictions = model_predictions

    # Evaluate
    results = {
        'total': len(ground_truth),
        'correct': 0,
        'incorrect': 0,
        'missing': 0,
        'errors': []
    }

    # Track answer distribution
    prediction_distribution = defaultdict(int)
    correct_distribution = defaultdict(int)

    for q_id, correct_answer in ground_truth.items():
        correct_distribution[correct_answer] += 1

        if q_id not in predictions:
            results['missing'] += 1
            results['errors'].append({
                'id': q_id,
                'type': 'missing',
                'correct': correct_answer
            })
            continue

        predicted = predictions[q_id]

        # Count prediction distribution
        if predicted in ['A', 'B', 'C', 'D', 'E']:
            prediction_distribution[predicted] += 1

        if predicted == correct_answer:
            results['correct'] += 1
        else:
            results['incorrect'] += 1
            results['errors'].append({
                'id': q_id,
                'type': 'incorrect',
                'predicted': predicted,
                'correct': correct_answer
            })

    results['accuracy'] = results['correct'] / results['total'] if results['total'] > 0 else 0
    results['prediction_distribution'] = dict(prediction_distribution)
    results['correct_distribution'] = dict(correct_distribution)

    return results

def print_results(results):
    """Print evaluation results in a readable format."""
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print("="*70)

    print(f"\nOverall Performance:")
    print(f"  Total Questions: {results['total']}")
    print(f"  Correct: {results['correct']}")
    print(f"  Incorrect: {results['incorrect']}")
    print(f"  Missing: {results['missing']}")
    print(f"  Accuracy: {results['accuracy']:.2%}")

    print(f"\nAnswer Distribution:")
    print(f"\n  Ground Truth Distribution:")
    for letter in sorted(results['correct_distribution'].keys()):
        count = results['correct_distribution'][letter]
        pct = count / results['total'] * 100
        print(f"    {letter}: {count:4d} ({pct:5.1f}%)")

    print(f"\n  Model Prediction Distribution:")
    for letter in ['A', 'B', 'C', 'D', 'E']:
        count = results['prediction_distribution'].get(letter, 0)
        pct = count / results['total'] * 100 if results['total'] > 0 else 0
        print(f"    {letter}: {count:4d} ({pct:5.1f}%)")

    if results['errors'] and results['incorrect'] > 0:
        print(f"\nFirst 20 Incorrect Answers:")
        print("-" * 70)
        for i, error in enumerate(results['errors'][:20]):
            if error['type'] == 'incorrect':
                print(f"  {error['id']}: Predicted {error['predicted']}, Correct: {error['correct']}")

    print("\n" + "="*70)

def main():
    """Main evaluation function."""
    if len(sys.argv) < 2:
        print("Usage: python evaluate_ssm_results.py <model_predictions.json>")
        print("\nThis script will:")
        print("  1. Load the model's predictions from the provided JSON file")
        print("  2. Load the ground truth from ssm_questions_with_solution.json")
        print("  3. Calculate accuracy metrics")
        print("  4. Display detailed results")
        sys.exit(1)

    # File paths
    predictions_file = sys.argv[1]
    solution_file = '/Users/causius/Desktop/ssm_questions_with_solution.json'

    # Load data
    print(f"Loading model predictions from: {predictions_file}")
    model_predictions = load_json_file(predictions_file)

    print(f"Loading ground truth from: {solution_file}")
    questions_with_solution = load_json_file(solution_file)

    # Evaluate
    print("\nEvaluating predictions...")
    results = evaluate_predictions(questions_with_solution, model_predictions)

    # Print results
    print_results(results)

    # Save detailed results
    output_file = '/Users/causius/Desktop/evaluation_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == '__main__':
    main()
