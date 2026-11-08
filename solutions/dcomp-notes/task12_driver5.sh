#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-values-gcc --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-value1024 dcomp-t12-valuecompact
python3 solutions/dcomp-notes/task12_run.py t12-values-clang --compiler clang --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-value1024 dcomp-t12-valuecompact
