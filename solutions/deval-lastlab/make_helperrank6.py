from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper-future/main.cpp').read_text()
for pair in [False,True]:
    x=s.replace('double score = pk.distance + dep + 1.8;','double score = pk.distance + dep + 1.8 + .5*future[pk.goal];')
    x=x.replace('pair_picks.push_back({pp.estimate + pk.distance, pk});','pair_picks.push_back({pp.estimate + pk.distance + .5*future[pk.goal], pk});')
    if pair:
        x=x.replace('    std::vector<double> future;','    std::vector<double> future;\n    std::vector<int> helper_goal_order;')
        old='''        if (cnt)
            for (auto& f : future) f /= cnt;'''
        new=old+'''
        helper_goal_order.resize(n);std::iota(helper_goal_order.begin(),helper_goal_order.end(),0);
        std::stable_sort(helper_goal_order.begin(),helper_goal_order.end(),[&](int a,int b){return future[a]<future[b];});'''
        assert x.count(old)==1;x=x.replace(old,new)
        old='''        for (int s = 0; s < n; s++) {
            const int d = comparator.distance(source, s), at = start[d]++;'''
        new='''        // Preserve minimum distance, then prefer the lower existing terminal value.
        for (int s : helper_goal_order) {
            const int d = comparator.distance(source, s), at = start[d]++;'''
        assert x.count(old)==1;x=x.replace(old,new)
    name='deval-helper-'+('pairfuture' if pair else 'rankfuture')
    p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
    (p/'README.md').write_text('改良元: `solutions/deval-helper-future`。\n\n単独/2枚helperの実行前の候補順位に、既存のgeneric末端価値future×0.5を加える。候補数と距離条件は維持する。'+('2枚helperの最少distance内でもfutureの低い状態を先に調べる。状態の優先順はinit_lookaheadで一度だけ安定整列し、距離別のbucketへの投入順に使う。' if pair else '')+'最終のplan_cost、設計、予算は変えない。時計による切替えはない。\n')
    assert len(x.encode())<=522000;print(name,len(x.encode()))
