#!/bin/bash
tmux start-server 2>/dev/null

name=agentic-rag-api
path=/mnt/f/codebase/Agentic-RAG-LLMs-API
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=ai-job-scraper
path=/mnt/f/codebase/ai-job-scraper
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=blackhole-sim
path=/mnt/f/codebase/blackhole-sim
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=bmai
path=/mnt/f/codebase/bmai
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=default
path=/mnt/f/codebase/default
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=elementary
path=/mnt/f/codebase/elementary
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=flight-tracker
path=/mnt/f/codebase/flight-tracker
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=golden-news
path=/mnt/f/codebase/golden_news
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=manus-app-researcher-agent
path=/mnt/f/codebase/manus-app-researcher-agent
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=manus-chris-portfolio
path=/mnt/f/codebase/manus-chris-porfolio
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=manus-intraday-trading-bot
path=/mnt/f/codebase/manus-intraday-trading-bot
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=max-projects
path=/mnt/f/codebase/max_projects
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=mec-agent
path=/mnt/f/codebase/mec-agent
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=power-teams
path=/mnt/f/codebase/power-teams
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=sw-api
path=/mnt/f/codebase/sw-api
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

name=tile-flip
path=/mnt/f/codebase/tile-flip
tmux new-session -d -s "$name" -x 120 -y 40 "cd $path && opencode"

tmux list-sessions