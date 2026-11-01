#!/usr/bin/env python3
"""Synthetic I/O regression fixtures for the atomic log adapter, not solver benchmarks."""
import concurrent.futures
import hashlib
import json
import sys
import time
from pathlib import Path

import compare

HERE = Path(__file__).resolve().parent


def main():
    root = HERE / "atomic-selftest-artifacts"
    root.mkdir(exist_ok=True)
    fake = root / "fake_tester.py"
    fake.write_text("#!" + sys.executable + "\n" + '''import json,os,sys,time
spec=json.load(open(sys.argv[1]))
out=spec["stdout"].encode()
err=spec["stderr"].encode()
for p in range(0,max(len(out),len(err)),4096):
    if p<len(out): os.write(1,out[p:p+4096])
    if p<len(err): os.write(2,err[p:p+4096])
    time.sleep(0.0005)
if spec.get("timeout"):
    time.sleep(2)
else:
    os.write(2,("Score = "+str(spec["score"])+"\\n").encode())
sys.exit(spec.get("exit_code",0))
''')
    fake.chmod(0o755)
    inputs = root / "in"
    inputs.mkdir(exist_ok=True)
    (inputs / "0017.txt").write_text("synthetic protocol transport fixture\n")
    dirs = [root / "arm0", root / "arm1"]
    for d in dirs:
        (d / "out").mkdir(parents=True, exist_ok=True)
        (d / "err").mkdir(exist_ok=True)
        for stream in ["out", "err"]:
            (d / stream / "0017.txt").unlink(missing_ok=True)
    specs = [
        {"stdout": "output arm zero\n" * 13000, "stderr": "diagnostic zero\n" * 6000, "score": 123},
        {"stdout": "output arm one\n" * 17000, "stderr": "diagnostic one\n" * 6000, "score": 456},
    ]
    binaries = []
    for i, spec in enumerate(specs):
        path = root / f"spec{i}.json"
        path.write_text(json.dumps(spec))
        binaries.append(path)
    observations = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(compare.atomic_compare_case, 17, [1, 0], binaries, dirs, inputs, fake)
        while not pending.done():
            for i, d in enumerate(dirs):
                for stream, key in [("out", "stdout"), ("err", "stderr")]:
                    path = d / stream / "0017.txt"
                    expected = specs[i][key]
                    if stream == "err":
                        expected += f"Score = {specs[i]['score']}\n"
                    if path.exists():
                        assert path.read_bytes() == expected.encode(), (path, "partial final file observed")
                        observations += 1
            time.sleep(0.001)
        records = pending.result()
    assert [x["score"] for x in records] == [123, 456]
    for i, record in enumerate(records):
        for stream in ["stdout", "stderr"]:
            content = (dirs[i] / ("out" if stream == "stdout" else "err") / "0017.txt").read_bytes()
            assert len(content) == record[stream + "_bytes"]
            assert hashlib.sha256(content).hexdigest() == record[stream + "_sha256"]
    # Preserve the existing runner's handling of a zero score and timeout.
    bad = {"stdout": "partial\n", "stderr": "Your program terminated abnormally\n", "score": 0, "exit_code": 1}
    binaries[0].write_text(json.dumps(bad))
    failed = compare.atomic_compare_case(17, [0], binaries[:1], dirs[:1], inputs, fake)[0]
    assert failed["score"] == 0 and "abnormally" in failed["error_message"]
    timeout = {"stdout": "before timeout\n", "stderr": "partial stderr\n", "timeout": True}
    binaries[0].write_text(json.dumps(timeout))
    original_timeout = compare.pahcer_run.COMPARE_CASE_TIMEOUT
    try:
        compare.pahcer_run.COMPARE_CASE_TIMEOUT = 0.05
        timed = compare.atomic_compare_case(17, [0], binaries[:1], dirs[:1], inputs, fake)[0]
    finally:
        compare.pahcer_run.COMPARE_CASE_TIMEOUT = original_timeout
    assert timed["score"] == 0 and timed["error_message"].startswith("timeout")
    assert (dirs[0] / "out" / "0017.txt").read_text() == timeout["stdout"]
    summary = {"passed": True, "valid_large_log_arms": 2, "abnormal_exit_fixture": True,
               "timeout_fixture": True, "atomic_publication_observations": observations,
               "transport": "capture stdout/stderr pipes, fsync temporary files, atomic os.replace",
               "known_scores": [record["score"] for record in records]}
    (HERE / "atomic-selftest-results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
