# Medical AI Leaderboard - Grading Script

This script grades AI model answers against the solution key and updates the leaderboard with the results.

## Usage

```bash
python scripts/grade_results.py --answers <path-to-answers.json>
```

### Arguments

- `--answers` (required): Path to AI answers JSON file
- `--solutions` (optional): Path to solutions JSON file (default: `data/solutions.json`)
- `--output` (optional): Path to output leaderboard JSON file (default: `frontend/public/leaderboard.json`)

### Examples

```bash
# Grade a model's answers
python scripts/grade_results.py --answers results/llama3-70b.json

# Specify custom solutions file
python scripts/grade_results.py --answers results/gpt4.json --solutions data/solutions.json

# Specify custom output location
python scripts/grade_results.py --answers results/claude.json --output custom/leaderboard.json
```

## Input Format

### Answers JSON

```json
{
  "model_name": "llama3-70b",
  "model_version": "optional version string",
  "timestamp": "2025-03-05T10:30:00Z",
  "answers": [
    {"question_id": 1, "chosen_answer": "B"},
    {"question_id": 2, "chosen_answer": "A"}
  ]
}
```

Required fields:
- `model_name`: Name of the AI model
- `answers`: Array of answer objects

Optional fields:
- `model_version`: Version string for the model
- `timestamp`: ISO 8601 timestamp of when the answers were generated

Answer object fields:
- `question_id`: Integer ID of the question
- `chosen_answer`: The answer choice (e.g., "A", "B", "C", "D")

### Solutions JSON

```json
{
  "questions": [
    {
      "id": 1,
      "correct_answer": "B",
      "specialty": "Cardiology",
      "source": "Italian SSM"
    }
  ]
}
```

Required fields:
- `questions`: Array of question objects

Question object fields:
- `id`: Unique integer ID
- `correct_answer`: The correct answer choice
- `specialty`: Medical specialty category (optional, defaults to "Unknown")
- `source`: Question source (optional, defaults to "Unknown")

## Output Format

The script generates/updates `leaderboard.json` with the following format:

```json
{
  "models": [
    {
      "name": "llama3-70b",
      "version": "v1.0",
      "timestamp": "2025-03-05T10:30:00Z",
      "total_correct": 142,
      "total_questions": 150,
      "accuracy": 94.5,
      "specialty_breakdown": {
        "Cardiology": {"correct": 45, "total": 50, "accuracy": 90.0}
      },
      "source_breakdown": {
        "Italian SSM": {"correct": 70, "total": 75, "accuracy": 93.3}
      }
    }
  ],
  "last_updated": "2025-03-05T10:30:00Z"
}
```

Models are automatically sorted by accuracy in descending order.

## Features

- **Automatic grading**: Compares model answers against solution key
- **Performance metrics**: Calculates overall accuracy and breakdowns by specialty and source
- **Leaderboard management**: Adds new models or updates existing ones
- **Sorted rankings**: Automatically sorts models by accuracy
- **Error handling**: Validates input formats and handles edge cases
- **Console summary**: Prints detailed grading results to console

## Behavior

### Adding New Models
When you grade a model that doesn't exist in the leaderboard, it's automatically added.

### Updating Existing Models
If you grade a model with the same name, the existing entry is updated with new results.

### Unknown Question IDs
If the answers JSON contains question IDs not found in the solutions, a warning is printed but processing continues.

### Error Handling
The script handles the following errors:
- Missing input files
- Invalid JSON format
- Missing required fields
- Invalid answer format

All errors are printed to stderr with exit code 1.

## Console Output

The script prints a summary showing:

```
============================================================
GRADING SUMMARY
============================================================
Model: test-model-1
Version: v1.0

Overall Performance:
  Score: 4/5
  Accuracy: 80.0%

Specialty Breakdown:
  Cardiology: 3/3 (100.0%)
  Neurology: 1/2 (50.0%)

Source Breakdown:
  Italian SSM: 3/3 (100.0%)
  USMLE: 1/2 (50.0%)
============================================================
```

## Exit Codes

- `0`: Success
- `1`: Error (missing files, invalid JSON, validation failures)
