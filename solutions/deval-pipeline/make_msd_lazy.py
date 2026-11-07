from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
for bits in [8,9]:
 s=(R/f'solutions/deval-sort-msd{bits}/main.cpp').read_text()
 old='''        for(int bucket=min_high,begin=0;bucket<=max_high;++bucket) {
            const int end=high[bucket];
            std::sort(sorted.begin()+begin,sorted.begin()+end);
            begin=end;
        }'''
 assert old in s;s=s.replace(old,'',1)
 old='''        for (int i = 0; i < size; i++) {
            const u64 x = sorted[i];'''
 new='''        int sorted_until=0,sort_bucket=min_high;
#if DESIGN_PROFILE >= 3
        unsigned long long deferred_sort=0;
#endif
        for (int i = 0; i < size; i++) {
            // The greedy uses a prefix of the sorted edges. Sort a high-key
            // bucket only when that prefix first reaches it; ties stay by pair id.
            if(i==sorted_until) {
                while(high[sort_bucket]==i)++sort_bucket;
                sorted_until=high[sort_bucket++];
#if DESIGN_PROFILE >= 3
                const auto tick=__builtin_ia32_rdtsc();
#endif
                std::sort(sorted.begin()+i,sorted.begin()+sorted_until);
#if DESIGN_PROFILE >= 3
                deferred_sort+=__builtin_ia32_rdtsc()-tick;
#endif
            }
            const u64 x = sorted[i];'''
 assert old in s;s=s.replace(old,new,1)
 s=s.replace('''        dp_cycles[dp_mc_greedy] += __builtin_ia32_rdtsc() - mt2;''','''        dp_cycles[dp_mc_sort] += deferred_sort;
        dp_cycles[dp_mc_greedy] += __builtin_ia32_rdtsc() - mt2 - deferred_sort;''',1)
 p=R/f'solutions/deval-msd-lazy{bits}';p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-sort-msd{bits}`（元はdeval-ordered8）。\n\n上位bitのbucketの中を、貪欲マッチングがそのbucketを読む時だけ整列する。71ペアに達して停止した後のbucketは整列しない。読むキーとpair-idによる同値順は従来と同じ。プロファイルでは遅延した整列の時間をsortへ加え、greedyから引く。固定予算・出力同一の高速化案。\n')
 print(p.name,len(s.encode()))
