#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-postmemo-gcc --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-postmemo dcomp-t12-postmemo-check
python3 solutions/dcomp-notes/task12_run.py t12-postmemo-clang --compiler clang --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-postmemo dcomp-t12-postmemo-check
