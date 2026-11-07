"""Exact greedy matching, sorting high-key buckets only as they are consumed."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
start=s.index('        std::array<int, 256> low{};',s.index('auto matching_cost'))
end=s.index('        candidate_selected.resize(matched);',start)
new='''        std::array<int,512> high{};
        int min_high=511,max_high=0;
        const int size=nvalid;
        for(int i=0;i<size;++i) {
            const int p=valid[i];
            const int key=1800*__builtin_popcountll(pairs.diff[p]&handle_mask)+5*int(rel[p]-1)+full144[p];
            assert(key<(1<<17));
            keyed[i]=u64(key)<<32|pair_tail[p];
            ++high[key>>8];
            min_high=std::min(min_high,key>>8);max_high=std::max(max_high,key>>8);
        }
#if DESIGN_PROFILE >= 3
        unsigned long long mt1=__builtin_ia32_rdtsc();
        dp_cycles[dp_mc_keys]+=mt1-mt0;
#endif
        for(int i=min_high,offset=0;i<=max_high;++i) {
            const int count=high[i];high[i]=offset;offset+=count;
        }
        // Stable high-byte distribution. high[b] is its end after this pass.
        for(int i=0;i<size;++i)tmp[high[keyed[i]>>40]++]=keyed[i];
#if DESIGN_PROFILE >= 3
        unsigned long long mt2=__builtin_ia32_rdtsc();
        dp_cycles[dp_mc_sort]+=mt2-mt1;
        int dp_last=size;
#endif
        candidate_selected.resize(need);
        int* const out=candidate_selected.data();
        std::array<unsigned char,256> used{};
        int matched=0;
        long long total=0;
        for(int bucket=min_high,begin=0;bucket<=max_high&&matched<need;++bucket) {
            const int end=high[bucket];
            // Insertion sort is stable on equal keys. No later bucket is
            // visited once the original greedy matching has enough pairs.
            for(int i=begin+1;i<end;++i) {
                const u64 value=tmp[i];
                int j=i;
                while(j>begin&&(tmp[j-1]>>32)>(value>>32)) { tmp[j]=tmp[j-1];--j; }
                tmp[j]=value;
            }
            for(int i=begin;i<end;++i) {
                const u64 x=tmp[i];
                const unsigned u=unsigned(x>>8)&255,v=unsigned(x)&255;
                const int ok=(used[u]|used[v])^1;
                used[u]|=ok;used[v]|=ok;
                out[matched]=int(x>>16)&0xffff;
                total+=ok?(long long)(x>>32):0LL;
                matched+=ok;
                if(matched==need) {
#if DESIGN_PROFILE >= 3
                    dp_last=i+1;
#endif
                    break;
                }
            }
            begin=end;
        }
'''
s=s[:start]+new+s[end:]
d=ROOT/'solutions/deval-msd';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-msd

改良元: solutions/deval-vbranch-o3。

窓割当てのgreedy matchingで、費用キーの上位桁を先に安定分配し、下位桁はgreedyが実際に読むバケットだけを安定挿入ソートする。必要な組数に達した後のバケットを並べ替えない。費用が同じ組の順序とgreedyの選択結果は元の2段radix sortと同じ。探索回数と時間ガードは変えない。
''')
print(d,len(s.encode()))
