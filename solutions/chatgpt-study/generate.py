#!/usr/bin/env python3
"""Generate same-distribution, explicitly non-official AHC074 input cases."""
import argparse
import fcntl
import hashlib
import json
import os
import random
from pathlib import Path

GENERATOR = "python-mt19937-uniform-v1"
SEED_OFFSET = 20_261_102


def case_text(index: int) -> str:
    rng = random.Random(SEED_OFFSET + index)
    patterns = []
    seen = set()
    while len(patterns) < 256:
        black = set(rng.sample(range(64), 32))
        pattern = "".join("1" if j in black else "0" for j in range(64))
        if pattern not in seen:
            seen.add(pattern)
            patterns.append(pattern)
    requests = [rng.randrange(256)]
    for _ in range(1023):
        x = rng.randrange(255)
        requests.append(x + (x >= requests[-1]))
    return "64 192 256 1024\n" + "\n".join(patterns) + "\n" + "\n".join(map(str, requests)) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "tools" / "in")
    args = parser.parse_args()
    if not 1 <= args.count <= 2000:
        parser.error("count must be in 1..2000")
    args.out.mkdir(parents=True, exist_ok=True)
    # Serialize generation so two background invocations cannot interleave
    # their input files and final manifests. Existing equal files need no write.
    with (args.out / ".chatgpt-generation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = []
        for index in range(args.count):
            content = case_text(index).encode("ascii")
            path = args.out / f"{index:04d}.txt"
            if path.exists():
                if path.read_bytes() != content:
                    raise SystemExit(f"Refusing to replace existing different input: {path}")
            else:
                path.write_bytes(content)
            records.append({"index": index, "rng_seed": SEED_OFFSET + index,
                            "sha256": hashlib.sha256(content).hexdigest()})
        manifest = {"generator": GENERATOR, "seed_offset": SEED_OFFSET, "count": args.count,
                    "official_rust_seeds": False, "cases": records}
        path = args.out / "chatgpt_manifest.json"
        temporary = path.with_name(f".chatgpt_manifest.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(temporary, path)
    print(f"Generated {args.count} {GENERATOR} cases in {args.out}")


if __name__ == "__main__":
    main()
