# LoRA Training Plan — Staged Runs with Review Gates

**Principle**: no long unattended runs. Every stage ends at a **review gate** where we evaluate, compare against hypotheses, and decide: continue, scale, or change direction. The medbench Postgres (`shuffled_*` tables) is the only scoreboard.

## SESSION LOG

### 2026-10-02/03 — Premise rewrite (before any training)

The project's motivation ("Liquid is bad, 23%") was dismantled by measurement. On the canonical PG-shuffled set, LFM2.5-8B-A1B (4-bit MLX):

| Budget | Score | run_id | Refusals |
|---|---|---|---|
| 256 (Sept, ollama) | 23.21% | 7 | ~most |
| 1,024 | 67.55% | 10 | 149 |
| +2,048 retry | 71.89% | 11 | 65 |
| +4,096 retry | **72.64%** | 12 | 35 |

Findings that reshape the plan:
- **Budget starvation, not capability**: 88% of the model's responses exceed 256 think-tokens (median ~490). The 23% entry measured a model cut off mid-thought.
- **Think length anticorrelates with accuracy**: <500 chars → 100%, 500–1500 → 86.5%, 1500–3000 → 74.2%, 3000+ → 59%, never-closes → 0%. The spiral is a symptom of uncertainty and usually ends wrong.
- **The budget lever is exhausted**: the 4096 retry recovered 30/65 refusals at 27% accuracy (random level). The remaining failures are behavioral, not budget.
- 24B-A2B baseline for reference: 60.38% (run_id=9) — the 8B beats it while thinking.

**New H0 (top of the stack): direct-answer SFT removes the uncertainty spiral.**
Success criterion for Stage 1: match or approach 72.64% at an 8-token budget
(no thinking). Even ~65% with zero CoT would beat everything in its size class
at 10–50× on-device speed. If direct-answer SFT degrades accuracy badly, the
reasoning is load-bearing → Stage 2 pivots to shortened-CoT distillation.

Other session outcomes: canonical PG eval set (`build_pg_shuffle.py`);
publish flow with run-parameter notes (`publish_to_medbench.py`);
CoT stored per-answer (`think_chars`/`reasoning` column); vision-description
pipeline for image questions (502 descriptions, audited, leak-checked);
LoRA data prepared (9,401 train / 500 dev, position-balanced, contamination-guarded).

## Fixed reference points

| Anchor | Value |
|---|---|
| Base model | `models/LFM2.5-8B-A1B-4bit` (mlx-community/LFM2.5-8B-A1B-MLX-4bit, patched config) |
| Eval | 1,060 PG-shuffled SSM questions (`scripts/build_pg_shuffle.py` output), greedy, single-question harness; thinking models scored post-`</think>` |
| **Baseline to beat** | **72.64%** (run_id=12, budget ladder 1024/2048/4096) |
| Historical leaderboard | qwen3:8b-thinking 88.96% · gemma3:12b 81.6% · qwen3:8b 79.34% · **LFM2.5-8B ladder 72.64%** · llama3.1:8b 68.96% · mistral:7b 54.62% · 24B-A2B 60.38% |
| Training data | `data/lora/train.jsonl` 9,401 · `valid.jsonl` 500 (checkpoint selection only) |
| Adapter eval budget | 8 tokens (direct answer, no thinking) — the whole point |

## Current hypotheses (ranked by what we expect)

- **H0 — Direct-answer SFT removes the spiral.** Training on bare-letter targets teaches commitment; the model matches or approaches 72.64% at 8-token budget. *Validate*: Stage 1 gate vs both 72.64% (ladder) and the short-think accuracy distribution (86–100%).
- **H1 — Format+domain SFT gives a fast, large early gain.** Most of the improvement arrives in the first ~1–2k iterations; after that gains come slowly. *Validate*: stage 1 vs stage 2 delta.
- **H2 — LoRA lifts the 8B toward qwen3:8b (79.3%), not past it.** *Validate*: trajectory across stages.
- **H3 — Valid loss ≠ eval accuracy.** Letter targets make valid loss noisy; the eval gate is the real signal. *Validate*: correlation between valid loss and gate accuracy at each break.
- **H4 — Position bias stays low.** The base already spreads predictions evenly; balanced training data should keep it that way. *Validate*: prediction distribution at each gate.
- **H5 — More layers (16→32) or rank adds little after stage 2.** Test once, only if stage 2 plateaus.
- **H6 — Cross-lingual training data helps Italian eval.** If stage 2+ plateaus, ablate Italian-only vs multilingual.
- **H7 — Thinking can be re-enabled selectively** for questions the direct mode gets wrong (self-consistency check), recovering accuracy without paying CoT cost everywhere. *Validate*: only if Stage 1 lands 60–70%.

## Stages (each ends in a review break)

### Stage 1 — Signal check (~30 min on the 8B): 1,500 iters
```
.venv/bin/python -m mlx_lm lora --train \
  --model models/LFM2.5-8B-A1B-4bit --data data/lora \
  --fine-tune-type lora --num-layers 16 --batch-size 4 \
  --learning-rate 1e-4 --iters 1500 --max-seq-length 1024 \
  --grad-checkpoint --mask-prompt \
  --adapter-path adapters/v2_s1 --save-every 250 \
  --steps-per-eval 250 --val-batches 20 --seed 42
```
Gate 1: eval adapter at **8-token budget** on the 1,060 (`--adapter adapters/v2_s1`).
- Δ ≥ 0 vs 72.64% (i.e., matches the ladder score with no thinking) → H0 confirmed; push Stage 2 for the last points.
- 60–70% at zero CoT → strong net win (10–50× faster); Stage 2 tunes; H7 becomes interesting.
- < 60% or model keeps emitting `<think>` → reasoning is load-bearing; pivot Stage 2 to shortened-CoT distillation (STaR-style: keep traces that close under ~200 tokens and reach the right answer).

### Stage 2 — Convergence check (~1 h on the 8B): resume to 6,000 iters
`--resume-adapter-file adapters/v2_s1/0001500_adapters.safetensors --iters 6000 --adapter-path adapters/v2_s2`
Gate 2: full eval + specialty breakdown + letter-distribution (H4) + top error categories.
- Still climbing vs Stage 1 → Stage 3.
- Plateau ≤ +2 pts → skip to ablations (H5/H6) instead of more compute.

### Stage 3 — Full epoch+ (~2 h): to ~12,000 iters (≈2.5 epochs at batch 4), cosine decay.
Gate 3 (final): full eval, McNemar vs baseline, insert best checkpoint into medbench `shuffled_*` at 8-token budget, decide next direction (CoT distillation, rank/layers ablation, multilingual ablation, or second model).

## Review-break checklist (every gate)
1. Gate accuracy + Δ vs previous stage (paired per-question diff, not just totals)
2. Valid-loss trajectory vs gate accuracy (H3)
3. Prediction-letter skew (H4)
4. Specialty breakdown — which specialties moved
5. 10 sampled wrong answers — error taxonomy (knowledge vs format vs language)
6. Decide: continue / scale / change — write the decision in this file before launching the next stage

## Bookkeeping
- Adapters: `adapters/v2_s1`, `v2_s2`, … (gitignored)
- Every gate result committed under `results/local/` and inserted into `medbench.shuffled_*`
- This file is the experiment log: append a dated line at every gate
