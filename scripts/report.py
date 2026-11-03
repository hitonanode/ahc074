#!/usr/bin/env python3
"""runs/ の評価結果を、ブラウザで見比べる 1 枚の HTML (runs/report.html) にまとめる。

    scripts/report.py [--open] [--quiet]

- scripts/pahcer_run.py が評価のたびに自動で実行する。手で実行し直してもよい。
- 載せるのは、正常に終わり、手元の全ケース (pahcer_config.toml の seed 範囲) を評価した run。
  ページの「ケース」で seed 0〜499 に切り替えると、その 500 ケースを評価した run（2000 ケースが
  既定になる前の run）も並べ、全ケースの run とはその 500 ケースで比べる（EXTRA_SCOPES）。
  どの範囲も評価し終えていない run（--seeds で一部だけを評価したもの）は対象外になる
  （ページの「載せていない run」に出る）。
- 画面の本体は scripts/report_template.html。このスクリプトは、そこへスコア・E・T などを埋め込む。
  ケースごとの E と T は runs/<run-id>/metrics.json（なければここで計算して作る）から読む。
- 出力を読み込んだビジュアライザを並べて見るには、scripts/serve_report.py で HTTP で開く
  （file:// で開くと、公式ビジュアライザへのリンクだけになる）。
- 同時に複数が実行されても、runs/.report.lock で 1 つずつ作り直す。
"""

import argparse
import datetime
import fcntl
import json
import os
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "report_template.html"
DATA_PLACEHOLDER = "/*REPORT_DATA*/"
VISUALIZER_URL = "https://img.atcoder.jp/ahc074/YAAu43G9.html"
# Same-origin copy of the official visualizer, relative to runs/ (made by scripts/serve_report.py).
MIRROR_URL = ".vis/YAAu43G9/YAAu43G9.html"

# Seed ranges the page can also compare on, besides all the local cases: the 500 cases that were
# the local set until 2026-11-01. A run is listed in every range that it evaluated completely.
EXTRA_SCOPES = [range(0, 500)]

QUIET = False


def log(msg: str) -> None:
    if not QUIET:
        print(f"[report] {msg}", flush=True)


def write_atomic(path: Path, text: str) -> None:
    """Replaces the file in one step, so that a browser never loads a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def collect_runs(scopes: list[range]) -> tuple[list[dict], list[dict]]:
    """Returns the entries of the runs to show, newest first, and the runs left out with the reason.

    The per-case arrays of an entry cover the first (widest) range of scopes that the run evaluated
    completely, given as its "seeds"; the page slices them to a narrower range.
    """
    shown, skipped = [], []
    for d in sorted(replay.runs_dir().iterdir(), reverse=True):
        if not d.is_dir() or d.name.startswith(".") or not (d / "meta.json").exists():
            continue
        try:
            meta = json.loads((d / "meta.json").read_text())
            status = meta.get("status")
            if status != "ok" or not (d / "result.json").exists():
                if status not in ("running", "waiting", "compiling"):
                    skipped.append({"id": d.name, "reason": f"正常に終わっていない (status: {status})"})
                continue
            cases = replay.run_cases(d)
        except (OSError, ValueError, KeyError) as e:  # e.g. a file that is being written right now
            skipped.append({"id": d.name, "reason": f"記録を読めない ({type(e).__name__})"})
            continue
        seeds = next((r for r in scopes if all(s in cases for s in r)), None)
        if seeds is None:
            full = scopes[0]
            missing = sum(s not in cases for s in full)
            skipped.append({"id": d.name, "reason": f"seed {full.start}〜{full.stop - 1} のうち {missing} 個が"
                                                    f"未評価 (評価済み {len(cases)} ケース)"})
            continue
        try:
            metrics = replay.run_metrics(d)
        except Exception as e:  # keep the page usable; E and T are shown as missing
            log(f"{d.name} の指標を計算できません: {type(e).__name__}: {e}")
            metrics = {}
        git = (meta.get("source") or {}).get("git") or {}
        shown.append({
            "id": d.name,
            "seeds": [seeds.start, seeds.stop],
            "comment": meta.get("comment") or "",
            "record": meta.get("record", True),
            "source": f"{meta.get('source', {}).get('path', '')} @ {git.get('commit', '')[:8]}"
                      + (" (dirty)" if git.get("dirty") else ""),
            "scores": [cases[s]["score"] for s in seeds],  # 0 means WA
            "E": [metrics[s]["E"] if s in metrics else None for s in seeds],
            "T": [metrics[s]["T"] if s in metrics else None for s in seeds],
            "times": [round(cases[s]["execution_time"], 3) for s in seeds],
            "errors": [cases[s].get("error_message") or (metrics.get(s) or {}).get("error") or "" for s in seeds],
            "max_time": round(max(cases[s]["execution_time"] for s in seeds), 3),
        })
    return shown, skipped


def build(open_browser: bool) -> int:
    seeds = replay.all_seeds()
    # Widest first; every extra range lies inside all the local cases, so that a slice of an entry covers it.
    scopes = [seeds] + [r for r in EXTRA_SCOPES if r != seeds and seeds.start <= r.start and r.stop <= seeds.stop]
    shown, skipped = collect_runs(scopes)
    generated_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    data = {
        "generated_at": generated_at,
        "scopes": [[r.start, r.stop] for r in scopes],  # the first is all the local cases
        "visualizer_url": VISUALIZER_URL,
        "mirror_url": MIRROR_URL,
        "runs": shown,
        "skipped": skipped,
    }
    # "<" is escaped so that no text (e.g. a comment containing "</script>") can end the <script>.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    template = TEMPLATE.read_text()
    if template.count(DATA_PLACEHOLDER) != 1:
        sys.exit(f"[report] {TEMPLATE} に {DATA_PLACEHOLDER} がちょうど 1 つ必要です")
    out = replay.runs_dir() / "report.html"
    write_atomic(out, template.replace(DATA_PLACEHOLDER, payload))
    # The page polls this file (when served) to notice that it was rebuilt.
    write_atomic(replay.runs_dir() / "report_stamp.txt", generated_at + "\n")
    counts = "、".join(f"seed {r.start}〜{r.stop - 1}: {sum(e['seeds'][0] <= r.start and r.stop <= e['seeds'][1] for e in shown)} run"
                      for r in scopes)
    log(f"{len(shown)} run を載せました ({counts})。対象外 {len(skipped)} run")
    log(str(out))
    if open_browser:
        webbrowser.open(out.as_uri())
    return 0


def main() -> int:
    global QUIET
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--open", action="store_true", help="作った HTML をブラウザで開く")
    parser.add_argument("--quiet", action="store_true", help="ログを出さない")
    args = parser.parse_args()
    QUIET = args.quiet
    try:
        os.nice(10)  # leave the CPU to evaluations running at the same time
    except OSError:
        pass
    replay.runs_dir().mkdir(exist_ok=True)
    fd = os.open(replay.runs_dir() / ".report.lock", os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        return build(args.open)
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
