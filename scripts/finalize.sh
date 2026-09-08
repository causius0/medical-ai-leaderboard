#!/bin/bash
# Finalization: after qwen-thinking finishes, run liquid, then rebuild leaderboard.
cd /Users/andre/medialb
PGPY=/tmp/pgvenv/bin/python
log() { echo "$(date +%F\ %T) $1" >> /tmp/finalize.log; }
log "finalizer waiting for qwen-thinking..."

# 1. Wait for qwen-thinking to finish
while pgrep -f "run_evaluation.py --models qwen3:8b --thinking" >/dev/null 2>&1; do
  sleep 60
done
log "qwen-thinking done"

# 2. Ingest qwen-thinking result into shuffled relation
$PGPY scripts/db_load.py --shuffled --ingest >> /tmp/finalize.log 2>&1
log "qwen-thinking ingested"

# 3. Run liquid (LFM) on shuffled
log "starting liquid (LFM) on shuffled..."
pkill -f "port 8081" 2>/dev/null; sleep 2
if ! curl -s http://127.0.0.1:8081/v1/models >/dev/null 2>&1; then
  nohup llama-server -m /tmp/LFM2.5-8B-A1B-Q4_K_M.gguf -c 8192 -ngl 99 --host 127.0.0.1 --port 8081 -np 1 > /tmp/lfm_server.log 2>&1 &
  sleep 15
fi
$PGPY scripts/run_evaluation.py --models LFM2.5-8B-A1B --endpoint http://127.0.0.1:8081 > /tmp/shuf_liquid.log 2>&1
log "liquid done"

# 4. Ingest liquid + rebuild leaderboard from shuffled
$PGPY scripts/db_load.py --shuffled --ingest >> /tmp/finalize.log 2>&1
$PGPY scripts/db_load.py --export-shuffled >> /tmp/finalize.log 2>&1
$PGPY scripts/export_responses.py >> /tmp/finalize.log 2>&1
log "leaderboard + question responses rebuilt from shuffled (final)"
echo "FINALIZED" > /tmp/finalize.flag
