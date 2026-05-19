#!/bin/bash
# Restart all Hermes Agent tmux sessions

echo "Starting tmux server..."
tmux start-server 2>/dev/null

sessions=(
  "agentic-rag-api:/mnt/f/codebase/Agentic-RAG-LLMs-API"
  "ai-job-scraper:/mnt/f/codebase/ai-job-scraper"
  "blackhole-sim:/mnt/f/codebase/blackhole-sim"
  "bmai:/mnt/f/codebase/bmai"
  "cato-claude:/mnt/f/codebase/cato-claude"
  "default:/mnt/f/codebase/default"
  "elementary:/mnt/f/codebase/elementary"
  "flight-tracker:/mnt/f/codebase/flight-tracker"
  "golden_news:/mnt/f/codebase/golden_news"
  "keepalive:/mnt/f/codebase/keepalive"
  "manus-app-researcher-agent:/mnt/f/codebase/manus-app-researcher-agent"
  "manus-chris-porfolio:/mnt/f/codebase/manus-chris-porfolio"
  "manus-intraday-trading-bot:/mnt/f/codebase/manus-intraday-trading-bot"
  "max_projects:/mnt/f/codebase/max_projects"
  "mec-agent:/mnt/f/codebase/mec-agent"
  "power-teams:/mnt/f/codebase/power-teams"
  "sw-api:/mnt/f/codebase/sw-api"
  "tile-flip:/mnt/f/codebase/tile-flip"
)

for entry in "${sessions[@]}"; do
  name="${entry%%:*}"
  path="${entry##*:}"

  if tmux has-session -t "$name" 2>/dev/null; then
    echo "[SKIP] $name - already running"
  else
    tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"
    echo "[START] $name"
  fi
done

echo ""
echo "=== All sessions ==="
tmux list-sessions