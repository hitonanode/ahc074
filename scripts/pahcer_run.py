#!/usr/bin/env python3
"""解法を手元のテストケースで評価し、評価ごとの記録を runs/<run-id>/ に残す（pahcer のラッパー）。

使い方:
    scripts/pahcer_run.py solutions/<name> -c "<comment>"          # 全 500 ケース (seed 0〜499)
    scripts/pahcer_run.py solutions/<name> -c "<comment>" --seeds 0-50
                                                                   # seed の範囲を指定 (END は含まない)
    scripts/pahcer_run.py --compare solutions/<A> solutions/<B> ... -c "<comment>"
                                                                   # 複数の解法を seed ごとに続けて実行して比べる
    （そのほか --no-record）

- 解法のソース（と solutions/<name>/README.md）を runs/<run-id>/src/ にコピーし、そのコピーをコンパイルして評価する。
- 1 ケースごとに公式テスター (tools/target/release/tester) が解法を起動して対話する。解法の stdout を
  runs/<run-id>/out/<seed>.txt に、解法の stderr とテスターの判定（エラー文と "Score = ..."）を
  err/<seed>.txt に保存する。result.json にスコアと実行時間、meta.json にコメントや commit が入る。
- --compare は、seed ごとに全部の解法を続けて実行し（順番は seed ごとにずらす）、その単位を並列に
  回す。評価中にマシンの速さが変わっても全部の解法に同じようにかかるので、別々に評価した run を
  比べるより差を正確に読める。各解法はふつうの run として runs/ と pahcer/ に記録され、最後に
  最初の解法に対する差（ケースごとの log スコア比の平均と標準誤差）を表示する。
- 同時に走る評価は 1 つだけ（runs/.lock）。他の評価が実行中なら、終わるまで待ってから始める
  （CPU を取り合うと探索量が減り、スコアを比較できなくなるため）。
- 評価が終わるたびに、ケースごとの指標 (runs/<run-id>/metrics.json) を計算し、ダッシュボード
  (runs/report.html) を作り直す。
- pahcer の設定は、ルートの pahcer_config.toml をテンプレートにして評価ごとに生成する。
- runs/ と pahcer/ は常に main checkout のものを使う（worktree から実行しても同じ）。
"""

import argparse
import concurrent.futures
import datetime
import fcntl
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402

COMPILE_CMD = ["g++", "-std=c++23", "-O2"]
CPP_SUFFIXES = {".cpp", ".cc", ".cxx"}
SOURCE_SUFFIXES = CPP_SUFFIXES | {".hpp", ".hh", ".hxx", ".h", ".ipp", ".inc"}
# The description that every solutions/<name>/ must have; saved with the sources.
DESCRIPTION_FILE = "README.md"
# The time limit of the problem. Cases above it are counted in the summary (the tester has no limit).
TIME_LIMIT_SEC = 2.0
SCORE_LINE = re.compile(r"(?m)^\s*Score\s*=\s*(\d+)\s*$")
# A case that takes longer than this is stopped and counted as WA (--compare only).
COMPARE_CASE_TIMEOUT = 60.0


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


# ---------------------------------------------------------------- lock and pahcer


def acquire_lock(lock_path: Path, holder: str) -> int:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        current = lock_path.read_text().strip() or "不明"
        log(f"実行中の評価の終了を待っています: {current}")
        fcntl.flock(fd, fcntl.LOCK_EX)
    os.ftruncate(fd, 0)
    os.write(fd, f"{holder} (pid {os.getpid()}, {now_iso()} から)\n".encode())
    return fd


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
    if metrics:
        valid = [m for m in metrics.values() if m["judge_score"] > 0]
        if valid:
            summary["average_E"] = sum(m["E"] for m in valid) / len(valid)
            summary["average_T"] = sum(m["T"] for m in valid) / len(valid)
        summary["replay_mismatch"] = sum(m["score"] != m["judge_score"] for m in metrics.values())
    return summary


def compute_metrics(run_dir: Path) -> dict[int, dict] | None:
    try:
        return replay.run_metrics(run_dir)
    except Exception as e:  # metrics are a convenience; the evaluation itself succeeded
        log(f"指標の計算に失敗しました: {type(e).__name__}: {e}")
        return None


def print_summary(run_id: str, run_dir: Path, summary: dict, record: bool) -> None:
    wa = summary["wa_seeds"]
    print(f"  run-id           : {run_id}")
    print(f"  記録先           : {run_dir}")
    print(f"  ケース数         : {summary['cases']} (WA {len(wa)}{': ' + ', '.join(map(str, wa[:10])) if wa else ''})")
    average = summary["average_score"]
    print(f"  平均スコア       : {'-' if average is None else f'{average:.2f}'} (WA を除く。小さいほど良い)")
    if "average_E" in summary:
        print(f"  平均 E / 平均 T  : {summary['average_E']:.3f} / {summary['average_T']:.1f} (WA を除く)")
    print(f"  平均相対スコア   : {summary['average_relative_score']:.3f}")
    print(f"  最大実行時間     : {summary['max_execution_time']:.3f} s"
          f" ({TIME_LIMIT_SEC:g} s 超え {summary['over_time_limit']} ケース)")
    if summary.get("replay_mismatch"):
        print(f"  警告: scripts/replay.py の再生スコアがテスターと {summary['replay_mismatch']} ケースで違います")
    print(f"  pahcer/ への記録 : {'した' if record else 'しない (--no-record)'}")


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
    lock_fd = None
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
        lock_fd = acquire_lock(runs_dir / ".lock", run_id)
        meta["status"] = "running"
        meta["started_at"] = now_iso()
        save_meta(run_dir, meta)
        log(f"評価を開始しました (seed {seeds[0]}〜{seeds[1] - 1})")
        returncode, result_json = run_pahcer(root, run_dir, config_path, f"{run_id} {args.comment}".strip(),
                                             out_dir, lock_fd)
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
    except (KeyboardInterrupt, Interrupted):
        meta["status"] = "interrupted"
        meta["finished_at"] = now_iso()
        save_meta(run_dir, meta)
        log("中断しました")
        return 130
    finally:
        if lock_fd is not None:
            os.close(lock_fd)

    summary = summarize(result, metrics)
    meta["status"] = "ok"
    meta["summary"] = summary
    save_meta(run_dir, meta)
    log("評価が終わりました")
    print_summary(run_id, run_dir, summary, record)
    refresh_report(root)
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
    lock_fd = None
    try:
        for arm in arms:
            arm["meta"]["status"] = "waiting"
            save_meta(arm["run_dir"], arm["meta"])
        lock_fd = acquire_lock(runs_dir / ".lock", f"{group[0]} ほか {count - 1} 個の比較")
        started = now_iso()
        start_time = datetime.datetime.now().astimezone().isoformat()
        for arm in arms:
            arm["meta"]["status"] = "running"
            arm["meta"]["started_at"] = started
            save_meta(arm["run_dir"], arm["meta"])
        log(f"{count} 個の解法を比べます (seed {seeds[0]}〜{seeds[1] - 1}、{threads} 並列、seed ごとに続けて実行)")
        records = {}
        began = time.perf_counter()
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
    except (KeyboardInterrupt, Interrupted):
        for arm in arms:
            arm["meta"]["status"] = "interrupted"
            arm["meta"]["finished_at"] = now_iso()
            save_meta(arm["run_dir"], arm["meta"])
        log("中断しました")
        return 130
    finally:
        if lock_fd is not None:
            os.close(lock_fd)

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
        if s.get("over_time_limit"):
            print(f"    {TIME_LIMIT_SEC:g} s 超え {s['over_time_limit']} ケース (最大 {s['max_execution_time']:.3f} s)")
        if s.get("replay_mismatch"):
            print(f"    警告: scripts/replay.py の再生スコアがテスターと {s['replay_mismatch']} ケースで違います")
    print(f"  pahcer/ への記録 : {'した' if record else 'しない (--no-record)'}")
    refresh_report(root)
    return 0


def main() -> int:
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
    args = parser.parse_args()
    if args.compare:
        if args.solution:
            parser.error("--compare を使うときは、解法をすべて --compare の後に並べてください")
    elif not args.solution:
        parser.error("解法を指定してください")

    root = replay.main_root()
    template = tomllib.loads((root / "pahcer_config.toml").read_text())
    signal.signal(signal.SIGTERM, _raise_interrupted)
    if args.compare:
        return evaluate_compare(args, root, template)
    return evaluate(args, root, template)


if __name__ == "__main__":
    sys.exit(main())
