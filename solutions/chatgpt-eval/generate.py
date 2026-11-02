#!/usr/bin/env python3
"""Generate fresh AHC074-distributed cases, distinct from the official ChaCha seed mapping."""
import argparse
import hashlib
import json
import platform
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, default=74020261102)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("count must be positive")
    files = [args.out / f"{i:04d}.txt" for i in range(args.start, args.start + args.count)]
    if any(p.exists() for p in files):
        raise SystemExit("Refusing to overwrite existing input files")
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for i, path in enumerate(files):
        seed = args.seed + i
        rng = random.Random(seed)
        patterns = []
        seen = set()
        while len(patterns) < 256:
            ones = set(rng.sample(range(64), 32))
            pattern = "".join("1" if j in ones else "0" for j in range(64))
            if pattern not in seen:
                seen.add(pattern)
                patterns.append(pattern)
        requests = [rng.randrange(256)]
        for _ in range(1023):
            request = rng.randrange(255)
            requests.append(request + (request >= requests[-1]))
        text = "64 192 256 1024\n" + "\n".join(patterns) + "\n" + "\n".join(map(str, requests)) + "\n"
        path.write_text(text)
        records.append({"case_id": args.start + i, "python_seed": seed,
                        "sha256": hashlib.sha256(text.encode()).hexdigest()})
    manifest = args.out / f"manifest-{args.start}-{args.start + args.count}.json"
    manifest.write_text(json.dumps({"generator": "Python random.Random / random.sample; not official ChaCha seed mapping",
                                    "python_version": platform.python_version(),
                                    "script": "solutions/chatgpt-eval/generate.py",
                                    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                    "start": args.start, "count": args.count, "seed": args.seed,
                                    "cases": records}, indent=2) + "\n")
    print(f"Generated {len(files)} fresh cases; manifest: {manifest}")


if __name__ == "__main__":
    main()
