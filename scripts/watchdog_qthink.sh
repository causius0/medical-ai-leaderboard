#!/bin/bash
# Watchdog for the full qwen-thinking run (checkpoint-resume aware).
# - Monitors every 10 min
# - If the process dies or stalls, restarts; the eval script resumes from its checkpoint
# - Exits only when a full (>=1000 answered) result exists
# Logs to /tmp/watchdog.log

cd /Users/andre/medialb
CKPT="results/openrouter/qwen3-8b_checkpoint.json"

log() { echo "$(date +%F\ %T) $1" >> /tmp/watchdog.log; }

launch() {
  pkill -f "run_evaluation.py --models qwen3:8b --thinking" 2>/dev/null
  sleep 3
  nohup python3 scripts/run_evaluation.py --models qwen3:8b --thinking >> /tmp/qthink_stdout.log 2>> /tmp/qthink_stderr.log &
  log "launched pid $! (restart #$RESTART_COUNT, checkpoint=$(test -f $CKPT && echo "$(python3 -c "import json;print(len(json.load(open('$CKPT'))))" 2>/dev/null || echo 0)")"
}

RESTART_COUNT=0
launch
RESTART_COUNT=1
LAST_QSIZE=0
STALL_COUNT=0

while true; do
  sleep 600

  Q=$(grep -oE '\[qwen3:8b\] [0-9]+/1060' /tmp/qthink_stdout.log 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
  [ -z "$Q" ] && Q=0
  PROC_ALIVE=$(pgrep -f "run_evaluation.py --models qwen3:8b --thinking" >/dev/null 2>&1 && echo yes || echo no)
  CKPT_N=$(python3 -c "import json;print(len(json.load(open('$CKPT'))))" 2>/dev/null || echo 0)
  log "check Q=$Q alive=$PROC_ALIVE checkpoint=${CKPT_N} restart=$RESTART_COUNT"

  # Completion check
  if ls results/openrouter/qwen3-8b_*.json >/dev/null 2>&1; then
    LATEST=$(ls -t results/openrouter/qwen3-8b_*.json | head -1)
    ANS=$(python3 -c "import json;print(json.load(open('$LATEST'))['total_questions_answered'])" 2>/dev/null)
    if [ -n "$ANS" ] && [ "$ANS" -ge 1000 ]; then
      log "COMPLETE: $LATEST answered=$ANS"
      rm -f "$CKPT"
      echo "COMPLETE" > /tmp/qthink_complete.flag
      exit 0
    fi
  fi

  # Stall: no forward progress for 3 checks (30 min) AND checkpoint not growing
  CKPT_NOW=$(python3 -c "import json;print(len(json.load(open('$CKPT'))))" 2>/dev/null || echo 0)
  if [ "$Q" -eq "$LAST_QSIZE" ] && [ "$CKPT_NOW" -eq "$CKPT_PREV" ]; then
    STALL_COUNT=$((STALL_COUNT+1))
  else
    STALL_COUNT=0
  fi
  LAST_QSIZE=$Q
  CKPT_PREV=$CKPT_NOW

  if [ "$PROC_ALIVE" = "no" ] || [ "$STALL_COUNT" -ge 3 ]; then
    log "RESTARTING (alive=$PROC_ALIVE stall=$STALL_COUNT Q=$Q ckpt=$CKPT_NOW)"
    RESTART_COUNT=$((RESTART_COUNT+1))
    launch
    STALL_COUNT=0
  fi

  if [ "$RESTART_COUNT" -gt 15 ]; then
    log "FATAL: too many restarts, giving up"
    exit 1
  fi
done
