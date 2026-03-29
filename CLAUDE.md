# Medical AI Leaderboard - Testing Procedures

## Overview

This document describes the procedures for evaluating different AI models on medical examination questions for the leaderboard.

## CRITICAL: Model Completion Requirements

**A model evaluation is NOT COMPLETE until ALL 1060 questions have been answered.**

- **Do NOT add models to leaderboard** if `num_answered < 1060`
- **Minimum acceptable threshold**: 99%+ (e.g., Qwen at 1059/1060 is acceptable)
- **For incomplete evaluations**:
  - Fix the issue (parser, rate limiting, context window)
  - Re-run the COMPLETE evaluation from scratch
  - Only add to leaderboard after all questions are answered
- **Common issues that prevent completion**:
  - Response format parsing failures (fix parser before re-running)
  - Rate limiting (use retry logic and smaller batches)
  - Context window overflow (reduce batch size to 50 for smaller models)
  - API errors (retry failed batches, don't just accept partial results)

## Prerequisites

1. **API Keys**: Set up your OpenRouter API key in `.env` file:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```

2. **Question Data**: Ensure questions are available in `data/` directory:
   - `ssm_questions_with_solution.json` - Original questions with correct answers
   - `ssm_questions_text_only_shuffled_no_answers.json` - Shuffled questions without answers (for bias testing)

## Standard Evaluation Procedure

### Step 1: Prepare Questions

Questions must be in JSON format with the following structure:
```json
{
  "id": "IT0001",
  "question": "Question text here...",
  "options": [
    {"letter": "A", "text": "Option A"},
    {"letter": "B", "text": "Option B"},
    ...
  ],
  "specialty": "Cardiology",
  "has_image": false
}
```

**IMPORTANT**: Questions sent to models must NOT include the `correct_answer` field!

### Step 2: Run Model Evaluation

#### Option A: Run a Single Model

```bash
cd /Users/causius/Documents/GitHub/medical-ai-leaderboard
python3 scripts/run_openrouter_pipeline.py qwen
```

Available models:
- `qwen` - Qwen 3.5 Flash
- `gemma` - Gemma 3 27B
- `mistral` - Mistral 7B Instruct
- `liquid` - Liquid LFM-2 24B
- `minimax` - MiniMax M2.5
- `llama` - Llama 3.3 70B

#### Option B: Run Multiple Models

```bash
python3 scripts/run_openrouter_pipeline.py qwen gemma mistral
```

#### Option C: Run All Models

```bash
python3 scripts/run_openrouter_pipeline.py all
```

### Step 3: Collect Results

Results are saved to `results/openrouter/` with timestamp:
```
results/openrouter/qwen_20250309_143022.json
```

### Step 4: Evaluate Performance

```bash
python3 scripts/evaluate_ssm_results.py results/openrouter/qwen_TIMESTAMP.json
```

This generates:
- Accuracy score
- Specialty breakdown
- Detailed analysis

### Step 5: Update Leaderboard

```bash
python3 scripts/add_to_leaderboard.py results/openrouter/qwen_TIMESTAMP.json
```

## Bias Testing Procedure (Shuffled Answer Keys)

### Purpose

Test if models show position bias by shuffling correct answers to different positions.

### Procedure

#### 1. Generate Shuffled Questions

```bash
python3 scripts/shuffle_answer_keys.py
```

This creates:
- `data/ssm_questions_text_only_shuffled.json` - With shuffled correct answers (for evaluation)
- `data/ssm_questions_text_only_shuffled_no_answers.json` - Without answers (for models)
- `data/shuffle_mapping.json` - Mapping of original → shuffled positions

#### 2. Run Model on Shuffled Questions

```bash
python3 scripts/run_qwen_shuffled.py
```

#### 3. Compare Results

Evaluate the shuffled results and compare with standard evaluation to detect position bias:
- If performance drops significantly on shuffled questions → model has position bias
- If performance stays similar → model is actually reasoning

## Filtered Evaluations

### Text-Only Questions

To evaluate only on text-based questions (no images):

1. Filter questions to text-only:
   ```python
   import json
   with open('data/ssm_questions_with_solution.json') as f:
       questions = json.load(f)
   text_only = [q for q in questions if not q.get('has_image')]
   ```

2. Save filtered questions:
   ```bash
   python3 -c "
   import json
   with open('data/ssm_questions_with_solution.json') as f:
       data = json.load(f)
   text_only = [q for q in data if not q.get('has_image')]
   with open('data/ssm_questions_text_only.json', 'w') as f:
       json.dump(text_only, f, indent=2, ensure_ascii=False)
   "
   ```

3. Run evaluation on filtered set

### Specialty-Specific Evaluation

```python
import json

with open('data/ssm_questions_with_solution.json') as f:
    questions = json.load(f)

# Filter by specialty
cardiology = [q for q in questions if q['specialty'] == 'Cardiology']

# Save specialty-specific questions
with open('data/ssm_questions_cardiology.json', 'w') as f:
    json.dump(cardiology, f, indent=2, ensure_ascii=False)
```

## Adding New Models

### 1. Define Model Configuration

Edit `scripts/run_openrouter_pipeline.py`:

```python
MODELS = {
    "new_model": {
        "id": "provider/model-name",
        "name": "Human Readable Name",
        "temperature": 0.7
    }
}
```

### 2. Test the Model

```bash
python3 scripts/run_openrouter_pipeline.py new_model
```

### 3. Evaluate and Add to Leaderboard

Follow steps 3-5 from standard evaluation procedure.

## Data Conversion

### Converting Excel to JSON

If you have new Excel data:

```bash
python3 scripts/convert_excel_to_json.py
```

This:
- Reads from `data/EuropeMedQA_Dataset.xlsx`
- Creates JSON with proper structure
- Flags image-based questions
- Adds metadata

### Important Features

After conversion, questions include:
- `has_image`: Boolean flag for image-dependent questions
- `image_link`: Image filename (if applicable)
- `metadata.test_year`: Exam year
- `metadata.number_in_test`: Question number
- `metadata.nullified`: Whether question was invalidated

## File Structure

```
medical-ai-leaderboard/
├── data/
│   ├── ssm_questions_with_solution.json           # Original questions with answers (PRIVATE)
│   ├── ssm_questions_text_only_shuffled.json       # Shuffled questions with answers (PRIVATE)
│   ├── ssm_questions_text_only_shuffled_no_answers.json  # Shuffled without answers (for models)
│   └── shuffle_mapping.json                       # Shuffle mapping (for analysis)
├── results/
│   ├── openrouter/                                # Model evaluation results
│   └── shuffled/                                  # Shuffled evaluation results
├── scripts/
│   ├── run_openrouter_pipeline.py                 # Main evaluation pipeline
│   ├── run_qwen_shuffled.py                       # Shuffled evaluation
│   ├── shuffle_answer_keys.py                     # Generate shuffled questions
│   ├── evaluate_ssm_results.py                    # Evaluate performance
│   └── add_to_leaderboard.py                      # Update leaderboard
└── frontend/out/
    └── leaderboard.json                           # Published leaderboard
```

## Security and Privacy

### CRITICAL RULES

1. **NEVER commit files with correct answers**:
   - `data/solutions.json` is in `.gitignore`
   - `data/ssm_questions_with_solution.json` should be PRIVATE
   - Only publish `frontend/out/ssm_questions_no_solution.json`

2. **ALWAYS verify questions sent to models don't include answers**:
   ```python
   # Check before sending
   assert 'correct_answer' not in questions[0], "Answers leaked!"
   ```

3. **Keep solution files private**:
   - Use `.gitignore` to prevent accidental commits
   - Only share results/leaderboard, not raw solutions

## Common Issues and Solutions

### Issue: Model Sees Correct Answers

**Problem**: Questions include `correct_answer` field

**Solution**: Use version without answers:
```bash
# Generate version without answers
python3 scripts/prepare_questions_for_model.py

# Verify
python3 -c "
import json
with open('data/questions_for_model.json') as f:
    q = json.load(f)
print('Has correct_answer:', 'correct_answer' in q[0])
"
```

### Issue: API Rate Limiting

**Problem**: OpenRouter rate limit errors

**Solution**: The client automatically retries with exponential backoff. Just wait.

### Issue: Models Don't Answer All Questions

**Problem**: Model stops answering before completing all questions

**Solution**:
1. Split into smaller batches (e.g., 200 questions at a time)
2. Increase `max_tokens` in the API call
3. Use models with larger context windows

## Evaluation Metrics

### Primary Metrics

- **Overall Accuracy**: Percentage of correct answers
- **Text-Only Accuracy**: Accuracy on text-only questions (no images)
- **Specialty Breakdown**: Accuracy per medical specialty

### Bias Metrics

- **Position Bias**: Difference in performance between standard and shuffled answer keys
- **Image Bias**: Performance difference on text-only vs. image questions

### Reporting

When reporting results, include:
1. Overall accuracy
2. Text-only accuracy
3. Top 5 performing specialties
4. Bottom 5 performing specialties
5. Comparison with other models
6. Any bias detected (position, image)

## Example Workflow

Complete workflow for testing a new model:

```bash
# 1. Prepare questions (if needed)
python3 scripts/convert_excel_to_json.py

# 2. Run model
python3 scripts/run_openrouter_pipeline.py qwen

# 3. Evaluate results
python3 scripts/evaluate_ssm_results.py results/openrouter/qwen_20250309_143022.json

# 4. Test for bias (optional)
python3 scripts/shuffle_answer_keys.py
python3 scripts/run_qwen_shuffled.py
python3 scripts/evaluate_ssm_results.py results/shuffled/qwen_shuffled_TIMESTAMP.json

# 5. Update leaderboard
python3 scripts/add_to_leaderboard.py results/openrouter/qwen_20250309_143022.json

# 6. Verify leaderboard
cat frontend/out/leaderboard.json
```

## Checklist Before Publishing Results

- [ ] Questions sent to model did NOT include `correct_answer` field
- [ ] Results evaluated against correct answer key
- [ ] Accuracy calculated correctly
- [ ] Specialty breakdown generated
- [ ] Leaderboard JSON formatted correctly
- [ ] No private/solution files committed to git
- [ ] Documentation updated with new model info

---

**Last Updated**: 2025-03-09
**Maintained by**: Claude Code Assistant
