from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper-retain/main.cpp').read_text()
a='''        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        std::array<int, K> helper_depth{};'''
b='''        u64 helper_holes=~paper[d].opaque & hmask;
        for(const auto& f:fillers)helper_holes&=~shown_by(f);
        const auto fixes = fix_costs(u, helper_holes);
        std::array<int, K> helper_depth{};'''
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-helper-retain-model';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-helper-retain`。

残すfillerが表示するhandleを、helper候補の事前見積りのfix費用からも除く。既に覆うhandleを新しいhelperの利益として二重に数えないためである。実行計画の処理は同じで、固定予算、検査、ログと実験スイッチを保つ。
''');print(len(s.encode()))
