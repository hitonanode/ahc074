#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-030225_argon-req-completefast-v3 20261106-030615_argon-des-perf-strata32-v2 20261106-030615_argon-des-perf-stratafast --output fast-500.json
python3 solutions/argon-des-perf-neighborhood/identity.py 20261106-030615_argon-des-perf-strata32-v2 20261106-030615_argon-des-perf-stratafast --end 500 --output fast-identity500.json
