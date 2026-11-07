"""Maintain the necessary-condition linked list across neighboring edit trials."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parent=root/'solutions/deval-vbranch-o3';dest=root/'solutions/deval-filterundo'
dest.mkdir(exist_ok=True)
s=(parent/'main.cpp').read_text()
needle='        auto evaluate = [&](const std::vector<Edit>& trial) {'
start=s.index(needle)
s=s[:start]+'''        // Neighboring trials share an edit prefix. Undo only the changed
        // suffix, then replay its replacement. This keeps exactly the same
        // final linked list, without copying both full link arrays per trial.
        Links filter_next=initial_next,filter_prev=initial_prev;
        std::vector<Edit> filter_edits;
        std::vector<int> filter_previous;
        filter_edits.reserve(input_ops.size()+3);
        filter_previous.reserve(input_ops.size()+3);
'''+s[start:]
s=s.replace('            auto next = initial_next, prev = initial_prev;','''            auto& next=filter_next;
            auto& prev=filter_prev;''',1)
needle='''                // Bit positions refer to the initial order. A run ends at a moved paper,'''
pos=s.index(needle,s.index('auto evaluate ='))
s=s[:pos]+'''                size_t common=0;
                while(common<trial.size()&&common<filter_edits.size()&&
                      trial[common].paper==filter_edits[common].paper&&
                      trial[common].anchor==filter_edits[common].anchor)++common;
                while(filter_edits.size()>common) {
                    splice_after(next,prev,filter_edits.back().paper,filter_previous.back());
                    filter_edits.pop_back();filter_previous.pop_back();
                }
                for(size_t j=common;j<trial.size();++j) {
                    const auto& e=trial[j];
                    const int a=e.anchor<0?root:e.anchor;
                    if(a==e.paper)return false;
                    filter_previous.push_back(prev[e.paper]);
                    filter_edits.push_back(e);
                    splice_after(next,prev,e.paper,a);
                }
'''+s[pos:]
pos=s.index('                for (const Edit& e : trial)',s.index('auto evaluate ='))
end=s.index('                for (int w = 0;',pos)
piece=s[pos:end].replace('                    splice_after(next, prev, k, a);\n','')
s=s[:pos]+piece+s[end:]
(dest/'main.cpp').write_text(s)
(dest/'README.md').write_text('''# deval-filterundo

改良元: solutions/deval-vbranch-o3。

注文の後処理で、候補ごとの最終表示を調べる連結リストを使い回す。直前の候補と同じ編集の先頭部分を残し、違う末尾だけを逆操作して新しい末尾を適用する。必要条件、可視性の再生、評価値、候補の順序は変更しない。探索予算と時間ガードは元のまま。
''')
print(dest,len(s.encode()))
