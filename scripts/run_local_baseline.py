#!/usr/bin/env python3
"""
Local Baseline Evaluation for medical-ai-leaderboard (MLX / Apple Silicon)

Runs a local model (default: LFM2-24B-A2B 4-bit) on the 1,060 SSM text-only
questions with a SINGLE-QUESTION harness:

  - same Italian prompt format as the LoRA training data
    (scripts/prepare_lora_data.py) so base-vs-LoRA comparisons are apples to
    apples — never compare these numbers to OpenRouter batch-pipeline results
  - greedy decoding (temperature 0), output is a single letter A-E
  - resumeable: answered ids are skipped on re-run
  - output is compatible with scripts/evaluate_ssm_results.py

Usage:
    .venv/bin/python scripts/run_local_baseline.py --limit 3        # smoke test
    .venv/bin/python scripts/run_local_baseline.py                  # full run
    .venv/bin/python scripts/run_local_baseline.py --model mlx-community/LFM2-24B-A2B-4bit
"""

import argparse
import json
import os
import re
import time
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_QUESTIONS = os.path.join(REPO_ROOT, "data", "ssm_questions_text_only.json")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "results", "local")
DEFAULT_MODEL = "mlx-community/LFM2-24B-A2B-4bit"

PROMPT_TEMPLATE = (
    "Sei un esperto medico che affronta una domanda a scelta multipla "
    "dell'esame di specializzazione medica.\n\n"
    "Domanda:\n{question}\n\n{options}\n\n"
    "Rispondi unicamente con la lettera della risposta corretta."
)

LETTER_RE = re.compile(r"\b([A-E])\b")


def render_prompt(q) -> str:
    options = "\n".join(f"{o['letter']}. {o['text']}" for o in q["options"])
    return PROMPT_TEMPLATE.format(question=q["question"], options=options)


def extract_letter(text: str):
    """Reasoning models emit <think>...</think>; score only the final answer
    segment. If thinking never closed (truncated), there is no answer."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    elif "<think>" in text:
        return None
    matches = LETTER_RE.findall(text.strip().upper())
    return matches[-1] if matches else None


def main():
    parser = argparse.ArgumentParser(description="Single-question local eval (MLX)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--adapter", default=None, help="Optional LoRA adapter path (fine-tuned model)")
    parser.add_argument("--questions", default=DEFAULT_QUESTIONS)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--limit", type=int, help="Only first N questions (smoke test)")
    parser.add_argument("--max-tokens", type=int, default=8,
                        help="Raise (e.g. 512) for reasoning models that emit <think> blocks")
    parser.add_argument("--tag", default=None, help="Output filename tag")
    args = parser.parse_args()

    from mlx_lm import load
    from mlx_lm.generate import stream_generate
    from mlx_lm.sample_utils import make_sampler

    with open(args.questions, encoding="utf-8") as f:
        questions = json.load(f)
    if args.limit:
        questions = questions[: args.limit]

    tag = args.tag or ("lora" if args.adapter else "baseline")
    out_path = os.path.join(args.out_dir, f"{args.model.split('/')[-1]}_{tag}.json")
    os.makedirs(args.out_dir, exist_ok=True)

    # resume support
    answers = {}
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as f:
            prior = json.load(f)
        answers = {a["id"]: a for a in prior.get("answers", [])}
        print(f"resuming: {len(answers)} already answered")

    print(f"loading {args.model}" + (f" + adapter {args.adapter}" if args.adapter else "") + " ...")
    model, tokenizer = load(args.model, adapter_path=args.adapter)
    sampler = make_sampler(temp=0.0)

    pending = [q for q in questions if q["id"] not in answers]
    print(f"to answer: {len(pending)} / {len(questions)}")

    t_start = time.time()
    prompt_tokens_total = 0
    gen_tokens_total = 0
    for i, q in enumerate(pending, 1):
        messages = [{"role": "user", "content": render_prompt(q)}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        letter = None
        raw = ""
        t0 = time.time()
        for chunk in stream_generate(
            model, tokenizer, prompt=prompt,
            max_tokens=args.max_tokens, sampler=sampler,
        ):
            raw += chunk.text
            prompt_tokens_total = chunk.prompt_tokens
            gen_tokens_total += 1
        letter = extract_letter(raw)

        answers[q["id"]] = {
            "id": q["id"],
            "answer": letter,
            "raw": raw,
            "think_chars": (len(raw.split("</think>")[0]) if "<think>" in raw else 0),
            "think_closed": "</think>" in raw,
        }
        if i % 25 == 0 or i == len(pending):
            elapsed = time.time() - t_start
            answered = len(answers)
            eta_min = (elapsed / i) * (len(pending) - i) / 60
            parsed = sum(1 for q2 in pending[:i] if answers[q2["id"]]["answer"])
            print(f"[{i}/{len(pending)}] parsed={parsed}/{i} "
                  f"({elapsed/i:.1f}s/q, ETA {eta_min:.0f} min)")
            result = {
                "model": args.model,
                "adapter": args.adapter,
                "model_name": f"{args.model.split('/')[-1]}" + (" + LoRA" if args.adapter else ""),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "harness": "local-single-question-v1 (greedy, LoRA-style prompt)",
                "max_tokens": args.max_tokens,
                "num_questions": len(questions),
                "num_answered": len(answers),
                "usage": {"prompt_tokens_last": prompt_tokens_total,
                          "gen_tokens_total": gen_tokens_total},
                "answers": list(answers.values()),
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    result = {
        "model": args.model,
        "adapter": args.adapter,
        "model_name": f"{args.model.split('/')[-1]}" + (" + LoRA" if args.adapter else ""),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "harness": "local-single-question-v1 (greedy, LoRA-style prompt)",
        "max_tokens": args.max_tokens,
        "num_questions": len(questions),
        "num_answered": len(answers),
        "usage": {"prompt_tokens_last": prompt_tokens_total,
                  "gen_tokens_total": gen_tokens_total},
        "answers": list(answers.values()),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    answered = sum(1 for a in answers.values() if a["answer"])
    print(f"\nDone: {answered}/{len(questions)} parsed -> {out_path}")
    print(f"Next: .venv/bin/python scripts/evaluate_ssm_results.py {out_path}")


if __name__ == "__main__":
    main()
