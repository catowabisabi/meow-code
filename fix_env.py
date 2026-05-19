import os

home = os.path.expanduser("~")
bashrc = os.path.join(home, ".bashrc")

# Remove bad lines and duplicates
good_lines = []
seen = set()
for line in open(bashrc):
    if "ANDROID_HOME" in line or "JAVA_HOME" in line or "flutter/bin" in line:
        if line.strip() and line not in seen:
            seen.add(line)
            good_lines.append(line)

# Clean file
with open(bashrc, "w") as f:
    f.writelines(good_lines)

# Append clean lines
with open(bashrc, "a") as f:
    f.write("\n# Android SDK\n")
    f.write("export ANDROID_HOME=$HOME/android-sdk\n")
    f.write("export JAVA_HOME=$HOME/jdk-17\n")
    f.write("# Flutter\n")
    f.write("export PATH=$HOME/flutter/bin:$PATH\n")

print("Done. Last 10 lines:")
with open(bashrc) as f:
    lines = f.readlines()
    for l in lines[-10:]:
        print(l, end="")