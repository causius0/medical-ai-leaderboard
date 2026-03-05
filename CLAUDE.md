# Medical AI Leaderboard - Claude Context

## Known Issues and Limitations

### Model Context Window Issues
**Problem:** Local models (tested with LM Studio) have difficulty processing more than 6 questions at a time.

**Symptoms:**
- Models stop responding after question 6-7
- Responses become incomplete or cutoff
- Model may lose context and provide inconsistent formatting

**Workarounds:**
1. Process questions in batches of 5-6 questions maximum
2. Use the included `prompt.txt` for consistent prompting
3. For SSM questions, the dataset has 200 questions - needs batch processing

**Future Improvements:**
- Test with models that have larger context windows
- Implement automatic batch splitting in the grading script
- Add support for streaming responses to catch cutoff issues

## Dataset Information

### Italian SSM (State Medical Examination)
- **Questions:** 200 medical questions
- **Format:** 5 options (A-E) per question
- **Language:** Italian
- **Location:** `data/ssm_questions_with_solution.json` (private)
- **Public Version:** `frontend/public/ssm_questions_no_solution.json`

### Question Structure
```json
{
  "id": "IT0001",
  "question": "Italian text...",
  "options": [
    {"letter": "A", "text": "..."},
    {"letter": "B", "text": "..."},
    {"letter": "C", "text": "..."},
    {"letter": "D", "text": "..."},
    {"letter": "E", "text": "..."}
  ],
  "correct_answer": {
    "letter": "E",
    "index": 4
  }
}
```

**Note:** SSM format uses 5 options (A-E) while the original leaderboard design used 4 options (A-D). The grading script needs to be updated to handle both formats.

## Evaluation Scripts

### Primary Script: `grade_results.py`
- Handles the leaderboard JSON format
- Supports specialty and source breakdowns
- Output: `frontend/public/leaderboard.json`

### SSM-Specific Script: `evaluate_ssm_results.py`
- Original evaluation script for SSM questions
- Located in `scripts/`
- Takes model predictions JSON as input
- Outputs: `evaluation_results.json` on Desktop

## Prompt Template

The `docs/prompt.txt` file contains the prompt used for LM Studio:
- Designed for Italian medical questions
- Requests JSON output format
- Emphasizes completing ALL questions
- Specifies uppercase letter answers (A-E)

## TODO Items

1. **Update grading script** to handle 5-option questions (A-E format)
2. **Add batch processing** for large question sets
3. **Convert SSM solutions** to leaderboard format
4. **Add more exam sources** (Spanish MIR, Portuguese, French)
5. **Test with larger context models** to bypass 6-question limit

## Git Repository Setup

### Public Files (committed):
- Frontend code
- Documentation
- Scripts
- `ssm_questions_no_solution.json` (questions without answers)

### Private Files (gitignored):
- `data/solutions.json`
- `data/ssm_questions_with_solution.json`
- `results/*.json` (model answers)

This keeps the correct answers private while making the leaderboard and questions publicly viewable.
