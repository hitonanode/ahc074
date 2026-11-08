#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-models --replay --orders 4 --seeds 0-500 dcomp-combo-dual25 dcomp-t12-charge75 dcomp-t12-charge65 dcomp-t12-end105 dcomp-t12-gen60 dcomp-t12-mergepool
python3 solutions/dcomp-notes/task12_run.py t12-noprefix-gcc --replay --orders 4 --seeds 0-500 dcomp-combo-dual25 dcomp-t12-noprefix
python3 solutions/dcomp-notes/task12_run.py t12-noprefix-clang --compiler clang --replay --orders 4 --seeds 0-500 dcomp-combo-dual25 dcomp-t12-noprefix
