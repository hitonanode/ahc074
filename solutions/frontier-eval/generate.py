#!/usr/bin/env python3
"""Independent seeds with the official probability distribution, not Rust seed parity."""
import argparse
import hashlib
import json
import random
from pathlib import Path


def generate(seed):
    rng = random.Random(seed)
    barcodes = []
    seen = set()
    while len(barcodes) < 256:
        ones = set(rng.sample(range(64), 32))
        pattern = "".join("1" if i in ones else "0" for i in range(64))
        if pattern not in seen:
            seen.add(pattern)
            barcodes.append(pattern)
    requests = [rng.randrange(256)]
    for _ in range(1023):
        x = rng.randrange(255)
        requests.append(x + (x >= requests[-1]))
    return "64 192 256 1024\n" + "\n".join(barcodes) + "\n" + "\n".join(map(str, requests)) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=5000)
    parser.add_argument("--count", type=int, default=128)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    dest = root / "tools" / "in"
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in range(args.start, args.start + args.count):
        text = generate(seed)
        path = dest / f"{seed:04d}.txt"
        if path.exists() and path.read_text() != text:
            raise SystemExit(f"Refusing to replace a different input: {path}")
        path.write_text(text)
        rows.append({"seed": seed, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    manifest = {"generator": "Python random.Random(seed), uniform 32-of-64 sample; consecutive requests differ",
                "official_seed_parity": False, "cases": rows}
    out = Path(__file__).parent / f"generated-{args.start}-{args.start + args.count}.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(rows)} independent-distribution cases: {args.start}..{args.start + args.count - 1}")


if __name__ == "__main__":
    main()
