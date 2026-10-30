#!/usr/bin/env python3
"""
Convert the downloaded exam CSVs (data/processed_csv/) into the canonical
question schema used by the pipeline (same shape as
data/ssm_questions_with_solution.json), one JSON per exam, written to
data/new_exams/.

The new exams covered (added Oct 2026, none present in EuropeMedQA):
  SSM Italy 2025/2026, MIR Spain 2025/2026, EDN France 2023-2025,
  PNA Portugal 2025, PES Poland (5 specialties x 10 sessions 2018-2022).

Answer-key semantics in the source CSVs:
  A-E    correct option (lowercase a-d in MIR rows is normalized)
  ANNULLED / X   question annulled by the exam board -> no key, nullified
  (empty)        EDN France: no official corrigé exists -> no key

Data containing correct answers is never committed (see .gitignore):
both data/processed_csv/ and data/new_exams/ stay untracked.

Usage: python3 scripts/convert_processed_csvs.py
"""
import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "processed_csv"
OUT = BASE / "data" / "new_exams"

PES_SPECIALTY_EN = {
    "pediatria": "Pediatrics",
    "choroby_wewnetrzne": "Internal Medicine",
    "chirurgia_ogolna": "General Surgery",
    "psychiatria": "Psychiatry",
    "medycyna_rodzinna": "Family Medicine",
}

# Answer-key provenance recorded per exam family (from the staging SUMMARY.md)
KEY_SOURCE = {
    "ssm": "official MUR paper header (correct answer printed as A)",
    "mir": "official plantilla definitiva (2025 FSE JSON / 2026 key PDF)",
    "pna": "official chave.pdf (Prova A column)",
    "pes": "official CEM klucz PDF per exam",
    "edn": "none (CNG publishes questions only)",
}


def exam_family(filename: str) -> str:
    for fam in ("ssm", "mir", "edn", "pna", "pes"):
        if filename.startswith(fam):
            return fam
    raise ValueError(f"Unknown exam file: {filename}")


def pes_specialty(exam_id: str) -> str:
    # exam_id like pes_poland_choroby_wewnetrzne_2021_jesien
    parts = exam_id.split("_")
    for slug, en in PES_SPECIALTY_EN.items():
        if slug in "_".join(parts[2:-2]):
            return en
    raise ValueError(f"Unknown PES specialty in {exam_id}")


def convert_file(path: Path) -> list[dict]:
    family = exam_family(path.name)
    out = []
    seen_ids: set[str] = set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            exam_id = row["exam_id"].strip()
            qnum = int(row["question_number"])
            year = int(row["year"])

            options = []
            for i, letter in enumerate("abcde"):
                text = row[f"choice_{letter}"].strip()
                if text:
                    options.append({"letter": letter.upper(), "text": text})

            raw_answer = row["correct_answer"].strip().upper()
            nullified = raw_answer in ("ANNULLED", "X")
            if raw_answer in ("A", "B", "C", "D", "E"):
                correct = {"letter": raw_answer, "index": "ABCDE".index(raw_answer)}
            else:
                # annulled, or EDN (no key published)
                correct = None

            images = [s.strip() for s in row["image_file"].split(";") if s.strip()]
            qid = row["question_id"].strip() or f"{exam_id}_q{qnum:03d}"
            # three scanned 2022 PES papers print the same question number on
            # two different questions — keep both, disambiguate the id
            if qid in seen_ids:
                qid = f"{qid}_b"
            seen_ids.add(qid)

            if family == "pes":
                specialty = pes_specialty(exam_id)
            else:
                specialty = None  # not labeled in the source CSVs

            metadata = {
                "test_year": year,
                "number_in_test": qnum,
                "nullified": nullified,
                "exam_id": exam_id,
                "language": row["language"].strip(),
                "country": row["country"].strip(),
                "answer_key_source": KEY_SOURCE[family],
                "source_csv": f"data/processed_csv/{path.name}",
            }
            if images:
                metadata["images"] = [
                    f"data/processed_csv/images/{exam_id}/{img}" for img in images
                ]

            out.append(
                {
                    "id": qid,
                    "question": row["question_text"].strip(),
                    "options": options,
                    "correct_answer": correct,
                    "specialty": specialty,
                    "has_image": bool(images),
                    "metadata": metadata,
                }
            )
    return out


def main():
    OUT.mkdir(exist_ok=True)
    csvs = sorted(SRC.glob("*.csv"))
    assert len(csvs) == 58, f"expected 58 CSVs, found {len(csvs)}"

    total = 0
    converted: dict[Path, list] = {}
    tallies = {}
    for path in csvs:
        questions = convert_file(path)
        converted[path] = questions
        total += len(questions)

        # when options were extracted, a lettered key must point at one of them;
        # a few dozen PES rows lost ALL options to OCR (key still kept above)
        for q in questions:
            ca = q["correct_answer"]
            if ca is not None and q["options"]:
                assert any(o["letter"] == ca["letter"] for o in q["options"]), (
                    f"{q['id']}: key {ca['letter']} missing from options"
                )

        dest = OUT / (path.stem + ".json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=1)

        fam = exam_family(path.name)
        t = tallies.setdefault(
            fam, {"questions": 0, "keyed": 0, "nullified": 0, "no_key": 0, "no_options": 0}
        )
        t["questions"] += len(questions)
        for q in questions:
            if q["correct_answer"]:
                t["keyed"] += 1
            elif q["metadata"]["nullified"]:
                t["nullified"] += 1
            else:
                t["no_key"] += 1
            if not q["options"]:
                t["no_options"] += 1

    assert total == 7812, f"expected 7812 questions total, got {total}"
    id_counts: dict[str, int] = {}
    for path in csvs:
        for q in converted[path]:
            id_counts[q["id"]] = id_counts.get(q["id"], 0) + 1
    dupes = {i: n for i, n in id_counts.items() if n > 1}
    assert not dupes, f"duplicate question ids across exams: {dupes}"
    print(f"Converted {len(csvs)} CSVs -> {total} questions in {OUT}/")
    for fam, t in sorted(tallies.items()):
        print(
            f"  {fam:4s}: {t['questions']:5d} questions | "
            f"{t['keyed']:5d} keyed | {t['nullified']} annulled | {t['no_key']} no key published"
            + (f" | {t['no_options']} without options (OCR)" if t["no_options"] else "")
        )


if __name__ == "__main__":
    main()
