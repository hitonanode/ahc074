#!/bin/bash
# usage: run_sim.sh <binary> <seed_from> <seed_to_exclusive> <outfile>  (fixed-iteration design, 8 random request sequences)
bin=$1; a=$2; b=$3; out=$4
: > $out
seq $a $((b-1)) | xargs -P 4 -I{} sh -c "f=\$(printf '%04d' {}); r=\$(MAP_ITERS=380000 GOPT_STEPS=110000 ANNEAL_ITERS=19000000 CLIMB_ITERS=65000 SIM_SEQS=8 ./$bin < ../../tools/in/\$f.txt 2>&1 | grep -E '^(sim_moves|sim_wrong) =' | tr '\n' ' '); echo {} \$r >> $out"
