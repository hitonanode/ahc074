#!/usr/bin/env python3
"""Rebuild research variants from the exact supplied eject-single-window base."""
from pathlib import Path
import argparse, hashlib, shutil, subprocess

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=Path, required=True, help='Original eject-single-window.cpp')
    ap.add_argument('--out', type=Path, default=Path('build/reconstructed'))
    ap.add_argument('--benchmark', action='store_true', help='Add an opt-in BENCH_FIXED clock hook')
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    patchdir = root / 'patches' if (root / 'patches').exists() else root
    data = args.base.read_bytes()
    expected = '8136e2455cc70038e3f7993ac1e7979d3ed2767f'
    if git_blob(data) != expected:
        raise SystemExit('Base mismatch: expected Git blob ' + expected)
    if shutil.which('patch') is None:
        raise SystemExit('The POSIX patch command is required.')
    args.out.mkdir(parents=True, exist_ok=True)
    for method in ('control', 'prior', 'permutation', 'portal'):
        destination = args.out / (method + '.cpp')
        destination.write_bytes(data)
        patches = [] if method == 'control' else ['neutral-escape-core.patch']
        if method in ('permutation', 'portal'):
            patches.append(method + '-core.patch')
        for name in patches:
            subprocess.run(['patch', '--batch', '--forward', '--silent', str(destination.resolve())],
                           input=(patchdir / name).read_bytes(), check=True)
        if args.benchmark:
            text = destination.read_text()
            marker = 'double elapsed_sec() {\n'
            if text.count(marker) != 1:
                raise SystemExit('Clock hook location is not unique.')
            text = text.replace(marker, marker + '    if(std::getenv("BENCH_FIXED"))return 0.0;\n', 1)
            destination.write_text(text)
        print(destination)

if __name__ == '__main__':
    main()
