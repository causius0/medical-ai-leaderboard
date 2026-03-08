#!/usr/bin/env python3
"""
Add medical specialty classification to each question in the SSM dataset.
"""

import json
import re
from pathlib import Path

# Define the specialty categories
MEDICAL_SPECIALTIES = [
    "General (Internal) Medicine",
    "Paediatrics",
    "Cardiology",
    "Respiratory Medicine",
    "Endocrinology",
    "Gastroenterology",
    "Rheumatology",
    "Neurology",
    "Psychiatry",
    "Dermatology"
]

SURGICAL_SPECIALTIES = [
    "General Surgery",
    "Neurological Surgery",
    "Plastic Surgery",
    "Orthopaedics",
    "Ophthalmology",
    "Urology",
    "Otorhinolaryngology",
    "Obstetrics and Gynaecology",
    "Thoracic Surgery",
    "Vascular Surgery"
]

ALL_SPECIALTIES = MEDICAL_SPECIALTIES + SURGICAL_SPECIALTIES


def classify_question(question_text, options_text):
    """
    Classify a medical question based on keywords and medical terminology.
    Returns the most appropriate specialty.
    """
    # Combine question and options for analysis
    full_text = f"{question_text} {options_text}".lower()

    # Keyword patterns for each specialty
    patterns = {
        "Cardiology": [
            r'\bcardio', r'\bcuor', r'\baritmia', r'\binfarto', r'\bangina',
            r'\bipertension', r'\becg', r'\becocardiogram', r'\bvalvol',
            r'\bendocardite', r'\bmiocardio', r'\bpericardio'
        ],
        "Respiratory Medicine": [
            r'\bpolmon', r'\brespiratori', r'\basma', r'\bbpco', r'\btorace',
            r'\bbroncopolmonite', r'\bpolmonite', r'\benfisema', r'\bfibrosi',
            r'\bdispnea', r'\bemotorace', r'\bpneumotorace'
        ],
        "Endocrinology": [
            r'\bdiabete', r'\btiroide', r'\binsulina', r'\bglicemia', r'\bormone',
            r'\bipofisi', r'\bsurrenal', r'\badrenal', r'\bcushing', r'\baddison',
            r'\biperparatiroid', r'\bipoparatiroid', r'\bacromegalia'
        ],
        "Gastroenterology": [
            r'\bgastro', r'\bintestin', r'\bfegato', r'\bepat', r'\bcirrosi',
            r'\bcolite', r'\bcrohn', r'\bceliac', r'\bpancreatite', r'\besofag',
            r'\bulcera', r'\bdiarrea', r'\bcolitica', r'\brettocolite'
        ],
        "Rheumatology": [
            r'\bartrite', r'\blupus', r'\bsclerosi sistemica', r'\bsjogren',
            r'\bvasculite', r'\bartropatia', r'\bspondiloartrite', r'\bgotta',
            r'\bfibromialgia', r'\bpolimialgia', r'\banti-nucleo', r'\bana\b'
        ],
        "Neurology": [
            r'\bneurolog', r'\bcerebr', r'\bictus', r'\beparkinson', r'\bsclerosi multipla',
            r'\bemicrania', r'\bepilessia', r'\bconvulsion', r'\batrofia muscolare',
            r'\bneuropatia', r'\bmielite', r'\bmeningite', r'\bencefalite', r'\balzheimer'
        ],
        "Psychiatry": [
            r'\bpsichiatr', r'\bdepression', r'\bansioso', r'\bschizofrenia',
            r'\bbipolar', r'\bdelirio', r'\ballucinazion', r'\bsuicid', r'\bpsicosi',
            r'\bautismo', r'\badhd', r'\banoressia', r'\bbulimia'
        ],
        "Dermatology": [
            r'\bcute', r'\bpelle', r'\bdermat', r'\beczema', r'\bpsoriasi',
            r'\bmelanoma', r'\beruzione', r'\bprurito', r'\borticaria', r'\bacne',
            r'\bvitiligine', r'\balopecia', r'\bunghie'
        ],
        "Paediatrics": [
            r'\bbambino', r'\bneonato', r'\bpediatric', r'\binfant', r'\badolescen',
            r'\bvaccin', r'\bmorbillo', r'\brosolia', r'\bvaricella', r'\bparotite',
            r'\bmesi di vita', r'\banni di età', r'\ballattamento'
        ],
        "General Surgery": [
            r'\bchirurgia generale', r'\bappendic', r'\bernia', r'\blaparotomia',
            r'\bperitonite', r'\baddome acuto', r'\bocclusion', r'\btrauma addominale'
        ],
        "Neurological Surgery": [
            r'\bneurochirurg', r'\btumor cerebral', r'\bidrocefalo', r'\bemorragia cerebrale',
            r'\baneurisma cerebrale', r'\btrauma cranico'
        ],
        "Orthopaedics": [
            r'\bortoped', r'\bfrattura', r'\bosso', r'\bartroscopia', r'\bprotesi',
            r'\blegamento', r'\bmenisco', r'\btendin', r'\blussazion', r'\bosteomielite',
            r'\bscoliosi', r'\bartroplastica'
        ],
        "Ophthalmology": [
            r'\bocchio', r'\boftalm', r'\bvisivo', r'\bretina', r'\bglaucoma',
            r'\bcataratta', r'\bcongiuntiv', r'\bmiopia', r'\bcecità', r'\bcornea'
        ],
        "Urology": [
            r'\burolog', r'\brene', r'\bvescica', r'\bprostata', r'\buretere',
            r'\bincontinenza', r'\bcalcoli renali', r'\bnefrolitiasi', r'\bematuria',
            r'\bpielonefrite', r'\biperplasia prostatica'
        ],
        "Otorhinolaryngology": [
            r'\borl\b', r'\borecchio', r'\bnaso', r'\bgola', r'\bfaringe',
            r'\blaringe', r'\botite', r'\bsinusite', r'\btonsill', r'\bipoacusia',
            r'\brinite', r'\bvertigine'
        ],
        "Obstetrics and Gynaecology": [
            r'\bginecologue', r'\bgravidanza', r'\bparto', r'\bostetric', r'\bfeto',
            r'\bplacenta', r'\butero', r'\bovai', r'\bmestruazion', r'\bamenorrea',
            r'\beclampsia', r'\bpreeclampsia', r'\bcesareo', r'\bendometriosi',
            r'\bgravida', r'\bdonna.*anni.*gravidanz'
        ],
        "Thoracic Surgery": [
            r'\bchirurgia toracica', r'\bresezion.*polmon', r'\blobectomia',
            r'\bpneumonectomia', r'\bmediastino', r'\btoracotomia'
        ],
        "Vascular Surgery": [
            r'\bchirurgia vascolare', r'\baneurisma aorta', r'\btrombosi', r'\bembolia',
            r'\bvarici', r'\bischemica cronica', r'\brivascolarizzazion', r'\bcarotide'
        ],
        "Plastic Surgery": [
            r'\bchirurgia plastica', r'\bricostruttiv', r'\bustion', r'\binnesto',
            r'\bmastoplastica', r'\brinoplastica'
        ],
        "General (Internal) Medicine": [
            # This will be the default for medical questions that don't fit elsewhere
            r'\binterni', r'\bmedicina generale', r'\bantibiotico', r'\bfebbre',
            r'\binfezion', r'\bsepsi', r'\bshock', r'\btrasfusion'
        ]
    }

    # Score each specialty based on keyword matches
    scores = {specialty: 0 for specialty in ALL_SPECIALTIES}

    for specialty, keyword_patterns in patterns.items():
        for pattern in keyword_patterns:
            matches = len(re.findall(pattern, full_text))
            scores[specialty] += matches

    # Find the specialty with the highest score
    max_score = max(scores.values())

    if max_score > 0:
        # Return the specialty with highest score
        for specialty, score in scores.items():
            if score == max_score:
                return specialty

    # Default classification
    # Check if it mentions surgery or surgical terms
    if any(word in full_text for word in ['chirurg', 'intervento', 'operazion', 'resezione']):
        return "General Surgery"

    # Default to General Internal Medicine
    return "General (Internal) Medicine"


def main():
    # Load the questions
    data_path = Path(__file__).parent.parent / "data" / "ssm_questions_with_solution.json"

    print(f"Loading questions from: {data_path}")
    with open(data_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"Total questions: {len(questions)}")
    print("\nClassifying questions by specialty...")

    # Classify each question
    for i, question in enumerate(questions, 1):
        # Get question text and options
        q_text = question['question']
        options_text = ' '.join([str(opt['text']) for opt in question['options']])

        # Classify
        specialty = classify_question(q_text, options_text)
        question['specialty'] = specialty

        if i % 100 == 0:
            print(f"Processed {i}/{len(questions)} questions...")

    # Save updated JSON
    output_path = data_path
    print(f"\nSaving updated questions to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    # Print statistics
    print("\n" + "="*60)
    print("SPECIALTY DISTRIBUTION")
    print("="*60)

    from collections import Counter
    specialty_counts = Counter(q['specialty'] for q in questions)

    print("\nMedical Specialties:")
    medical_total = 0
    for specialty in MEDICAL_SPECIALTIES:
        count = specialty_counts[specialty]
        medical_total += count
        print(f"  {specialty:35s}: {count:4d} ({count/len(questions)*100:5.1f}%)")

    print(f"\nSurgical Specialties:")
    surgical_total = 0
    for specialty in SURGICAL_SPECIALTIES:
        count = specialty_counts[specialty]
        surgical_total += count
        print(f"  {specialty:35s}: {count:4d} ({count/len(questions)*100:5.1f}%)")

    print(f"\n{'Total Medical:':<37s} {medical_total:4d} ({medical_total/len(questions)*100:5.1f}%)")
    print(f"{'Total Surgical:':<37s} {surgical_total:4d} ({surgical_total/len(questions)*100:5.1f}%)")
    print(f"{'Grand Total:':<37s} {len(questions):4d}")

    print("\n✓ Classification complete!")


if __name__ == "__main__":
    main()
