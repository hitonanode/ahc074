"""Writes the comparison variants of solutions/legal-roll (a copy of main.cpp with other #define defaults and a
short README.md each). Usage: python make_variants.py NAME KEY=VALUE... -- "README difference text"
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    name = sys.argv[1]
    args = sys.argv[2:]
    sep = args.index("--")
    defs = dict(a.split("=") for a in args[:sep])
    text = " ".join(args[sep + 1:])
    src = (HERE / "main.cpp").read_text()
    for k, v in defs.items():
        pat = re.compile(r"(#define %s )(\S+)" % k)
        assert len(pat.findall(src)) == 1, k
        src = pat.sub(lambda m: m.group(1) + v, src)
    out = HERE.parent / name
    os.makedirs(out, exist_ok=True)
    (out / "main.cpp").write_text(src)
    (out / "README.md").write_text(
        f"# {name}（段階 2 の研究版。提出用ではない）\n\n改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: "
        f"{text}。仕組みと指標は solutions/legal-roll/README.md。\n")
    print(out, defs)


if __name__ == "__main__":
    main()
