# Medical AI Leaderboard Workflow

## Overview

This project evaluates and ranks AI models on their ability to answer medical questions accurately.

## Project Structure

```
medical-ai-leaderboard/
├── frontend/          # Next.js web application for displaying the leaderboard
├── data/             # Data files (solutions.json is private)
├── scripts/          # Python scripts for grading and processing
├── results/          # AI model answers (JSON format)
└── docs/             # Documentation
```

## Workflow

### 1. Add Questions to Leaderboard

Questions are added to `data/leaderboard.json` with:
- Unique ID
- Question text
- Medical specialty
- Difficulty level

### 2. Collect AI Answers

Run AI models to generate answers for each question:
- Results are stored in `results/{model_name}_{timestamp}.json`
- Each JSON contains the model's answers for all questions
- Files are gitignored to avoid committing large AI responses

### 3. Grade Answers

Use the grading script to evaluate AI answers:
```bash
python scripts/grade_results.py --model results/{model_name}.json --solutions data/solutions.json
```

The grading script:
- Compares AI answers against reference solutions
- Assigns scores (0-100) based on accuracy and completeness
- Uses another AI model (e.g., GPT-4) for nuanced grading
- Updates `data/leaderboard.json` with new model results

### 4. Deploy Frontend

The Next.js frontend reads from `data/leaderboard.json` to display:
- Overall rankings
- Scores by specialty
- Scores by difficulty
- Individual question breakdowns

## Data Privacy

**Important**: `data/solutions.json` is gitignored and contains:
- Correct answers to all questions
- Reference explanations
- Key points for grading

This ensures the correct answers remain private and don't influence AI responses.

## Leaderboard.json Structure

The public `leaderboard.json` includes:
- Question metadata (but not solutions)
- AI model rankings and scores
- Individual model answers and scores
- Aggregated statistics by specialty and difficulty

See `docs/leaderboard-format.json` for the complete schema.
