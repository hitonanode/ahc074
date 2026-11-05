#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-032336_argon-req-completefast-v3 20261106-032336_argon-des-perf-strata32-v2 20261106-032336_argon-des-perf-stratacut --output cut-500.json
python3 solutions/argon-des-perf-neighborhood/identity.py 20261106-032336_argon-des-perf-strata32-v2 20261106-032336_argon-des-perf-stratacut --end 500 --output cut-identity500.json
