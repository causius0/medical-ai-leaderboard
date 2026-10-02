# LoRA Training Plan — Staged Runs with Review Gates

**Principle**: no long unattended runs. Every stage ends at a **review gate** where we evaluate, compare against hypotheses, and decide: continue, scale, or change direction. The medbench Postgres (`shuffled_*` tables) is the only scoreboard.

## Fixed reference points

| Anchor | Value |
|---|---|
| Base model | `models/LFM2-24B-A2B-4bit` (mlx, 4-bit) |
| Eval | 1,060 PG-shuffled SSM questions (`scripts/build_pg_shuffle.py` output), greedy, single-question harness |
| **Baseline (no LoRA)** | **see results/local/*_pg_shuffled.json — inserted into medbench as run on canonical set** |
| Historical leaderboard | gemma3:12b 81.6% · qwen3:8b 79.3% · llama3.1:8b 69.0% · mistral:7b 54.6% · LFM2.5-8B-A1B 23.2% |
| Training data | `data/lora/train.jsonl` 9,401 · `valid.jsonl` 500 (checkpoint selection only) |

## Current hypotheses (ranked by what we expect)

- **H1 — Format+domain SFT gives a fast, large early gain.** Most of the improvement arrives in the first ~1–2k iterations (the model learns the task/answer-format and domain register); after that gains come slowly. *Validate*: stage 1 vs stage 2 delta.
- **H2 — LoRA lifts Liquid toward small-model peers, not past them.** Expect ~65–75% ceiling for rank-16 on 9.4k examples; beating gemma3:12b would require CoT or full FT. *Validate*: trajectory across stages.
- **H3 — Valid loss ≠ eval accuracy.** Letter targets make valid loss noisy; the eval gate (1,060 questions) is the real signal. *Validate*: correlation between valid loss and gate accuracy at each break.
- **H4 — Position bias shrinks after training on balanced data.** Compare prediction-letter distribution pre/post (eval set is uniform, so skew = bias). *Validate*: prediction distribution at each gate.
- **H5 — More layers (16→32) or rank (16→64) adds little after stage 2.** Cheap to test once, only if stage 2 plateaus.
- **H6 — Cross-lingual training data helps Italian eval.** Train-set already mixes IT/ES/FR/PT; if stage 2+ plateaus, ablate Italian-only vs multilingual.

## Stages (each ends in a review break)

### Stage 1 — Signal check (~40 min): 1,500 iters
```
.venv/bin/python -m mlx_lm lora --train \
  --model models/LFM2-24B-A2B-4bit --data data/lora \
  --fine-tune-type lora --num-layers 16 --batch-size 2 \
  --learning-rate 1e-4 --iters 1500 --max-seq-length 1024 \
  --grad-checkpoint --mask-prompt \
  --adapter-path adapters/v1_s1 --save-every 250 \
  --steps-per-eval 250 --val-batches 20 --seed 42
```
Gate 1: eval adapter on the 1,060 (harness `--adapter adapters/v1_s1`).
- Δ ≥ +5 pts over baseline → H1 confirmed → proceed to Stage 2 unchanged.
- Δ +1–5 → proceed but raise num-layers to 24 in Stage 2.
- Δ ≈ 0 or worse → stop; debug (adapter attached? lr? data parsing) before any longer run.

### Stage 2 — Convergence check (~2 h): resume to 6,000 iters
`--resume-adapter-file adapters/v1_s1/0001500_adapters.safetensors --iters 6000 --adapter-path adapters/v1_s2`
Gate 2: full eval + specialty breakdown + letter-distribution (H4) + top error categories.
- Still climbing vs Stage 1 → Stage 3.
- Plateau ≤ +2 pts → skip to ablations (H5/H6) instead of more compute.

### Stage 3 — Full epoch+ (~4 h): to ~12,000 iters (≈2.5 epochs), cosine decay.
Gate 3 (final): full eval, McNemar vs baseline, insert best checkpoint into medbench `shuffled_*`, decide next direction (CoT distillation, rank/layers ablation, multilingual ablation, or second model).

## Review-break checklist (every gate)
1. Gate accuracy + Δ vs previous stage (paired per-question diff, not just totals)
2. Valid-loss trajectory vs gate accuracy (H3)
3. Prediction-letter skew (H4)
4. Specialty breakdown — which specialties moved
5. 10 sampled wrong answers — error taxonomy (knowledge vs format vs language)
6. Decide: continue / scale / change — write the decision in this file before launching the next stage

## Bookkeeping
- Adapters: `adapters/v1_s1`, `v1_s2`, … (gitignored)
- Every gate result committed under `results/local/` and inserted into `medbench.shuffled_*`
- This file is the experiment log: append a dated line at every gate
