from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text();s=base
needle='    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost('
a=s.index(needle);b=s.index('    // Lexicographic permutation rank',a)
original=s[a:b]
fields='''    struct NextPrefix {
        std::array<uint8_t,128> key;
        std::array<int,64> rank;
        std::array<int,128> first;
        std::array<uint32_t,64> code;
        double cost;
        bool valid=false;
    };
    mutable std::array<std::array<NextPrefix,32>,2> next_prefix;
    mutable long long next_prefix64=0,next_prefix128=0;
'''
t=original
assert t.count('u64 hash = 0xcbf29ce484222325ULL ^ key_size;')==1
t=t.replace('u64 hash = 0xcbf29ce484222325ULL ^ key_size;','u64 hash = 0xcbf29ce484222325ULL;\n        std::array<u64,2> prefix_hash;')
t=t.replace('            hash = (hash ^ word) * 0x100000001b3ULL;','''            hash = (hash ^ word) * 0x100000001b3ULL;
            if(i==56)prefix_hash[0]=hash;
            if(i==120)prefix_hash[1]=hash;''')
a1=t.index('        double cost = 0;');b1=t.index('        // covered[c][color]:',a1)
origscan=t[a1:b1]
new='''        double cost = 0;
        int start=0;
        if(in_place>128) {
            for(int level=1;level>=0;--level) {
                const int length=64*(level+1);
                const u64 h=prefix_hash[level];
                auto& memo=next_prefix[level][(h^(h>>32))&31];
                if(memo.valid && std::memcmp(memo.key.data(),key.data(),length)==0) {
                    std::copy_n(memo.rank.data(),H,rank.data());
                    std::copy_n(memo.first.data(),2*H,first.data());
                    if(mdp_scan)std::copy_n(memo.code.data(),H,mdp_code.data());
                    cost=memo.cost;start=length;
                    if(level)++next_prefix128;else ++next_prefix64;
                    break;
                }
            }
        }
        // Checkpoints retain the exact running double after 64/128 terms, together
        // with integer scan state. No addition is reassociated or omitted on a miss.
        for(int phase=start/64;phase<3;++phase) {
            const int end=phase<2?std::min(in_place,64*(phase+1)):in_place;
            for(int i=start;i<end;) {
                const int c=next_paper[key[i]].color>>1;
                int depth=rank[c];uint32_t code=mdp_scan?mdp_code[c]:0;
                do {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0)first[np.color]=depth;
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                } while(i<end && (next_paper[key[i]].color>>1)==c);
                rank[c]=depth;if(mdp_scan)mdp_code[c]=code;
            }
            if(phase<2 && end==64*(phase+1)) {
                const u64 h=prefix_hash[phase];auto& memo=next_prefix[phase][(h^(h>>32))&31];
                std::memcpy(memo.key.data(),key.data(),end);
                std::copy_n(rank.data(),H,memo.rank.data());std::copy_n(first.data(),2*H,memo.first.data());
                if(mdp_scan)std::copy_n(mdp_code.data(),H,memo.code.data());
                memo.cost=cost;memo.valid=true;
            }
            start=end;if(end==in_place)break;
        }
'''
t=t[:a1]+new+t[b1:]
t=t.replace('''        cached.size = key_size;''','''#ifdef NEXT_PREFIX_CHECK
        const double reference=adaptive_next_cost_reference(split);
        if(std::bit_cast<u64>(reference)!=std::bit_cast<u64>(cost)) {
            std::cerr<<"NEXT_PREFIX_MISMATCH "<<std::hexfloat<<reference<<' '<<cost<<'\\n';std::abort();
        }
#endif
        cached.size = key_size;''')
ref=original.replace('double adaptive_next_cost(', 'double adaptive_next_cost_reference(')
ref=ref.replace('if (cached.size == key_size', 'if (false && cached.size == key_size')
ref=ref.replace('''        cached.size = key_size;
        std::memcpy(cached.key.data(), key.data(), key_size);
        cached.value = cost;''','')
s=s[:a]+fields+'#ifdef NEXT_PREFIX_CHECK\n'+ref+'#endif\n'+t+s[b:]
# Full-key hit needs no scan and bypasses the checker; prefix-produced misses are always checked.
needle='"\\ncf_value_hits = " << solver.cf_value_hits'
# Keep new diagnostics close to existing value cache stats using their actual source spelling.
for check in [False,True]:
 p=r/'solutions'/('dcomp-next-prefix'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define NEXT_PREFIX_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\nnext_costの列内走査で64枚・128枚目までのkey、途中のdouble和、rank/first/MDP codeを完全keyで保存。共通prefixがあればその同じ途中状態から残りだけを走査する。加算の順序は変えず、近似やfast-mathも使わない。検証版はcacheに頼らない元の全走査とdouble bitを比較する。\n\n固定探索予算、ログ・実験スイッチ・DesignStoreを維持し、時間fallbackなし。\n')
