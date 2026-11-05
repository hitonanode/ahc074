from pathlib import Path
import sys
name=sys.argv[1];p=Path('solutions')/name
s=Path('solutions/argon-req-filldp-joint-fast/main.cpp').read_text()
s=s.replace('''    Moves process(int u) {''','''    bool value_filler_probe = false;
    Moves process(int u) {''',1)
s=s.replace('''        if (d != top0) opts.push_back({1, 5, true, true});''','''        if (value_filler_probe && d != top0) opts.push_back({1, 5, true, true});''',1)
s=s.replace('''    long long total = 0, generic = 0, wrong = 0;''','''    auto oracle = std::make_unique<Solver>(solver);
    oracle->value_filler_probe = true;
    long long r2_same = 0, r2_better = 0, r2_worse = 0, r2_neutral = 0;
    long long r2_move_gain = 0, r2_ceiling_moves = 0;
    double r2_final_gain = 0, r2_final_loss = 0;
    long long total = 0, generic = 0, wrong = 0;''',1)
s=s.replace('''        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;''','''        const auto initial = solver.save();
        auto moves = solver.process(u);
        oracle->restore(initial);
        const auto extra = oracle->process(u);
        const double value = solver.plan_cost(moves.size()), alternative = oracle->plan_cost(extra.size());
        const bool better = alternative < value - 1e-9, worse = alternative > value + 1e-9;
        const bool same = oracle->order == solver.order;
        r2_same += same;
        r2_better += better;
        r2_worse += worse;
        r2_neutral += !same && !better && !worse;
        r2_final_gain += std::max(0.0, value - alternative);
        r2_final_loss += std::max(0.0, alternative - value);
        r2_move_gain += better * (int(moves.size()) - int(extra.size()));
        r2_ceiling_moves += std::max(0, int(moves.size()) - int(extra.size()));
        if (better || worse || !same) {
            std::cerr << "r2_oracle_value_" << r << " = " << value - alternative << '\\n'
                      << "r2_oracle_moves_" << r << " = " << int(moves.size()) - int(extra.size()) << '\\n';
        }
        req_sec += elapsed_sec() - t_req;''',1)
s=s.replace('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "r2_oracle_same = " << r2_same << "\\nr2_oracle_better = " << r2_better
              << "\\nr2_oracle_worse = " << r2_worse << "\\nr2_oracle_neutral = " << r2_neutral
              << "\\nr2_oracle_value_gain = " << r2_final_gain << "\\nr2_oracle_value_loss = " << r2_final_loss
              << "\\nr2_oracle_move_gain = " << r2_move_gain << "\\nr2_oracle_ceiling_moves = " << r2_ceiling_moves
              << "\\nr2_oracle_zero_trials = " << oracle->value_filler_zero
              << "\\nr2_oracle_zero_useful = " << oracle->value_filler_zero_useful
              << "\\nr2_oracle_zero_picks = " << oracle->value_filler_zero_picks
              << "\\nr2_oracle_zero_better = " << oracle->value_filler_zero_better << '\\n';
''',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/esw-slim

R2の基準軌跡上の測定版。実際の出力と積層は基準のまま、同じ開始状態の別Solverで状態価値付き共同DPを追加した探索を最後まで行う。未来の注文は読まない。

r2_oracle_same/better/worse/neutralは、完成後の積層一致・目的関数改善・悪化・同値の別積層の注文数。value_gain/lossは改善/悪化の評価値の和、move_gainは評価値が良い時の即時手数差、ceiling_movesは手数だけ見て良い方を選ぶ楽観値。zero_*は利得0区間の検討・有望・選択数。注文単位のvalue/movesも記録する。

既存ログ・スイッチ・プロファイラは保持。測定の時間を含むため時間超過の通常評価では--no-recordを用いる。設計固定の測定を想定する。
''')
