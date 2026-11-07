"""Exact necessary-condition mask for one-paper repair candidates."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parent=root/'solutions/deval-vbranch-o3';dest=root/'solutions/deval-repairmask'
dest.mkdir(exist_ok=True)
s=(parent/'main.cpp').read_text()
needle='    void prepare_post_context(const State& initial) {'
s=s.replace(needle,'''    // Immutable paper/color incidence for exact repair rejection. A paper
    // which owns no wrong window must cover every current error correctly.
    bool repair_masks_ready=false;
    std::array<std::array<std::array<u64,3>,2>,64> repair_masks{};
'''+needle,1)
needle='        CF_SCOPE(post_setup);'
s=s.replace(needle,needle+'''
        if(!repair_masks_ready) {
            repair_masks_ready=true;
            for(int k=0;k<K;++k)for(u64 z=paper[k].opaque;z;z&=z-1) {
                const int w=__builtin_ctzll(z);
                repair_masks[w][(paper[k].black>>w)&1][k>>6]|=1ULL<<(k&63);
            }
        }''',1)
start=s.index('    void eject_repairs(');end=s.index('    // ==== Post-processing: two deletions and two repairs',start)
b=s[start:end]
b=b.replace('''        std::array<int, K> candidates;
        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) candidates[candidate_count++] = k;''','''        std::array<u64,3> candidate_bits{};
        for(int k=0;k<K;++k)
            if(k!=kCapPaper&&possible[k])candidate_bits[k>>6]|=1ULL<<(k&63);''',1)
b=b.replace('                trial_stamp++;','                trial_stamp++;\n                std::array<u64,3> wrong_owners{};',1)
b=b.replace('                        if (one) owner_stamp[k] = trial_stamp;','''                        if (one) owner_stamp[k] = trial_stamp;
                        if(one&(paper[k].black^A[u]))wrong_owners[k>>6]|=1ULL<<(k&63);''',1)
b=b.replace('''                for (int ci = 0; ci < candidate_count; ci++) {
                    const int k = candidates[ci];''','''                auto eligible=candidate_bits;
                for(u64 z=shown^A[u];z;z&=z-1) {
                    const int w=__builtin_ctzll(z);
                    const auto& correct=repair_masks[w][(A[u]>>w)&1];
                    for(int j=0;j<3;++j)eligible[j]&=correct[j];
                }
                // Lifting a wrong owner can itself clear an error. All other
                // papers must cover the entire old error set; retain its exact
                // original check below and its ascending paper enumeration.
                for(int j=0;j<3;++j)eligible[j]=(eligible[j]|wrong_owners[j])&candidate_bits[j];
                for(int word=0;word<3;++word)for(u64 pending=eligible[word];pending;pending&=pending-1) {
                    const int k=64*word+__builtin_ctzll(pending);''',1)
assert 'candidate_count' not in b
s=s[:start]+b+s[end:]
(dest/'main.cpp').write_text(s)
(dest/'README.md').write_text('''# deval-repairmask

改良元: solutions/deval-vbranch-o3。

後処理の1枚修復で、紙の色・不透明窓を192ビットの表にする。現在の誤窓を所有していない紙は、全誤窓を正しい色で覆わなければ修復できない。この必要条件をビット集合で調べ、誤窓の所有紙を加えてから元の厳密な判定を行う。候補の順序と採否判定、探索予算、時間ガードは元と同じ。
''')
print(dest,len(s.encode()))
