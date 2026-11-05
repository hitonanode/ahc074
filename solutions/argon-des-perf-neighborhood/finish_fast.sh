#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-030225_argon-req-completefast-v3 20261106-030615_argon-des-perf-stratafast --output fast-2000.json
python3 solutions/argon-des-perf-neighborhood/identity.py 20261106-025319_argon-des-perf-strata32-v2 20261106-030615_argon-des-perf-stratafast --end 2000 --output fast-identity2000.json
python3 solutions/argon-des-perf-stratafast/final_audit.py 20261106-030615_argon-des-perf-stratafast
python3 solutions/argon-des-perf-neighborhood/finalize_fast.py
