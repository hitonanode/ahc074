from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
needle='    template <class Evaluate>\n    void eject_repairs('
i=s.index(needle)
s=s[:i]+'''    struct EjectVisibility {
        ByteOrder order;
        std::array<u64,K+1> cover;
        int valid=0;
    };
    std::vector<EjectVisibility> eject_visibility;
'''+s[i:]
lo=s.index('    void eject_repairs(');hi=s.index('// ==== Post-processing: two deletions and two repairs',lo)
b=s[lo:hi]
b=b.replace('''                const int length = trial.size();''','''                const int length = trial.size();
                int visibility_states=0;
                auto visible_in_prefix=[&](EjectVisibility& v,int k,int p) {
                    for(;v.valid<p;++v.valid)
                        v.cover[v.valid+1]=v.cover[v.valid]|paper[v.order[v.valid]].opaque;
                    return bool(paper[k].opaque&~v.cover[p]);
                };
                auto prepare_visibility=[&] {
                    if(visibility_states)return;
                    if(int(eject_visibility.size())<length+1)eject_visibility.resize(length+1);
                    eject_visibility[0].order=initial_bytes;
                    for(int t=0;;++t) {
                        auto& v=eject_visibility[t];v.valid=0;v.cover[0]=0;
                        visibility_states=t+1;
                        if(t==length)break;
                        const auto& e=trial[t];
                        const int p=find_paper(v.order,e.paper);
                        int dest=e.anchor<0?0:find_paper(v.order,e.anchor)+1;
                        if(p<dest)--dest;
                        if(dest!=p&&!visible_in_prefix(v,e.paper,p))break;
                        auto& next=eject_visibility[t+1];next.order=v.order;
                        if(dest!=p)shift_byte(next.order,p,dest);
                    }
                };''',1)
a=b.index('                    int earliest = length + 1, latest = -1;')
c=b.index('                    if (latest < 0) continue;',a)
b=b[:a]+'''                    prepare_visibility();
                    int earliest=length+1,latest=-1;
                    for(int t=0;t<visibility_states;++t) {
                        auto& v=eject_visibility[t];
                        if(visible_in_prefix(v,k,find_paper(v.order,k))) {
                            earliest=std::min(earliest,t);latest=t;
                        }
                    }
'''+b[c:]
s=s[:lo]+b+s[hi:]
d=ROOT/'solutions/deval-ejectprefix';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-ejectprefix

改良元: solutions/deval-vbranch-o3。

後処理で削除後の編集列を修復するとき、修復紙ごとに繰り返していた同じ編集列の再生を共有する。最初の候補が必要になるまで作らず、各時点の紙の順序と必要な範囲だけの被覆和を保持する。最初の不合法操作の直前までという列挙範囲・最早/最遅の差込み時点を保つ。探索予算と時間ガードは同じ。
''')
print(len(s.encode()))
