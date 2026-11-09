#!/usr/bin/env python3
"""Reconstruct the experiment sources without modifying any tracked solver."""
from __future__ import annotations
import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE_SHA256 = "5f58f1c24f8a643c589124bad0b93d29c35d029a2c7d6ca9f2964726ff7b4bdd"
HISTORICAL_SHA256 = "ffe3afdb636114b52eeaf4bf5ed399d95ebdb2c5e63e45d2a4cdb62ff58e9df1"
ROOT = Path(__file__).resolve().parent


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence: {old!r}")
    return text.replace(old, new, 1)


def fixed_work(text: str) -> str:
    text = replace_once(text, "double elapsed_sec() {\n",
                        'double elapsed_sec() {\n    if(std::getenv("BENCH_FIXED"))return 0.0;\n')
    return replace_once(text, "        if (t_req > kFastAfter) solver.fast_mode = true;",
                        "        // Research: do not change policy midway through a sample.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT.parents[1] / "solutions/eject-single-window/main.cpp")
    parser.add_argument("--out", type=Path, required=True, help="New output directory; must not exist")
    parser.add_argument("--fixed-work", action="store_true", help="Recreate the archived benchmark sources; NOT for submission")
    args = parser.parse_args()
    raw = args.base.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA256:
        parser.error("Baseline differs from the archived eject-single-window source; do not apply blindly.")
    if args.out.exists():
        parser.error("Output directory already exists; choose a new directory.")
    if not shutil.which("patch"):
        parser.error("The patch executable is required.")
    control = raw.decode("utf-8")
    with tempfile.TemporaryDirectory(prefix="ahc074-neutral-") as directory:
        candidate = Path(directory) / "candidate.cpp"
        candidate.write_bytes(raw)
        subprocess.run(["patch", "--batch", "--fuzz=0", str(candidate), str(ROOT / "neutral-escape-core.patch")], check=True)
        neutral = candidate.read_text()
    if args.fixed_work:
        control = fixed_work(control)
        neutral = fixed_work(neutral)
        # Restore historical environment-default behavior, then use explicit 2/4 when running.
        neutral = replace_once(neutral,
            'neutral_width=std::getenv("NEUTRAL_WIDTH")?std::max(1,env_int("NEUTRAL_WIDTH")):4;',
            'neutral_width=std::max(1,env_int("NEUTRAL_WIDTH"));')
        neutral = replace_once(neutral,
            'int mode=std::getenv("NEUTRAL_DEPTH")?env_int("NEUTRAL_DEPTH"):2;',
            'int mode=std::getenv("NEUTRAL_DEPTH")?env_int("NEUTRAL_DEPTH"):1;')
        if hashlib.sha256(neutral.encode()).hexdigest() != HISTORICAL_SHA256:
            raise ValueError("Reconstructed source differs from the archived research source")
    args.out.mkdir(parents=True)
    for name, text in [("control.cpp", control), ("neutral_escape.cpp", neutral)]:
        destination = args.out / name
        destination.write_text(text)
        print(destination, hashlib.sha256(text.encode()).hexdigest())
    print("Research only: two-second compliance has NOT been established.")


if __name__ == "__main__":
    main()
