from pathlib import Path
p=Path('solutions/argon-req-oldvalue-oracle')
s=Path('solutions/argon-req-oldvalue-fix/main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b,1)
sub('''                if (opt.old_value == 2 && covers(x, c)) value += returned.fixes - fix[c];''','''                if (opt.old_value % 2 == 0 && covers(x, c)) value += returned.fixes - fix[c];
                if (opt.old_value >= 3) value = .5 * (value + previous);''')
sub('''    Moves process(int u) {''','''    int old_force = -1;
    bool old_force_valid = false;
    std::array<uint8_t, K> old_forced_order{};
    std::vector<std::array<uint8_t, K>> old_raw_orders;
    Moves process(int u) {''')
sub('''        CF_SCOPE(process);
''','''        CF_SCOPE(process);
        old_force_valid = false;
        if (old_force < 0) old_raw_orders.clear();
''')
sub('''        if (d != top0) opts.push_back({1, 5, true, true, 2});''','''        if (old_force >= 0) opts = {{1, 5, true, true, old_force}};''')
sub('''        auto record_future = [&](double cost) {''','''        auto record_future = [&](double cost) {
            if (old_force < 0) old_raw_orders.push_back(order);''')
sub('''        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''','''        if (old_force < 0 && interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''')
sub('''        if (best > 1e17) {
            plan_failures++;''','''        if (best > 1e17) {
            if (old_force >= 0) { invalid = true; return {}; }
            plan_failures++;''')
sub('''        restore(best_state);
        canonicalize();''','''        old_force_valid = true;
        old_forced_order = best_state.order;
        restore(best_state);
        canonicalize();''')
sub('''    long long total = 0, generic = 0, wrong = 0;''','''    auto oracle = std::make_unique<Solver>(solver);
    struct OldProbe {
        long long valid = 0, raw_existing = 0, same = 0, better = 0, moves = 0;
        double gain = 0;
    } probes[5];
    long long residual_better = 0, residual_moves = 0, residual_ceiling = 0;
    double residual_gain = 0;
    long long total = 0, generic = 0, wrong = 0;''')
sub('''        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;''','''        const auto initial = solver.save();
        auto moves = solver.process(u);
        if (solver.ded[u] != initial.top_d) {
            const double actual = solver.plan_cost(moves.size());
            double current_best = actual, best = actual;
            int current_moves = moves.size(), best_moves = moves.size();
            int current_fewest = moves.size(), fewest = moves.size();
            for (int mode = 0; mode < 5; mode++) {
                oracle->restore(initial);
                oracle->old_force = mode;
                const auto path = oracle->process(u);
                if (!oracle->old_force_valid || oracle->display() != state.A[u] || !oracle->fillers_reachable()) continue;
                const double value = oracle->plan_cost(path.size());
                auto& stats = probes[mode];
                stats.valid++;
                stats.raw_existing += std::find(solver.old_raw_orders.begin(), solver.old_raw_orders.end(),
                                               oracle->old_forced_order) != solver.old_raw_orders.end();
                stats.same += oracle->order == solver.order;
                stats.better += value < actual - 1e-9;
                stats.gain += std::max(0.0, actual - value);
                if (value < actual - 1e-9) stats.moves += int(moves.size()) - int(path.size());
                if (mode == 0) {
                    current_fewest = std::min(current_fewest, int(path.size()));
                    if (value < current_best) current_best = value, current_moves = path.size();
                    best = current_best; best_moves = current_moves; fewest = current_fewest;
                } else {
                    fewest = std::min(fewest, int(path.size()));
                    if (value < best - 1e-9) best = value, best_moves = path.size();
                }
            }
            residual_better += best < current_best - 1e-9;
            residual_gain += current_best - best;
            residual_moves += current_moves - best_moves;
            residual_ceiling += current_fewest - fewest;
            if (best < current_best - 1e-9)
                std::cerr << "old_probe_gain_" << r << " = " << current_best - best
                          << "\\nold_probe_moves_" << r << " = " << current_moves - best_moves << '\\n';
        }
        req_sec += elapsed_sec() - t_req;''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    for (int mode = 0; mode < 5; mode++) {
        const std::string prefix = "old_probe_" + std::to_string(mode) + '_';
        const auto& p = probes[mode];
        std::cerr << prefix << "valid = " << p.valid << '\\n'
                  << prefix << "raw_existing = " << p.raw_existing << '\\n'
                  << prefix << "same = " << p.same << '\\n'
                  << prefix << "better = " << p.better << '\\n'
                  << prefix << "gain = " << p.gain << '\\n'
                  << prefix << "moves = " << p.moves << '\\n';
    }
    std::cerr << "old_probe_residual_better = " << residual_better
              << "\\nold_probe_residual_gain = " << residual_gain
              << "\\nold_probe_residual_moves = " << residual_moves
              << "\\nold_probe_residual_ceiling = " << residual_ceiling << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-req-filldp-positive

R2の旧紙価値の測定専用版。実際の出力は基準のまま、同じ開始状態の別Solverで共同DPの計画を後処理まで単独で仕上げる。mode 0は採用済みの共同DP、1は旧紙の価値差、2は返却による自列の色修正の補正も含むもの、3/4はそれぞれ従来重みとの中間。将来の注文は読まない。

old_probe_<mode>のvalid/raw_existing/same/better/gain/movesは有効計画数、初期積層が既存候補にもある数、完成積層が基準と同じ数、完成評価値改善数、その改善合計、その場合の即時手数差。residual_*はmode 0も十分処理した場合に比べて、旧紙重みの4案を追加した残りの改善。ceilingは手数だけを見て選ぶ楽観値。

既存ログ・スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは削除。測定版は固定設計で使う。通常評価で時間超過となる場合は--no-recordとする。
''')
