#!/bin/sh
set -eu
python3 solutions/dcomp-notes/task12_run.py t12-profile-gcc --replay --seeds 0-200 dcomp-combo-dual25 dcomp-t12-profile
python3 solutions/dcomp-notes/task12_run.py t12-profile-clang --compiler clang --replay --seeds 0-200 dcomp-combo-dual25 dcomp-t12-profile
python3 solutions/dcomp-notes/task12_run.py t12-rawcopy-gcc --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-rawcopy
python3 solutions/dcomp-notes/task12_run.py t12-rawcopy-clang --compiler clang --replay --orders 4 --seeds 0-200 dcomp-combo-dual25 dcomp-t12-rawcopy
