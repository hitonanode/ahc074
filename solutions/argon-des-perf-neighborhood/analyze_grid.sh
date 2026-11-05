#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-021800_argon-des-perf-gaincache 20261106-021800_argon-des-perf-w65 20261106-021800_argon-des-perf-w75 20261106-021800_argon-des-perf-s32c70 20261106-021800_argon-des-perf-s32c75 20261106-021800_argon-des-perf-strata70 20261106-021800_argon-des-perf-strata32 --end 500 --output grid-500.json
python3 solutions/argon-des-perf-neighborhood/effects.py 20261106-021800_argon-des-perf-gaincache 20261106-021800_argon-des-perf-strata32 --end 500 --general --output strata32-effects500.json
