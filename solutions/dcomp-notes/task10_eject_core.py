from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
a=s.index('    // ==== Post-processing: two deletions and one repair (eject) ====');b=s.index('    // ==== Post-processing: two deletions and two repairs (neutral rewrite) ====',a)
f=s[a:b]
def sub(x,y):
 global f
 assert f.count(x)==1,(f.count(x),x[:90]);f=f.replace(x,y)
needle='        alignas(32) std::array<int, K+4> candidates{};'
code='''        // Every unedited paper already covered by two unedited papers can never
        // own either top opaque layer in any deletion trial. Keep just those two
        // fixed layers, all edited papers, and every edit anchor. Splicing this
        // reduced list gives exactly the first two layers of the full list.
        std::array<bool,K> edited{}, relevant{};
        for(const auto& e:base_edits) {
            edited[e.paper]=relevant[e.paper]=true;
            if(e.anchor>=0)relevant[e.anchor]=true;
        }
        u64 fixed_once=0,fixed_twice=0;
        for(int k:initial.order)if(!edited[k]) {
            const u64 op=paper[k].opaque;
            if(op&~fixed_twice)relevant[k]=true;
            fixed_twice|=fixed_once&op;fixed_once|=op;
        }
        Links core_next{},core_prev{};
        int core_last=root;
        for(int k:initial.order)if(relevant[k]) {
            core_next[core_last]=k;core_prev[k]=core_last;core_last=k;
        }
        core_next[core_last]=root;core_prev[root]=core_last;
'''
assert f.count(needle)==1;f=f.replace(needle,code+needle)
sub('                int processed = K, tail = root;\n','')
sub('                auto nx = initial_next;\n                {\n                    auto pv = initial_prev;','                auto nx = core_next;\n                {\n                    auto pv = core_prev;')
sub('''                    int t = 0, k = nx[root];
                    for (; k != root; k = nx[k]) {
                        ord[t] = k;
                        ord_position[k] = t++;
''','''                    for (int k=nx[root]; k != root; k = nx[k]) {
''')
sub('''                        if (twice == ~u64(0)) {
                            processed = t;
                            k = nx[k];
                            break;
                        }
                    }
                    tail = k;
''','''                        if (twice == ~u64(0)) break;
                    }
''')
sub('''                    int t = processed;
                    for (int k = tail; k != root; k = nx[k]) {
                        ord[t] = k;
                        ord_position[k] = t++;
                    }
''','''                    // Positions are needed only after a repair survives the display test.
                    // Rebuild the ordinary full linked list then, including discarded papers.
                    auto full_next=initial_next, full_prev=initial_prev;
                    for(const auto& e:trial)splice_after(full_next,full_prev,e.paper,e.anchor<0?root:e.anchor);
                    int t=0;
                    for(int k=full_next[root];k!=root;k=full_next[k]) {
                        ord[t]=k;ord_position[k]=t++;
                    }
''')
# Verify the complete top-two summary and every relevant candidate's ownership.
needle='''                bool order_ready = false;'''
code='''#ifdef EJECT_CORE_CHECK
                {
                    auto nn=initial_next,pp=initial_prev;
                    for(const auto& e:trial)splice_after(nn,pp,e.paper,e.anchor<0?root:e.anchor);
                    u64 cv=0,tw=0,sh=0,sc=0;
                    for(int k=nn[root];k!=root;k=nn[k]) {
                        const u64 op=paper[k].opaque,one=op&~cv,two=op&cv&~tw;
                        if(one && (owner_stamp[k]!=trial_stamp || owned[k]!=one))std::abort();
                        if(!one && owner_stamp[k]==trial_stamp)std::abort();
                        sh|=paper[k].black&one;sc|=paper[k].black&two;cv|=op;tw|=two;
                        if(tw==~u64(0))break;
                    }
                    if(cv!=covered || tw!=twice || sh!=shown || sc!=second_black)std::abort();
                }
#endif
'''
assert f.count(needle)==1;f=f.replace(needle,code+needle)
f=f.replace('''                // way down the display of the final order (shown), the windows where each paper is the
                // top opaque one (owned; papers from position `processed` on own nothing) and the''','''                // way down the display of the final order (shown), the windows where each paper is the
                // top opaque one (owned, with stamps for nonowners) and the''')
f=f.replace('''                // suffice to reject every paper, so only materialize the untouched tail when a
                // surviving repair needs its positions/anchors. Stamps distinguish real owners''','''                // suffice to reject every paper, so only materialize the full order when a
                // surviving repair needs its positions/anchors. Stamps distinguish real owners''')
s=s[:a]+f+s[b:]
for name,extra in [('dcomp-eject-core',''),('dcomp-eject-core-check','#define EJECT_CORE_CHECK 1\n')]:
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(extra+s)
 (p/'README.md').write_text('''改良元: solutions/dcomp-screen-replay

ejectの表示検査を縮める。元の操作列が動かす紙を取り除いた固定の紙列で、既に他の2枚に完全に覆われる紙は、どの削除試行でも最初と2番目の不透明紙にならない。その紙を表示用のlinked listから除く。ただし操作の紙とanchorはすべて残すので、元と同じspliceを適用できる。最初の2層の色と所有窓は全紙の再生と同じになる。

修復候補が表示検査を通ったら、元の全192枚のlinked listを再生して、挿入深さ・列境界・可視性を計算する。探索候補や順序は変えない。EJECT_CORE_CHECKは各試行の2層と所有窓を全紙の再生と比較する。予算固定、fast-mathや時間fallbackなし。既存ログ・実験スイッチ・DesignStoreを保持する。
''')
