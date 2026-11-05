#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-023231_argon-des-perf-gaincache 20261106-023813_argon-des-perf-dense70 20261106-023813_argon-des-perf-dense80 --output dense-500.json
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-023600_argon-des-perf-gaincache 20261106-023813_argon-des-perf-pass2 20261106-023813_argon-des-perf-reprob2 --output refresh-500.json
python3 solutions/argon-des-perf-neighborhood/summarize.py 20261106-022926_argon-des-perf-gaincache 20261106-023813_argon-des-perf-nonhead70 20261106-023813_argon-des-perf-nonhead70wide --output nonhead-500.json
python3 solutions/argon-des-perf-neighborhood/effects.py 20261106-022926_argon-des-perf-gaincache 20261106-023813_argon-des-perf-nonhead70 --end 500 --general --output nonhead-effects500.json
