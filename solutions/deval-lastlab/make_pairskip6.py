from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
a=s.index('        // pairs: a helper x at most 3 deep')
b=s.index('        for (const auto& item : pair_picks) {',a)
mid=s[a:b]
fa=mid.index('        auto finish = [&]() {')
finish=mid[fa:];mid=mid[:fa]
mid=mid.replace('        if (!pairs.empty()) sort_by_distance(s, states_by_distance);','''        if(!pairs.empty()) {
            // Only distance zero is eligible when the strict limit is one.
            if(base_generic==1){states_by_distance.state={uint16_t(s)};states_by_distance.distance={0};}
            else sort_by_distance(s,states_by_distance);
        }''')
s=s[:a]+finish+'        if(base_generic>0) {\n'+mid+s[b:]
a=s.index('        for (const auto& item : picks) {',a)
s=s[:a]+'        }\n'+s[a:]
p=root/'solutions/deval-pairskip6';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n2枚の補助紙はgeneric移動数を厳密に減らす候補しか受理しない。移動数0では2枚候補の作成を省く。移動数1では距離0の現在の並びだけを渡し、720状態の距離順整列を省く。単独補助紙の処理は従来通り。候補順と浮動小数点演算は保つ。GCC/Clangのstdout照合と24並列compareで検証する。\n')
assert len(s.encode())<=522000;print(len(s.encode()))
