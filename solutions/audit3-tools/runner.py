"""Compares solution binaries with the annealing fixed (deterministic designs), without the tester.

usage: runner.py <first seed> <end seed> <name>=<binary>[,ENV=VAL...] ...   (the first is the reference)

Each binary runs on tools/in/<seed>.txt directly (the input holds the requests) with HUB_ANNEAL=9000000
and CLIMB_ITERS=60000 unless set; the score is total_moves + 384 * self_wrong from its stderr (the
solution's own replay; moves are not checked for visibility, use scripts/pahcer_run.py for that).
runs/.lock of the main checkout is held so that timed evaluations of other agents do not share the
CPU. Prints the mean per binary and, against the first, the mean log ratio (%) +- standard error and
W/D/L. STATS=a,b prints the means of those `name = value` stderr lines. JOBS (default 12) parallel.
"""
import datetime, fcntl, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

common = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--path-format=absolute",
                         "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
root = Path(common).parent
lo, hi = int(sys.argv[1]), int(sys.argv[2])
cfgs = []
for a in sys.argv[3:]:
    name, _, rest = a.partition("=")
    parts = rest.split(",")
    env = dict(os.environ)
    env.setdefault("HUB_ANNEAL", "9000000")
    env.setdefault("CLIMB_ITERS", "60000")
    for kv in parts[1:]:
        k, v = kv.split("=", 1)
        env[k] = v
    cfgs.append((name, str(Path(parts[0]).resolve()), env))
stat_names = [s for s in os.environ.get("STATS", "").split(",") if s]


def job(arg):
    ci, s = arg
    name, binary, env = cfgs[ci]
    with open(root / "tools" / "in" / f"{s:04d}.txt") as fi:
        err = subprocess.run([binary], stdin=fi, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, text=True).stderr
    vals = {m.group(1): float(m.group(2)) for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*) = ([-+0-9.eE]+)$", err, re.M)}
    return ci, s, vals.get("total_moves", 0) + 384 * vals.get("self_wrong", 0), vals


lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"audit3 runner.py (pid {os.getpid()}, {datetime.datetime.now().isoformat()})\n".encode())
res, stats = {}, {}
with ThreadPoolExecutor(int(os.environ.get("JOBS", "12"))) as ex:
    for ci, s, sc, vals in ex.map(job, [(ci, s) for s in range(lo, hi) for ci in range(len(cfgs))]):
        res[(ci, s)] = sc
        for k in stat_names:
            stats.setdefault((ci, k), []).append(vals.get(k, float("nan")))
os.close(lock_fd)
seeds = range(lo, hi)
for ci, (name, _, _) in enumerate(cfgs):
    sc = [res[(ci, s)] for s in seeds]
    line = f"{name}: mean {sum(sc) / len(sc):.2f}"
    if ci > 0:
        d = [100 * math.log(res[(ci, s)] / res[(0, s)]) for s in seeds]
        m = sum(d) / len(d)
        se = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1) / len(d)) if len(d) > 1 else 0
        w = sum(res[(ci, s)] < res[(0, s)] for s in seeds)
        l = sum(res[(ci, s)] > res[(0, s)] for s in seeds)
        line += f"  vs {cfgs[0][0]}: {m:+.3f} +- {se:.3f}%  W/D/L {w}/{len(d) - w - l}/{l}"
    for k in stat_names:
        v = stats[(ci, k)]
        line += f"  {k}={sum(v) / len(v):.4f}"
    print(line, flush=True)
