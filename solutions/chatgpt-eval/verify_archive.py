#!/usr/bin/env python3
"""Independently verify an authoritative PIPE archive in a fresh process."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--check-materialized", action="store_true")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    raw = args.archive.read_bytes()
    archive_hash = hashlib.sha256(raw).hexdigest()
    if args.expected_sha256 and archive_hash != args.expected_sha256:
        raise SystemExit("Archive SHA-256 mismatch")
    evidence = json.loads(gzip.decompress(raw))
    if evidence["format"] != "ahc074-pipe-capture-v1":
        raise SystemExit("Unknown archive format")
    inputs = {}
    for seed, entry in evidence["inputs"].items():
        data = base64.b64decode(entry["base64"], validate=True)
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], (seed, "input hash")
        inputs[int(seed)] = (replay.parse_input(data.decode()), entry["sha256"])
    seen = set()
    runs = {}
    for entry in evidence["entries"]:
        run_id, record = entry["run_id"], entry["record"]
        seed = record["seed"]
        assert Path(run_id).name == run_id and run_id not in (".", ".."), "unsafe run id"
        assert (run_id, seed) not in seen, "duplicate capture"
        seen.add((run_id, seed))
        stdout = base64.b64decode(entry["stdout_base64"], validate=True)
        stderr = base64.b64decode(entry["stderr_base64"], validate=True)
        for channel, data, folder in (("stdout",stdout,"out"),("stderr",stderr,"err")):
            assert hashlib.sha256(data).hexdigest() == record[channel+"_sha256"], (run_id,seed,channel,"hash")
            assert len(data) == record[channel+"_bytes"], (run_id,seed,channel,"size")
            if args.check_materialized:
                path = ROOT / "runs" / run_id / folder / f"{seed:04d}.txt"
                assert path.read_bytes() == data, (run_id,seed,channel,"materialized bytes differ")
        inp, input_hash = inputs[seed]
        assert input_hash == record["input_sha256"]
        parsed = replay.parse_output(inp,stdout.decode())
        rep = replay.replay(inp,parsed,check=True)
        if record["score"] > 0:
            assert rep.error is None and rep.score == record["score"], (run_id,seed,rep.error,rep.score,record["score"])
            design = ("\n".join(p.pattern for p in parsed.designs)+"\n").encode()
            if "paper_design_sha256" in record:
                assert hashlib.sha256(design).hexdigest() == record["paper_design_sha256"]
        result = runs.setdefault(run_id,{"cases":0,"WA":0,"score_sum":0,"E_sum":0,"T_sum":0,"case_records":[]})
        result["cases"] += 1
        result["WA"] += int(record["score"] == 0)
        result["score_sum"] += record["score"]
        result["E_sum"] += rep.game.mistakes
        result["T_sum"] += rep.game.moves
        result["case_records"].append({"seed":seed,"score":record["score"],"E":rep.game.mistakes,"T":rep.game.moves,
                                       "paper_design_sha256":record.get("paper_design_sha256")})
    for name,result in runs.items():
        result["mean_score"] = result["score_sum"] / result["cases"]
        result["mean_E"] = result["E_sum"] / result["cases"]
        result["mean_T"] = result["T_sum"] / result["cases"]
        print(f"{name}: {result['cases']} captures verified; WA={result['WA']}; mean score={result['mean_score']:.4f}; mean E={result['mean_E']:.4f}; mean T={result['mean_T']:.4f}")
    report = {"archive":str(args.archive),"sha256":archive_hash,"verified_captures":len(seen),
              "materialized_checked":args.check_materialized,"environment":evidence.get("environment",{}),"runs":runs}
    if args.summary:
        args.summary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"PASS: {len(seen)} authoritative captures; archive SHA-256={archive_hash}")


if __name__ == "__main__":
    main()
