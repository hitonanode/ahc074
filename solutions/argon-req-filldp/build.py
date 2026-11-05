from pathlib import Path
import sys

name = sys.argv[1] if len(sys.argv) > 1 else 'argon-req-filldp'
mode = int(sys.argv[2]) if len(sys.argv) > 2 else 1
p = Path('solutions') / name
assert p.is_dir(), 'Check ls solutions and create a new directory first'
s = Path('solutions/esw-slim/main.cpp').read_text()

def sub(a, b):
    global s
    assert a in s, a[:100]
    s = s.replace(a, b, 1)

sub('        bool use_filler = false;\n    };', '        bool use_filler = false;\n        int r2_mode = 0;\n    };')
sub('    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {', '''    int r2_mode = 0;
    long long r2_intervals = 0, r2_zero = 0, r2_zero_profitable = 0;
    long long r2_alt_trials = 0, r2_alt_valid = 0, r2_alt_novel = 0, r2_raw_better = 0;
    double r2_raw_gain = 0;
    // Experimental weights: 1 also tries immediate ties; 2 charges the later return;
    // 3 measures the change in the current stack value after extracting this paper.
    // The real plan is always scored and checked again after all its moves.
    double r2_weight(int gain, int c, int depth, int level) {
        if (!r2_mode || gain < 0) return gain;
        ++r2_intervals;
        r2_zero += gain == 0;
        if (r2_mode == 1) return gain + 1e-5;
        std::vector<int> top;
        column_tops(c, depth + 1, top);
        if (depth >= int(top.size())) return -1e30;
        const int f = top[depth];
        if (r2_mode == 2)
            return gain - kFillerCharge - kStayStrength * (.3 - stay_table[f][level].probability);
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        const double before = plan_cost(0);
        check_vis = false;
        invalid = false;
        u64 hh = 0;
        place_filler(c, depth, level, hh);
        const double delta = invalid ? 1e30 : plan_cost(0) - before;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        r2_zero_profitable += gain == 0 && gain - delta > 1e-9;
        return gain - delta;
    }
    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) {''')
sub('''                int gain = save - kFillerCost - depth;
                if (gain > 0) cand[c].push_back({lvl, (double)gain, c, depth});''', '''                double gain = r2_weight(save - kFillerCost - depth, c, depth, lvl);
                if (gain > 0) cand[c].push_back({lvl, gain, c, depth});''')
sub('''                    int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    if (g >= kFillerCost) cand[c].push_back({lv, (double)g, c, 0, 0, f, post});''', '''                    const int raw = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    const double g = r2_weight(raw, c, depth, lv);
                    if (r2_mode ? g > 0 : raw >= kFillerCost)
                        cand[c].push_back({lv, g, c, 0, 0, f, post});''')
sub('''                    int gain = save - kFillerCost - depth;
                    if (gain > 0) cand[c].push_back({lv, (double)gain, c, depth, 0, -1, post});''', '''                    double gain = r2_weight(save - kFillerCost - depth, c, depth, lv);
                    if (gain > 0) cand[c].push_back({lv, gain, c, depth, 0, -1, post});''')
sub('''        CF_SCOPE(run_plan);
        if (opt.fret_mode == 5)''', '''        CF_SCOPE(run_plan);
        r2_mode = opt.r2_mode;
        if (opt.fret_mode == 5)''')
sub('        if (!tail_cache_on || invalid) {', '        if (!tail_cache_on || invalid || r2_mode) {')
sub('''        double best = 1e18, best_normal = 1e18;''', f'''        const auto original_opts = opts;
        for (auto o : original_opts) {{ o.r2_mode = {mode}; opts.push_back(o); }}
        double r2_baseline_best = 1e18;
        std::vector<std::array<uint8_t, K>> r2_orders;
        double best = 1e18, best_normal = 1e18;''')
sub('''if (q.opt.fret_mode == o.fret_mode && q.opt.use_filler == o.use_filler) { repeated = &q; break; }''', '''if (q.opt.fret_mode == o.fret_mode && q.opt.use_filler == o.use_filler && q.opt.r2_mode == o.r2_mode) { repeated = &q; break; }''')
sub('''        for (const PlanOpt& o : opts) {
            start_plan(st0);''', '''        for (const PlanOpt& o : opts) {
            if (o.r2_mode) ++r2_alt_trials;
            start_plan(st0);''')
sub('''            double cost = plan_cost(ops.size());
            record_future(cost);''', '''            double cost = plan_cost(ops.size());
            if (!o.r2_mode) {
                r2_baseline_best = std::min(r2_baseline_best, cost);
                r2_orders.push_back(order);
            } else {
                ++r2_alt_valid;
                r2_alt_novel += std::find(r2_orders.begin(), r2_orders.end(), order) == r2_orders.end();
                if (cost < r2_baseline_best - 1e-9) ++r2_raw_better, r2_raw_gain += r2_baseline_best - cost;
            }
            record_future(cost);''')
sub('''if (o.fret_mode != 5 && cost < best_normal)''', '''if (!o.r2_mode && o.fret_mode != 5 && cost < best_normal)''')
sub('''        tail_cache_on = false;
        int source = 0''', '''        tail_cache_on = false;
        r2_mode = 0;
        int source = 0''')
sub('''    // ==== main: statistics ====
''', '''    // ==== main: statistics ====
    std::cerr << "r2_intervals = " << solver.r2_intervals << "\\nr2_zero = " << solver.r2_zero
              << "\\nr2_zero_profitable = " << solver.r2_zero_profitable
              << "\\nr2_alt_trials = " << solver.r2_alt_trials << "\\nr2_alt_valid = " << solver.r2_alt_valid
              << "\\nr2_alt_novel = " << solver.r2_alt_novel << "\\nr2_raw_better = " << solver.r2_raw_better
              << "\\nr2_raw_gain = " << solver.r2_raw_gain << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/esw-slim

R2の整数フィラー閾値の検証。既存の計画を全て保ち、別の重みでフィラー区間DPを解く計画を追加する。
今回のモードは{mode}（1: 即時利得0も微小な正の重みで選ぶ、2: 将来の返却費用を引く、3: 紙を取り出した時の状態価値変化も引く）。目的関数plan_costは変更しない。追加計画も従来の可視性・表示・回収可能性の検査を通す。既存のログ・実験スイッチ・プロファイラは維持する。

追加計画の尾部は重みが違うので基準の尾部キャッシュを使わない。同じ返却方法の重複除去はDPモードも区別する。連鎖・ヘルパーと既存の二枚重ね候補は基準どおり。

追加指標 `r2_intervals/zero/zero_profitable` は調べた非負利得区間・そのうち利得0・状態価値を含めて正になった利得0区間の延べ数。`r2_alt_trials/valid/novel` は追加計画の試行・有効・既存の初期計画と異なる積層の延べ数。`r2_raw_better/raw_gain` は後処理前の最良既存計画を上回った延べ数・評価値差の和（完成計画の利得ではない）。
''')
