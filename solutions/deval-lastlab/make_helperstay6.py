from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
a='''    Pick best(int s, const Helper& h,const std::vector<double>& future) const {
        CF_SCOPE(single_helper);  // the nearest goal (deeper on ties)
        Pick b{h.paper, -1, 0, 255};
        for (auto g : h.goals) {
            const int d = comp->distance(s, g.state);
            if(d<b.distance || (d==b.distance && (future[g.state]<future[b.goal] || (future[g.state]==future[b.goal] && g.depth>b.depth))))b={h.paper,g.state,g.depth,d};
        }
        return b;
    }'''
b='''    Pick best(int s, const Helper& h,const std::vector<double>& future,double below_charge) const {
        CF_SCOPE(single_helper);  // Same-distance goals use existing terminal terms.
        Pick b{h.paper, -1, 0, 255};double value=1e100;
        for (auto g : h.goals) {
            const int d = comp->distance(s, g.state);
            const double v=.5*future[g.state]+(g.depth==GM?below_charge:0.);
            if(d<b.distance || (d==b.distance && (v<value || (v==value && g.depth>b.depth)))) {
                b={h.paper,g.state,g.depth,d};value=v;
            }
        }
        return b;
    }'''
assert s.count(a)==1;s=s.replace(a,b)
a='auto pk = interleave->best(s, h, future);';assert s.count(a)==1
s=s.replace(a,'auto pk = interleave->best(s, h, future, kStayStrength*(.3-stay_table[h.paper][0].probability));')
p=root/'solutions/deval-helper-staygoal';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-helpeq1`。

同じgeneric移動数のhelper goalを選ぶとき、既存のgeneric terminal value (`0.5*future`) に、helperがgeneric最下段より下へ入る場合の既存filler_charge差 (`kStayStrength*(0.3-stay probability)`) を加える。近い距離を優先する条件は同じ。係数や模型項を新しく学習せず、実際のplan_costが使う項を同手数のgoal選択へ反映する。同距離helperは上位1件、他の候補数・設計・時計に依存しない予算・ログを保つ。
''');print(len(s.encode()))
