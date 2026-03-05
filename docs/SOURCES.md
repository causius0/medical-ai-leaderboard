# Medical Examination Sources

This document tracks all medical examination sources used in the Medical AI Leaderboard.

## Current Sources

### 1. Italian SSM (Selezione Specializzazioni in Medicina)

**Description**: Italian National Medical Residency Examination
**Language**: Italian
**Years**: [Add years covered]
**Number of Questions**: [Add count]
**Specialties Covered**:
- Cardiology
- Neurology
- Oncology
- [Add more as needed]

**Notes**:
- National examination for medical residency admission
- Multiple choice format (typically 5 options)
- [Add any source-specific considerations]

**File Prefix**: `italian_ssm_`

### 2. Spanish MIR (Médico Interno Residente)

**Description**: Spanish Medical Residency Examination
**Language**: Spanish
**Years**: [Add years covered]
**Number of Questions**: [Add count]
**Specialties Covered**:
- Cardiology
- Neurology
- Oncology
- [Add more as needed]

**Notes**:
- National examination for medical residency admission in Spain
- Multiple choice format (typically 5 options)
- [Add any source-specific considerations]

**File Prefix**: `spanish_mir_`

### 3. Portuguese Medical Residency Examination

**Description**: Portuguese Medical Residency Examination
**Language**: Portuguese
**Years**: [Add years covered]
**Number of Questions**: [Add count]
**Specialties Covered**:
- [List specialties]

**Notes**:
- [Add source-specific information]

**File Prefix**: `portuguese_`

### 4. French Medical Residency Examination

**Description**: French Medical Residency Examination
**Language**: French
**Years**: [Add years covered]
**Number of Questions**: [Add count]
**Specialties Covered**:
- [List specialties]

**Notes**:
- [Add source-specific information]

**File Prefix**: `french_`

## TODO: Update This List

**IMPORTANT**: As more exam sources are added to the leaderboard, please update this document with:
- Complete source information
- Number of questions added
- Years covered
- Any special considerations for formatting or evaluation

## Template for Adding New Sources

When adding a new medical examination source, use the following template:

### [Source Name] ([Abbreviation])

**Description**: [Full name and description of the examination]
**Language**: [Language]
**Years**: [Years covered, e.g., 2020-2024]
**Number of Questions**: [Total count]
**Specialties Covered**:
- [List all specialties represented]
- [Add more as needed]

**Format Details**:
- Number of answer options: [e.g., 4, 5]
- Question format: [e.g., clinical vignette, direct question]
- Scoring system: [e.g., +1 for correct, 0 for incorrect, -0.25 for wrong]

**Notes**:
- [Any source-specific considerations]
- [Copyright or licensing information]
- [Difficulty level or special characteristics]

**File Prefix**: `[unique_prefix]_`

**Access Information**:
- [How to obtain the questions]
- [Official website or contact]
- [Availability: public/restricted/permission required]

**Quality Considerations**:
- [Question quality notes]
- [Answer key reliability]
- [Any known issues or ambiguities]

## Source Quality Metrics

For each source, track the following metrics:

| Source | Total Questions | Verified Answers | Ambiguous Questions | Last Updated |
|--------|----------------|------------------|-------------------|--------------|
| Italian SSM | [count] | [count] | [count] | [date] |
| Spanish MIR | [count] | [count] | [count] | [date] |
| Portuguese | [count] | [count] | [count] | [date] |
| French | [count] | [count] | [count] | [date] |

## Special Considerations

### Language-Specific Notes

- **Italian**: [Any language-specific considerations]
- **Spanish**: [Any language-specific considerations]
- **Portuguese**: [Any language-specific considerations]
- **French**: [Any language-specific considerations]

### Cross-Language Comparison

When comparing performance across languages:
- Consider translation accuracy if questions are translated
- Account for cultural differences in medical practice
- Note any differences in examination style or difficulty

## Adding New Sources: Checklist

- [ ] Source documented in this file using the template above
- [ ] File prefix established and documented
- [ ] Questions added to `solutions.json` with proper IDs
- [ ] Answers verified for accuracy
- [ ] Specialty classifications added
- [ ] Any ambiguous questions flagged
- [ ] Source-specific evaluation rules documented (if different from standard)
- [ ] README.md updated if workflow changes are needed

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-03-05 | Initial documentation with 4 sources | [Your Name] |
| [Date] | [Description of changes] | [Author] |
