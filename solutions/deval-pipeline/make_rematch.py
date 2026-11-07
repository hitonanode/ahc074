from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,mode in [('deval-anchor-high',1),('deval-anchor-low',2),('deval-free-color',4),('deval-free-anchor',5)]:
 s=b.replace('const std::vector<u64>* extra = nullptr) {\n    AF_SCOPE(rematch, 1);','const std::vector<u64>* extra = nullptr, int search_mode=0) {\n    AF_SCOPE(rematch, 1);',1)
 old='''                if (rng() & 1) std::swap(anchor[x], mobile[x]);'''
 new=old+'''
                if(search_mode&3) {
                    auto degree=[&](int a) {
                        int n=0;for(int t:d.partners[a])n+=int(d.hb[t]>>u.c&1)==color[x];return n;
                    };
                    const int da=degree(anchor[x]),dm=degree(mobile[x]);
                    if((search_mode&3)==1?da<dm:da>dm)std::swap(anchor[x],mobile[x]);
                }'''
 assert old in s;s=s.replace(old,new,1)
 old='''                if (int(d.hb[b] >> c & 1) != color[i] || (a >= 0 && !d.ok[a][b])) continue;'''
 new='''                const bool flexible=(search_mode&4) && a<0;
                if ((!flexible && int(d.hb[b] >> c & 1) != color[i]) || (a >= 0 && !d.ok[a][b])) continue;'''
 assert old in s;s=s.replace(old,new,1)
 old='''            d.rebuild();
            const double head_value = head.rebuild();'''
 new='''            d.rebuild();
            // A whole Hungarian cycle may remove a column's last paper of
            // one color. Such a proposal is infeasible before head rebuilding.
            if(search_mode&4) {
                bool valid=true;for(int c=0;c<d.H;++c)valid&=d.n1[c]>0 && d.n1[c]<d.nc[c];
                if(!valid) {
                    for(int z=0;z<int(cycle.size());++z)d.unit[cycle[z]]=old[z];
                    d.rebuild();continue;
                }
            }
            const double head_value = head.rebuild();'''
 assert old in s;s=s.replace(old,new,1)
 s=s.replace('rematch_probability(*des, late_iterations, 1.05, 2.0, &extra);',f'rematch_probability(*des, late_iterations, 1.05, 2.0, &extra, extra_mode);',1)
 s=s.replace('''        const auto late = rematch_probability''',f'''        const int extra_mode=extra.empty()?0:({mode}*(warm_state.papers.size()>0 && deval_salt%2==1));
        const auto late = rematch_probability''',1)
 # Inside the late block, extra is the hole vector, shadowing finish's mode.
 # warm_state is nonempty only after the first warm pass. Odd ids 5,7
 # are exactly the two warm passes (DEVAL_SALT=0 in all experiments).
 # Prefer an explicit flag before the local vector to support every salt.
 s=s.replace('''        const double late_start = elapsed_sec();
        std::vector<u64> extra''','''        const double late_start = elapsed_sec();
        const bool warm_pass=extra==2;
        std::vector<u64> extra''',1)
 s=s.replace(f'const int extra_mode=extra.empty()?0:({mode}*(warm_state.papers.size()>0 && deval_salt%2==1));',f'const int extra_mode=warm_pass?{mode}:0;',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n穴を保存する2回の再仕上げの最終Hungarian再割当てだけ、探索の制約を変える（mode={mode}）。1は相手候補数の多い側をペアの固定側にし、2は少ない側を固定する。4は単独紙の元の色を固定しない。5は1と4の組合せ。列から片方の色が消える巡回は不採用。巡回は従来の仕上げ目的の改善で受理し、完成した8候補をVで選ぶ。全予算は固定、時間不足による切り替えなし。\n')
 print(name,len(s.encode()))
