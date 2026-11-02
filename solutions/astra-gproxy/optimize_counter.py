"""同じ整数カウンタを carry-save 加算で計算する。目的の値は変わらない。"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'main.cpp').read_text()
start=s.index('            u64 count[7]{};')
end=s.index('            int sum=0, sq=0;',start)
new=r'''
            u64 count[7]{};
            // Add eight masks at a time with carry-save addition. Each bit position is an
            // independent counter; the carry masks are shifted in significance, never in
            // physical bit position. This produces exactly the same seven binary planes.
            auto csa = [](u64& high, u64& low, u64 a, u64 b, u64 c) {
                const u64 x=a^b;
                high=(a&b)|(x&c);
                low=x^c;
            };
            const int count_n=int(candidate_selected.size());
            int at=0;
            for (; at+8<=count_n; at+=8) {
                u64 twos_a,twos_b,fours_a,fours_b,eights;
                csa(twos_a,count[0],count[0],pairs.diff[candidate_selected[at]],pairs.diff[candidate_selected[at+1]]);
                csa(twos_b,count[0],count[0],pairs.diff[candidate_selected[at+2]],pairs.diff[candidate_selected[at+3]]);
                csa(fours_a,count[1],count[1],twos_a,twos_b);
                csa(twos_a,count[0],count[0],pairs.diff[candidate_selected[at+4]],pairs.diff[candidate_selected[at+5]]);
                csa(twos_b,count[0],count[0],pairs.diff[candidate_selected[at+6]],pairs.diff[candidate_selected[at+7]]);
                csa(fours_b,count[1],count[1],twos_a,twos_b);
                csa(eights,count[2],count[2],fours_a,fours_b);
                for (int b=3; b<7; ++b) {
                    const u64 next=count[b]&eights;
                    count[b]^=eights;
                    eights=next;
                }
            }
            for (; at<count_n; ++at) {
                u64 carry=pairs.diff[candidate_selected[at]];
                for (int b=0; b<7; ++b) {
                    const u64 next=count[b]&carry;
                    count[b]^=carry;
                    carry=next;
                }
            }
            for (u64& plane:count) plane&=handle_mask;
'''
s=s[:start]+new+s[end:]
(HERE/'main.cpp').write_text(s)
sim=s.replace('solver.hmask, kHelperGiveUp);','solver.hmask, anneal_iters > 0 ? 1e9 : kHelperGiveUp);')
(HERE/'candidate_sim.cpp').write_text(sim)
