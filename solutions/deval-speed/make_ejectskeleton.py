from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-fast/main.cpp').read_text()
a=s.index('    void eject_repairs(');b=s.index('    // ==== Post-processing: two deletions and two repairs',a);v=s[a:b]
needle='''        auto& trial = eject_trial;'''
insert='''        // Papers never moved retain their relative order. A paper already
        // hidden by two such papers at every opaque window can never enter the
        // top two layers. Retain every edited paper and anchor as well, making
        // every splice commute exactly with filtering this fixed skeleton.
        std::array<bool,K> edited{},essential{};
        for(const auto& e:base_edits) {
            edited[e.paper]=essential[e.paper]=true;
            if(e.anchor>=0)essential[e.anchor]=true;
        }
        u64 fixed_once=0,fixed_twice=0;
        for(int k:initial.order)if(!edited[k]) {
            const u64 cover=paper[k].opaque;
            if(cover&~fixed_twice)essential[k]=true;
            fixed_twice|=fixed_once&cover;fixed_once|=cover;
        }
        Links skeleton_next{},skeleton_prev{};
        int previous=root;
        for(int k:initial.order)if(essential[k]) {
            skeleton_next[previous]=k;skeleton_prev[k]=previous;previous=k;
        }
        skeleton_next[previous]=root;skeleton_prev[root]=previous;
'''+needle
assert needle in v;v=v.replace(needle,insert,1)
start=v.index('                int processed = K, tail = root;');end=v.index('                // Most deletions have no single-paper repair.',start)
v=v[:start]+'''                trial_stamp++;
                {
                    auto nx=skeleton_next,pv=skeleton_prev;
                    for(const Edit& e:trial)splice_after(nx,pv,e.paper,e.anchor<0?root:e.anchor);
                    for(int k=nx[root];k!=root;k=nx[k]) {
                        const u64 two=paper[k].opaque&covered&~twice,one=paper[k].opaque&~covered;
                        second_black|=paper[k].black&two;
                        if(one){owned[k]=one;owner_stamp[k]=trial_stamp;}
                        shown|=paper[k].black&one;
                        covered|=paper[k].opaque;twice|=two;
                        if(twice==~u64(0))break;
                    }
                }
                bool order_ready=false;
                auto prepare_order=[&] {
                    if(order_ready)return;
                    order_ready=true;
                    auto nx=initial_next,pv=initial_prev;
                    for(const Edit& e:trial)splice_after(nx,pv,e.paper,e.anchor<0?root:e.anchor);
                    int t=0;
                    for(int k=nx[root];k!=root;k=nx[k]){ord[t]=k;ord_position[k]=t++;}
                };
'''+v[end:]
v=v.replace('// surviving repair needs its positions/anchors. Stamps distinguish real owners','// surviving repair needs its positions/anchors. Stamps distinguish real owners',1)
s=s[:a]+v+s[b:]
d=R/'solutions/deval-ejectskeleton';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-ejectskeleton

改良元: solutions/deval-fast。

注文の2操作削除・1操作修復で、最初の2枚の表示を調べる走査を短くする。移動されない紙の相対順序は変わらないので、その紙の全不透明窓が他の非移動紙2枚に覆われていれば、どの試行でも表示の1番目・2番目にはならない。全編集紙と全anchor、非移動紙の上位2層だけを残す。anchorも残すことで、編集とこの間引きが可換になる。

所有窓・表示・2番目の色はこの短い列で厳密に求める。修復可能な候補が残ったときだけ、従来の全192枚の列を作って位置と差込先を求める。試行の列挙順、合法性、費用評価、乱数、探索予算を変えない。
''')
print(len(s.encode()))
