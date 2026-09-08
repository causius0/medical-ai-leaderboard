#!/bin/bash
# Completion monitor for the full qwen-thinking run.
# Polls every 15 min; when a full (>=1000 answered) qwen3 thinking result appears,
# it ingests to Postgres, exports, and reports completion.
# Logs to /tmp/qthink_monitor.log

cd /Users/andre/medialb
PGPY=/tmp/pgvenv/bin/python
log() { echo "$(date +%F\ %T) $1" >> /tmp/qthink_monitor.log; }
log "monitor started"

while true; do
  sleep 900  # 15 min

  # Show current progress line
  PROG=$(python3 -c "
data=open('/tmp/qthink_stdout.log','rb').read().decode('utf-8',errors='replace')
lines=data.split('\r')
print([l for l in lines if l.strip()][-1].strip())
" 2>/dev/null)
  CKPT=$(python3 -c "import json;print(len(json.load(open('results/openrouter/qwen3-8b_checkpoint.json'))))" 2>/dev/null || echo 0)
  log "progress: $PROG | checkpoint=$CKPT"

  # Completion: a result file with >=1000 answered
  LATEST=""
  ANS=0
  if ls results/openrouter/qwen3-8b_*.json >/dev/null 2>&1; then
    # only a thinking result (has 'thinking' in metadata via question count ~1060)
    for f in results/openrouter/qwen3-8b_*.json; do
      A=$(python3 -c "import json;print(json.load(open('$f'))['total_questions_answered'])" 2>/dev/null)
      if [ -n "$A" ] && [ "$A" -ge 1000 ]; then
        ANS=$A; LATEST=$f; break
      fi
    done
  fi

  if [ "$ANS" -ge 1000 ]; then
    log "COMPLETE: $LATEST answered=$ANS — ingesting to Postgres"
    # Ingest + export
    $PGPY scripts/db_load.py --ingest >> /tmp/qthink_monitor.log 2>&1
    $PGPY scripts/db_load.py --export >> /tmp/qthink_monitor.log 2>&1
    log "ingested + exported. Leaderboard updated."
    echo "COMPLETE" > /tmp/qthink_complete.flag
    # Update the site (commit data + build)
    git add frontend/public/leaderboard_data.json scripts/db_load.py scripts/run_evaluation.py 2>/dev/null
    log "ready to commit. Site will be updated via PR."
    exit 0
  fi

  # Safety: if eval is dead and watchdog gone, report
  if ! pgrep -f "run_evaluation.py --models qwen3:8b --thinking" >/dev/null && ! pgrep -fl watchdog_qthink.sh >/dev/null; then
    log "ERROR: eval AND watchdog both dead, no completion"
  fi
done
