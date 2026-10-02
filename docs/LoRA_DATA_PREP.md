# LoRA Data Preparation

**Script**: `scripts/prepare_lora_data.py` · **Output**: `data/lora/` (gitignored, regenerable)

Builds the LoRA fine-tuning corpus from the non-SSM exams in EuropeMedQA, with strict hygiene so that results measured on the 1,060 SSM eval questions remain a clean generalization measurement.

## Current dataset (v1, seed 42)

| | |
|---|---|
| train | **9,401** questions |
| dev (checkpoint selection only) | **500** (from Abilitazione clinical — same language family as eval, never trained on) |
| answer letters | perfectly balanced: ~1,980 per letter (options permuted, seeded) |
| format | JSONL chat records (`messages` user→assistant), portable across mlx-lm and TRL/PEFT |

Train composition: Abilitazione clinical 2,883 · Abilitazione pre-clinical 3,288 · MIR 2,038 · PNA 888 · ECN 304.

## Hygiene rules applied

1. **No SSM questions** — the whole SSM exam (1,120) is the eval set and is excluded. Additionally, a contamination guard drops any train question whose normalized text matches an eval question (caught **5**: 2 clinical, 3 pre-clinical — the Abilitazione reuses some SSM items).
2. **Answer parsing** handles each exam's quirks: ECN quotes its answers (`"A"`, `['C']`) and is largely **multi-answer** (`['C', 'E']`) — 809 multi-answer ECN questions are dropped (single-letter targets only); MIR `X` and missing answers dropped; PNA `ANULADA` treated as nullified.
3. **Nullified questions** dropped (46 MIR, 2 PNA).
4. **Exact dedup** on normalized question text (20 dropped).
5. **Image-dependent questions** excluded in v1 (they can be re-added with `--include-image-descriptions` now that vision descriptions exist in `data/image_descriptions.json`).
6. **Answer-position balancing**: the source exams are heavily letter-skewed; options are deterministically permuted so correct answers are uniform across A–E. `meta.orig_answer` preserves the original letter; the permutation is verified 100% correct against the source CSV (the rendered prompt re-letters options A–E by position, and the target letter marks the original correct text).
7. Prompts are **per-exam language** (Italian/Spanish/French/Portuguese) with a one-line instruction to answer with the bare letter; the assistant target is the bare letter (`--answer-style fulltext` switches to letter + full answer text).

## Usage

```bash
python3 scripts/prepare_lora_data.py                                  # v1 defaults (seed 42)
python3 scripts/prepare_lora_data.py --include-image-descriptions     # add described image questions
python3 scripts/prepare_lora_data.py --answer-style fulltext          # letter + answer text targets
```

`data/lora/meta.json` records seed, per-exam filter disposition, before/after letter distributions, and split composition — the run is fully reproducible from seed.

## Next step (training)

Proposed first run (pending hardware check): QLoRA r=16, alpha=32, lr 1e-4–2e-4, 2–3 epochs, eval on `dev.jsonl` for checkpoint selection, then final eval on the untouched 1,060 SSM text-only questions with the standard leaderboard harness. Compare against a **locally re-baselined** base model — never against OpenRouter-served numbers.
