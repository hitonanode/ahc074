from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n'+d+'\n\n候補の列挙・受理と浮動小数点計算は変えない。親とのstdoutをGCC/Clangで照合し、時間は24並列compareで測る。ログ・実験スイッチ・プロファイラを保つ。\n')
 assert len(text.encode())<=522000,(n,len(text.encode()))
 print(n,len(text.encode()))
x=s.replace('''        if (prev[k] == a) return;
        next[prev[k]] = next[k];
        prev[next[k]] = prev[k];''','''        const int before=prev[k],after=next[k];
        if(before==a)return;
        next[before]=after;
        prev[after]=before;''')
emit('deval-linkload6',x,'後処理のlinked-list移動で、削除前の前後ノードを一度だけ読む。別配列や別添字への書込み後の不要な再読出しを避ける。')
x=s
marker='    struct EndMemo {\n'
x=x.replace(marker,'''    struct FilterState { Links next,prev; std::array<u64,3> moved{},breaks{}; };
    std::vector<FilterState> filter_states;
    std::vector<Edit> filter_edits;
'''+marker)
needle='        auto edits = anchorize(initial_bytes, input_ops OP_TAG(, tags));'
x=x.replace(needle,needle+'\n        filter_edits.clear();')
needle='''            std::array<u64, 3> moved{}, breaks{};
            auto next = initial_next, prev = initial_prev;'''
replacement='''            // Cache only the current base path. Trial paths reuse its exact
            // linked prefix; every changed suffix still goes through the filter.
            bool fresh=filter_edits.size()!=edits.size();
            if(!fresh)for(int j=0;j<int(edits.size());++j)
                if(edits[j].paper!=filter_edits[j].paper || edits[j].anchor!=filter_edits[j].anchor){fresh=true;break;}
            if(fresh) {
                filter_edits=edits;filter_states.resize(edits.size()+1);
                filter_states[0]={initial_next,initial_prev,{},{}};
                for(int j=0;j<int(edits.size());++j) {
                    auto& f=filter_states[j+1];f=filter_states[j];
                    const int k=edits[j].paper,a=edits[j].anchor;
                    const int p=initial_position[k];f.moved[p>>6]|=1ULL<<(p&63);
                    if(a>=0){const int q=initial_position[a];f.breaks[q>>6]|=1ULL<<(q&63);}
                    splice_after(f.next,f.prev,k,a<0?root:a);
                }
            }
            int shared=0;
            while(shared<int(trial.size()) && shared<int(filter_edits.size()) &&
                  trial[shared].paper==filter_edits[shared].paper && trial[shared].anchor==filter_edits[shared].anchor)++shared;
            const auto& f=filter_states[shared];
            auto moved=f.moved,breaks=f.breaks;auto next=f.next,prev=f.prev;'''
assert x.count(needle)==1;x=x.replace(needle,replacement)
needle='''                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;'''
replacement='''                for(int qi=shared;qi<int(trial.size());++qi) {
                    const Edit& e=trial[qi];
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;'''
assert x.count(needle)==1;x=x.replace(needle,replacement)
emit('deval-filterprefix6',x,'後処理のdisplay検査で、現在の基準操作列の各prefixのlinked-list状態と区間境界を保存する。候補と同じprefixを再利用し、異なるsuffixを通常通り適用する。途中可視性の検査と末端費用・全キー照合は従来通り。')
