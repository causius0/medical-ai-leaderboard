#!/bin/bash
# Monitor for the shuffled (bias-free) re-run.
# - Polls every 10 min, logs progress + checkpoint
# - When the direct batch finishes, launches qwen thinking on shuffled
# - Ingest+export when results appear
# Logs to /tmp/shuf_monitor.log

cd /Users/andre/medialb
PGPY=/tmp/pgvenv/bin/python
log() { echo "$(date +%F\ %T) $1" >> /tmp/shuf_monitor.log; }
log "shuffled monitor started"

DIRECT_RUNNING=0
THINK_STARTED=0

while true; do
  sleep 600

  # Progress of current run
  PROG=$(python3 -c "
data=open('/tmp/shuf_direct.log','rb').read().decode('utf-8',errors='replace')
lines=[l for l in data.split('\r') if l.strip()]
print(lines[-1].strip() if lines else 'no progress')
" 2>/dev/null)
  log "direct: $PROG"

  # Detect if direct batch still running
  if pgrep -f "run_evaluation.py --models gemma3:12b" >/dev/null 2>&1; then
    DIRECT_RUNNING=1
  else
    # Direct batch finished
    if [ "$DIRECT_RUNNING" = "1" ] && [ "$THINK_STARTED" = "0" ]; then
      log "DIRECT BATCH DONE — launching qwen thinking on shuffled"
      nohup python3 scripts/run_evaluation.py --models qwen3:8b --thinking > /tmp/shuf_think.log 2>&1 &
      log "qwen-thinking launched (shuffled)"
      THINK_STARTED=1
      DIRECT_RUNNING=0
    fi
  fi

  # Ingest any new result files into Postgres
  NEW=$(ls results/openrouter/*.json 2>/dev/null | wc -l | tr -d ' ')
  log "result files: $NEW"

  # Check if ALL models done (gemma, qwen-direct, mistral, llama, qwen-thinking)
  TOTAL_DONE=$(python3 -c "
import glob
files=glob.glob('results/openrouter/*.json')
done=0
for f in files:
    try:
        import json
        r=json.load(open(f))
        if r['total_questions_answered']>=1000: done+=1
    except: pass
print(done)
" 2>/dev/null)
  log "full results completed: $TOTAL_DONE"

  if [ "$TOTAL_DONE" -ge 5 ]; then
    log "ALL 5 MODELS DONE — ingesting + exporting"
    $PGPY scripts/db_load.py --ingest >> /tmp/shuf_monitor.log 2>&1
    $PGPY scripts/db_load.py --export >> /tmp/shuf_monitor.log 2>&1
    log "COMPLETE — leaderboard rebuilt from shuffled results"
    echo "SHUFFLED_COMPLETE" > /tmp/shuf_complete.flag
    exit 0
  fi
done
