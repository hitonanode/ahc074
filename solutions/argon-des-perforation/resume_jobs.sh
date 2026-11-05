#!/bin/bash
set -eu
cd /home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629
export PATH="$PWD/solutions/argon-des-genopt/bin:$PATH"
python3 scripts/pahcer_run.py --extend 20261105-233934_esw-slim 20261105-234020_argon-des-headmix --seeds 0-2000 -c 'argon D2: 中断された上流2候補混合の延長を未登録seedから再開' > solutions/argon-des-perforation/headmix-2000-resume.log 2>&1
python3 scripts/pahcer_run.py --compare solutions/esw-slim solutions/argon-des-perf-dense --seeds 0-500 -c 'argon D2: 64標本の再比較。先行比較に外部負荷警告があったため' > solutions/argon-des-perforation/dense-repeat-500.log 2>&1
