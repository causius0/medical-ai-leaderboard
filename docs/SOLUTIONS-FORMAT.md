# Solutions Format Specification

## Purpose

The `solutions.json` file contains the correct answers and metadata for all medical examination questions in the leaderboard. This file serves as the ground truth for evaluating AI model performance.

**CRITICAL SECURITY NOTICE**: This file contains correct answers to examination questions and should **NEVER** be committed to Git or shared publicly. It must be included in `.gitignore`.

## File Location

```
/data/solutions.json
```

This file is **gitignored** and should never be committed to version control.

## JSON Schema

```json
{
  "version": "1.0",
  "last_updated": "2025-03-05",
  "total_questions": 1000,
  "sources": ["italian_ssm", "spanish_mir", "portuguese", "french"],
  "specialties": ["cardiology", "neurology", "oncology", "internal_medicine"],
  "questions": [
    {
      "question_id": "unique_identifier",
      "source": "italian_ssm",
      "year": 2023,
      "specialty": "cardiology",
      "question_text": "Complete question text here...",
      "options": {
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text",
        "E": "Option E text"
      },
      "correct_answer": "B",
      "explanation": "Explanation of why B is correct...",
      "difficulty": "medium",
      "language": "italian",
      "tags": ["diagnosis", "pharmacology", "heart_failure"],
      "verified": true,
      "ambiguous": false,
      "notes": "Any special notes about this question"
    }
  ],
  "metadata": {
    "created_by": "Your Name",
    "verification_status": "partially_verified",
    "last_verification_date": "2025-03-05"
  }
}
```

## Field Specifications

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Format version (e.g., "1.0") |
| `last_updated` | string (ISO date) | Yes | Last update date |
| `total_questions` | integer | Yes | Total number of questions |
| `sources` | array of strings | Yes | List of all sources represented |
| `specialties` | array of strings | Yes | List of all medical specialties |
| `questions` | array of objects | Yes | Array of question objects |
| `metadata` | object | Yes | Metadata about the solutions file |

### Question Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question_id` | string | Yes | Unique identifier (format: `{source}_{year}_{number}`) |
| `source` | string | Yes | Source identifier (e.g., "italian_ssm") |
| `year` | integer | Yes | Year of examination |
| `specialty` | string | Yes | Medical specialty category |
| `question_text` | string | Yes | Complete question text |
| `options` | object | Yes | Object with keys A, B, C, D, E (or fewer) |
| `correct_answer` | string | Yes | Single letter (A, B, C, D, or E) |
| `explanation` | string | No | Explanation of correct answer |
| `difficulty` | string | No | "easy", "medium", or "hard" |
| `language` | string | Yes | Language of question (italian, spanish, etc.) |
| `tags` | array of strings | No | Relevant medical topics/tags |
| `verified` | boolean | Yes | Whether answer has been verified |
| `ambiguous` | boolean | Yes | Whether question has known ambiguity |
| `notes` | string | No | Any special notes |

## Example Entries

### Example 1: Italian SSM Cardiology Question

```json
{
  "question_id": "italian_ssm_2023_001",
  "source": "italian_ssm",
  "year": 2023,
  "specialty": "cardiology",
  "question_text": "Un paziente di 65 anni presenta dispnea progressiva ed edema agli arti inferiori. All'ECG si rileva ritmo sinusale con onde Q anormali in derivazioni precordiali. Qual è la diagnosi più probabile?",
  "options": {
    "A": "Insufficienza cardiaca congestizia",
    "B": "Infarto miocardico vecchio",
    "C": "Pericardite acuta",
    "D": "Miocardite virale",
    "E": "Stenosi aortica grave"
  },
  "correct_answer": "B",
  "explanation": "Le onde Q anormali in derivazioni precordiali sono indicative di un pregresso infarto miocardico.",
  "difficulty": "medium",
  "language": "italian",
  "tags": ["ecg", "ischemia", "diagnosi"],
  "verified": true,
  "ambiguous": false,
  "notes": ""
}
```

### Example 2: Spanish MIR Neurology Question

```json
{
  "question_id": "spanish_mir_2022_045",
  "source": "spanish_mir",
  "year": 2022,
  "specialty": "neurology",
  "question_text": "Un paciente de 45 años presenta debilidad progresiva en ambas piernas que empeora con el ejercicio físico. El reflejo delmaseterino está disminuido. ¿Cuál es el diagnóstico más probable?",
  "options": {
    "A": "Esclerosis lateral amiotrófica",
    "B": "Miastenia gravis",
    "C": "Síndrome de Lambert-Eaton",
    "D": "Distrofia muscular de Duchenne",
    "E": "Polimiositis"
  },
  "correct_answer": "C",
  "explanation": "El síndrome de Lambert-Eaton se caracteriza por debilidad que mejora con el ejercicio y está asociado a disminución del reflejo maseterino.",
  "difficulty": "hard",
  "language": "spanish",
  "tags": ["neuromuscular", "diagnostico", "sindrome"],
  "verified": true,
  "ambiguous": false,
  "notes": "Pregunta clínica compleja que requiere conocimiento de patología neuromuscular"
}
```

### Example 3: Portuguese Oncology Question

```json
{
  "question_id": "portuguese_2023_012",
  "source": "portuguese",
  "year": 2023,
  "specialty": "oncology",
  "question_text": "Um paciente de 60 anos é diagnosticado com carcinoma pulmonar de não pequenas células. A biópsia revela mutação no EGFR. Qual é o tratamento de primeira linha recomendado?",
  "options": {
    "A": "Quimioterapia com carboplatino e paclitaxel",
    "B": "Inibidor de tirosina quinase do EGFR (erlotinibe)",
    "C": "Imunoterapia com pembrolizumabe",
    "D": "Cirurgia de ressecção",
    "E": "Radioterapia exclusiva"
  },
  "correct_answer": "B",
  "explanation": "Em pacientes com mutação ativadora do EGFR, os inibidores de tirosina quinase (erlotinibe, gefitinibe) são o tratamento de primeira linha.",
  "difficulty": "medium",
  "language": "portuguese",
  "tags": ["cancer de pulmao", "egfr", "terapia alvo"],
  "verified": true,
  "ambiguous": false,
  "notes": ""
}
```

## Best Practices

### Question ID Format

Use the format: `{source}_{year}_{sequential_number}`

Examples:
- `italian_ssm_2023_001`
- `spanish_mir_2022_045`
- `portuguese_2023_012`

### Verification Status

- Set `verified: true` only after double-checking the answer
- For questions with disputed or ambiguous answers, set `ambiguous: true`
- Include notes explaining any ambiguities

### Tagging

Use consistent tags for:
- Medical topics (e.g., "pharmacology", "diagnosis", "pathology")
- Body systems (e.g., "cardiovascular", "nervous", "respiratory")
- Question types (e.g., "clinical", "basic_science", "ethics")

### Language Field

Always specify the language code:
- "italian" - Italian
- "spanish" - Spanish
- "portuguese" - Portuguese
- "french" - French
- "english" - English (for translated questions)

## Handling Special Cases

### Ambiguous Questions

For questions with known issues:

```json
{
  "question_id": "italian_ssm_2023_078",
  "ambiguous": true,
  "notes": "Options A and C are very similar; official answer key lists A but C could also be considered correct based on recent guidelines",
  "correct_answer": "A",
  "verified": true
}
```

### Multiple Correct Answers

If a source has questions with multiple correct answers:

```json
{
  "question_id": "spanish_mir_2022_156",
  "correct_answer": "B,C",
  "notes": "Multiple select question - both B and C must be selected",
  "options": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "...",
    "E": "..."
  }
}
```

### Questions with Images

For questions including images or diagrams:

```json
{
  "question_id": "french_2023_034",
  "has_image": true,
  "image_path": "images/french_2023_034.png",
  "image_description": "ECG showing atrial fibrillation",
  "question_text": "Analysez l'ECG présenté ci-dessus. Quel est le diagnostic?",
  "correct_answer": "D",
  "notes": "Question requires image interpretation"
}
```

## Validation

Before using the solutions file, validate that:

1. All `question_id` values are unique
2. All `correct_answer` values match existing option keys
3. All required fields are present
4. All `source` and `specialty` values are defined in the top-level arrays
5. No duplicate questions exist

## Security and Privacy

### Why This File Must Be Gitignored

1. **Academic Integrity**: Prevents cheating on medical examinations
2. **Copyright Protection**: Respects intellectual property of exam creators
3. **Data Privacy**: May contain patient information in clinical vignettes
4. **Benchmark Integrity**: Ensures fair evaluation without data leakage

### .gitignore Entry

Ensure `.gitignore` contains:

```
# Never commit correct answers
data/solutions.json

# Optional: Ignore all JSON files in data/ except specific ones
data/*.json
!data/example_answers.json
!data/template_answers.json
```

## Template File

For testing purposes, you can create a `data/example_solutions.json` file with a small subset of questions (5-10) that can be committed to Git. This helps developers test the evaluation system without exposing the full answer key.

Example template file is provided in the repository at `data/example_solutions.json`.

## Version Control

When updating `solutions.json`:

1. Update the `version` field if format changes
2. Always update `last_updated` timestamp
3. Update `total_questions` count
4. Add new sources/specialties to top-level arrays if needed
5. Update `metadata.verification_status`

## Support

For questions about the solutions format or to report issues, please [contact information].
