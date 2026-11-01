#!/usr/bin/env python3
"""Same problem distribution, deliberately distinct from official ChaCha seeds."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=100000)
    p.add_argument("--count", type=int, default=64)
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument("--out", type=Path, default=HERE.parents[1] / "tools" / "in")
    p.add_argument("--manifest", type=Path, default=HERE / "generated_manifest.json")
    args = p.parse_args()
    if args.start < 0 or args.count < 1: p.error("start >= 0 and count >= 1 required")
    paths = [args.out / f"{index:04d}.txt" for index in range(args.start, args.start + args.count)]
    if any(path.exists() for path in paths): p.error("Refusing to overwrite an existing case")
    args.out.mkdir(parents=True, exist_ok=True)
    files = []
    for index, path in zip(range(args.start, args.start + args.count), paths):
        seed = args.base_seed + index
        rng = random.Random(seed)
        designs, seen = [], set()
        while len(designs) < 256:
            ones = set(rng.sample(range(64), 32))
            s = "".join("1" if j in ones else "0" for j in range(64))
            if s not in seen: seen.add(s); designs.append(s)
        requests = [rng.randrange(256)]
        for _ in range(1023):
            x = rng.randrange(255)
            requests.append(x + (x >= requests[-1]))
        text = "64 192 256 1024\n" + "\n".join(designs + list(map(str, requests))) + "\n"
        path.write_text(text)
        files.append({"file_index": index, "generator_seed": seed, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    manifest = {"generator": "Python random.Random (MT19937), random.sample(range(64), 32)",
                "official_seed_compatible": False, "base_seed": args.base_seed, "files": files}
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(files)} fresh cases; manifest: {args.manifest}")

if __name__ == "__main__": main()
