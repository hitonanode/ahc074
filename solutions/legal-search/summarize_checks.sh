#!/bin/bash
# Summaries of the stage 1 follow-up checks (results/multi, results/unk).
cd "$(dirname "$0")"
echo "multi-move restricted search (mode 2, seeds 0-3):"
cat results/multi/*.txt 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^(mopt|mimp|munk)$/) c[$i]++; if ($6 == "opt0") c["opt0"]++; if ($3 - $4 == 1) g1++} END {for (k in c) print "  " k, c[k]; print "  gap-1 orders (skipped)", g1}'
echo "unknown orders rerun (10M nodes):"
cat results/unk/*.txt 2>/dev/null | awk '{c[$6]++; if ($6 == "imp") s += $3 - $5} END {for (k in c) print "  " k, c[k]; print "  moves saved", s + 0}'
