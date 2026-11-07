"""Writes the external candidate file of legal-roll (ROLL_EXT) from same_end mode-8 results.

Each `dimp` line (a shorter sequence to another end state that shows the request) becomes
`key r k:d ...` with key = A_0 ^ rotl(A_1, 1) of the case (bit j = character j of the barcode), the key
that legal-roll computes from the input.

Usage: python ext_candidates.py OUT.txt RESULT_FILE...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def key_of(seed):
    inp = replay.load_input(seed)
    a0, a1 = inp.target[0], inp.target[1]
    return a0 ^ (((a1 << 1) | (a1 >> 63)) & ((1 << 64) - 1))


def main():
    out = Path(sys.argv[1])
    lines = []
    for path in sys.argv[2:]:
        for line in Path(path).read_text().splitlines():
            t = line.split()
            if len(t) > 5 and t[5] == "dimp":
                seed, r = int(t[0]), int(t[1])
                ops = [x for x in t[11:] if ":" in x]
                lines.append(f"{key_of(seed)} {r} {' '.join(ops)}")
    out.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} candidates written to {out}")


if __name__ == "__main__":
    main()
