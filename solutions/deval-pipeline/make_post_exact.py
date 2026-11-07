from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
s=b
start=s.index('        auto evaluate = [&](const std::vector<Edit>& trial) {');end=s.index('            auto& path = path_buffer;',start)
x=s[start:end];assert x.count('u64 seen = 0, view = 0;')==1
x=x.replace('u64 seen = 0, view = 0;','u64 seen = 0;').replace('                    view |= disp & ~seen;\n','').replace('if (view != A[u]) return false;','// Every exposed bit matched above; only uncovered black bits remain.\n                if (A[u] & ~seen) return false;')
s=s[:start]+x+s[end:]
p=R/'solutions/deval-filter-mask';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n後処理の最終表示の必要条件チェックでは、露出した各ビットの色を直ちに検査している。そのため表示値の再集計を省き、最後は未被覆の黒ビットがないことを調べる。区間の色・順番・計画採否・memoと計測点を変えない。出力同一の高速化案。\n')
print(p.name,len(s.encode()))
s=b
needle='''        std::array<int, K> candidates;
        int candidate_count = 0;'''
start=s.index('    void eject_repairs(');at=s.index(needle,start)
s=s[:at]+s[at:].replace(needle,'''        // Every deletion trial moves a subset of base_edits. These cuts are
        // valid for all trials, and allow unchanged suffix ranges to be read at once.
        std::array<int,K> initial_at;
        for(int i=0;i<K;++i)initial_at[initial_bytes[i]]=i;
        std::array<u64,3> cuts{},moved_cuts{};
        for(const auto& e:base_edits) {
            const int i=initial_at[e.paper];moved_cuts[i>>6]|=u64(1)<<(i&63);
            if(e.anchor>=0){const int j=initial_at[e.anchor];cuts[j>>6]|=u64(1)<<(j&63);}
        }
        for(int w=0;w<3;++w) {
            cuts[w]|=moved_cuts[w]|(moved_cuts[w]>>1);
            if(w<2)cuts[w]|=moved_cuts[w+1]<<63;
        }
        auto range_end=[&](int i) {
            int w=i>>6;u64 mask=cuts[w]&(~u64(0)<<(i&63));
            while(!mask){if(++w==3)return K-1;mask=cuts[w];}
            return 64*w+__builtin_ctzll(mask);
        };
'''+needle,1)
a=s.index('                    int t = 0, k = nx[root];',start);z=s.index('                }\n                bool order_ready = false;',a)
s=s[:a]+'''                    int t=0;
                    for(int k=nx[root];k!=root;k=nx[k]) {
                        ord[t]=k;ord_position[k]=t++;
                        const u64 two=paper[k].opaque&covered&~twice,one=paper[k].opaque&~covered;
                        second_black|=paper[k].black&two;owned[k]=one;
                        if(one)owner_stamp[k]=trial_stamp;
                        shown|=paper[k].black&one;covered|=paper[k].opaque;twice|=two;
                        if(covered==~u64(0)){processed=t;tail=nx[k];break;}
                    }
                    // Once the first layer covers every window, only the second
                    // colors are needed. No later paper owns a visible window.
                    for(int k=tail;k!=root&&twice!=~u64(0);) {
                        const int i=initial_at[k],e=(cuts[i>>6]>>(i&63)&1)?i:range_end(i);
                        const int level=31-__builtin_clz(unsigned(e-i+1));
                        const auto a=post_context.blocks[level][i],b=post_context.blocks[level][e+1-(1<<level)];
                        const u64 cov=a.cov|b.cov,disp=a.disp|(b.disp&~a.cov);
                        second_black|=disp&~twice;twice|=cov;k=nx[initial_bytes[e]];
                    }
'''+s[z:]
p=R/'solutions/deval-eject-range';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n削除と補修の探索で、最上位の紙が全窓を覆った後は、第2層の色だけを既存の区間表から読む。試行ごとに動く紙は元の操作列の部分集合なので、全試行に共通で有効な区切りを先に作る。補修候補が残った場合だけ、従来どおり後半の紙順を展開する。値・探索順・計測点を維持する出力同一の高速化案。\n')
print(p.name,len(s.encode()))
