#!/usr/bin/env python3
"""Start the real game as a player would (a program, not imported), answer the new-game
questions, then close its input: it must greet, start a game, autosave and exit cleanly,
without a traceback, even when its output cannot show Unicode.

    python3 tools/smoke.py python3 cargo.py      # the script
    python3 tools/smoke.py dist/cargo.exe        # a built executable
"""
import os, subprocess, sys, tempfile

command = sys.argv[1:] or [sys.executable, "cargo.py"]
problems = []
for encoding in ("utf-8", "cp1252"):
    home = tempfile.mkdtemp(prefix="cargo-smoke-")
    env = dict(os.environ, CARGO_SAGA_HOME=home, PYTHONIOENCODING=encoding)
    try:
        run = subprocess.run(command, input="1\n2\nSmoke\n".encode(), env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    except subprocess.TimeoutExpired:
        problems.append("%s: did not exit when its input ended" % encoding)
        continue
    out = run.stdout.decode(encoding, "replace")
    saved = any(name.endswith(".json") for _, _, files in os.walk(home) for name in files)
    if run.returncode != 0:
        problems.append("%s: exit code %d" % (encoding, run.returncode))
    if "Traceback" in out:
        problems.append("%s: traceback\n%s" % (encoding, out[out.index("Traceback"):][:800]))
    if "Space Trading Saga" not in out:
        problems.append("%s: no title screen" % encoding)
    if not saved:
        problems.append("%s: no autosave written" % encoding)
for problem in problems:
    print("FAIL", problem)
print("smoke test:", "ok" if not problems else "%d problems" % len(problems))
sys.exit(1 if problems else 0)
