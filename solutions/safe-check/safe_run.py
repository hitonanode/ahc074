#!/usr/bin/env python3
"""Runs a solver binary with the official tester on many inputs in parallel (outside the records of
scripts/pahcer_run.py: for extra inputs made with tools/target/release/gen, e.g. seeds 500-2499).

usage: safe_run.py BINARY INDIR OUTDIR [-j 12] [--first SEED_OF_FILE_0] [--files a-b] [--list i,j]
                   [--env K=V ...]
Writes OUTDIR/out/<seed>.txt, OUTDIR/err/<seed>.txt and OUTDIR/result.json
(seed, file, score, wall time, key = value lines of stderr). Keep OUTDIR outside runs/ and tools/.
"""
import argparse, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

TESTER = "/home/sato/ahc074/tools/target/release/tester"

ap = argparse.ArgumentParser()
ap.add_argument("binary")
ap.add_argument("indir")
ap.add_argument("outdir")
ap.add_argument("-j", type=int, default=12)
ap.add_argument("--first", type=int, default=0, help="seed of file 0000.txt")
ap.add_argument("--files", default=None, help="range a-b of file indices (b excluded)")
ap.add_argument("--list", default=None, help="comma separated file indices")
ap.add_argument("--env", nargs="*", default=[])
a = ap.parse_args()

files = sorted(f for f in os.listdir(a.indir) if f.endswith(".txt"))
idx = [int(f[:4]) for f in files]
if a.files:
    lo, hi = map(int, a.files.split("-"))
    idx = [i for i in idx if lo <= i < hi]
if a.list:
    want = set(int(x) for x in a.list.split(","))
    idx = [i for i in idx if i in want]
os.makedirs(f"{a.outdir}/out", exist_ok=True)
os.makedirs(f"{a.outdir}/err", exist_ok=True)
env = dict(os.environ)
for kv in a.env:
    k, v = kv.split("=", 1)
    env[k] = v


def run(i):
    seed = a.first + i
    inp = f"{a.indir}/{i:04d}.txt"
    outp = f"{a.outdir}/out/{seed}.txt"
    errp = f"{a.outdir}/err/{seed}.txt"
    with open(inp) as fi, open(outp, "w") as fo, open(errp, "w") as fe:
        t0 = time.perf_counter()
        p = subprocess.run([TESTER, a.binary], stdin=fi, stdout=fo, stderr=fe, env=env)
        t = time.perf_counter() - t0
    txt = open(errp).read()
    kv = {}
    score = None
    for line in txt.splitlines():
        m = re.match(r"^(\w+) = ([-\d.eE+]+)$", line)
        if m:
            kv[m.group(1)] = float(m.group(2))
    m = re.findall(r"^Score = (\d+)$", txt, re.M)
    score = int(m[-1]) if m else None
    tail = txt.strip().splitlines()[-3:]
    return {"seed": seed, "file": i, "score": score, "time": t, "rc": p.returncode, "kv": kv, "tail": tail}


t0 = time.time()
with ThreadPoolExecutor(a.j) as ex:
    res = list(ex.map(run, idx))
json.dump(res, open(f"{a.outdir}/result.json", "w"))
bad = [r for r in res if not r["score"]]
sc = [r["score"] for r in res if r["score"]]
print(f"cases {len(res)}  zero/missing {len(bad)}  mean {sum(sc)/max(1,len(sc)):.1f}  "
      f"max time {max(r['time'] for r in res):.3f}  wall {time.time()-t0:.1f}s")
for r in bad[:20]:
    print("BAD", r["seed"], r["rc"], r["tail"])
