"""Cover the official 2000 inputs in separate production-path runs of at most 500 cases."""
import os
from pathlib import Path
import subprocess

here = Path(__file__).resolve().parent
root = here.parents[1]
env = dict(os.environ)
for key in ("REVIEW_CHECK", "REVIEW_FORCE", "REVIEW_INPUT_DIR"):
    env.pop(key, None)
env["JFLAGS_ARMS"] = '''[["clang++", "-std=gnu++23 -O2 -march=native -stdlib=libc++ -ftrivial-auto-var-init=zero -Wall -Wextra -Wuninitialized"]]'''
commands = [("prod_missing170.log", [
    "nice", "-n", "10", "python3", "scripts/pahcer_run.py", "--extend",
    "20261109-025050_final-time-pace", "--seeds", "50-220", "-c",
    "Astra review: complete original Clang production run to 500 inputs; inherited no-record"
])]
for start in (500, 1000, 1500):
    commands.append((f"prod_{start}_{start+500}.log", [
        "nice", "-n", "10", "python3", "solutions/review-astra1/run.py",
        "solutions/final-time-pace", "--seeds", f"{start}-{start+500}", "--no-record",
        "-c", "Astra review: original Clang production path, correctness and time coverage; 500-case batch"
    ]))
for name, command in commands:
    with (here / name).open("w") as out:
        subprocess.run(command, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    print(name, "finished", flush=True)
