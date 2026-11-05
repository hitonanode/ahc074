#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-032942_argon-req-completefast-v3 20261106-032942_argon-des-perf-strata24 20261106-032942_argon-des-perf-stratacut --output final-options2000.json
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-032001_argon-req-completefast-v3 20261106-032053_argon-des-perf-strata16 20261106-032053_argon-des-perf-strata24 --output smaller-500.json
python3 solutions/argon-des-perf-neighborhood/identity.py 20261106-025319_argon-des-perf-strata32-v2 20261106-032942_argon-des-perf-stratacut --end 2000 --output cut-identity2000.json
python3 solutions/argon-des-perf-stratacut/final_audit.py 20261106-032942_argon-des-perf-stratacut
python3 solutions/argon-des-perf-strata24/final_audit.py 20261106-032942_argon-des-perf-strata24
