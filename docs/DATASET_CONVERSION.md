# Italian SSM Dataset Conversion Documentation

## Overview

The Italian SSM (Selezione Specializzazioni in Medicina) questions have been successfully converted from the EuropeMedQA Excel format to the leaderboard's JSON format, with enhanced tracking for image-dependent questions.

## Source Data

- **Source File**: `data/EuropeMedQA_Dataset.xlsx`
- **Sheet**: "SSM_Q_ITA"
- **Total Questions**: 1,120
- **Year Range**: 2017-2024 (140 questions per year)

## Conversion Script

**Location**: `scripts/convert_excel_to_json.py`

The script converts Excel data to JSON and generates two versions:
1. **With solutions**: `data/ssm_questions_with_solution.json` (private, gitignored)
2. **Without solutions**: `frontend/out/ssm_questions_no_solution.json` (public)

## New Features

### 1. Image Flagging

**Problem**: Original analysis showed 102 questions (9%) referenced images but had no way to identify them.

**Solution**: Added `has_image` boolean field to flag image-dependent questions.

**Statistics**:
- Questions with images: **60** (5.4%)
- Questions without images: **1,060** (94.6%)

**Fields Added**:
```json
{
  "has_image": true/false,
  "image_link": "IT0006.PNG"  // Only present when has_image=true
}
```

### 2. Enhanced Metadata

**Fields Added**:
```json
"metadata": {
  "test_year": 2017,
  "number_in_test": 6,
  "nullified": false
}
```

- `test_year`: Year the exam was administered
- `number_in_test`: Question number in the original exam
- `nullified`: Whether the question was invalidated/removed

### 3. Specialty Classification

Uses the **European medical specialty classification** from the Excel dataset's `domain` field, providing:
- Standardized taxonomy aligned with EU medical specialties
- Cross-European comparability
- 54 distinct medical specialties

**Top Specialties by Volume**:
1. Cardiology (96 questions)
2. Obstetrics and gynecology (74 questions)
3. Gastroenterology (73 questions)
4. Neurology (58 questions)
5. Accident and emergency medicine (57 questions)

**Specialties with Most Image Questions**:
1. Cardiology (12 image questions)
2. Orthopaedics (7 image questions)
3. Dermatology (6 image questions)
4. Radiology (6 image questions)
5. Neurology (5 image questions)

## JSON Structure

### Complete Question (With Solutions)

```json
{
  "id": "IT0006",
  "question": "L'immagine mostra un tracciato elettrocardiografico corrispondente a:",
  "options": [
    {"letter": "A", "text": "Infarto miocardico della parete anteriore"},
    {"letter": "B", "text": "Fibrillazione atriale"},
    {"letter": "C", "text": "Infarto miocardico della parete posteriore"},
    {"letter": "D", "text": "Infarto miocardico della parete inferiore"},
    {"letter": "E", "text": "Blocco atrioventricolare di terzo grado"}
  ],
  "correct_answer": {
    "letter": "A",
    "index": 0
  },
  "specialty": "Cardiology",
  "has_image": true,
  "image_link": "IT0006.PNG",
  "metadata": {
    "test_year": 2017,
    "number_in_test": 6,
    "nullified": false
  }
}
```

### Public Version (No Solutions)

```json
{
  "id": "IT0006",
  "question": "L'immagine mostra un tracciato elettrocardiografico corrispondente a:",
  "options": [
    {"letter": "A", "text": "Infarto miocardico della parete anteriore"},
    {"letter": "B", "text": "Fibrillazione atriale"},
    {"letter": "C", "text": "Infarto miocardico della parete posteriore"},
    {"letter": "D", "text": "Infarto miocardico della parete inferiore"},
    {"letter": "E", "text": "Blocco atrioventricolare di terzo grado"}
  ],
  "specialty": "Cardiology",
  "has_image": true,
  "image_link": "IT0006.PNG",
  "metadata": {
    "test_year": 2017,
    "number_in_test": 6,
    "nullified": false
  }
}
```

## Usage

### Running the Conversion

```bash
python3 scripts/convert_excel_to_json.py
```

### Filtering Image-Based Questions

```python
import json

with open('data/ssm_questions_with_solution.json', 'r') as f:
    questions = json.load(f)

# Get only text-based questions
text_only = [q for q in questions if not q['has_image']]

# Get only image-based questions
image_based = [q for q in questions if q['has_image']]
```

### Filtering by Specialty

```python
# Get all cardiology questions
cardiology = [q for q in questions if q['specialty'] == 'Cardiology']

# Get cardiology questions without images
cardiology_text_only = [
    q for q in cardiology
    if not q['has_image']
]
```

## Impact on AI Evaluation

### Text-Only Models
Models without vision capabilities should only be evaluated on the **1,060 text-only questions** (94.6% of the dataset) to ensure fair assessment.

### Multimodal Models
Models with vision capabilities can be evaluated on:
- **All 1,120 questions** (full dataset)
- **60 image-based questions** (vision-specific subset)

### Recommended Evaluation Approach

1. **Text-only evaluation**: Use only `has_image: false` questions
2. **Multimodal evaluation**: Use all questions
3. **Separate leaderboards**: Track performance on text-only vs. image-based questions

## Data Quality

- **Total questions**: 1,120
- **Questions per year**: 140 (2017-2024)
- **Medical specialties**: 54
- **Image questions**: 60 (5.4%)
- **Nullified questions**: Tracked via metadata
- **Answer format**: 5 options (A-E)

## Files Modified/Created

1. ✅ `data/EuropeMedQA_Dataset.xlsx` - Source Excel file
2. ✅ `data/ssm_questions_with_solution.json` - Private version with answers
3. ✅ `frontend/out/ssm_questions_no_solution.json` - Public version
4. ✅ `scripts/convert_excel_to_json.py` - Conversion script
5. ✅ `docs/DATASET_CONVERSION.md` - This documentation

## Future Enhancements

Potential improvements:
1. Add actual image files to `data/images/` directory
2. Implement image serving for frontend display
3. Create separate evaluation modes for text-only vs. multimodal
4. Add image-type classification (ECG, X-ray, dermatology, etc.)
5. Track image difficulty/complexity metrics

---

**Last Updated**: 2025-03-09
**Conversion Status**: ✅ Complete
**Data Quality**: ✅ Verified
