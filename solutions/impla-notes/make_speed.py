"""設計時間の節約案。どちらも出力を変え得るので通常比較する。"""
from make_small import BASE, replace, write

s=BASE
s=replace(s,'    DesignState warm_state;', '''    DesignState warm_state;
#ifdef LOCAL_BENCH
    const bool perf_after_select=env_real("D30A_PERF_AFTER",1)!=0;
#else
    constexpr bool perf_after_select=true;
#endif
    int perf_branch_chosen=-1;''')
s=replace(s,'    if(!raw && extra!=2) {','    if(!raw && extra!=2 && extra!=3) {')
s=replace(s,'    if(raw)return state;', '''    // Branches are ranked after climb + early rematch. Only the selected
    // branch runs perforation + late rematch; extra=3 resumes those two stages.
    if(raw || (perf_after_select && extra==0))return state;''')
s=replace(s,'    // Repeat the full native finishing from the best completed assignment.', '''    if(perf_after_select && best_assignment) {
        perf_branch_chosen=chosen;
        const std::string branch_log=chosen_log;
        const int branch_count=finished;
        des=std::make_unique<Design>(*best_assignment);
        deval_salt=first_salt+perf_branch_chosen;
        best=1e100;
        complete(perf_branch_chosen,3);
        finished=branch_count;  // The extra V call refines the same candidate.
        chosen_log=branch_log+chosen_log;
    }
    // Repeat the full native finishing from the best completed assignment.''')
s=replace(s,'    std::cerr << chosen_log;','''    std::cerr << chosen_log;
    std::cerr<<"perf_branch_chosen = "<<perf_branch_chosen
             <<"\\nperf_full_candidates = "<<(perf_after_select?finished-3:finished)<<'\\n';''')
write('perf-select',s,'''4 つの焼きなまし分岐を filler_climb と最初の再割り当てまで仕上げ、穴あけ前の V で 1 分岐を選ぶ。その分岐だけ穴あけ・後段の再割り当てを実行して V を計算し直す。選んだ分岐の乱数状態と salt を引き継ぐ。後続の 5 回の仕上げは元と同じで、毎回現在の最良候補を出発点にする。選ばれなかった 3 分岐の重い仕上げを省く。

全 9 候補を評価し、V は選んだ分岐の仕上げ後にもう 1 回評価する。dv_first は最初の分岐の穴あけ前の値、dv_best は従来と同じ完成設計の値。chosen_log は選んだ分岐の前半と後半をまとめ、後続候補が勝てばその候補のログに置き換える。

LOCAL_BENCH の D30A_PERF_AFTER=0 で元の全分岐仕上げに戻る。新指標 perf_branch_chosen は穴あけ前に選んだ分岐番号（0〜3、切替無効時 -1）、perf_full_candidates は穴あけと後段再割り当てを行う候補数（通常 6、元は 9）。DEVAL_DUMP_FEATURES=1 では選んだ分岐の @deval_final が前後の 2 回出る。''')

s=BASE
s=replace(s,'    constexpr double kWindowRate = 0.6;', '''#ifdef LOCAL_BENCH
    const double kWindowRate = env_real("D30A_WINDOW_RATE",0.45);
#else
    constexpr double kWindowRate = 0.45;
#endif''')
s=replace(s,'constexpr int kMapIters = int(450000 * ITER_SCALE)',
          'constexpr int kMapIters = int(490000 * ITER_SCALE)')
write('wr45',s,'''窓割り当ての役割交換の提案割合 kWindowRate を 0.6 から 0.45 に下げる。安い transfer 提案の割合を増やし、同じ時間で多く探索する狙い。既定 MAP_ITERS は 450000 から 490000 に増やす（提案段階の時間測定から約 9% を戻す）。gopt と後続の設計・注文処理は変更しない。

LOCAL_BENCH の D30A_WINDOW_RATE で提案割合、既存の MAP_ITERS で固定反復数を指定できる。元の設定は D30A_WINDOW_RATE=0.6、MAP_ITERS=450000。新しい stderr 指標はない。gobj_after、map_end_sec、dv_best とスコアで効果を見る。''')
