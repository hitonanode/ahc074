#!/usr/bin/env bash
# Run from repository root. Research compute is intentionally not limited to 2 seconds.
set -euo pipefail
D=solutions/joint-pairing
B="$PWD/$D/build"
O="${1:-$PWD/runs/joint-designs}"
mkdir -p "$B" tools/target/release
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -m pip install numpy==2.3.5 scipy==1.17.0
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 "$D/main.cpp" -o "$B/driver"
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 -fPIC -shared "$D/engine.cpp" -o "$B/libjoint.so"
# Official tester preferred. tester.cpp is the cross-checked C++ port for environments without Rust.
(cd tools && cargo build --release --bin tester)
python "$D/generate.py" --start 6001 --count 32
python "$D/prepare.py" --seeds 6001-6033 --out "$O" --driver "$B/driver" --lib "$B/libjoint.so" --threads 4
for s in $(seq 6001 6032); do cp "$O/$s/base.design" "$O/$s/legacy.design"; done
arms=(base.design legacy.design pair-only.final)
for i in $(seq 0 7); do arms+=("linear-$i.final"); done
for i in $(seq 0 3); do arms+=("nonlinear-$i.final"); done
arms+=(linear-selected.final mixed-selected.final union-selected.final)
python "$D/evaluate.py" --designs "$O" --seeds 6001-6033 --arms "${arms[@]}"
python "$D/extra_orders.py"
python "$D/evaluate.py" --designs "$O" --seeds 6200-6424 --mapping "$D/extra-order-map.json" --arms base.design linear-selected.final mixed-selected.final
for s in $(seq 6001 6008); do
  python "$D/anneal.py" "$O/$s/base.design" --out "$O/$s/deep" --lib "$B/libjoint.so" --steps 3000 --seed 3911707
  for arm in deep-two deep-all deep-forced-four; do
    head -n 257 "tools/in/$s.txt" | JOINT_STAGE=refit JOINT_INPUT="$O/$s/deep/$arm.design" JOINT_MATCH="$O/$s/deep/$arm.match" JOINT_OUTPUT="$O/$s/$arm.final" "$B/driver"
  done
done
python "$D/evaluate.py" --designs "$O" --seeds 6001-6009 --arms base.design deep-two.final deep-all.final deep-forced-four.final
python "$D/test_oracle.py" "$O/6001/base.design" --lib "$B/libjoint.so" --out "$O/oracle-check.json"
python "$D/verify_runs.py" --designs "$O" --out "$O/verification.json"
python "$D/recompute.py"
