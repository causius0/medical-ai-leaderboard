# AI Answers Format Specification

## Purpose

The AI answers JSON file contains responses from medical AI models to examination questions. This is the output format generated when prompting models (e.g., using LM Studio) and serves as input for the evaluation scripts.

## File Location

```
/data/[model_name]_answers.json
```

Examples:
- `data/llama-3-70b-answers.json`
- `data/gpt-4-medical-answers.json`
- `data/mistral-large-answers.json`

## JSON Schema

```json
{
  "model_name": "Model Name and Version",
  "model_version": "optional_version_string",
  "test_date": "2025-03-05",
  "test_date_iso": "2025-03-05T14:30:00Z",
  "temperature": 0.0,
  "top_p": 1.0,
  "max_tokens": 4096,
  "prompt_template": "description_of_prompt_used",
  "system_prompt": "system_prompt_used_if_any",
  "total_questions_attempted": 100,
  "total_questions_answered": 98,
  "responses": [
    {
      "question_id": "unique_identifier_matching_solutions",
      "answer": "B",
      "confidence": 85,
      "explanation": "Model's explanation for its answer...",
      "reasoning": "Detailed reasoning if provided...",
      "tokens_used": 450,
      "time_to_response": 2.5,
      "refusal": false,
      "notes": "any additional notes"
    }
  ],
  "metadata": {
    "generated_by": "Your Name",
    "generation_method": "lm_studio_api",
    "model_parameters": {
      "context_length": 8192,
      "batch_size": 1
    },
    "hardware_info": {
      "gpu": "NVIDIA RTX 4090",
      "ram_gb": 64
    },
    "additional_info": "any_other_relevant_info"
  }
}
```

## Field Specifications

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model_name` | string | Yes | Full name of the model (e.g., "Llama 3 70B") |
| `model_version` | string | No | Specific version or checkpoint |
| `test_date` | string (ISO date) | Yes | Date when answers were generated |
| `test_date_iso` | string (ISO datetime) | No | Full timestamp with timezone |
| `temperature` | float | Yes | Temperature used for generation |
| `top_p` | float | No | Nucleus sampling parameter |
| `max_tokens` | integer | Yes | Maximum tokens allowed per response |
| `prompt_template` | string | Yes | Description of prompt structure |
| `system_prompt` | string | No | System prompt if used |
| `total_questions_attempted` | integer | Yes | Total questions presented to model |
| `total_questions_answered` | integer | Yes | Questions where model gave an answer |
| `responses` | array of objects | Yes | Array of response objects |
| `metadata` | object | No | Additional metadata about generation |

### Response Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question_id` | string | Yes | Must match ID in solutions.json |
| `answer` | string | Yes | Model's chosen answer (A, B, C, D, or E) |
| `confidence` | integer (0-100) | Yes | Model's confidence percentage |
| `explanation` | string | No | Model's explanation |
| `reasoning` | string | No | Detailed reasoning chain |
| `tokens_used` | integer | No | Tokens consumed for this response |
| `time_to_response` | float | No | Response time in seconds |
| `refusal` | boolean | No | Whether model refused to answer |
| `notes` | string | No | Any additional notes |

## Example Entries

### Example 1: Complete Response with High Confidence

```json
{
  "question_id": "italian_ssm_2023_001",
  "answer": "B",
  "confidence": 95,
  "explanation": "La presenza di onde Q anormali in derivazioni precordiali è un segno elettrocardiografico caratteristico di un pregresso infarto miocardico. Le onde Q indicano necrosi del tessuto miocardico e sono considerate patologiche quando hanno durata >0.04s o profondità >25% dell'onda R seguente.",
  "reasoning": "Il paziente presenta dispnea progressiva ed edema, che sono sintomi di insufficienza cardiaca. Tuttavia, la chiave per la diagnosi è l'ECG con onde Q patologiche, che indicano un danno miocardico pregresso. Questo, combinato con i sintomi attuali, suggerisce un infarto miocardico vecchio come causa sottostante.",
  "tokens_used": 487,
  "time_to_response": 3.2,
  "refusal": false,
  "notes": ""
}
```

### Example 2: Response with Lower Confidence

```json
{
  "question_id": "spanish_mir_2022_045",
  "answer": "C",
  "confidence": 65,
  "explanation": "El síndrome de Lambert-Eaton se caracteriza por debilidad que mejora con el ejercicio, lo que se conoce como fenómeno de 'facilitación'. La disminución del reflejo maseterino es también un hallazgo característico.",
  "reasoning": "La debilidad que empeora con el ejercicio es típica de la miastenia gravis, no del síndrome de Lambert-Eaton. Sin embargo, el reflejo maseterino disminuido apunta más hacia Lambert-Eaton. Existe cierta ambigüedad en la pregunta, pero el reflejo maseterino es un signo más específico.",
  "tokens_used": 612,
  "time_to_response": 4.1,
  "refusal": false,
  "notes": "Confidence reduced due to overlapping symptoms between Lambert-Eaton and myasthenia gravis"
}
```

### Example 3: Model Refusal

```json
{
  "question_id": "portuguese_2023_089",
  "answer": "N/A",
  "confidence": 0,
  "explanation": "Não posso responder a esta questão sem mais informações clínicas.",
  "reasoning": "",
  "tokens_used": 45,
  "time_to_response": 0.8,
  "refusal": true,
  "notes": "Model refused to answer due to perceived lack of information"
}
```

## Prompt Engineering for This Format

To ensure models output in this JSON format, use structured prompts:

### Method 1: Direct JSON Request

```
You are a medical AI assistant. Answer the following medical examination questions.

IMPORTANT: You must respond in valid JSON format with this exact structure:
{
  "question_id": "copy_the_question_id_here",
  "answer": "A, B, C, D, or E",
  "confidence": 0-100,
  "explanation": "your brief explanation",
  "reasoning": "your detailed reasoning",
  "refusal": false
}

Answer the following question:

Question ID: italian_ssm_2023_001
Question: [Question text here]
Options:
A. [Option A]
B. [Option B]
C. [Option C]
D. [Option D]
E. [Option E]

Provide your answer in the specified JSON format:
```

### Method 2: Few-Shot Prompting

```
You are a medical AI assistant specializing in multiple-choice medical examination questions.

Here are examples of how to format your responses:

Example 1:
Question ID: italian_ssm_2023_001
Question: A 65-year-old patient presents with progressive dyspnea...
Options: A) X, B) Y, C) Z, D) W, E) V

Response:
{
  "question_id": "italian_ssm_2023_001",
  "answer": "B",
  "confidence": 90,
  "explanation": "The clinical presentation and ECG findings indicate...",
  "reasoning": "Considering the patient's age, symptoms, and ECG abnormalities...",
  "refusal": false
}

Example 2:
[Include another example]

Now answer this question:

Question ID: [actual question ID]
Question: [actual question text]
Options: [actual options]

Response:
```

### Method 3: LM Studio / API Format

When using LM Studio's API:

```python
import requests
import json

def prompt_model(question_data):
    prompt = f"""
Answer this medical question and respond in JSON format:

Question: {question_data['question_text']}
Options:
A) {question_data['options']['A']}
B) {question_data['options']['B']}
C) {question_data['options']['C']}
D) {question_data['options']['D']}
E) {question_data['options']['E']}

Respond with JSON in this format:
{{
  "question_id": "{question_data['question_id']}",
  "answer": "A/B/C/D/E",
  "confidence": 0-100,
  "explanation": "brief explanation",
  "reasoning": "detailed reasoning",
  "refusal": false
}}
"""

    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "You are a medical AI assistant. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 2000
        }
    )

    return json.loads(response.json()['choices'][0]['message']['content'])
```

## Best Practices

### Confidence Scoring

Define clear confidence ranges:
- **90-100**: Very confident, unambiguous answer
- **70-89**: Confident, minor uncertainties
- **50-69**: Moderately confident, some ambiguity
- **30-49**: Low confidence, significant uncertainty
- **10-29**: Very low confidence, highly uncertain
- **0**: Complete guess or refusal

### Handling Refusals

When a model refuses to answer:
- Set `answer: "N/A"`
- Set `confidence: 0`
- Set `refusal: true`
- Include explanation in `explanation` field
- Note reason for refusal in `notes`

### Error Handling

If the model outputs invalid JSON:
1. Log the error with `question_id`
2. Attempt to extract answer using regex
3. If extraction fails, mark as `refusal: true`
4. Include raw output in `notes` for manual review

## Validation Scripts

Use validation scripts to ensure answer files are properly formatted:

```python
import json

def validate_answers_file(answers_path, solutions_path):
    """Validate answers JSON file format and completeness"""

    with open(answers_path) as f:
        answers = json.load(f)

    with open(solutions_path) as f:
        solutions = json.load(f)

    errors = []

    # Check required top-level fields
    required_fields = ['model_name', 'test_date', 'responses']
    for field in required_fields:
        if field not in answers:
            errors.append(f"Missing required field: {field}")

    # Check responses
    solution_ids = {q['question_id'] for q in solutions['questions']}
    answer_ids = {r['question_id'] for r in answers['responses']}

    # Check for missing questions
    missing = solution_ids - answer_ids
    if missing:
        errors.append(f"Missing answers for {len(missing)} questions")

    # Check for extra questions
    extra = answer_ids - solution_ids
    if extra:
        errors.append(f"Answers for {len(extra)} questions not in solutions")

    # Check each response
    for response in answers['responses']:
        if 'question_id' not in response:
            errors.append("Response missing question_id")
        if 'answer' not in response:
            errors.append(f"Response {response.get('question_id')} missing answer")
        if 'confidence' not in response:
            errors.append(f"Response {response.get('question_id')} missing confidence")

    return errors

# Usage
errors = validate_answers_file('data/model_answers.json', 'data/solutions.json')
if errors:
    for error in errors:
        print(f"ERROR: {error}")
else:
    print("Validation passed!")
```

## Batch Processing

For processing multiple questions:

```python
def batch_process_questions(model, questions_file, output_file):
    """Process multiple questions and save to answers file"""

    with open(questions_file) as f:
        questions = json.load(f)['questions']

    responses = []

    for question in questions:
        response = prompt_model(question)
        responses.append(response)
        print(f"Answered {response['question_id']}")

    # Create complete answers file
    answers = {
        "model_name": model,
        "test_date": datetime.now().isoformat(),
        "temperature": 0.0,
        "max_tokens": 2000,
        "total_questions_attempted": len(questions),
        "total_questions_answered": len(responses),
        "responses": responses,
        "metadata": {
            "generated_by": "batch_processor",
            "generation_method": "lm_studio_api"
        }
    }

    with open(output_file, 'w') as f:
        json.dump(answers, f, indent=2)
```

## Common Issues and Solutions

### Issue 1: Invalid JSON Output

**Problem**: Model outputs JSON wrapped in markdown or with extra text.

**Solution**: Use post-processing to extract JSON:
```python
import json
import re

def extract_json(text):
    # Try to find JSON in code blocks
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Try to find raw JSON
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    raise ValueError("Could not extract JSON from response")
```

### Issue 2: Inconsistent Answer Format

**Problem**: Model returns answers in various formats (e.g., "Option B", "B)", "(B)").

**Solution**: Normalize answers:
```python
def normalize_answer(answer):
    # Extract single letter
    match = re.search(r'[A-E]', str(answer).upper())
    if match:
        return match.group(0)
    return None
```

### Issue 3: Missing Confidence Values

**Problem**: Model doesn't provide confidence scores.

**Solution**: Use text analysis or default value:
```python
def extract_confidence(response_text):
    # Try to extract explicit confidence
    match = re.search(r'confidence[:\s]+(\d+)', response_text.lower())
    if match:
        return int(match.group(1))

    # Analyze language certainty
    if certain_indicators in response_text:
        return 80
    elif uncertain_indicators in response_text:
        return 40
    else:
        return 60  # Default
```

## Integration with Evaluation Pipeline

The answers file integrates with the evaluation pipeline:

```bash
# Step 1: Generate answers (using this format)
python scripts/generate_answers.py --model llama-3-70b --questions data/solutions.json

# Step 2: Validate format
python scripts/validate_answers.py --answers data/llama-3-70b-answers.json

# Step 3: Evaluate performance
python scripts/evaluate_model.py --answers data/llama-3-70b-answers.json --solutions data/solutions.json

# Step 4: Update leaderboard
python scripts/generate_leaderboard.py
```

## Support

For questions about the answers format or to report issues, please [contact information].
