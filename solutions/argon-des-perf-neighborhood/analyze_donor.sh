#!/bin/bash
set -eu
python3 solutions/argon-des-perf-neighborhood/effects.py 20261106-022157_argon-des-perf-gaincache 20261106-022157_argon-des-perf-donorhole --end 500 --general --output donorhole-effects500.json
python3 solutions/argon-des-perf-neighborhood/effects.py 20261106-022157_argon-des-perf-gaincache 20261106-022157_argon-des-perf-donorcolumn --end 500 --general --output donorcolumn-effects500.json
