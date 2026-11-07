#!/bin/sh
set -eu
D=solutions/deval-speed
for compiler in g++ clang++; do
 "$compiler" -std=c++23 -O2 "$D/recip_unit.cpp" -o "$D/recip-unit"
 "$D/recip-unit"
done
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python "$D/make_recip.py"
