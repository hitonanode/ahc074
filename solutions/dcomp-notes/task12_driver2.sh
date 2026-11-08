#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-poolprune-gcc --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-poolprune
python3 solutions/dcomp-notes/task12_run.py t12-poolprune-clang --compiler clang --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-poolprune
