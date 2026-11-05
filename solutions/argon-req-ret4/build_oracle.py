from pathlib import Path
s=Path('solutions/argon-req-ret4-all/main.cpp').read_text()
s=s.replace('    Moves process(int u) {','    int r1_force_mode = -1;  // -1: baseline; 1/4: force this keep-filler seed for measurement\n    bool r1_force_valid = false;\n    Moves process(int u) {',1)
s=s.replace('        CF_SCOPE(process);', '        CF_SCOPE(process);\n        r1_force_valid = false;', 1)
s=s.replace('        restore(best_state);\n        canonicalize();', '        r1_force_valid = true;\n        restore(best_state);\n        canonicalize();', 1)
s=s.replace('const bool r1_eligible = r1_color_safe && (!ARGON_R1_NEW_ONLY || r1_extension);','const bool r1_eligible = r1_force_mode == 0 && r1_color_safe && (!ARGON_R1_NEW_ONLY || r1_extension);',1)
s=s.replace('''        double best = 1e18, best_normal = 1e18;''','''        if (r1_force_mode > 0) opts = {{4, r1_force_mode, true}};
        double best = 1e18, best_normal = 1e18;''',1)
s=s.replace('''        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''','''        if (r1_force_mode <= 0 && interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''',1)
s=s.replace('''        if (best > 1e17) {
            plan_failures++;''','''        if (best > 1e17) {
            if (r1_force_mode > 0) { invalid = true; return {}; }
            plan_failures++;''',1)
s=s.replace('''    long long total = 0, generic = 0, wrong = 0;''','''    auto oracle = std::make_unique<Solver>(solver);
    struct OracleStats {
        long long requests = 0, valid = 0, same_order = 0, better = 0, move_better = 0;
        double value_gain = 0, optimistic_moves = 0, selected_moves = 0;
    } oracle_all, oracle_extension;
    long long total = 0, generic = 0, wrong = 0;''',1)
s=s.replace('''        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;''','''        const bool can_keep = solver.can_keep_previous(u);
        const bool extension = can_keep && (solver.gmask & ~solver.paper[solver.ded[u]].opaque
                                            & solver.paper[solver.top_d].opaque);
        Solver::State initial;
        if (can_keep) initial = solver.save();
        auto moves = solver.process(u);
        if (can_keep) {
            const double baseline_value = solver.plan_cost(moves.size());
            double best_value = baseline_value;
            int best_moves = moves.size(), fewest = moves.size();
            bool valid = false, same_order = false;
            for (int fm : {1, 4}) {
                if (fm == 4 && initial.fillers.empty()) continue;
                oracle->restore(initial);
                oracle->r1_force_mode = fm;
                auto path = oracle->process(u);
                if (!oracle->r1_force_valid || oracle->display() != state.A[u] || !oracle->fillers_reachable()) continue;
                valid = true;
                same_order |= oracle->order == solver.order;
                fewest = std::min(fewest, int(path.size()));
                const double cost = oracle->plan_cost(path.size());
                if (cost < best_value - 1e-9) best_value = cost, best_moves = path.size();
            }
            auto count = [&](OracleStats& s) {
                ++s.requests;
                s.valid += valid;
                s.same_order += same_order;
                s.better += best_value < baseline_value - 1e-9;
                s.move_better += fewest < int(moves.size());
                s.value_gain += baseline_value - best_value;
                s.optimistic_moves += int(moves.size()) - fewest;
                s.selected_moves += int(moves.size()) - best_moves;
            };
            count(oracle_all);
            if (extension) count(oracle_extension);
            if (best_value < baseline_value - 1e-9 || extension) {
                std::cerr << "r1_oracle_target_" << r << " = " << u << '\\n'
                          << "r1_oracle_extension_" << r << " = " << extension << '\\n'
                          << "r1_oracle_gain_" << r << " = " << baseline_value - best_value << '\\n'
                          << "r1_oracle_move_gain_" << r << " = " << int(moves.size()) - best_moves << '\\n';
            }
        }
        req_sec += elapsed_sec() - t_req;''',1)
s=s.replace('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    auto print_oracle = [](const char* prefix, const OracleStats& s) {
        std::cerr << prefix << "requests = " << s.requests << '\\n'
                  << prefix << "valid = " << s.valid << '\\n'
                  << prefix << "same_order = " << s.same_order << '\\n'
                  << prefix << "better = " << s.better << '\\n'
                  << prefix << "move_better = " << s.move_better << '\\n'
                  << prefix << "value_gain = " << s.value_gain << '\\n'
                  << prefix << "optimistic_moves = " << s.optimistic_moves << '\\n'
                  << prefix << "selected_moves = " << s.selected_moves << '\\n';
    };
    print_oracle("r1_oracle_all_", oracle_all);
    print_oracle("r1_oracle_extension_", oracle_extension);
''',1)
Path('solutions/argon-req-ret4-oracle/main.cpp').write_text(s)
Path('solutions/argon-req-ret4-oracle/README.md').write_text('''改良元: solutions/esw-slim

R1の測定専用版。実際の出力と次注文へ渡す積層は基準のまま、同じ開始状態の別Solverで「前の商品紙の据え置き」を初期計画に固定し、現在の後処理・中立探索を最後まで実行する。旧フィラーの返却と再利用の両方を試す。未来の注文は読まない。

全ての既存ログ・スイッチ・プロファイラは基準Solver側で維持する。新しい集計は `r1_oracle_all_*`（全ての色安全な据え置き）と `r1_oracle_extension_*`（色付き汎用窓により新たに許可された部分）。requests/valid/same_order/better/move_betterは注文数、value_gainは評価値の改善量、optimistic_movesは将来価値を無視して少ない手数だけ選んだ改善量、selected_movesは評価値で選んだ場合の即時手数差。注文単位のtarget/extension/gain/move_gainも出す。

測定コストを含むreq_secなので採用候補の時間評価には使わない。通常評価なら時間超過の測定版として--no-record、ここでは設計固定評価を使う。
''')
