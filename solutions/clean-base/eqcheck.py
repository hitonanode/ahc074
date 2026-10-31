"""Output-equivalence check for refactoring (not an evaluation record).

Runs each binary on seeds [lo, hi) through the tester with the annealing and the climb fixed to
the given iteration counts (HUB_ANNEAL / ANNEAL_ITERS and CLIMB_ITERS, so that the outputs do not
depend on the machine), holding runs/.lock, and reports for every binary after the first whether
its stdout (the papers and every move) is identical to the first one's, seed by seed, and the
mean log score ratio against the first one (negative: better) for behavior-changing variants.

usage: eqcheck.py <lo> <hi> <anneal_iters> <climb_iters> <binary> <binary> ...   (JOBS env, default 8)
"""
import fcntl, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root = Path("/home/sato/ahc074")
lo, hi, ai, ci = (int(x) for x in sys.argv[1:5])
bins = sys.argv[5:]
env = dict(os.environ, HUB_ANNEAL=str(ai), ANNEAL_ITERS=str(ai), CLIMB_ITERS=str(ci))


def job(args):
    b, s = args
    with open(root / "tools/in" / f"{s:04d}.txt") as fi:
        p = subprocess.run([str(root / "tools/target/release/tester"), b], stdin=fi,
                           capture_output=True, text=True, env=env)
    m = re.findall(r"^Score = (\d+)", p.stderr, re.M)
    return b, s, p.stdout, int(m[-1]) if m else -1


lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"clean-base eqcheck.py (pid {os.getpid()})\n".encode())
with ThreadPoolExecutor(int(os.environ.get("JOBS", "8"))) as ex:
    res = list(ex.map(job, [(b, s) for s in range(lo, hi) for b in bins]))
out = {(b, s): (o, sc) for b, s, o, sc in res}
ref = bins[0]
print(f"ref {ref}: mean score {sum(out[(ref, s)][1] for s in range(lo, hi)) / (hi - lo):.1f}")
for b in bins[1:]:
    diff = [s for s in range(lo, hi) if out[(b, s)][0] != out[(ref, s)][0]]
    ds = [s for s in range(lo, hi) if out[(b, s)][1] != out[(ref, s)][1]]
    mean = sum(out[(b, s)][1] for s in range(lo, hi)) / (hi - lo)
    print(f"{b}: stdout differs on {len(diff)} / {hi - lo} seeds {diff[:10]}; score differs on {len(ds)}; mean score {mean:.1f}")
    xs = [100 * math.log(out[(b, s)][1] / out[(ref, s)][1]) for s in range(lo, hi) if out[(b, s)][1] > 0 and out[(ref, s)][1] > 0]
    if len(xs) > 1:
        m = sum(xs) / len(xs)
        se = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1) / len(xs))
        print(f"  log ratio vs ref: {m:+.3f} +- {se:.3f}% (W/D/L {sum(x < 0 for x in xs)}/{sum(x == 0 for x in xs)}/{sum(x > 0 for x in xs)}), "
              f"WA {sum(out[(b, s)][1] == 0 for s in range(lo, hi))}")
