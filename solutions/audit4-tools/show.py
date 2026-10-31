"""Prints the plan of a request and the better plan found by the insertion analysis (INS_SHOW).

usage: show.py <binary> <seed> <request> [<seed> <request> ...] [ENV=VAL ...]
S0 = records of the solution, D0 = records rebuilt by describe(), BASE = the plan chosen,
VAR / S1 / ALT = the inserted move, the rebuilt state and the plan after it. PLAN_DBG=<request>
also prints every plan option with its outcome (PDBG)."""
import os, subprocess, sys

b = sys.argv[1]
args = [a for a in sys.argv[2:] if "=" not in a]
extra = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
for i in range(0, len(args), 2):
    s, r = int(args[i]), args[i + 1]
    env = dict(os.environ, HUB_ANNEAL="9000000", CLIMB_ITERS="60000", INS="1024", INS_OFF=r, INS_SHOW=r, **extra)
    with open(f"/home/sato/ahc074/tools/in/{s:04d}.txt") as fi:
        err = subprocess.run([b], stdin=fi, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, text=True).stderr
    print(f"=== seed {s} request {r}")
    for line in err.splitlines():
        if line.split(" ")[0] in ("S0", "D0", "BASE", "SHOWHEAD", "VAR", "S1", "ALT", "INS", "PDBG"):
            print(line)
