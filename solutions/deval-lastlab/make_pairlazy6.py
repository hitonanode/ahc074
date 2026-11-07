from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-paireq1/main.cpp').read_text()
a='''        const int base_generic = comparator.plan(current, A[u], ~paper[d].opaque & gmask).size();'''
b='''        const auto normal_generic=comparator.plan(current,A[u],~paper[d].opaque & gmask);
        const int base_generic=normal_generic.size();
        const bool normal_valid=normal_generic.empty() || normal_generic.front().first>=0;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''            auto pk = best_interleave_pair(states_by_distance, u, pp.x, pp.y, base_generic + 1);
            if (pk.goal >= 0) pair_picks.push_back({pp.estimate + pk.distance, pk});'''
b='''            auto pk = best_interleave_pair(states_by_distance,u,pp.x,pp.y,base_generic+!normal_valid);
            // A legal ordinary goal also works with both helpers below all generic sheets.
            // Thus a failed strict search has exact distance base_generic; defer its goal.
            if(pk.goal<0 && normal_valid)pk={pp.x,pp.y,-2,M,M,base_generic};
            if(pk.goal>=0 || pk.goal==-2)pair_picks.push_back({pp.estimate+pk.distance,pk});'''
assert s.count(a)==1;s=s.replace(a,b)
a='''        if (pair_picks.size() > 6) pair_picks.resize(6);
        auto finish = [&]() {'''
b='''        if (pair_picks.size() > 6) pair_picks.resize(6);
        for(auto& item:pair_picks)if(item.second.goal==-2) {
            auto& p=item.second;p=best_interleave_pair(states_by_distance,u,p.upper,p.lower,base_generic+1);
            assert(p.goal>=0);
        }
        auto finish = [&]() {'''
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-paireq-lazy';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-paireq1`。

2枚helperの同generic距離候補のgoal探索を遅らせる。普通のgeneric計画が合法なら、そのgoalで2枚ともgenericの直下に置くことができる。このため「厳密に少ない距離の解がない」ことを調べた時点で、最少距離が通常と同じであることは確定する。まず距離と元の見積りだけで全候補を元と同じ順で整列・制限し、残った同距離候補1件だけのgoalを探索する。普通の計画が不正な場合は従来と同じ探索を行う。比較するkey、同点の並び、採用するgoalと実際の計画は変えない。プロフィール・統計・注釈・実験スイッチを保ち、時計による切替えはしない。
''');print(len(s.encode()))
