import subprocess, sys
# Run grep inside WSL
result = subprocess.run(
    ["wsl", "-d", "Ubuntu", "-u", "enomars", "--",
     "grep", "-n", "WHATSAPP\\|whatsapp\\|_PLATFORM_CONNECTED",
     "/home/enomars/.hermes/hermes-agent/gateway/config.py"],
    capture_output=True, text=True, timeout=15
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:200] if result.stderr else "")
print("RC:", result.returncode)
