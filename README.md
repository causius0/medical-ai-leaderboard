# Medical AI Leaderboard

A comprehensive benchmarking system for evaluating medical AI models on real medical examination questions from multiple countries and specialties.

## Project Overview

This leaderboard evaluates Large Language Models (LLMs) and medical AI systems on their ability to answer real medical examination questions from:
- Italian National Medical Residency Exam (SSM - Selezione Specializzazioni in Medicina)
- Spanish Medical Residency Exam (MIR - Médico Interno Residente)
- Portuguese Medical Residency Examination
- French Medical Residency Examination

The system provides standardized metrics to compare model performance across different medical specialties and languages.

## Quick Start Guide

### Prerequisites

- Python 3.8 or higher
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/medical-ai-leaderboard.git
cd medical-ai-leaderboard
```

2. Create the data directory structure:
```bash
mkdir -p data results
```

3. Prepare your data:
   - Add `data/solutions.json` with correct answers (see [SOLUTIONS-FORMAT.md](docs/SOLUTIONS-FORMAT.md))
   - Add AI model responses to `data/` (see [ANSWERS-FORMAT.md](docs/ANSWERS-FORMAT.md))

4. Run the evaluation:
```bash
python scripts/evaluate_model.py --answers data/model_x_answers.json --solutions data/solutions.json
```

## Workflow Explanation

```
1. Collect Questions → 2. Generate AI Responses → 3. Evaluate → 4. Update Leaderboard
```

### Step 1: Collect Questions
- Gather medical exam questions from official sources
- Add to `data/solutions.json` with correct answers
- Document source in `docs/SOURCES.md`

### Step 2: Generate AI Responses
- Use LM Studio or similar tool to prompt models
- Output responses in JSON format (see [ANSWERS-FORMAT.md](docs/ANSWERS-FORMAT.md))
- Save to `data/[model_name]_answers.json`

### Step 3: Evaluate Performance
- Run evaluation script to compare AI answers with solutions
- Calculate accuracy, confidence scores, and specialty breakdowns
- Generate detailed performance reports

### Step 4: Update Leaderboard
- Add results to `results/leaderboard.json`
- Generate visualizations and summary statistics
- Commit results (but never commit solutions!)

## Directory Structure

```
medical-ai-leaderboard/
├── README.md                          # This file
├── .gitignore                         # Git ignore rules (solutions.json included)
├── docs/
│   ├── SOURCES.md                     # List of exam sources and templates
│   ├── SOLUTIONS-FORMAT.md            # Solutions JSON specification
│   └── ANSWERS-FORMAT.md              # AI answers JSON specification
├── data/
│   ├── solutions.json                 # Correct answers (GITIGNORED)
│   └── [model_name]_answers.json      # AI model responses
├── scripts/
│   ├── evaluate_model.py              # Evaluation script
│   ├── generate_leaderboard.py        # Leaderboard generator
│   └── visualize_results.py           # Visualization tools
└── results/
    ├── leaderboard.json               # Current leaderboard
    └── [model_name]_report.json       # Individual model reports
```

## How to Add New Model Results

### 1. Generate Responses

Use LM Studio or your preferred tool to prompt the model with questions. Structure your prompts to output JSON in the format specified in [ANSWERS-FORMAT.md](docs/ANSWERS-FORMAT.md).

Example prompt structure:
```
Answer the following medical questions. For each question, provide:
1. Your chosen answer (A, B, C, D, or E)
2. Your confidence level (0-100)
3. Brief explanation

Output in JSON format with structure:
{
  "model_name": "Model Name",
  "test_date": "2025-03-05",
  "responses": [
    {
      "question_id": "unique_id",
      "answer": "B",
      "confidence": 85,
      "explanation": "..."
    }
  ]
}

Questions:
[Insert questions here]
```

### 2. Save Responses

Save the model's output to `data/[model_name]_answers.json`

### 3. Evaluate

Run the evaluation script:
```bash
python scripts/evaluate_model.py \
    --answers data/[model_name]_answers.json \
    --solutions data/solutions.json \
    --output results/[model_name]_report.json
```

### 4. Update Leaderboard

```bash
python scripts/generate_leaderboard.py
```

## JSON Format Specifications

The project uses two main JSON formats:

### Solutions Format
See [docs/SOLUTIONS-FORMAT.md](docs/SOLUTIONS-FORMAT.md) for the complete specification of the `solutions.json` file.

**Important**: `solutions.json` contains correct answers and should NEVER be committed to Git. It is included in `.gitignore`.

### Answers Format
See [docs/ANSWERS-FORMAT.md](docs/ANSWERS-FORMAT.md) for the complete specification of AI model response format.

## Metrics and Scoring

The leaderboard tracks multiple metrics:

- **Overall Accuracy**: Percentage of correct answers across all questions
- **Specialty Breakdown**: Performance by medical specialty (Cardiology, Neurology, etc.)
- **Source Breakdown**: Performance by exam source (Italian SSM, Spanish MIR, etc.)
- **Confidence-Accuracy Correlation**: How well model confidence predicts correctness
- **Confidence Score**: Weighted accuracy based on confidence levels

## Contributing

Contributions are welcome! To add new exam sources or improve evaluation:

1. Document new sources in `docs/SOURCES.md`
2. Follow the JSON format specifications in `docs/`
3. Add evaluation scripts to `scripts/`
4. Update this README with any workflow changes

## Data Sources

Current medical examination sources are documented in [docs/SOURCES.md](docs/SOURCES.md).

Please see that file for:
- Complete list of current sources
- Templates for adding new sources
- Source-specific considerations

## License

[Your License Here]

## Citation

If you use this leaderboard in your research, please cite:
```
@software{medical_ai_leaderboard,
  title={Medical AI Leaderboard: Comprehensive Evaluation of Medical LLMs},
  author={[Your Name]},
  year={2025},
  url={https://github.com/yourusername/medical-ai-leaderboard}
}
```

## Contact

[Your Contact Information]
