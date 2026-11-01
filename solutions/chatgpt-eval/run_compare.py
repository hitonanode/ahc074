#!/usr/bin/env python3
"""Run the repository evaluator with an explicitly identified C++ tester port."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime
import hashlib
import importlib.util
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def build_tester(_root: Path) -> Path:
    source = HERE / "tester.cpp"
    binary = HERE / "build" / "tester"
    binary.parent.mkdir(exist_ok=True)
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(["g++", "-std=c++23", "-O2", "-Wall", "-Wextra", str(source), "-o", str(binary)], check=True)
    return binary

def smoke_single(module, args, root: Path, template: dict, threads: int) -> int:
    """Compose existing evaluator functions for a recorded single-solver smoke.

    The repository's normal single-solver entry point requires pahcer, whereas
    its compare_case/recording primitives do not. Smoke runs only write runs/.
    """
    if not args.no_record:
        raise SystemExit("Single-solver smoke requires --no-record")
    seeds = module.seed_range(args, template)
    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)
    arm = module.prepare_run(args.solution, runs_dir,
        args.comment + f" [single smoke; tester={module.tester_label}]", seeds, False, root / "pahcer")
    print("run-id:", arm["run_id"], flush=True)
    if not module.compile_solution(arm["compile_cmd"], arm["run_dir"], arm["src_root"]): return 1
    tester = module.ensure_tester(root)
    lock_fd = module.acquire_lock(runs_dir / ".lock", arm["run_id"])
    try:
        arm["meta"]["status"] = "running"
        arm["meta"]["started_at"] = module.now_iso()
        module.save_meta(arm["run_dir"], arm["meta"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            results = list(pool.map(lambda seed: module.compare_case(seed,[0],[arm["binary"]],
                [arm["run_dir"]],root/"tools"/"in",tester)[0],range(*seeds)))
        for case in results: case["relative_score"] = 100.0 if case["score"] > 0 else 0.0
        result = module.compare_result(results,arm["meta"]["comment"],
            datetime.datetime.now().astimezone().isoformat())
        module.replay.write_json_atomic(arm["run_dir"]/"result.json",result,indent=2)
        metrics = module.compute_metrics(arm["run_dir"])
        summary = module.summarize(result,metrics)
        arm["meta"].update(status="ok",finished_at=module.now_iso(),summary=summary,out_dir=None)
        module.save_meta(arm["run_dir"],arm["meta"])
        module.print_summary(arm["run_id"],arm["run_dir"],summary,False)
    finally: os.close(lock_fd)
    module.refresh_report(root)
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--official-tester", action="store_true")
    options, rest = parser.parse_known_args()
    if options.threads < 1: parser.error("--threads must be positive")
    spec = importlib.util.spec_from_file_location("ahc074_pahcer_run", ROOT / "scripts" / "pahcer_run.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    module.tester_label = "official Rust" if options.official_tester else "C++ port"
    if not options.official_tester:
        module.ensure_tester = build_tester
    if any(flag in rest for flag in ("-h","--help")):
        print("Wrapper options: --threads N (default 4); --official-tester (use/build the original Rust tester).")
    original_prepare_run = module.prepare_run
    def evaluation_context():
        source_root = module.replay.main_root() if options.official_tester else ROOT
        source_paths = ([source_root/"tools"/"src"/"lib.rs",source_root/"tools"/"src"/"bin"/"tester.rs"]
                        if options.official_tester else [HERE/"tester.cpp"])
        return {
            "tester": "tools/target/release/tester" if options.official_tester else "solutions/chatgpt-eval/tester.cpp",
            "tester_kind": module.tester_label,
            "tester_sources_sha256": {str(p.relative_to(source_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
            "log_capture": "stdout/stderr captured until exit; complete files published atomically",
            "threads": options.threads,
            "explicit_parameters": {k:os.environ[k] for k in ("ALIAS_LIMIT","GATE_COUNT","GATE_ARITY","GATE_FULL","GATE_PASSES","MAP_ITERS","GOPT_STEPS","ANNEAL_ITERS","CLIMB_ITERS") if k in os.environ},
        }
    def prepare_run_with_context(*a, **kw):
        arm = original_prepare_run(*a, **kw)
        arm["meta"]["evaluation_adapter"] = evaluation_context()
        arm["meta"]["evaluation_adapter_scope"] = "initial run; each extension records its own adapter"
        module.save_meta(arm["run_dir"],arm["meta"])
        return arm
    module.prepare_run = prepare_run_with_context
    def atomic_bytes(path, contents):
        temporary = path.with_name(path.name + ".complete.tmp")
        with temporary.open("wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    def captured_compare_case(seed, order, binaries, run_dirs, in_dir, tester):
        # Capture both streams until the tester exits, then publish whole files
        # atomically. The workspace occasionally exposed/reverted partial files
        # while children wrote directly to them; completed byte strings avoid
        # using such a partially saved transcript as a validation record.
        infile = in_dir / f"{seed:04d}.txt"
        records = [{} for _ in binaries]
        for index in order:
            error = ""
            began = time.perf_counter()
            with infile.open("rb") as source:
                process = subprocess.Popen([str(tester),str(binaries[index])],stdin=source,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                try:
                    stdout,stderr = process.communicate(timeout=module.COMPARE_CASE_TIMEOUT)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL)
                    stdout,stderr = process.communicate()
                    error = f"timeout ({module.COMPARE_CASE_TIMEOUT:.0f} s)"
            elapsed = time.perf_counter() - began
            atomic_bytes(run_dirs[index]/"out"/f"{seed:04d}.txt",stdout)
            atomic_bytes(run_dirs[index]/"err"/f"{seed:04d}.txt",stderr)
            err_text = stderr.decode(errors="replace")
            scores = module.SCORE_LINE.findall(err_text)
            score = int(scores[-1]) if scores and not error else 0
            if not error and score == 0: error = module.judge_message(err_text)
            records[index] = {"seed":seed,"score":score,"relative_score":0.0,
                "execution_time":elapsed,"error_message":error,
                "stdout_sha256":hashlib.sha256(stdout).hexdigest(),
                "stderr_sha256":hashlib.sha256(stderr).hexdigest()}
        return records
    module.compare_case = captured_compare_case
    original_seed_range = module.seed_range
    def extended_seed_range(args, template):
        # Generated holdout cases use file ids >= 100000, leaving all official
        # 0..1999 inputs intact in a complete checkout. Only an explicit range
        # of already existing inputs can extend the repository's bounds.
        if args.seeds and (match := re.fullmatch(r"(\d+)-(\d+)",args.seeds)):
            lo, hi = map(int,match.groups())
            if lo >= 100000 and lo < hi:
                missing = [s for s in range(lo,hi) if not (module.replay.main_root()/"tools"/"in"/f"{s:04d}.txt").exists()]
                if missing: raise SystemExit(f"Missing generated input: {missing[0]}")
                template = {**template,"test":{**template["test"],"end_seed":max(hi,template["test"]["end_seed"])}}
        return original_seed_range(args,template)
    module.seed_range = extended_seed_range
    module.evaluate = lambda args, root, template: smoke_single(module,args,root,template,options.threads)
    for name in ("evaluate_compare", "evaluate_extend"):
        original = getattr(module, name)
        def invoke(args, root, template, original=original, operation=name):
            template["test"]["threads"] = options.threads
            note = f" [tester={module.tester_label}; generated file ids >=100000 equal MT19937 seeds]"
            args.comment += note
            previous_extensions = {}
            if operation == "evaluate_extend":
                for argument in args.extend:
                    try:
                        run = module.replay.resolve_run(argument)
                        meta = module.json.loads((run/"meta.json").read_text())
                        previous_extensions[run.name] = len(meta.get("extensions",[]))
                    except LookupError:
                        pass  # The original evaluator reports the invalid run.
            result = original(args, root, template)
            if operation == "evaluate_extend" and result == 0:
                # Preserve the original tester identity when an existing run
                # is extended using a different explicitly selected tester.
                for argument in args.extend:
                    run = module.replay.resolve_run(argument)
                    meta = module.json.loads((run/"meta.json").read_text())
                    if len(meta.get("extensions",[])) > previous_extensions.get(run.name,0):
                        meta["extensions"][-1]["evaluation_adapter"] = evaluation_context()
                        meta["evaluation_adapter_scope"] = "initial run; each extension records its own adapter"
                        module.save_meta(run,meta)
            return result
        setattr(module, name, invoke)
    sys.argv = [str(ROOT / "scripts" / "pahcer_run.py"), *rest]
    return module.main()

if __name__ == "__main__":
    raise SystemExit(main())
