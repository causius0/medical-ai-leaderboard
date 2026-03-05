# Quick Start Guide - Grading Script

## Basic Usage

```bash
# Grade a model's answers
python scripts/grade_results.py --answers results/your-model.json
```

## Workflow

1. **Create your answers JSON file** (`results/my-model.json`):
```json
{
  "model_name": "my-model-name",
  "model_version": "v1.0",
  "timestamp": "2025-03-05T10:30:00Z",
  "answers": [
    {"question_id": 1, "chosen_answer": "B"},
    {"question_id": 2, "chosen_answer": "A"}
  ]
}
```

2. **Run the grading script**:
```bash
python scripts/grade_results.py --answers results/my-model.json
```

3. **View results**:
   - Console output shows grading summary
   - Leaderboard updated at `frontend/public/leaderboard.json`

## What the Script Does

1. Loads your model's answers from the JSON file
2. Loads the solution key from `data/solutions.json`
3. Grades each answer (compares chosen_answer vs correct_answer)
4. Calculates:
   - Overall accuracy
   - Specialty breakdown (Cardiology, Neurology, etc.)
   - Source breakdown (Italian SSM, USMLE, etc.)
5. Adds/updates model in leaderboard
6. Sorts all models by accuracy (highest first)
7. Saves updated leaderboard
8. Prints summary to console

## Key Behaviors

- **New models**: Added to leaderboard
- **Existing models**: Updated with new results
- **Sorting**: Automatic by accuracy (descending)
- **Unknown question IDs**: Warning printed, but processing continues

## File Locations

| File | Default Location |
|------|------------------|
| Answers | `results/*.json` (you create these) |
| Solutions | `data/solutions.json` |
| Leaderboard | `frontend/public/leaderboard.json` |

## Example Output

```
Loading answers from: results/my-model.json
Loading solutions from: data/solutions.json
Grading answers...
Loading leaderboard from: frontend/public/leaderboard.json
Added new model: my-model-name
Leaderboard saved to: frontend/public/leaderboard.json

============================================================
GRADING SUMMARY
============================================================
Model: my-model-name
Version: v1.0

Overall Performance:
  Score: 142/150
  Accuracy: 94.7%

Specialty Breakdown:
  Cardiology: 45/50 (90.0%)
  Neurology: 48/50 (96.0%)
  ...

Source Breakdown:
  Italian SSM: 70/75 (93.3%)
  USMLE: 72/75 (96.0%)
  ...
============================================================
```

## Troubleshooting

**Error: File not found**
→ Check the file path in your `--answers` argument

**Error: Missing required field**
→ Ensure your JSON has `model_name` and `answers` fields

**Warning: Unknown question IDs**
→ Some question IDs in your answers don't exist in solutions.json
→ These are skipped but don't stop processing
