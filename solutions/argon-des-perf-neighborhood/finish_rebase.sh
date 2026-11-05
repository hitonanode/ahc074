#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-025319_argon-req-completefast-v3 20261106-025319_argon-des-perf-strata32-v2 --output rebase-2000.json
python3 solutions/argon-des-perf-strata32-v2/final_audit.py 20261106-025319_argon-des-perf-strata32-v2
python3 solutions/argon-des-perf-neighborhood/finalize_rebase.py
