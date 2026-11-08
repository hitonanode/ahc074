"""Exercise the already built ASan/UBSan production-path review binary at efforts 1..5."""
import os
from pathlib import Path
import subprocess

here = Path(__file__).resolve().parent
root = here.parents[1]
for level in range(1, 6):
    begin = 170 + (level - 1) * 10
    env = dict(os.environ, REVIEW_FORCE=str(level), REVIEW_CHECK="1",
               ASAN_OPTIONS="detect_leaks=0")
    with (here / f"effort{level}.log").open("w") as out:
        subprocess.run([
            "nice", "-n", "10", "python3", "scripts/pahcer_run.py", "--extend",
            "20261109-025517_review-astra1", "--seeds", f"{begin}-{begin + 10}",
            "-c", f"Astra review: ASan/UBSan and state checks, forced effort {level}; inherited no-record"
        ], cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
