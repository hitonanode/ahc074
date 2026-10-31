"""Own measurement runner (not an evaluation record). Runs a binary on seeds [lo, hi) through the
tester holding runs/.lock, and writes `seed score T E stat...` lines.
usage: runm.py <binary> <outfile> <lo> <hi> [ENV=VAL ...]   (JOBS env: parallelism, default 12)"""
import os, re, subprocess, sys, time, fcntl, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

binary, outfile = sys.argv[1], Path(sys.argv[2])
lo, hi = int(sys.argv[3]), int(sys.argv[4])
env = dict(os.environ)
for kv in sys.argv[5:]:
    k, v = kv.split("=", 1)
    env[k] = v
root = Path("/home/sato/ahc074")
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)\s*$")
errdir = outfile.with_suffix(".err")
errdir.mkdir(parents=True, exist_ok=True)


def job(s):
    f = f"{s:04d}.txt"
    t0 = time.perf_counter()
    with open(root / "tools/in" / f) as fi:
        p = subprocess.run([str(root / "tools/target/release/tester"), binary], stdin=fi,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    el = time.perf_counter() - t0
    (errdir / f).write_text(p.stderr)
    vals = {}
    for line in p.stderr.splitlines():
        m = LINE.match(line)
        if m:
            vals[m.group(1)] = m.group(2)
    return s, vals, el


lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"cons runm.py {binary} (pid {os.getpid()}, {datetime.datetime.now().isoformat()} から)\n".encode())
with ThreadPoolExecutor(int(env.get("JOBS", "12"))) as ex, open(outfile, "w") as fo:
    for s, vals, el in ex.map(job, range(lo, hi)):
        score = int(vals.get("Score", 0))
        T = int(vals.get("total_moves", 0))
        E = (score - T) // 384 if score else -1
        extra = " ".join(f"{k}={v}" for k, v in vals.items() if k not in ("Score", "total_moves"))
        fo.write(f"{s} {score} {T} {E} {el:.3f} {extra}\n")
        fo.flush()
