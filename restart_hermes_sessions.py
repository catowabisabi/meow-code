import subprocess

SESSIONS = [
    ("agentic-rag-api", "cd /mnt/f/codebase/Agentic-RAG-LLMs-API && opencode"),
    ("ai-job-scraper", "cd /mnt/f/codebase/ai-job-scraper && opencode"),
    ("blackhole-sim", "cd /mnt/f/codebase/blackhole-sim && opencode"),
    ("bmai", "cd /mnt/f/codebase/bmai && opencode"),
    ("cato-claude", "cd /mnt/f/codebase/cato-claude && opencode"),
    ("default", "cd /mnt/f/codebase/default && opencode"),
    ("elementary", "cd /mnt/f/codebase/elementary && opencode"),
    ("flight-tracker", "cd /mnt/f/codebase/flight-tracker && opencode"),
    ("golden_news", "cd /mnt/f/codebase/golden_news && opencode"),
    ("keepalive", "cd /mnt/f/codebase/keepalive && opencode"),
    ("manus-app-researcher-agent", "cd /mnt/f/codebase/manus-app-researcher-agent && opencode"),
    ("manus-chris-porfolio", "cd /mnt/f/codebase/manus-chris-porfolio && opencode"),
    ("manus-intraday-trading-bot", "cd /mnt/f/codebase/manus-intraday-trading-bot && opencode"),
    ("max_projects", "cd /mnt/f/codebase/max_projects && opencode"),
    ("mec-agent", "cd /mnt/f/codebase/mec-agent && opencode"),
    ("power-teams", "cd /mnt/f/codebase/power-teams && opencode"),
    ("sw-api", "cd /mnt/f/codebase/sw-api && opencode"),
    ("tile-flip", "cd /mnt/f/codebase/tile-flip && opencode"),
]

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.returncode

def main():
    print("Restarting all tmux sessions...")
    run("tmux start-server 2>/dev/null")

    for name, cmd in SESSIONS:
        out, rc = run(f"tmux list-session -t {name} 2>&1")
        if rc == 0:
            print(f"[SKIP] {name} - already running")
            continue

        run(f'tmux new-session -d -s {name} -x 120 -y 40 "{cmd}"')
        print(f"[START] {name}")

    print("\n--- Final status ---")
    out, _ = run("tmux list-sessions 2>&1")
    print(out)