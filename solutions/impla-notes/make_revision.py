from pathlib import Path
from make_small import replace,write
s=Path('solutions/d30a-perf-select/main.cpp').read_text()
s=replace(s,'    int perf_branch_chosen=-1;','''#ifdef LOCAL_BENCH
    const int perf_keep=std::clamp(int(env_real("D30A_PERF_KEEP",2)),1,candidates);
#else
    constexpr int perf_keep=2;
#endif
    int perf_branch_chosen=-1,perf_raw_first=-1;
    std::array<std::unique_ptr<Design>,4> branch_assignments;
    std::array<double,4> branch_values{};
    std::array<std::string,4> branch_logs;''')
s=replace(s,'        if(!finished)first=v;','''        if(perf_after_select && extra==0 && id<candidates)branch_logs[id]=log.str();
        if(!finished)first=v;''')
s=replace(s,'        if(v<best){best=v;', '''        // Full branches are evaluated in raw-V order. Preserve the original
        // lower-id tie break so keeping all four reproduces the parent.
        if(v<best || (perf_after_select && extra==3 && v==best && id<chosen)){best=v;''')
s=replace(s,'        complete(i,0);','''        branch_values[i]=complete(i,0);
        if(perf_after_select)branch_assignments[i]=std::make_unique<Design>(*des);''')
old='''    if(perf_after_select && best_assignment) {
        perf_branch_chosen=chosen;
        const std::string branch_log=chosen_log;
        const int branch_count=finished;
        des=std::make_unique<Design>(*best_assignment);
        deval_salt=first_salt+perf_branch_chosen;
        best=1e100;
        complete(perf_branch_chosen,3);
        finished=branch_count;  // The extra V call refines the same candidate.
        chosen_log=branch_log+chosen_log;
    }'''
new='''    if(perf_after_select && best_assignment) {
        const int branch_count=finished;
        std::array<int,4> ranking{0,1,2,3};
        std::stable_sort(ranking.begin(),ranking.end(),[&](int a,int b){return branch_values[a]<branch_values[b];});
        perf_raw_first=ranking[0];
        best=1e100;
        for(int i=0;i<perf_keep;++i) {
            const int id=ranking[i];
            des=std::make_unique<Design>(*branch_assignments[id]);
            deval_salt=first_salt+id;
            complete(id,3);
            if(chosen==id)chosen_log=branch_logs[id]+chosen_log;
        }
        perf_branch_chosen=chosen;
        finished=branch_count;  // Extra V calls refine the same branch candidates.
    }'''
s=replace(s,old,new)
s=replace(s,'    // The original four candidates remain eligible throughout the search.',
'''    // The completed branches remain eligible throughout the search.''')
s=replace(s,'<<(perf_after_select?finished-3:finished)', '<<(perf_after_select?finished-candidates+perf_keep:finished)')
s=replace(s,'    std::cerr << "anneal_iters = " << total_iters;', '    std::cerr << "anneal_iters = " << total_iters;') if False else s
s=replace(s,'    std::cerr << "anneal_iters = " << total_iters << "\\nanneal_end_sec = "',
'''    std::cerr<<"perf_raw_first = "<<perf_raw_first<<'\\n';
    std::cerr << "anneal_iters = " << total_iters << "\\nanneal_end_sec = "''')
write('perf-top2',s,'''穴あけ前の V で4分岐を順位付けし、上位2分岐だけ穴あけと後段の再割り当てを行う。その完成後の V が良い分岐を、元と同じ5回の追加仕上げの出発点にする。分岐の乱数状態・salt・ログを保存して再開する。完成後のVが同点なら元と同じ小さい分岐番号を優先する。仕上げ候補の取り違えを抑えつつ、2分岐の後半処理を省く狙い。

LOCAL_BENCH の D30A_PERF_AFTER=0 は元の全候補仕上げ、D30A_PERF_KEEP は仕上げる分岐数（1〜4、既定2）。4は全分岐を仕上げる対照設定。新指標 perf_branch_chosen は完成後に選んだ分岐番号、perf_raw_first は穴あけ前の最良分岐番号、perf_full_candidates は全体で後半まで仕上げた候補数（既定7、元は9）。DEVAL_DUMP_FEATURES=1 は選んだ分岐を前後2回記録する。dv_first は最初の分岐の穴あけ前、dv_best は完成後の値。''')
p=Path('solutions/d30a-perf-top2/README.md');p.write_text(p.read_text().replace('新しい stderr 指標はない。評価と採否は','評価と採否は'))
s=Path('solutions/d30a-wr45/main.cpp').read_text();s=replace(s,'int(490000 * ITER_SCALE)','int(502000 * ITER_SCALE)')
write('wr45-equal',s,'''kWindowRate=0.45 とし、窓割り当ての既定反復数を502000にする。450000回・割合0.6の親と同じ設計時間を狙う。490000回でも約9ms余ったため、割合0.45での1反復あたり時間の見積りから12000回を追加する。他の反復数は変えない。

LOCAL_BENCH の D30A_WINDOW_RATE と MAP_ITERS で割合・反復数を指定できる。gobj_after、map_end_sec、dv_best で設計の変化を確認する。新しいstderr指標はない。''')
