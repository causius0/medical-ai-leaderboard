#!/usr/bin/env python3
"""
Prepare LoRA Fine-Tuning Data from EuropeMedQA

Builds train/dev JSONL (chat format, portable across mlx-lm and TRL) for LoRA
experiments, with strict hygiene:

  - EXCLUDES all Italian SSM questions (they are the benchmark eval set —
    training on them would be contamination). Contamination guard additionally
    drops any train question whose normalized text matches an eval question.
  - Drops nullified / ANULADA / unparseable-answer / <4-option / empty questions.
  - Image-dependent questions are excluded by default (v1 trains text-only);
    --include-image-descriptions keeps them when a vision description exists.
  - Dedupes exact normalized question text (keeps first occurrence).
  - Balances correct-answer positions by permuting options (the source exams
    are heavily letter-skewed — SSM is 91% 'A'), seeded and reproducible.
  - Dev split (checkpoint selection only) drawn from Abilitazione clinical:
    same language family as the eval set, never trained on.

Output: data/lora/train.jsonl, data/lora/dev.jsonl, data/lora/meta.json
Each line: {"messages": [{"role": "user", "content": <prompt>},
                         {"role": "assistant", "content": <letter>}],
            "meta": {exam, question_id, domain, orig_letter}}

Usage:
    python3 scripts/prepare_lora_data.py
    python3 scripts/prepare_lora_data.py --dev-size 500 --seed 42
    python3 scripts/prepare_lora_data.py --include-image-descriptions
"""

import argparse
import csv
import json
import os
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "europemedqa", "EuropeMedQA.csv")
DEFAULT_EVAL = os.path.join(REPO_ROOT, "data", "ssm_questions_with_solution.json")
DEFAULT_DESC = os.path.join(REPO_ROOT, "data", "image_descriptions.json")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "lora")

NA_VALUES = {"", "N/A", "n/a", "NA", "NULL", "null", "-", "None"}
YES_VALUES = {"yes", "si", "sí", "true", "1", "y", "anulada"}
NULLIFIED_COLS = ["nullified", "Nullified", "nullified "]
IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff"}

LETTERS = ["A", "B", "C", "D", "E"]

PROMPT_TEMPLATES = {
    "Italian": (
        "Sei un esperto medico che affronta una domanda a scelta multipla "
        "dell'esame di specializzazione medica.\n\n"
        "Domanda:\n{question}\n\n{options}\n\n"
        "Rispondi unicamente con la lettera della risposta corretta."
    ),
    "Spanish": (
        "Eres un experto médico respondiendo una pregunta tipo test "
        "del examen MIR.\n\nPregunta:\n{question}\n\n{options}\n\n"
        "Responde únicamente con la letra de la respuesta correcta."
    ),
    "French": (
        "Vous êtes un expert médical répondant à une question à choix multiples "
        "des ECN.\n\nQuestion :\n{question}\n\n{options}\n\n"
        "Répondez uniquement avec la lettre de la réponse exacte."
    ),
    "Portuguese": (
        "És um especialista em medicina a responder a uma pergunta de escolha "
        "múltipla do exame PNA.\n\nPergunta:\n{question}\n\n{options}\n\n"
        "Responde apenas com a letra da resposta correta."
    ),
}
EXAM_LANGUAGE = {
    "Abilitazione_Italy_clinical": "Italian",
    "Abilitazione_Italy_preclinical": "Italian",
    "MIR_Spain": "Spanish",
    "ECN_France": "French",
    "PNA_Portugal": "Portuguese",
}
DEV_EXAM = "Abilitazione_Italy_clinical"


def real(v) -> bool:
    return (v or "").strip() not in NA_VALUES and (v or "").strip() != ""


def norm_text(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def clean_answer(v) -> str:
    """Strip quotes/brackets; 'C', \"A\", ['C'] -> C ; ['C', 'E'] -> 'C,E'."""
    return re.sub(r"[\[\]\"']", "", (v or "")).strip().upper()


def parse_answer(v) -> Optional[str]:
    v = clean_answer(v)
    return v if len(v) == 1 and v in LETTERS else None


def is_nullified(row) -> bool:
    for col in NULLIFIED_COLS:
        if col in row and row[col].strip().lower() in YES_VALUES:
            return True
    return False


def link_ext(link: str) -> str:
    base = link.split("?")[0]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def is_image_dependent(row) -> bool:
    """Conservative union of the two source signals; over-exclusion is safe."""
    if row.get("picture_provided", "").strip().lower() in YES_VALUES:
        return True
    link = row.get("picture_link", "").strip()
    return real(link) and link_ext(link) in IMAGE_EXTS


def render_options(options: list) -> str:
    return "\n".join(f"{letter}. {text}" for letter, text in options)


def build_prompt(question: str, options: list, language: str, description: str = None) -> str:
    q = question
    if description:
        label = {"Italian": "Descrizione dell'immagine", "Spanish": "Descripción de la imagen",
                 "French": "Description de l'image", "Portuguese": "Descrição da imagem"}.get(
                     language, "Image description")
        q = f"{question}\n\n[{label}: {description}]"
    return PROMPT_TEMPLATES[language].format(question=q, options=render_options(options))


def main():
    parser = argparse.ArgumentParser(description="Prepare LoRA train/dev data from EuropeMedQA")
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--eval", dest="eval_json", default=DEFAULT_EVAL,
                        help="Eval dataset JSON (for the contamination guard)")
    parser.add_argument("--descriptions", default=DEFAULT_DESC)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--dev-size", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-image-descriptions", action="store_true",
                        help="Keep image questions that have a vision description")
    parser.add_argument("--answer-style", choices=["letter", "fulltext"], default="letter",
                        help="Assistant target: bare letter, or letter + full answer text")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    stats = defaultdict(Counter)

    # Eval-side normalized texts for the contamination guard
    with open(args.eval_json, encoding="utf-8") as f:
        eval_questions = json.load(f)
    eval_norms = {norm_text(q["question"]) for q in eval_questions}

    descriptions = {}
    if args.include_image_descriptions:
        if os.path.isfile(args.descriptions):
            with open(args.descriptions, encoding="utf-8") as f:
                raw = json.load(f)
            descriptions = {qid: e["description"] for qid, e in raw.items() if e.get("status") == "ok"}
        else:
            print(f"Warning: {args.descriptions} not found; proceeding without image descriptions")

    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # ---- clean + filter ----
    kept = []
    for r in rows:
        exam = r["exam"]
        if exam == "SSM_Italy":
            stats[exam]["excluded_eval_exam"] += 1
            continue
        qid = r.get("questionID", "").strip()
        qtext = r.get("question_text", "").strip()
        answer = parse_answer(r.get("correct_option"))

        if is_nullified(r):
            stats[exam]["dropped_nullified"] += 1
            continue
        if not qtext:
            stats[exam]["dropped_empty_question"] += 1
            continue
        if answer is None:
            cleaned = clean_answer(r.get("correct_option"))
            if "," in cleaned:  # genuinely multi-answer (ECN format)
                stats[exam]["dropped_multi_answer"] += 1
            else:
                stats[exam]["dropped_bad_answer"] += 1
            continue

        options = []
        for letter in LETTERS:
            col = f"option_{letter.lower()}"
            if real(r.get(col)):
                options.append((letter, r[col].strip()))
        correct_text = next((t for l, t in options if l == answer), None)
        if correct_text is None:
            stats[exam]["dropped_answer_not_in_options"] += 1
            continue
        if len(options) < 4:
            stats[exam]["dropped_too_few_options"] += 1
            continue

        image_q = is_image_dependent(r)
        if image_q:
            if args.include_image_descriptions and qid in descriptions:
                description = descriptions[qid]
            else:
                stats[exam]["dropped_image_question"] += 1
                continue
        else:
            description = None

        n = norm_text(qtext)
        if n in eval_norms:
            stats[exam]["dropped_contaminates_eval"] += 1
            continue

        kept.append({
            "exam": exam, "question_id": qid, "question": qtext, "options": options,
            "answer": answer, "answer_text": correct_text, "norm": n,
            "domain": (r.get("domain") or "").strip(), "description": description,
        })

    # ---- dedup (keep first) ----
    deduped = []
    seen = set()
    for q in kept:
        if q["norm"] in seen:
            stats[q["exam"]]["dropped_duplicate"] += 1
            continue
        seen.add(q["norm"])
        deduped.append(q)

    # ---- dev split from Abilitazione clinical ----
    dev_pool = [q for q in deduped if q["exam"] == DEV_EXAM]
    train_pool = [q for q in deduped if q["exam"] != DEV_EXAM]
    rng.shuffle(dev_pool)
    dev = dev_pool[: args.dev_size]
    stats[DEV_EXAM]["held_out_dev"] = len(dev)
    train = train_pool + dev_pool[args.dev_size:]

    # ---- balance answer positions by permuting options ----
    letter_dist_after = Counter()
    for i, q in enumerate(train + dev):
        shuffled = [opt for opt in q["options"] if opt[0] != q["answer"]]
        shuffled.append((q["answer"], q["answer_text"]))
        rng.shuffle(shuffled)
        # correct option goes to the globally least-used letter slot that exists
        # in this question (some questions have only 4 options)
        slots = LETTERS[: len(shuffled)]
        target = min(slots, key=lambda L: (letter_dist_after[L], rng.random()))
        new_index = next(j for j, (l, _) in enumerate(shuffled) if l == q["answer"])
        target_index = LETTERS.index(target)
        shuffled[new_index], shuffled[target_index] = shuffled[target_index], shuffled[new_index]
        q["final_options"] = shuffled
        q["final_answer"] = target
        letter_dist_after[target] += 1

    # ---- write JSONL ----
    os.makedirs(args.out_dir, exist_ok=True)

    def write_split(path, questions, split_name):
        with open(path, "w", encoding="utf-8") as f:
            for q in questions:
                language = EXAM_LANGUAGE[q["exam"]]
                # final_options holds (orig_letter, text) in final order; the
                # prompt must re-letter them A..E by position so the target
                # letter (final_answer) refers to what the model actually sees
                positional = [(LETTERS[i], text) for i, (_, text) in enumerate(q["final_options"])]
                prompt = build_prompt(q["question"], positional, language, q.get("description"))
                completion = q["final_answer"]
                if args.answer_style == "fulltext":
                    completion = f"{q['final_answer']}. {q['answer_text']}"
                rec = {
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": completion},
                    ],
                    "meta": {
                        "exam": q["exam"], "question_id": q["question_id"],
                        "domain": q["domain"], "orig_answer": q["answer"],
                        "split": split_name,
                    },
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    train_path = os.path.join(args.out_dir, "train.jsonl")
    dev_path = os.path.join(args.out_dir, "dev.jsonl")
    write_split(train_path, train, "train")
    write_split(dev_path, dev, "dev")

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "answer_style": args.answer_style,
        "include_image_descriptions": args.include_image_descriptions,
        "dev_exam": DEV_EXAM,
        "totals": {"train": len(train), "dev": len(dev)},
        "train_by_exam": dict(Counter(q["exam"] for q in train)),
        "dev_by_exam": dict(Counter(q["exam"] for q in dev)),
        "dev_domains": dict(Counter(q["domain"] for q in dev).most_common(10)),
        "letters_after_balancing": dict(sorted(letter_dist_after.items())),
        "per_exam_filters": {exam: dict(c) for exam, c in sorted(stats.items())},
    }
    with open(os.path.join(args.out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"train: {len(train)}  dev: {len(dev)}  ->  {args.out_dir}")
    print(f"answer letters after balancing: {dict(sorted(letter_dist_after.items()))}")
    print("\nper-exam disposition:")
    for exam, c in sorted(stats.items()):
        print(f"  {exam}: {dict(c)}")


if __name__ == "__main__":
    main()
