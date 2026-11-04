#!/usr/bin/env python3
"""解法を手元のテストケースで評価し、評価ごとの記録を runs/<run-id>/ に残す（pahcer のラッパー）。

使い方:
    scripts/pahcer_run.py solutions/<name> -c "<comment>"          # 全 2000 ケース (seed 0〜1999)
    scripts/pahcer_run.py solutions/<name> -c "<comment>" --seeds 0-50
                                                                   # seed の範囲を指定 (END は含まない)
    scripts/pahcer_run.py --compare solutions/<A> solutions/<B> ... -c "<comment>"
                                                                   # 複数の解法を seed ごとに続けて実行して比べる
    scripts/pahcer_run.py --extend <run-id> [<run-id> ...] [-c "<comment>"]
                                                                   # 既存の run に未評価の seed を加える
    scripts/pahcer_run.py --status                                 # 評価中・待機中の評価と、評価の外の CPU 負荷を表示
    （そのほか --no-record）

- 解法のソース（と solutions/<name>/README.md）を runs/<run-id>/src/ にコピーし、そのコピーをコンパイルして評価する。
- 1 ケースごとに公式テスター (tools/target/release/tester) が解法を起動して対話する。解法の stdout を
  runs/<run-id>/out/<seed>.txt に、解法の stderr とテスターの判定（エラー文と "Score = ..."）を
  err/<seed>.txt に保存する。result.json にスコアと実行時間、meta.json にコメントや commit が入る。
- --compare は、seed ごとに全部の解法を続けて実行し（順番は seed ごとにずらす）、その単位を並列に
  回す。評価中にマシンの速さが変わっても全部の解法に同じようにかかるので、別々に評価した run を
  比べるより差を正確に読める。各解法はふつうの run として runs/ と pahcer/ に記録され、最後に
  最初の解法に対する差（ケースごとの log スコア比の平均と標準誤差）を表示する。
- --extend は、既存の run（--seeds で一部だけ評価した run や、既定が 2000 ケースになる前の 500 ケースの
  run）に、未評価の seed を同じバイナリで評価して加える。複数の run は --compare と同じく seed ごとに
  続けて実行する。run-id はそのままで、result.json に追加したケースが入り、meta.json の extensions に
  追加の記録が残る。
- 同時に走る評価は 1 つだけ（runs/.lock）。他の評価が実行中なら、終わるまで待ってから始める
  （CPU を取り合うと探索量が減り、スコアを比較できなくなるため）。待っている間と評価中は
  runs/.queue/<pid>.json に自分を登録し、--status はそれ（と古い版が書いた runs/.lock の中身）を読む。
- 評価中は、評価の外のプロセスが使った CPU を LOAD_INTERVAL_SEC ごとに測り、平均と最大を meta.json の
  outside_load（--extend では extensions の各記録）に残して、要約の最後に出す。目安を超えたら警告する。
- 評価が終わるたびに、ケースごとの指標 (runs/<run-id>/metrics.json) を計算し、ダッシュボード
  (runs/report.html) を作り直す。どちらもロックを持ったまま行う（次の評価と CPU を取り合わないため）。
- pahcer の設定は、ルートの pahcer_config.toml をテンプレートにして評価ごとに生成する。
- runs/ と pahcer/ は常に main checkout のものを使う（worktree から実行しても同じ）。
"""

import argparse
import atexit
import concurrent.futures
import contextlib
import datetime
import fcntl
import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402

# CLOCK_SCALE: solutions that multiply their clock readings by it (see CLAUDE.md, 時間の扱い) search
# here as much as on the judge, which is about 1.1 times slower than this 24-parallel evaluation
# (trial_log.md, clock-probe). The judge does not define it (the solutions default to 1.0).
# LOCAL_BENCH: defined only here, never on the judge. A solution that switches to lighter work when
# it runs short of time (such as a light plan for the remaining requests) turns that switch off
# under it and always does the normal work, so that the load of the machine during an evaluation
# does not change its results (AGENTS.md, 時計の倍率). Both flags are recorded in meta.json with
# the rest of the compile command.
COMPILE_CMD = ["g++", "-std=c++23", "-O2", "-DCLOCK_SCALE=1.1", "-DLOCAL_BENCH"]
CPP_SUFFIXES = {".cpp", ".cc", ".cxx"}
SOURCE_SUFFIXES = CPP_SUFFIXES | {".hpp", ".hh", ".hxx", ".h", ".ipp", ".inc"}
# The description that every solutions/<name>/ must have; saved with the sources.
DESCRIPTION_FILE = "README.md"
# The time limit of the problem. Cases above it are counted in the summary (the tester has no limit).
TIME_LIMIT_SEC = 2.0
SCORE_LINE = re.compile(r"(?m)^\s*Score\s*=\s*(\d+)\s*$")
# A case that takes longer than this is stopped and counted as WA (--compare only).
COMPARE_CASE_TIMEOUT = 60.0
# The summary lists the cases over the time limit, slowest first, up to this many.
SLOW_CASES_SHOWN = 10
# Thresholds for the judge-time estimate `end_sec = ...` that solutions print to stderr.
END_SEC_LIMITS = (1.8, 1.9, 2.0)

# runs/.queue/<pid>.json: an evaluation that waits for runs/.lock or holds it (QueueEntry).
QUEUE_DIR = ".queue"
# The text of runs/.lock, as acquire_lock writes it (also the versions without the queue entries).
LOCK_LINE = re.compile(r"^(?P<holder>.+) \(pid (?P<pid>\d+), (?P<since>\S+) から\)$")
LOCK_HOLDER = re.compile(r"^(?P<first>\S+)(?: ほか \d+ 個(?P<kind>の比較|への seed の追加))?$")
# How often LoadMonitor samples the CPU used outside the evaluation while its cases run.
LOAD_INTERVAL_SEC = 2.0
# Above these, the summary warns that the outside load may have changed the results (see
# LoadMonitor; measured as the mean over the cases and the maximum over the sampling intervals).
# Calibration (2026-11-04, solutions/eject-single-window, seeds 0-119, i.e. 5 rounds of 24 cases):
# nothing else running gave mean 0.12 / max 0.31 cores, and 2 of 120 cases with end_sec > 1.8;
# one busy-loop process alongside gave 1.04 / 1.22 and 16 cases; four gave 3.05 / 3.66 and 43.
# A short-lived compile of a queued evaluation adds about 1 core to a single interval.
LOAD_WARN_MEAN_CORES = 0.5
LOAD_WARN_MAX_CORES = 3.0
# Shorter measurements are not compared with the thresholds: /proc/stat counts in ticks of 10 ms
# per CPU, so over 0.1 s its rounding alone can amount to a couple of cores.
LOAD_MIN_SEC = 5.0
CLK_TCK = os.sysconf("SC_CLK_TCK")


class Interrupted(Exception):
    pass


def _raise_interrupted(signum, frame):
    raise Interrupted()


def log(msg: str) -> None:
    print(f"[pahcer_run] {msg}", flush=True)


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def save_meta(run_dir: Path, meta: dict) -> None:
    replay.write_json_atomic(run_dir / "meta.json", meta, indent=2)


# ---------------------------------------------------------------- preparing a run


def resolve_solution(arg: str) -> tuple[Path, Path, str, bool]:
    """Returns (source root, entry .cpp, solution name, whether the whole directory is the solution)."""
    path = Path(arg).resolve()
    if path.is_dir():
        entry = path / "main.cpp"
    elif path.is_file() and path.suffix in CPP_SUFFIXES:
        entry = path
    else:
        sys.exit(f"[pahcer_run] 解法のディレクトリか .cpp ファイルを指定してください: {arg}")
    if not entry.is_file():
        sys.exit(f"[pahcer_run] {entry} がありません")
    at_checkout_root = (entry.parent / ".git").exists()
    if entry.name == "main.cpp" and not at_checkout_root:
        # solutions/<name>/main.cpp: the whole directory (with its headers) is the solution.
        return entry.parent, entry, entry.parent.name, True
    # A single file such as a root main.cpp: only it and the headers next to it are used.
    return entry.parent, entry, "main" if at_checkout_root and entry.stem == "main" else entry.stem, False


def git_info(src_root: Path, paths: list[Path]) -> dict | None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(src_root), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    try:
        status = git("status", "--porcelain", "--", *map(str, paths))
        return {
            "toplevel": git("rev-parse", "--show-toplevel"),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": git("rev-parse", "HEAD"),
            # True if the evaluated sources differ from the commit (modified or untracked).
            "dirty": bool(status),
        }
    except subprocess.CalledProcessError:
        return None


def create_run_dir(runs_dir: Path, name: str) -> tuple[str, Path]:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    for i in range(1, 100):
        run_id = f"{stamp}_{name}" if i == 1 else f"{stamp}_{name}-{i}"
        try:
            (runs_dir / run_id).mkdir()
            return run_id, runs_dir / run_id
        except FileExistsError:
            continue
    sys.exit("[pahcer_run] run ディレクトリを作成できません")


def snapshot_sources(src_root: Path, entry: Path, dest: Path, whole_dir: bool) -> Path:
    """Copies the sources to dest and returns the copied entry file.

    For a directory, every source file under it and its description (README.md) are copied.
    For a single file, only that file and the headers next to it are copied.
    """
    if whole_dir and not (src_root / DESCRIPTION_FILE).is_file():
        print(f"[pahcer_run] 警告: {src_root / DESCRIPTION_FILE} がありません（解法の説明を書いてください）",
              file=sys.stderr)
    files = src_root.rglob("*") if whole_dir else src_root.iterdir()
    for f in files:
        is_description = whole_dir and f == src_root / DESCRIPTION_FILE
        if not f.is_file() or (f.suffix not in SOURCE_SUFFIXES and not is_description):
            continue
        if not whole_dir and f.suffix in CPP_SUFFIXES and f != entry:
            continue
        target = dest / f.relative_to(src_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
    return dest / entry.relative_to(src_root)


def compiler_version(compiler: str) -> str | None:
    """First line of `<compiler> --version`, recorded so that a later rebuild can be checked."""
    try:
        out = subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.splitlines()[0] if out else None


def compile_solution(compile_cmd: list[str], run_dir: Path, src_root: Path) -> bool:
    """Runs the compile command and saves its output in the run directory."""
    compiled = subprocess.run(compile_cmd, capture_output=True, text=True)
    output = compiled.stdout + compiled.stderr
    (run_dir / "compile.log").write_text(output)
    if output:
        # Point diagnostics at the original files, which are the ones to edit.
        shown = output.replace(str(run_dir / "src"), str(src_root))
        print("\n".join(shown.splitlines()[:50]), file=sys.stderr)
    return compiled.returncode == 0


def prepare_run(solution: str, runs_dir: Path, comment: str, seeds: tuple[int, int], record: bool,
                out_dir: Path) -> dict:
    """Creates the run directory of one solution with its sources and meta.json (not compiled yet)."""
    src_root, entry, name, whole_dir = resolve_solution(solution)
    run_id, run_dir = create_run_dir(runs_dir, name)
    for sub in ("src", "out", "err"):
        (run_dir / sub).mkdir()
    # Snapshot first, so later edits to the solution never mix into this run.
    src_entry = snapshot_sources(src_root, entry, run_dir / "src", whole_dir)
    binary = run_dir / "a.out"
    compile_cmd = COMPILE_CMD + ["-o", str(binary), str(src_entry)]
    meta = {
        "run_id": run_id,
        "comment": comment,
        "status": "compiling",
        "created_at": now_iso(),
        "source": {
            "path": str(entry if not whole_dir else src_root),
            "git": git_info(src_root, [src_root] if whole_dir else [entry]),
        },
        "compile_command": compile_cmd,
        "compiler": compiler_version(compile_cmd[0]),
        "seeds": list(seeds),
        "record": record,
        "out_dir": str(out_dir),
    }
    save_meta(run_dir, meta)
    return {"run_id": run_id, "run_dir": run_dir, "binary": binary, "meta": meta,
            "src_root": src_root, "compile_cmd": compile_cmd}


def ensure_tester(root: Path) -> Path:
    """Builds the official tester if it is missing or older than its sources."""
    tools = root / "tools"
    tester = tools / "target" / "release" / "tester"
    sources = list((tools / "src").rglob("*.rs")) + [tools / "Cargo.toml", tools / "Cargo.lock"]
    newest = max(p.stat().st_mtime for p in sources if p.exists())
    if not tester.exists() or tester.stat().st_mtime < newest:
        log("テスターをビルドしています")
        subprocess.run(["cargo", "build", "--release", "--bin", "tester"], cwd=tools, check=True,
                       stdout=subprocess.DEVNULL)
    return tester


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        # A JSON string (without \u escapes for non-ASCII) is a valid TOML basic string.
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    raise TypeError(f"unsupported TOML value: {v!r}")


def write_config(path: Path, template: dict, *, seeds: tuple[int, int], out_dir: Path,
                 compile_cmd: list[str], binary: Path, tester: Path, in_dir: Path, run_dir: Path) -> None:
    sections = [
        ("[general]", template["general"]),
        ("[problem]", template["problem"]),
        ("[test]", {
            "start_seed": seeds[0],
            "end_seed": seeds[1],
            "threads": template["test"].get("threads", 0),
            "out_dir": str(out_dir),
        }),
        # Recorded for reproducibility only: this script compiles beforehand and passes --no-compile.
        ("[[test.compile_steps]]", {"program": compile_cmd[0], "args": compile_cmd[1:]}),
        # The tester runs the solution; its stderr gets the solution's stderr and then the verdict.
        ("[[test.test_steps]]", {
            "program": str(tester),
            "args": [str(binary)],
            "stdin": f"{in_dir}/{{SEED04}}.txt",
            "stdout": f"{run_dir}/out/{{SEED04}}.txt",
            "stderr": f"{run_dir}/err/{{SEED04}}.txt",
            "measure_time": True,
        }),
    ]
    lines = ["# Generated by scripts/pahcer_run.py"]
    for header, table in sections:
        lines += ["", header] + [f"{k} = {toml_value(v)}" for k, v in table.items()]
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- processes, queue and outside load
#
# Read from /proc (Linux). The CPU times there are in clock ticks (CLK_TCK per second).


def read_stat(pid: int | str) -> tuple[int, int, int, int] | None:
    """(ppid, own CPU, CPU of its reaped children, start time) of a process from /proc/<pid>/stat,
    or None if it is gone. The times are in ticks; the start time counts from the boot.

    The own CPU (utime + stime) covers all the threads. When a child exits and is waited for, its
    CPU, with that of its own reaped children, moves into the parent's cutime + cstime. So the sum
    of both over the live processes of a tree also counts the processes of the tree that finished.
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as f:
            data = f.read()
        # The command name in parentheses may contain spaces; the fields after it start at "state".
        rest = data[data.rindex(b")") + 2:].split()
        return int(rest[1]), int(rest[11]) + int(rest[12]), int(rest[13]) + int(rest[14]), int(rest[19])
    except (OSError, ValueError, IndexError):  # gone, or exiting while read
        return None


def read_procs() -> dict[int, tuple[int, int, int, int]]:
    """read_stat of every process (about 2 ms for 250 processes)."""
    procs = {}
    for name in os.listdir("/proc"):
        if name.isdigit() and (stat := read_stat(name)) is not None:
            procs[int(name)] = stat
    return procs


def descendants(procs: dict[int, tuple], roots) -> set[int]:
    """The roots that are alive and all their descendants."""
    children: dict[int, list[int]] = {}
    for pid, stat in procs.items():
        children.setdefault(stat[0], []).append(pid)
    found: set[int] = set()
    stack = [pid for pid in roots if pid in procs]
    while stack:
        pid = stack.pop()
        if pid not in found:
            found.add(pid)
            stack.extend(children.get(pid, ()))
    return found


def tree_ticks(procs: dict[int, tuple], tree: set[int]) -> int:
    """CPU used so far by a process tree, including its finished processes (see read_stat)."""
    return sum(procs[pid][1] + procs[pid][2] for pid in tree)


def busy_ticks() -> int:
    """CPU used by the whole machine since the boot (/proc/stat: all but idle and iowait)."""
    with open("/proc/stat") as f:
        user, nice, system, _idle, _iowait, irq, softirq, steal = map(int, f.readline().split()[1:9])
    return user + nice + system + irq + softirq + steal


def boot_time() -> float:
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("btime "):
                return float(line.split()[1])
    return 0.0


def cmdline(pid: int) -> list[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().decode(errors="replace").split("\0")[:-1]
    except OSError:
        return []


class LoadMonitor:
    """Measures the CPU used outside this evaluation while its cases run, in cores.

    Every LOAD_INTERVAL_SEC, a thread reads the CPU used by the whole machine (/proc/stat) and by
    this script's process tree (pahcer, the testers and the solutions; tree_ticks). The outside load
    of an interval is the increase of the first minus that of the second, divided by the interval:
    any other process (an agent's own tester runs or simulations, a compile, the dashboard) counts,
    including the processes that start and finish between two samples. A sample reads /proc/*/stat
    once (a few ms), so the measurement itself takes about 0.1% of a core.
    """

    def __init__(self, interval: float = LOAD_INTERVAL_SEC):
        self.interval = interval
        self.samples: list[float] = []  # cores, one per full interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _read(self) -> tuple[float, int, int]:
        procs = read_procs()
        busy = busy_ticks()
        return time.monotonic(), busy, tree_ticks(procs, descendants(procs, [os.getpid()]))

    def _sample(self) -> None:
        now = self._read()
        (t0, busy0, own0), (t1, busy1, own1) = self._last, now
        # A short last interval would be dominated by the rounding to ticks; it still enters the mean.
        if t1 - t0 >= self.interval / 2:
            self.samples.append(((busy1 - busy0) - (own1 - own0)) / CLK_TCK / (t1 - t0))
        self._last = now

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._sample()

    def start(self) -> "LoadMonitor":
        self._first = self._last = self._read()
        self._thread.start()
        return self

    def stop(self) -> dict:
        """Stops the sampling and returns the record for meta.json."""
        self._stop.set()
        self._thread.join()
        self._sample()
        (t0, busy0, own0), (t1, busy1, own1) = self._first, self._last
        span = t1 - t0
        mean = ((busy1 - busy0) - (own1 - own0)) / CLK_TCK / span if span > 0 else 0.0
        return {
            "mean_cores": round(mean, 3),
            "max_cores": round(max(self.samples, default=mean), 3),
            "interval_sec": self.interval,
            "seconds": round(span, 1),
        }


def load_is_heavy(load: dict | None) -> bool:
    return (bool(load) and load["seconds"] >= LOAD_MIN_SEC
            and (load["mean_cores"] >= LOAD_WARN_MEAN_CORES or load["max_cores"] >= LOAD_WARN_MAX_CORES))


def print_load(load: dict | None) -> None:
    """The last lines of a summary: the outside load and, above the thresholds, a warning."""
    if not load:
        return
    print(f"  評価の外の負荷: 平均 {max(0.0, load['mean_cores']):.2f} コア、最大 {max(0.0, load['max_cores']):.2f} コア"
          f" ({load['interval_sec']:g} 秒ごとに {load['seconds']:.1f} 秒間測定"
          f"{'。短いので目安とは比べない' if load['seconds'] < LOAD_MIN_SEC else ''})")
    if load_is_heavy(load):
        print(f"  警告: 評価の外の負荷が目安 (平均 {LOAD_WARN_MEAN_CORES:g} コアか最大 {LOAD_WARN_MAX_CORES:g} コア) を"
              "超えました。時間で打ち切る解法は探索量が減っています。差の小さい比較の判断には使わず、比べ直してください")


class QueueEntry:
    """runs/.queue/<pid>.json, by which `--status` sees an evaluation waiting for runs/.lock or holding it.

    Written before waiting for the lock and removed when the lock is released (also on an
    interruption, and at exit as a fallback). A file left by a killed process is ignored by
    `--status` (its pid is gone or belongs to a process with another start time), and removed by
    the next evaluation that registers.
    """

    def __init__(self, runs_dir: Path, kind: str, run_ids: list[str], solutions: list[str], comment: str,
                 seeds: tuple[int, int], cases: int | None):
        queue_dir = runs_dir / QUEUE_DIR
        queue_dir.mkdir(exist_ok=True)
        for path in queue_dir.glob("[0-9]*.json"):
            if live_queue_entry(path) is None:
                path.unlink(missing_ok=True)
        self.path = queue_dir / f"{os.getpid()}.json"
        stat = read_stat(os.getpid())
        self.data = {
            "pid": os.getpid(), "proc_start": stat[3] if stat else None, "kind": kind, "run_ids": run_ids,
            "solutions": solutions, "comment": comment, "seeds": list(seeds), "cases": cases,
            "state": "waiting", "queued_at": now_iso(), "started_at": None, "started_epoch": None,
            "phase": None,
        }
        self.removed = False
        self._save()
        atexit.register(self.remove)

    def _save(self) -> None:
        if not self.removed:
            replay.write_json_atomic(self.path, self.data, indent=1)

    def update(self, **fields) -> None:
        self.data.update(fields)
        self._save()

    def started(self, started_at: str, cases: int | None = None) -> None:
        """Called right after the lock is acquired."""
        self.update(state="running", started_at=started_at, started_epoch=time.time(), phase="cases",
                    **({} if cases is None else {"cases": cases}))

    def remove(self) -> None:
        self.removed = True
        self.path.unlink(missing_ok=True)


def live_queue_entry(path: Path) -> dict | None:
    """The contents of a queue entry, or None if its process is gone."""
    try:
        data = json.loads(path.read_text())
        stat = read_stat(data["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return data if stat is not None and stat[3] == data.get("proc_start") else None


# ---------------------------------------------------------------- --status


def lock_owners(lock_path: Path) -> tuple[list[int], list[int]] | None:
    """(pids holding the flock of runs/.lock, pids blocked waiting for it) from /proc/locks.

    Reading /proc/locks does not touch the lock, so it never delays an evaluation. A holder's pid is
    the process that called flock (pahcer_run.py; pahcer inherits the lock but is not listed).
    None if /proc/locks cannot be read.
    """
    try:
        st = lock_path.stat()
        lines = Path("/proc/locks").read_text().splitlines()
    except OSError:
        return None
    key = f"{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}"
    holders, waiters = [], []
    for line in lines:
        # "3: FLOCK  ADVISORY  WRITE 123 08:30:464184 0 EOF"; a blocked waiter has "->" after "3:".
        parts = line.split()
        blocked = len(parts) > 1 and parts[1] == "->"
        if blocked:
            del parts[1]
        if len(parts) >= 6 and parts[1] == "FLOCK" and parts[5] == key:
            (waiters if blocked else holders).append(int(parts[4]))
    return holders, waiters


def parse_other_cmdline(pid: int) -> argparse.Namespace | None:
    """The arguments of another pahcer_run.py process (of any version), from its command line."""
    argv = cmdline(pid)
    script = next((i for i, a in enumerate(argv) if a.endswith("pahcer_run.py")), None)
    if script is None:
        return None
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            args, _ = build_parser().parse_known_args(argv[script + 1:])
    except SystemExit:
        return None
    return args


def missing_case_count(run_ids: list[str], runs_dir: Path, seeds: tuple[int, int]) -> int | None:
    """The cases an --extend of these runs evaluates: the seeds in range without a result yet."""
    total = 0
    for run_id in run_ids:
        try:
            done = {c["seed"] for c in json.loads((runs_dir / run_id / "result.json").read_text())["cases"]}
        except (OSError, ValueError, KeyError):
            return None
        total += sum(s not in done for s in range(*seeds))
    return total


def info_from_cmdline(pid: int, runs_dir: Path, template: dict) -> dict:
    """What an evaluation without a queue entry (an older version) is doing, from its command line."""
    info = {"pid": pid, "old": True, "kind": "single", "run_ids": [], "solutions": [], "comment": "",
            "seeds": None, "cases": None}
    args = parse_other_cmdline(pid)
    if args is None:
        return info
    lo, hi = template["test"]["start_seed"], template["test"]["end_seed"]
    if args.seeds and (m := re.fullmatch(r"(\d+)-(\d+)", args.seeds)):
        lo, hi = int(m[1]), int(m[2])
    info.update(comment=args.comment, seeds=[lo, hi])
    if args.extend:
        info["kind"], info["solutions"] = "extend", args.extend
        for arg in args.extend:
            try:
                info["run_ids"].append(replay.resolve_run(arg).name)
            except LookupError:
                pass
        info["cases"] = missing_case_count(info["run_ids"], runs_dir, (lo, hi))
    elif args.compare:
        info.update(kind="compare", solutions=args.compare, cases=(hi - lo) * len(args.compare))
    elif args.solution:
        info.update(solutions=[args.solution], cases=hi - lo)
    return info


def info_from_lock_text(text: str, runs_dir: Path, template: dict) -> dict | None:
    """The evaluation holding the lock, from the text of runs/.lock and the meta.json of its first run.

    For an evaluation without a queue entry: one started by an older version of this script, whose
    lock text has the first run-id, the kind of evaluation, the pid and the time it got the lock.
    """
    m = LOCK_LINE.match(text.strip())
    if not m:
        return None
    pid = int(m["pid"])
    h = LOCK_HOLDER.match(m["holder"])
    first = h["first"] if h else m["holder"]
    kind = "single" if not h or not h["kind"] else "compare" if h["kind"] == "の比較" else "extend"
    if kind == "extend":  # the lock text names only the first run; the others are on the command line
        info = info_from_cmdline(pid, runs_dir, template)
        info.update(kind="extend", run_ids=info["run_ids"] or [first])
    else:
        info = {"pid": pid, "old": True, "kind": kind, "run_ids": [first], "solutions": [], "comment": "",
                "seeds": None, "cases": None}
        try:
            meta = json.loads((runs_dir / first / "meta.json").read_text())
        except (OSError, ValueError):
            meta = {}
        info["comment"] = meta.get("comment", "")
        info["seeds"] = meta.get("seeds")
        if kind == "compare":
            info["run_ids"] = meta.get("compare", {}).get("runs") or [first]
        if info["seeds"]:
            info["cases"] = (info["seeds"][1] - info["seeds"][0]) * len(info["run_ids"])
    info.update(state="running", started_at=m["since"], phase=None)
    return info


def finished_case_count(run_ids: list[str], runs_dir: Path, since: float) -> int:
    """Cases of these runs finished since the evaluation got the lock: err files written since then
    that end with the tester's "Score = ..." line (it is written last, when the case ends)."""
    count = 0
    for run_id in run_ids:
        try:
            files = list(os.scandir(runs_dir / run_id / "err"))
        except OSError:
            continue
        for entry in files:
            try:
                st = entry.stat()
                if st.st_mtime < since:
                    continue
                with open(entry.path, "rb") as f:
                    f.seek(max(0, st.st_size - 64))
                    tail = f.read()
            except OSError:
                continue
            count += bool(re.search(rb"Score = \d+\s*$", tail))
    return count


def clock(iso: str | None, now: float) -> str:
    """"11:16:57 (4.9 分前)" for an ISO time."""
    if not iso:
        return "不明"
    t = datetime.datetime.fromisoformat(iso)
    return f"{t:%H:%M:%S} ({(now - t.timestamp()) / 60:.1f} 分前)"


KIND_LABEL = {"single": "", "compare": "--compare、", "extend": "--extend、"}


def describe_running(info: dict, runs_dir: Path, now: float) -> list[str]:
    run_ids = info.get("run_ids") or ["(run-id 不明)"]
    lines = [f"  {', '.join(run_ids)}"
             f" ({KIND_LABEL.get(info.get('kind'), '')}pid {info['pid']}{'、古い版の pahcer_run.py' if info.get('old') else ''})"]
    if info.get("comment"):
        lines.append(f"    comment  : {info['comment']}")
    lines.append(f"    開始     : {clock(info.get('started_at'), now)}")
    since = info.get("started_epoch") or (datetime.datetime.fromisoformat(info["started_at"]).timestamp()
                                          if info.get("started_at") else None)
    total = info.get("cases")
    if since is None or not total:
        lines.append("    進み具合 : 不明")
        return lines
    done = finished_case_count(info.get("run_ids") or [], runs_dir, since)
    lines.append(f"    進み具合 : {done}/{total} ケース ({100 * done / total:.0f}%)")
    if info.get("phase") == "postprocess" or done >= total:
        lines.append("    終了見込 : 全ケースが終わり、指標の計算と記録の途中")
    elif done == 0:
        lines.append("    終了見込 : まだ終わったケースがないので見積もれない")
    else:
        rest = (now - since) * (total - done) / done
        end = datetime.datetime.fromtimestamp(now + rest)
        lines.append(f"    終了見込 : {end:%H:%M:%S} ごろ (残り約 {rest / 60:.1f} 分。この後に指標の計算と記録)")
    return lines


def describe_waiting(info: dict, now: float) -> list[str]:
    seeds = info.get("seeds")
    kind = {"compare": "--compare ", "extend": "--extend "}.get(info.get("kind"), "")
    parts = [kind + " ".join(info.get("solutions") or info.get("run_ids") or ["(解法不明)"])]
    if seeds:
        parts.append(f"seed {seeds[0]}〜{seeds[1] - 1}")
    if info.get("cases"):
        parts.append(f"{info['cases']} ケース")
    since = info.get("queued_at")
    # An older version does not register; its process start time (before compiling) stands in.
    head = (f"  {clock(since, now)} から待機" if since
            else f"  {clock(info.get('proc_start_iso'), now)} に起動")
    lines = [f"{head} (pid {info['pid']}{'、古い版の pahcer_run.py' if info.get('old') else ''}): {'、'.join(parts)}"]
    if info.get("comment"):
        lines.append(f"    comment : {info['comment']}")
    return lines


def process_label(pid: int) -> str:
    """A short name of a process: the program and its first two arguments, paths shortened."""
    argv = cmdline(pid)
    if not argv:
        return f"pid {pid}"
    words = [os.path.basename(argv[0])]
    for arg in argv[1:3]:
        if "/" in arg:
            arg = "/".join(Path(arg).parts[-2:])
        words.append(arg if len(arg) <= 40 else arg[:37] + "...")
    return " ".join(words)


def outside_usage(eval_roots: list[int], seconds: float) -> tuple[float, list[tuple[float, int, str, list[int]]]]:
    """CPU used outside the evaluations during `seconds`: (total cores, [(cores, processes, label, pids)]).

    The total is the machine's CPU minus that of the evaluations' process trees (as in LoadMonitor),
    so it includes the processes that are too short-lived to be listed; the list groups the processes
    alive at the end by process_label.
    """
    procs0, busy0, t0 = read_procs(), busy_ticks(), time.monotonic()
    time.sleep(seconds)
    procs1, busy1, t1 = read_procs(), busy_ticks(), time.monotonic()
    tree0, tree1 = descendants(procs0, eval_roots), descendants(procs1, eval_roots)
    span = (t1 - t0) * CLK_TCK
    total = ((busy1 - busy0) - (tree_ticks(procs1, tree1) - tree_ticks(procs0, tree0))) / span
    groups: dict[str, list] = {}
    for pid, stat in procs1.items():
        if pid in tree1 or pid in tree0 or pid == os.getpid():
            continue
        before = procs0.get(pid)
        # A process that started during the measurement (or a reused pid) counts from 0.
        used = stat[1] - (before[1] if before and before[3] == stat[3] else 0)
        if used <= 0:
            continue
        group = groups.setdefault(process_label(pid), [0.0, 0, []])
        group[0] += used / span
        group[1] += 1
        group[2].append(pid)
    rows = sorted(((cores, n, label, pids) for label, (cores, n, pids) in groups.items()), reverse=True)
    return total, rows


def print_status(root: Path, template: dict) -> int:
    """`--status`: the evaluation holding runs/.lock, those waiting for it, and the CPU used outside them."""
    runs_dir = root / "runs"
    lock_path = runs_dir / ".lock"
    now = time.time()
    owners = lock_owners(lock_path) if lock_path.exists() else ([], [])
    entries = {}
    for path in (runs_dir / QUEUE_DIR).glob("[0-9]*.json"):
        if (data := live_queue_entry(path)) is not None:
            entries[data["pid"]] = data
    text = lock_path.read_text() if lock_path.exists() else ""
    m = LOCK_LINE.match(text.strip())
    lock_pid = int(m["pid"]) if m else None
    if owners is None:  # no /proc/locks: trust a live pid in the lock text
        held = lock_pid is not None and read_stat(lock_pid) is not None
        owners = ([lock_pid] if held else [], [])
    holders, blocked = owners

    running = None
    if holders:
        # The queue entry of the holder, or else what an older version wrote in runs/.lock.
        running = entries.get(lock_pid) or info_from_lock_text(text, runs_dir, template) or {
            "pid": holders[0], "old": True, "run_ids": [text.strip() or "(runs/.lock の中身が読めない)"]}
        if running is entries.get(lock_pid):
            running = dict(running, state="running")
    print("評価中 (runs/.lock を持っている評価):")
    for line in describe_running(running, runs_dir, now) if running else ["  なし"]:
        print(line)

    waiting = [e for pid, e in entries.items() if pid != (running or {}).get("pid") and e["state"] == "waiting"]
    btime = boot_time()
    for pid in blocked:
        if pid not in entries and (stat := read_stat(pid)) is not None:
            info = info_from_cmdline(pid, runs_dir, template)
            started = datetime.datetime.fromtimestamp(btime + stat[3] / CLK_TCK).astimezone()
            info["proc_start_iso"] = started.isoformat(timespec="seconds")
            waiting.append(info)
    waiting.sort(key=lambda e: e.get("queued_at") or e.get("proc_start_iso") or "")
    print(f"待っている評価 ({len(waiting)} 件{'。始まる順は保証されない' if len(waiting) > 1 else ''}):")
    for info in waiting:
        for line in describe_waiting(info, now):
            print(line)
    if not waiting:
        print("  なし")

    seconds = 1.0
    total, rows = outside_usage(holders + ([lock_pid] if holders and lock_pid else []), seconds)
    shown = [row for row in rows if row[0] >= 0.05][:8]
    print(f"評価の外で CPU を使っているプロセス ({seconds:g} 秒間の測定。評価のプロセス木を除く):"
          f" 合計 {max(0.0, total):.2f} コア / {os.cpu_count()} コア")
    for cores, n, label, pids in shown:
        pid_text = ", ".join(map(str, pids[:3])) + (" ほか" if len(pids) > 3 else "")
        print(f"  {cores:5.2f} コア {n:>3} 個  {label} (pid {pid_text})")
    if not shown:
        print("  0.05 コア以上のプロセスはない")
    listed = sum(row[0] for row in rows)
    if total - listed >= 0.5:
        print(f"  ほかに、測定中に終わった短いプロセスなどが約 {total - listed:.1f} コア")
    if running and total >= LOAD_WARN_MEAN_CORES:
        print(f"  注意: 評価中に評価の外で {total:.1f} コア使われている。時間で打ち切る解法の結果がゆがむ")
    return 0


# ---------------------------------------------------------------- lock and pahcer


def acquire_lock(lock_path: Path, holder: str) -> int:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        current = lock_path.read_text().strip() or "不明"
        log(f"実行中の評価の終了を待っています: {current} (scripts/pahcer_run.py --status で状況を見られる)")
        fcntl.flock(fd, fcntl.LOCK_EX)
    os.ftruncate(fd, 0)
    os.write(fd, f"{holder} (pid {os.getpid()}, {now_iso()} から)\n".encode())
    return fd


def release_lock(lock_fd: int | None, queue: "QueueEntry | None") -> None:
    """Releases runs/.lock and removes the queue entry. After a successful evaluation this comes
    after the dashboard is rebuilt, so that the next evaluation does not share the CPU with it."""
    if queue is not None:
        queue.remove()
    if lock_fd is not None:
        os.close(lock_fd)


def wait_for_unused_result_name(json_dir: Path) -> None:
    """pahcer names its result JSON after the second it starts in. When a short run started in
    the same second just before, wait, so that its JSON is not overwritten."""
    latest = max((p.stem for p in json_dir.glob("result_*.json")), default="")
    while f"result_{datetime.datetime.now():%Y%m%d_%H%M%S}" <= latest:
        time.sleep(0.1)


def run_pahcer(root: Path, run_dir: Path, config: Path, comment: str, out_dir: Path,
               lock_fd: int) -> tuple[int, Path | None]:
    """Runs pahcer once while holding the lock. Returns (exit code, the result JSON it wrote)."""
    json_dir = out_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    wait_for_unused_result_name(json_dir)
    before = set(json_dir.glob("result_*.json"))
    cmd = ["pahcer", "run", "--setting-file", str(config), "--no-compile", "-c", comment]
    # pahcer inherits the lock fd, so the lock is held until pahcer exits even if this script dies.
    if sys.stdout.isatty():
        proc = subprocess.Popen(cmd, cwd=root, pass_fds=(lock_fd,))
    else:
        # Agents are not on a TTY; keep pahcer's per-case lines in a file.
        with open(run_dir / "pahcer.log", "w") as pahcer_log:
            proc = subprocess.Popen(cmd, cwd=root, stdout=pahcer_log, stderr=subprocess.STDOUT,
                                    pass_fds=(lock_fd,))
    try:
        returncode = proc.wait()
    except (KeyboardInterrupt, Interrupted):
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        raise
    new_results = sorted(set(json_dir.glob("result_*.json")) - before)
    if returncode != 0 or not new_results:
        log(f"pahcer が失敗しました (exit code {returncode})")
        if (run_dir / "pahcer.log").exists():
            print("\n".join((run_dir / "pahcer.log").read_text().splitlines()[-30:]), file=sys.stderr)
        return returncode or 1, None
    return 0, new_results[-1]


# ---------------------------------------------------------------- results


def judge_message(err_text: str) -> str:
    """The tester's message before its last "Score = ..." line (empty for a valid output)."""
    lines = err_text.rstrip("\n").splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if SCORE_LINE.fullmatch(lines[i]):
            if lines[i].split("=")[1].strip() == "0" and i > 0:
                return lines[i - 1].strip()
            return ""
    return "no score line"


def add_judge_messages(result: dict, run_dir: Path) -> None:
    """Fills error_message of WA cases from the err files (pahcer leaves it empty for a score of 0)."""
    for case in result["cases"]:
        if case["score"] == 0 and not case.get("error_message"):
            err = replay.err_path(run_dir, case["seed"])
            case["error_message"] = judge_message(err.read_text(errors="replace")) if err.exists() else "no err file"


def rescore_relative(result: dict, best_path: Path) -> None:
    """Recomputes relative scores against the best scores including this run.

    pahcer computes them against the best scores from before the run, so a case that beats the
    old best gets more than 100 (pahcer list recomputes them, and shows the corrected values).
    """
    best = {int(k): v for k, v in json.loads(best_path.read_text()).items()} if best_path.exists() else {}
    for case in result["cases"]:
        s = case["score"]
        if s > 0:
            ref = min(best.get(case["seed"]) or s, s)
            case["relative_score"] = 100.0 * ref / s
        else:
            case["relative_score"] = 0.0
    result["total_relative_score"] = sum(c["relative_score"] for c in result["cases"])


def summarize(result: dict, metrics: dict[int, dict] | None) -> dict:
    n = result["case_count"]
    cases = result["cases"]
    valid = [c["score"] for c in cases if c["score"] > 0]
    summary = {
        "cases": n,
        "total_score": result["total_score"],
        # WA scores 0, which would look good for a score to minimize, so it is left out.
        "average_score": sum(valid) / len(valid) if valid else None,
        "average_relative_score": result["total_relative_score"] / n if n else None,
        "max_execution_time": result["max_execution_time"],
        "over_time_limit": sum(c["execution_time"] > TIME_LIMIT_SEC for c in cases),
        "wa_seeds": result["wa_seeds"],
    }
    # Real times of all cases (the tester's wall time, at this machine's speed while evaluating).
    times = [c["execution_time"] for c in cases]
    summary["time_p99"] = replay.percentile(times, 0.99)
    summary["time_p999"] = replay.percentile(times, 0.999)
    slow = sorted((c for c in cases if c["execution_time"] > TIME_LIMIT_SEC), key=lambda c: -c["execution_time"])
    summary["over_time_limit_cases"] = [[c["seed"], round(c["execution_time"], 3)] for c in slow[:SLOW_CASES_SHOWN]]
    if metrics:
        valid = [m for m in metrics.values() if m["judge_score"] > 0]
        if valid:
            summary["average_E"] = sum(m["E"] for m in valid) / len(valid)
            summary["average_T"] = sum(m["T"] for m in valid) / len(valid)
        summary["replay_mismatch"] = sum(m["score"] != m["judge_score"] for m in metrics.values())
        # `end_sec = ...` on the solution's stderr: its own end time with CLOCK_SCALE, an estimate
        # of the time on the judge.
        end = [m["stderr"]["end_sec"] for m in metrics.values() if "end_sec" in m.get("stderr", {})]
        if end:
            summary["end_sec_cases"] = len(end)
            summary["end_sec_max"] = max(end)
            summary["end_sec_over"] = {f"{x:.1f}": sum(e > x for e in end) for x in END_SEC_LIMITS}
    return summary


def time_lines(summary: dict) -> list[str]:
    """The lines of the real times and of end_sec in a summary."""
    lines = [f"実行時間: 99% 点 {summary['time_p99']:.3f} s、99.9% 点 {summary['time_p999']:.3f} s、"
             f"最大 {summary['max_execution_time']:.3f} s ({TIME_LIMIT_SEC:g} s 超え {summary['over_time_limit']} ケース)"]
    if summary["over_time_limit_cases"]:
        shown = ", ".join(f"{seed} ({t:.3f} s)" for seed, t in summary["over_time_limit_cases"])
        more = summary["over_time_limit"] - len(summary["over_time_limit_cases"])
        lines.append(f"{TIME_LIMIT_SEC:g} s 超えの seed (遅い順): {shown}{f' ほか {more} ケース' if more > 0 else ''}")
    if "end_sec_max" in summary:
        over = "・".join(f"{x} s 超え {n}" for x, n in summary["end_sec_over"].items())
        lines.append(f"end_sec (ジャッジでの時間の見積り): 最大 {summary['end_sec_max']:.3f} s、{over} ケース"
                     f" ({summary['end_sec_cases']} ケース中)")
    return lines


def compute_metrics(run_dir: Path) -> dict[int, dict] | None:
    try:
        return replay.run_metrics(run_dir)
    except Exception as e:  # metrics are a convenience; the evaluation itself succeeded
        log(f"指標の計算に失敗しました: {type(e).__name__}: {e}")
        return None


def print_summary(run_id: str, run_dir: Path, summary: dict, record: bool, load: dict | None) -> None:
    wa = summary["wa_seeds"]
    print(f"  run-id           : {run_id}")
    print(f"  記録先           : {run_dir}")
    print(f"  ケース数         : {summary['cases']} (WA {len(wa)}{': ' + ', '.join(map(str, wa[:10])) if wa else ''})")
    average = summary["average_score"]
    print(f"  平均スコア       : {'-' if average is None else f'{average:.2f}'} (WA を除く。小さいほど良い)")
    if "average_E" in summary:
        print(f"  平均 E / 平均 T  : {summary['average_E']:.3f} / {summary['average_T']:.1f} (WA を除く)")
    print(f"  平均相対スコア   : {summary['average_relative_score']:.3f}")
    for line in time_lines(summary):
        print(f"  {line}")
    if summary.get("replay_mismatch"):
        print(f"  警告: scripts/replay.py の再生スコアがテスターと {summary['replay_mismatch']} ケースで違います")
    print(f"  pahcer/ への記録 : {'した' if record else 'しない (--no-record)'}")
    print_load(load)


def refresh_report(root: Path) -> None:
    """Rebuilds runs/report.html. A failure is reported but does not fail the evaluation."""
    try:
        done = subprocess.run([sys.executable, str(root / "scripts" / "report.py"), "--quiet"],
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        log("ダッシュボードの更新が時間切れになりました")
        return
    if done.returncode != 0:
        log("ダッシュボードの更新に失敗しました: " + (done.stdout + done.stderr).strip()[-500:])
    else:
        log(f"ダッシュボードを更新しました: {root / 'runs' / 'report.html'}")


def parse_seeds(text: str, template: dict) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)-(\d+)", text)
    if not m or int(m[1]) >= int(m[2]):
        sys.exit("[pahcer_run] --seeds は START-END (START < END) の形で指定してください")
    lo, hi = template["test"]["start_seed"], template["test"]["end_seed"]
    if int(m[1]) < lo or int(m[2]) > hi:
        sys.exit(f"[pahcer_run] --seeds は手元のケースの範囲 {lo}-{hi} の中で指定してください")
    return int(m[1]), int(m[2])


def seed_range(args, template: dict) -> tuple[int, int]:
    if args.seeds:
        return parse_seeds(args.seeds, template)
    return template["test"]["start_seed"], template["test"]["end_seed"]


# ---------------------------------------------------------------- single solution


def evaluate(args, root: Path, template: dict) -> int:
    """Compiles a solution and evaluates it as a new run."""
    seeds = seed_range(args, template)
    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)
    record = not args.no_record
    # The run directory is created first so that --no-record can keep its pahcer files inside it.
    arm = prepare_run(args.solution, runs_dir, args.comment, seeds, record, root / "pahcer")
    run_id, run_dir, meta = arm["run_id"], arm["run_dir"], arm["meta"]
    out_dir = root / "pahcer" if record else run_dir / "pahcer"
    meta["out_dir"] = str(out_dir)
    log(f"run-id: {run_id}")
    log(f"記録先: {run_dir}")
    lock_fd = queue = None
    finished = False  # the lock is then kept until the dashboard is rebuilt
    try:
        # Compile outside the lock: compile errors are reported without waiting for other runs.
        if not compile_solution(arm["compile_cmd"], run_dir, arm["src_root"]):
            # Nothing was evaluated, so do not leave a run directory behind.
            shutil.rmtree(run_dir)
            log("コンパイルに失敗しました (run ディレクトリは削除しました)")
            return 1
        tester = ensure_tester(root)
        config_path = run_dir / "pahcer_config.toml"
        write_config(config_path, template, seeds=seeds, out_dir=out_dir, compile_cmd=arm["compile_cmd"],
                     binary=arm["binary"], tester=tester, in_dir=root / "tools" / "in", run_dir=run_dir)
        if not record:
            (out_dir / "json").mkdir(parents=True)
            best = root / "pahcer" / "best_scores.json"
            if best.exists():  # keep relative scores meaningful without touching the shared file
                shutil.copy2(best, out_dir / "best_scores.json")

        meta["status"] = "waiting"
        save_meta(run_dir, meta)
        queue = QueueEntry(runs_dir, "single", [run_id], [args.solution], args.comment, seeds, seeds[1] - seeds[0])
        lock_fd = acquire_lock(runs_dir / ".lock", run_id)
        meta["status"] = "running"
        meta["started_at"] = now_iso()
        save_meta(run_dir, meta)
        queue.started(meta["started_at"])
        log(f"評価を開始しました (seed {seeds[0]}〜{seeds[1] - 1})")
        monitor = LoadMonitor().start()
        try:
            returncode, result_json = run_pahcer(root, run_dir, config_path, f"{run_id} {args.comment}".strip(),
                                                 out_dir, lock_fd)
        finally:
            meta["outside_load"] = monitor.stop()
        queue.update(phase="postprocess")
        meta["finished_at"] = now_iso()
        if result_json is None:
            meta["status"] = "failed"
            save_meta(run_dir, meta)
            return returncode
        result = json.loads(result_json.read_text())
        add_judge_messages(result, run_dir)
        rescore_relative(result, out_dir / "best_scores.json")
        replay.write_json_atomic(run_dir / "result.json", result, indent=2)
        # Still under the lock, so the next evaluation does not share the CPU with the replay.
        metrics = compute_metrics(run_dir)
        finished = True
    except (KeyboardInterrupt, Interrupted):
        meta["status"] = "interrupted"
        meta["finished_at"] = now_iso()
        save_meta(run_dir, meta)
        log("中断しました")
        return 130
    finally:
        if not finished:
            release_lock(lock_fd, queue)

    summary = summarize(result, metrics)
    meta["status"] = "ok"
    meta["summary"] = summary
    save_meta(run_dir, meta)
    log("評価が終わりました")
    print_summary(run_id, run_dir, summary, record, meta.get("outside_load"))
    refresh_report(root)
    release_lock(lock_fd, queue)
    return 0


# ---------------------------------------------------------------- --compare


def compare_case(seed: int, order: list[int], binaries: list[Path], run_dirs: list[Path],
                 in_dir: Path, tester: Path) -> list[dict]:
    """Runs every solution on one seed, one after another in the given order.

    Returns one case record per solution (in the solutions' order), in the format of the
    "cases" of a pahcer result JSON. relative_score is filled in later.
    """
    seed4 = f"{seed:04d}"
    infile = in_dir / f"{seed4}.txt"
    records: list[dict] = [{} for _ in binaries]
    for i in order:
        outfile = run_dirs[i] / "out" / f"{seed4}.txt"
        errfile = run_dirs[i] / "err" / f"{seed4}.txt"
        error = ""
        start = time.perf_counter()
        with open(infile, "rb") as stdin, open(outfile, "wb") as stdout, open(errfile, "wb") as stderr:
            try:
                subprocess.run([str(tester), str(binaries[i])], stdin=stdin, stdout=stdout, stderr=stderr,
                               timeout=COMPARE_CASE_TIMEOUT)
            except subprocess.TimeoutExpired:
                error = f"timeout ({COMPARE_CASE_TIMEOUT:.0f} s)"
        elapsed = time.perf_counter() - start
        err_text = errfile.read_text(errors="replace")
        scores = SCORE_LINE.findall(err_text)
        score = int(scores[-1]) if scores and not error else 0
        if not error and score == 0:
            error = judge_message(err_text)
        records[i] = {"seed": seed, "score": score, "relative_score": 0.0,
                      "execution_time": elapsed, "error_message": error}
    return records


def compare_result(cases: list[dict], comment: str, start_time: str) -> dict:
    """A result in the format pahcer writes to pahcer/json/result_*.json."""
    return {
        "start_time": start_time,
        "case_count": len(cases),
        "total_score": sum(c["score"] for c in cases),
        "total_score_log10": sum(math.log10(c["score"]) for c in cases if c["score"] > 0),
        "total_relative_score": sum(c["relative_score"] for c in cases),
        "max_execution_time": max(c["execution_time"] for c in cases),
        "comment": comment,
        "tag_name": None,
        "wa_seeds": [c["seed"] for c in cases if c["score"] == 0],
        "cases": cases,
    }


def summary_row(start: str, result: dict) -> str:
    """One line of pahcer/summary.md, formatted as pahcer formats it."""
    n = result["case_count"]
    return (f"{start} | {n:>5,} | {result['total_score']:>16,} | {result['total_score'] / n:>16.2f} | "
            f"{result['total_score_log10']:>12,.5f} | {result['total_score_log10'] / n:>11.5f} | "
            f"{result['comment']}")


def compare_against_first(results: list[dict]) -> list[dict]:
    """For each solution, its difference from the first one over the seeds both solved.

    The difference is the mean of log(score / score of the first) over cases (negative is better),
    which follows the contest's per-case ranking better than the mean score; its standard error
    comes from the per-case differences.
    """
    base = {c["seed"]: c["score"] for c in results[0]["cases"]}
    table = []
    for result in results:
        diffs = [math.log(c["score"] / base[c["seed"]]) for c in result["cases"]
                 if c["score"] > 0 and base.get(c["seed"], 0) > 0]
        n = len(diffs)
        mean = sum(diffs) / n if n else float("nan")
        se = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1) / n) if n > 1 else float("nan")
        table.append({
            "cases": n,
            "mean_log_ratio": mean,
            "standard_error": se,
            "better": sum(d < 0 for d in diffs),
            "equal": sum(d == 0 for d in diffs),
            "worse": sum(d > 0 for d in diffs),
            "mean_execution_time": sum(c["execution_time"] for c in result["cases"]) / len(result["cases"]),
        })
    return table


def evaluate_compare(args, root: Path, template: dict) -> int:
    """Evaluates several solutions on the same seeds, interleaved seed by seed.

    Each seed is one task: every solution runs on it in turn, starting from a solution that
    rotates with the seed. Tasks run in parallel with the thread count of pahcer_config.toml.
    Each solution gets an ordinary run directory and, unless --no-record, an ordinary pahcer
    record (summary line, result JSON and best scores).
    """
    if len(args.compare) < 2:
        sys.exit("[pahcer_run] --compare には解法を 2 つ以上指定してください")
    seeds = seed_range(args, template)
    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)
    out_dir = root / "pahcer"
    record = not args.no_record
    arms = [prepare_run(s, runs_dir, args.comment, seeds, record, out_dir) for s in args.compare]
    group = [arm["run_id"] for arm in arms]
    for index, arm in enumerate(arms):
        arm["meta"]["compare"] = {"runs": group, "index": index}
        if not record:
            arm["meta"]["out_dir"] = None
        save_meta(arm["run_dir"], arm["meta"])
        log(f"run-id: {arm['run_id']}")
    # Compile outside the lock. Nothing is kept if any solution fails to compile.
    for arm in arms:
        if not compile_solution(arm["compile_cmd"], arm["run_dir"], arm["src_root"]):
            for other in arms:
                shutil.rmtree(other["run_dir"], ignore_errors=True)
            log(f"{arm['run_id']} のコンパイルに失敗しました (run ディレクトリはすべて削除しました)")
            return 1
    tester = ensure_tester(root)
    in_dir = root / "tools" / "in"
    threads = int(template["test"].get("threads", 0)) or os.cpu_count() or 1
    seed_list = list(range(*seeds))
    count = len(arms)
    lock_fd = queue = None
    load = None
    finished = False  # the lock is then kept until the dashboard is rebuilt
    try:
        for arm in arms:
            arm["meta"]["status"] = "waiting"
            save_meta(arm["run_dir"], arm["meta"])
        queue = QueueEntry(runs_dir, "compare", group, args.compare, args.comment, seeds, len(seed_list) * count)
        lock_fd = acquire_lock(runs_dir / ".lock", f"{group[0]} ほか {count - 1} 個の比較")
        started = now_iso()
        start_time = datetime.datetime.now().astimezone().isoformat()
        for arm in arms:
            arm["meta"]["status"] = "running"
            arm["meta"]["started_at"] = started
            save_meta(arm["run_dir"], arm["meta"])
        queue.started(started)
        log(f"{count} 個の解法を比べます (seed {seeds[0]}〜{seeds[1] - 1}、{threads} 並列、seed ごとに続けて実行)")
        records = {}
        began = time.perf_counter()
        monitor = LoadMonitor().start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
                futures = {pool.submit(compare_case, seed, [(seed + j) % count for j in range(count)],
                                       [arm["binary"] for arm in arms], [arm["run_dir"] for arm in arms],
                                       in_dir, tester): seed for seed in seed_list}
                try:
                    for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
                        records[futures[future]] = future.result()
                        if done % max(1, len(seed_list) // 10) == 0 or done == len(seed_list):
                            spent = time.perf_counter() - began
                            log(f"{done}/{len(seed_list)} seed 完了 (経過 {spent / 60:.1f} 分、"
                                f"残り約 {spent / done * (len(seed_list) - done) / 60:.1f} 分)")
                except BaseException:
                    pool.shutdown(wait=True, cancel_futures=True)
                    raise
        finally:
            load = monitor.stop()
            for arm in arms:
                arm["meta"]["outside_load"] = load
        queue.update(phase="postprocess")

        # Relative scores use the best known score of each seed, including every solution here.
        best_path = out_dir / "best_scores.json"
        best = {int(k): v for k, v in json.loads(best_path.read_text()).items()} if best_path.exists() else {}
        for seed in seed_list:
            scores = [best.get(seed, 0)] + [records[seed][i]["score"] for i in range(count)]
            valid = [s for s in scores if s > 0]
            if valid:
                best[seed] = min(valid)
        results = []
        for index, arm in enumerate(arms):
            cases = []
            for seed in seed_list:
                case = dict(records[seed][index])
                if case["score"] > 0:
                    case["relative_score"] = 100.0 * best[seed] / case["score"]
                cases.append(case)
            result = compare_result(cases, f"{arm['run_id']} {args.comment}".strip(), start_time)
            replay.write_json_atomic(arm["run_dir"] / "result.json", result, indent=2)
            results.append(result)
        if record:
            # The lock is still held, so no pahcer run writes these files meanwhile.
            (out_dir / "json").mkdir(parents=True, exist_ok=True)
            base_name = datetime.datetime.fromisoformat(start_time)
            for index, result in enumerate(results):
                stamp = base_name + datetime.timedelta(seconds=index)
                replay.write_json_atomic(out_dir / "json" / f"result_{stamp:%Y%m%d_%H%M%S}.json", result, indent=2)
            with open(out_dir / "summary.md", "a") as summary:
                for result in results:
                    summary.write(summary_row(started, result) + "\n")
            replay.write_json_atomic(best_path, {f"{seed:04d}": score for seed, score in sorted(best.items())},
                                     indent=2)
        metrics = [compute_metrics(arm["run_dir"]) for arm in arms]
        finished = True
    except (KeyboardInterrupt, Interrupted):
        for arm in arms:
            arm["meta"]["status"] = "interrupted"
            arm["meta"]["finished_at"] = now_iso()
            save_meta(arm["run_dir"], arm["meta"])
        log("中断しました")
        return 130
    finally:
        if not finished:
            release_lock(lock_fd, queue)

    table = compare_against_first(results)
    for arm, result, row, m in zip(arms, results, table, metrics):
        arm["meta"]["status"] = "ok"
        arm["meta"]["finished_at"] = now_iso()
        arm["meta"]["summary"] = summarize(result, m)
        arm["meta"]["compare"]["against_first"] = row
        save_meta(arm["run_dir"], arm["meta"])
    log("比較が終わりました")
    print("  差は最初の解法に対するケースごとの log スコア比の平均（負なら良い）。± は標準誤差。"
          "勝/分/敗は最初の解法よりスコアが小さい/同じ/大きいケースの数")
    print(f"  {'run-id':<44} {'ケース':>5} {'WA':>3} {'平均スコア':>10} {'平均E':>7} {'平均T':>8}"
          f" {'差':>8} {'±':>7} {'勝/分/敗':>13} {'平均時間':>8}")
    for arm, result, row in zip(arms, results, table):
        s = arm["meta"]["summary"]
        print(f"  {arm['run_id']:<44} {result['case_count']:>6} {len(result['wa_seeds']):>3} "
              f"{s['average_score'] or float('nan'):>12.2f} {s.get('average_E', float('nan')):>8.3f} {s.get('average_T', float('nan')):>9.1f} "
              f"{100 * row['mean_log_ratio']:>+8.3f}% {100 * row['standard_error']:>6.3f}% "
              f"{row['better']:>5}/{row['equal']:>3}/{row['worse']:>4} {row['mean_execution_time']:>8.3f}s")
        for line in time_lines(s):
            print(f"    {line}")
        if s.get("replay_mismatch"):
            print(f"    警告: scripts/replay.py の再生スコアがテスターと {s['replay_mismatch']} ケースで違います")
    print(f"  pahcer/ への記録 : {'した' if record else 'しない (--no-record)'}")
    print_load(load)
    refresh_report(root)
    release_lock(lock_fd, queue)
    return 0


# ---------------------------------------------------------------- --extend


def evaluate_extend(args, root: Path, template: dict) -> int:
    """Evaluates existing runs on the seeds they lack and adds the cases to the same runs.

    For runs of fewer cases than the default range: the 500 cases of the runs from before 2000
    became the default, or a first look with --seeds 0-500. Each run keeps its run-id and its binary
    (runs/<run-id>/a.out, compiled again from src/ with the recorded command if it is missing).
    As in --compare, each seed is one task in which the runs that lack it run one after another.
    The new cases are merged into result.json and the extension is recorded in meta.json
    ("extensions"). A run recorded in pahcer/ gets a new summary line and result JSON there, with
    all its cases, and its scores enter the best scores.
    """
    seeds = seed_range(args, template)
    runs_dir = root / "runs"
    out_dir = root / "pahcer"
    arms = []
    for arg in args.extend:
        try:
            run_dir = replay.resolve_run(arg)
        except LookupError as e:
            sys.exit(f"[pahcer_run] {e}")
        meta = json.loads((run_dir / "meta.json").read_text())
        if meta.get("status") != "ok" or not (run_dir / "result.json").exists():
            sys.exit(f"[pahcer_run] 正常に終わった run ではありません: {run_dir.name}")
        if any(arm["run_dir"] == run_dir for arm in arms):
            sys.exit(f"[pahcer_run] 同じ run が 2 回指定されています: {run_dir.name}")
        arms.append({"run_id": run_dir.name, "run_dir": run_dir, "binary": run_dir / "a.out"})
        log(f"run-id: {run_dir.name}")
    # Compile outside the lock, only when the binary of the run is gone.
    for arm in arms:
        if not arm["binary"].exists():
            meta = json.loads((arm["run_dir"] / "meta.json").read_text())
            log(f"{arm['run_id']} の a.out がないので、記録したコマンドでコンパイルします")
            if not compile_solution(meta["compile_command"], arm["run_dir"], arm["run_dir"] / "src"):
                log(f"{arm['run_id']} のコンパイルに失敗しました")
                return 1
    tester = ensure_tester(root)
    in_dir = root / "tools" / "in"
    threads = int(template["test"].get("threads", 0)) or os.cpu_count() or 1
    group = [arm["run_id"] for arm in arms]
    lock_fd = queue = None
    load = None
    finished = False  # the lock is then kept until the dashboard is rebuilt
    try:
        # The number of cases is an estimate until the runs are read again under the lock.
        queue = QueueEntry(runs_dir, "extend", group, args.extend, args.comment, seeds,
                           missing_case_count(group, runs_dir, seeds))
        lock_fd = acquire_lock(runs_dir / ".lock", f"{group[0]} ほか {len(arms) - 1} 個への seed の追加")
        # Read the runs under the lock: an extension that held it before may have added seeds.
        for arm in arms:
            arm["meta"] = json.loads((arm["run_dir"] / "meta.json").read_text())
            arm["result"] = json.loads((arm["run_dir"] / "result.json").read_text())
            done = {c["seed"] for c in arm["result"]["cases"]}
            arm["missing"] = [s for s in range(*seeds) if s not in done]
            if not arm["missing"]:
                log(f"{arm['run_id']} は seed {seeds[0]}〜{seeds[1] - 1} をすべて評価済みです")
        arms = [arm for arm in arms if arm["missing"]]
        if not arms:
            log("追加する seed はありません")
            return 0
        count = len(arms)
        missing = [set(arm["missing"]) for arm in arms]
        seed_list = sorted(set().union(*missing))
        started = now_iso()
        start_time = datetime.datetime.now().astimezone().isoformat()
        queue.started(started, cases=sum(map(len, missing)))
        log(f"{count} 個の run に seed を追加します (seed {seed_list[0]}〜{seed_list[-1]} のうち未評価の"
            f" {sum(map(len, missing))} ケース、{threads} 並列、seed ごとに続けて実行)")
        records = {}
        began = time.perf_counter()
        monitor = LoadMonitor().start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
                futures = {}
                for seed in seed_list:
                    order = [i for i in ((seed + j) % count for j in range(count)) if seed in missing[i]]
                    futures[pool.submit(compare_case, seed, order, [arm["binary"] for arm in arms],
                                        [arm["run_dir"] for arm in arms], in_dir, tester)] = seed
                try:
                    for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
                        records[futures[future]] = future.result()
                        if done % max(1, len(seed_list) // 10) == 0 or done == len(seed_list):
                            spent = time.perf_counter() - began
                            log(f"{done}/{len(seed_list)} seed 完了 (経過 {spent / 60:.1f} 分、"
                                f"残り約 {spent / done * (len(seed_list) - done) / 60:.1f} 分)")
                except BaseException:
                    pool.shutdown(wait=True, cancel_futures=True)
                    raise
        finally:
            load = monitor.stop()
        queue.update(phase="postprocess")

        # Relative scores use the best known score of each seed, including every run here. Only
        # the runs recorded in pahcer/ enter its best scores (as with --no-record).
        best_path = out_dir / "best_scores.json"
        shared = {int(k): v for k, v in json.loads(best_path.read_text()).items()} if best_path.exists() else {}
        best_all, best_recorded = dict(shared), dict(shared)
        for index, arm in enumerate(arms):
            recorded = arm["meta"].get("record", True)
            for case in arm["result"]["cases"] + [records[s][index] for s in arm["missing"]]:
                if case["score"] > 0:
                    for best in (best_all, best_recorded) if recorded else (best_all,):
                        best[case["seed"]] = min(best.get(case["seed"], case["score"]), case["score"])
        finished = now_iso()
        new_results, results = [], []
        for index, arm in enumerate(arms):
            new_cases = [dict(records[s][index]) for s in arm["missing"]]
            cases = sorted(arm["result"]["cases"] + new_cases, key=lambda c: c["seed"])
            for case in cases:
                case["relative_score"] = 100.0 * best_all[case["seed"]] / case["score"] if case["score"] > 0 else 0.0
            lo, hi = arm["missing"][0], arm["missing"][-1] + 1
            note = f"seed {lo}〜{hi - 1} の {len(new_cases)} ケースを追加" + (f": {args.comment}" if args.comment else "")
            result = compare_result(cases, f"{arm['result'].get('comment') or arm['run_id']} ({note})", start_time)
            replay.write_json_atomic(arm["run_dir"] / "result.json", result, indent=2)
            evaluated = [c["seed"] for c in cases]
            arm["meta"]["seeds"] = [evaluated[0], evaluated[-1] + 1]
            arm["meta"].setdefault("extensions", []).append({
                "seeds": [lo, hi], "cases": len(new_cases), "comment": args.comment, "group": group,
                "started_at": started, "finished_at": finished, "outside_load": load,
            })
            save_meta(arm["run_dir"], arm["meta"])
            new_results.append(compare_result(new_cases, "", start_time))
            results.append(result)
        if any(arm["meta"].get("record", True) for arm in arms):
            # The lock is still held, so no pahcer run writes these files meanwhile.
            (out_dir / "json").mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now()
            with open(out_dir / "summary.md", "a") as summary:
                for arm, result in zip(arms, results):
                    if arm["meta"].get("record", True):
                        while (path := out_dir / "json" / f"result_{stamp:%Y%m%d_%H%M%S}.json").exists():
                            stamp += datetime.timedelta(seconds=1)
                        replay.write_json_atomic(path, result, indent=2)
                        stamp += datetime.timedelta(seconds=1)
                        summary.write(summary_row(started, result) + "\n")
            replay.write_json_atomic(best_path, {f"{seed:04d}": score for seed, score in sorted(best_recorded.items())},
                                     indent=2)
        metrics = [compute_metrics(arm["run_dir"]) for arm in arms]
        finished = True
    except (KeyboardInterrupt, Interrupted):
        log("中断しました")
        return 130
    finally:
        if not finished:
            release_lock(lock_fd, queue)

    for arm, result, m in zip(arms, results, metrics):
        arm["meta"]["summary"] = summarize(result, m)
        save_meta(arm["run_dir"], arm["meta"])
    log("seed の追加が終わりました")
    print("  差は最初の run に対するケースごとの log スコア比の平均（負なら良い）。± は標準誤差。"
          "「追加分」は今回評価した seed だけ（seed ごとに続けて実行したので、マシンの速さの影響がそろう）")
    print(f"  {'run-id':<44} {'ケース':>5} {'WA':>3} {'平均スコア':>10} {'追加分の平均':>10}"
          f" {'追加分の差':>9} {'±':>7} {'全体の差':>8} {'±':>7}")
    new_table, all_table = compare_against_first(new_results), compare_against_first(results)
    for arm, result, new, row_new, row_all in zip(arms, results, new_results, new_table, all_table):
        s = arm["meta"]["summary"]
        valid = [c["score"] for c in new["cases"] if c["score"] > 0]
        print(f"  {arm['run_id']:<44} {result['case_count']:>6} {len(result['wa_seeds']):>3} "
              f"{s['average_score'] or float('nan'):>12.2f} {sum(valid) / len(valid) if valid else float('nan'):>14.2f} "
              f"{100 * row_new['mean_log_ratio']:>+10.3f}% {100 * row_new['standard_error']:>6.3f}% "
              f"{100 * row_all['mean_log_ratio']:>+8.3f}% {100 * row_all['standard_error']:>6.3f}%")
        for line in time_lines(s):  # over all the cases of the run, as in its meta.json
            print(f"    {line}")
        if s.get("replay_mismatch"):
            print(f"    警告: scripts/replay.py の再生スコアがテスターと {s['replay_mismatch']} ケースで違います")
    print_load(load)  # while the added cases ran
    refresh_report(root)
    release_lock(lock_fd, queue)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The command line parser (also used by --status to read the arguments of other evaluations)."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("solution", nargs="?", help="解法のディレクトリ (solutions/<name>) か .cpp ファイル")
    parser.add_argument("-c", "--comment", default="", help="pahcer/summary.md とダッシュボードに残すコメント")
    parser.add_argument("--seeds", metavar="START-END",
                        help="評価する seed の範囲。END は含まない (例: 0-100 で 0〜99)。省略時は全ケース")
    parser.add_argument("--compare", nargs="+", metavar="SOLUTION",
                        help="複数の解法を seed ごとに続けて実行して比べる。最初の解法が比較の基準")
    parser.add_argument("--no-record", action="store_true",
                        help="pahcer/ の履歴とベストスコアを更新しない（動作確認用）")
    parser.add_argument("--extend", nargs="+", metavar="RUN",
                        help="既存の run（run-id か末尾の解法名）に、未評価の seed（既定は全ケースのうち未評価のもの）を"
                             "評価して加える。複数なら seed ごとに続けて実行する")
    parser.add_argument("--status", action="store_true",
                        help="評価を始めずに、実行中・待機中の評価（進み具合と終わる時刻の見積り）と、"
                             "評価の外で CPU を使っているプロセスを表示する")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.status:
        if args.solution or args.compare or args.extend:
            parser.error("--status は解法や --compare、--extend と一緒には使えません")
    elif args.extend:
        if args.solution or args.compare:
            parser.error("--extend は解法や --compare と一緒には使えません")
        if args.no_record:
            parser.error("--extend の記録の有無は、元の run に従います（--no-record は使えません）")
    elif args.compare:
        if args.solution:
            parser.error("--compare を使うときは、解法をすべて --compare の後に並べてください")
    elif not args.solution:
        parser.error("解法を指定してください")

    root = replay.main_root()
    template = tomllib.loads((root / "pahcer_config.toml").read_text())
    if args.status:
        return print_status(root, template)
    signal.signal(signal.SIGTERM, _raise_interrupted)
    if args.extend:
        return evaluate_extend(args, root, template)
    if args.compare:
        return evaluate_compare(args, root, template)
    return evaluate(args, root, template)


if __name__ == "__main__":
    sys.exit(main())
