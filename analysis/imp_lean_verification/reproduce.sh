#!/usr/bin/env bash
# [NOT FOR MERGE] Re-evaluation commands for reconstructed experiments.
# These do NOT re-create the historical measurements automatically.
set -euo pipefail
cd "$(dirname "$0")/../.."
for v in imp-dual-mean imp-poset-7-38 imp-poset-8-44 imp-poset-cached7-38 imp-poset-cached8-44; do
  echo "Comparing imp-lean vs ${v}"
  python3 scripts/pahcer_run.py --compare "solutions/imp-lean" "solutions/${v}" --seeds 0-500 -c "imp-lean research report ${v}"
done
