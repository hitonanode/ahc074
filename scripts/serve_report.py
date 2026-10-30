#!/usr/bin/env python3
"""ダッシュボード (runs/report.html) を HTTP で配信する（人間用）。

    scripts/serve_report.py [--port 8074] [--host 127.0.0.1]

- runs/ を配信し、http://localhost:<port>/report.html を開くと、ケースをクリックしたときに
  その出力を読み込んだ公式ビジュアライザが並ぶ（file:// で開いたページからは出力を読めないため）。
- 公式ビジュアライザ（HTML・JS・wasm）は、初回に runs/.vis/ へ取ってきて、同じオリジンから配る。
  ページから出力を流し込めるのは、同じオリジンのコピーだけ（公式のページは別オリジンで、
  出力を URL で渡すには長すぎる）。
- WSL で動かしたときも、Windows のブラウザから http://localhost:<port>/report.html で開ける。
- ページはキャッシュさせない。評価が終わると report.html が作り直され、開いているページに
  「更新があります」のボタンが出る。
"""

import argparse
import functools
import http.server
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402

VIS_BASE = "https://img.atcoder.jp/ahc074/"
VIS_NAME = "YAAu43G9"
VIS_FILES = [f"{VIS_NAME}.html", f"{VIS_NAME}.js", f"{VIS_NAME}_bg.wasm", "gif.js", "gif.worker.js", "jszip.min.js"]


def ensure_mirror() -> Path:
    """Downloads the official visualizer into runs/.vis/<name>/ if it is not there yet."""
    dest = replay.runs_dir() / ".vis" / VIS_NAME
    dest.mkdir(parents=True, exist_ok=True)
    for name in VIS_FILES:
        path = dest / name
        if path.exists() and path.stat().st_size > 0:
            continue
        print(f"[serve_report] 公式ビジュアライザを取得しています: {VIS_BASE}{name}", flush=True)
        with urllib.request.urlopen(VIS_BASE + name, timeout=60) as res:
            data = res.read()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return dest


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".js": "text/javascript"}

    def end_headers(self):
        # Always revalidate, so that a reload shows the rebuilt report and fresh outputs.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):  # keep the terminal quiet; errors still show
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8074)
    parser.add_argument("--host", default="127.0.0.1", help="待ち受けるアドレス（既定は自分のマシンからだけ）")
    args = parser.parse_args()
    runs = replay.runs_dir()
    runs.mkdir(exist_ok=True)
    try:
        ensure_mirror()
    except OSError as e:
        print(f"[serve_report] 公式ビジュアライザを取得できません ({e})。表は見られますが、"
              "ビジュアライザは表示できません", file=sys.stderr)
    if not (runs / "report.html").exists():
        print("[serve_report] runs/report.html がありません。scripts/report.py で作ってください", file=sys.stderr)
    handler = functools.partial(Handler, directory=str(runs))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"[serve_report] http://localhost:{args.port}/report.html を開いてください (Ctrl-C で終了)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
