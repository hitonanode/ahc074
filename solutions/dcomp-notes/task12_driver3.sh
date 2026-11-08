#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-seeds --replay --orders 4 --seeds 0-500 dcomp-combo-dual25 dcomp-t12-expanded-seed dcomp-t12-pool-seed
python3 solutions/dcomp-notes/task12_run.py t12-mapalign-gcc --seeds 0-500 dcomp-combo-alt1 dcomp-combo-dual25 dcomp-t12-mapalign
