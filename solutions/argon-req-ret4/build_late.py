from pathlib import Path
s=Path('solutions/esw-slim/main.cpp').read_text()
full=Path('solutions/argon-req-ret4/main.cpp').read_text()
start=full.index('    bool can_keep_previous(int u) const {')
end=full.index('    struct PlanOpt {',start)
s=s.replace('    struct PlanOpt {',full[start:end]+'    struct PlanOpt {',1)
start=full.index('        if (opt.ret_mode == 4) {',full.index('    void run_plan(int u,'))
end=full.index('        if (top_d >= 0 && opt.ret_mode == 3)',start)
s=s.replace('        if (top_d >= 0 && opt.ret_mode == 3)',full[start:end]+'        if (top_d >= 0 && opt.ret_mode == 3)',1)
s=s.replace('''        set_generic(u, holes);
        u64 hh = holes & ~gmask & ~pre_cov;''','''        // A kept product may cover correct generic holes as well as handles.
        set_generic(u, holes & ~pre_cov);
        u64 hh = holes & ~gmask & ~pre_cov;''',1)
s=s.replace('''    Moves process(int u) {
        CF_SCOPE(process);''','''    bool keep_seed_valid = false;
    Moves process_core(int u, int keep_fm = 0) {
        CF_SCOPE(process);
        keep_seed_valid = false;''',1)
s=s.replace('OP_TAG(if (neutral_enabled) ++request_counter;)','OP_TAG(if (neutral_enabled && !keep_fm) ++request_counter;)',1)
s=s.replace('''        double best = 1e18, best_normal = 1e18;''','''        if (keep_fm) opts = {{4, keep_fm, true}};
        double best = 1e18, best_normal = 1e18;''',1)
s=s.replace('''        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''','''        if (!keep_fm && interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''',1)
s=s.replace('''        if (best > 1e17) {
            plan_failures++;''','''        if (best > 1e17) {
            if (keep_fm) { invalid = true; return {}; }
            plan_failures++;''',1)
s=s.replace('''        restore(best_state);
        canonicalize();''','''        keep_seed_valid = true;
        restore(best_state);
        canonicalize();''',1)
marker='''        return chosen_path;
    }
};

// ==== Emergency design ===='''
extra='''        return chosen_path;
    }
#ifndef ARGON_R1_LATE_NO_LONGER
#define ARGON_R1_LATE_NO_LONGER 0
#endif
    long long r1_late_requests = 0, r1_late_trials = 0, r1_late_valid = 0, r1_late_selected = 0;
    long long r1_late_saved = 0;
    double r1_late_gain = 0;
    Moves process(int u) {
        // Keep the ordinary search intact: extra seeds cannot evict its candidates or change its ties.
        const bool eligible = can_keep_previous(u) &&
            (gmask & ~paper[ded[u]].opaque & paper[top_d].opaque);
        State initial;
        if (eligible) initial = save();
        Moves best_path = process_core(u);
        if (!eligible || !keep_seed_valid) return best_path;
        ++r1_late_requests;
        State best_state = save();
        OP_TAG(auto best_tags = op_tags;)
        const int initial_moves = best_path.size();
        const double initial_value = plan_cost(best_path.size());
        double best_value = initial_value;
        bool changed = false;
        for (int fm : {1, 4}) {
            if (fm == 4 && initial.fillers.empty()) continue;
            ++r1_late_trials;
            restore(initial);
            auto path = process_core(u, fm);
            if (!keep_seed_valid || display() != A[u] || !fillers_reachable()) continue;
            ++r1_late_valid;
            if (ARGON_R1_LATE_NO_LONGER && int(path.size()) > initial_moves) continue;
            const double value = plan_cost(path.size());
            if (value >= best_value - 1e-9) continue;
            best_value = value;
            best_state = save();
            best_path = std::move(path);
            OP_TAG(best_tags = op_tags;)
            changed = true;
        }
        restore(best_state);
        OP_TAG(op_tags = std::move(best_tags);)
        r1_late_selected += changed;
        r1_late_saved += initial_moves - int(best_path.size());
        r1_late_gain += initial_value - best_value;
#ifdef LOCAL_BENCH
        if (changed && search_config().predict)
            heavy_log += "r1_late_gain_" + std::to_string(request_counter - 1) + " = "
                + trace_value(initial_value - best_value) + '\\n';
#endif
        return best_path;
    }
};

// ==== Emergency design ===='''
assert marker in s
s=s.replace(marker,extra,1)
s=s.replace('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "r1_late_requests = " << solver.r1_late_requests
              << "\\nr1_late_trials = " << solver.r1_late_trials << "\\nr1_late_valid = " << solver.r1_late_valid
              << "\\nr1_late_selected = " << solver.r1_late_selected << "\\nr1_late_saved = " << solver.r1_late_saved
              << "\\nr1_late_gain = " << solver.r1_late_gain << '\\n';
''',1)
for name,short in [('argon-req-ret4-late',0),('argon-req-ret4-late-short',1)]:
 p=Path('solutions',name)
 p.joinpath('main.cpp').write_text(s.replace('#define ARGON_R1_LATE_NO_LONGER 0',f'#define ARGON_R1_LATE_NO_LONGER {short}'))
 p.joinpath('README.md').write_text('''改良元: solutions/esw-slim

R1の色付き据え置き計画を、通常探索が終わった後で独立に後処理する。通常の候補を押し出さず、通常探索の完成計画と評価値が同点なら元の計画を維持する。汎用窓の順序だけ異なる同点状態を不用意に選ぶことを避ける。

今回の商品紙の全ての穴で前の商品紙が透明または正しい色であり、その紙が汎用穴を覆う場合だけ追加計画を作る。古いフィラーを返す／再利用する2系統を初期計画とし、それぞれ既存の後処理・中立探索を同じ予算で実行する。設計・目的関数・通常探索の予算は変更しない。

全ての既存ログ・スイッチ・プロファイラ・DesignStoreを維持する。探索の内部統計は追加探索も含む。@opsは選んだ操作列に対応し、追加探索でも注文番号は増やさない。

追加指標: r1_late_requests（対象注文数）、trials/valid（追加試行／有効な完成計画）、selected（完成計画を改善した注文数）、saved（採用時の即時手数削減合計）、gain（完成計画のplan_cost改善合計）。F3_HEAVY_PREDICTで採用した注文ごとのr1_late_gain_<注文番号>も出す。

ARGON_R1_LATE_NO_LONGER='''+str(short)+('''。通常の完成計画より即時手数が多い候補も評価値で選ぶ。
''' if short==0 else '''。通常の完成計画より即時手数が多い候補は採用しない。
'''))
