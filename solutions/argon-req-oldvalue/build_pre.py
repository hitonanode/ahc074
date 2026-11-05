from pathlib import Path
p=Path('solutions/argon-req-prevalue')
s=Path('solutions/argon-req-filldp-positive/main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n',
             '                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n',
             '              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n',
             '              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
    sub(line,'')
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;',
    'long long value_filler_trials = 0;')
sub('''        bool value_fillers = false;  // joint DP also tries the marginal stack value
''','''        bool value_fillers = false;  // joint DP also tries the marginal stack value
        bool value_prelift = false;
''')
sub('''    void run_joint(int u, const PlanOpt& opt) {''','''    bool pre_value = false;
    long long pre_value_trials = 0, pre_value_stacks = 0, pre_value_plans = 0, pre_value_better = 0;
    double pre_value_gain = 0;
    double stack_value_increment(int cu, int du, int cl, int dl, int level, double before) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;
        invalid = false;
        u64 hh = 0;
        place_filler(cu, du, level, hh);
        place_filler(cl, dl, level, hh);
        const double delta = invalid ? 1e30 : plan_cost(0) - before;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return delta;
    }
    void run_joint(int u, const PlanOpt& opt) {''')
sub('''        CF_SCOPE(run_plan);
''','''        CF_SCOPE(run_plan);
        pre_value = opt.value_prelift;
''')
sub('''        if (!tail_cache_on || invalid) {''','''        if (!tail_cache_on || invalid || pre_value) {''')
sub('''        CF_SCOPE(choose_fillers);
        placement_chains.clear();''','''        CF_SCOPE(choose_fillers);
        const double before_value = pre_value ? plan_cost(0) : 0;
        placement_chains.clear();''')
sub('''                    int gain = save - kFillerCost - depth;
                    if (gain > 0) cand[c].push_back({lv, (double)gain, c, depth, 0, -1, post});''','''                    double gain = save - kFillerCost - depth;
                    if (pre_value && gain > 0) {
                        ++pre_value_trials;
                        gain -= filler_value_increment(c, depth, lv, before_value);
                    }
                    if (gain > 0) cand[c].push_back({lv, gain, c, depth, 0, -1, post});''')
sub('''                int gain = save - 2 * kFillerCost - U.depth - L.depth;
                if (gain < 1) continue;
                stacks.push_back''','''                double gain = save - 2 * kFillerCost - U.depth - L.depth;
                if (gain < 1) continue;
                if (pre_value) {
                    ++pre_value_stacks;
                    gain -= stack_value_increment(U.c, U.depth, L.c, L.depth, a, before_value);
                    if (gain <= 0) continue;
                }
                stacks.push_back''')
sub('''q.opt.value_fillers == o.value_fillers) { repeated = &q; break; }''','''q.opt.value_fillers == o.value_fillers && q.opt.value_prelift == o.value_prelift) { repeated = &q; break; }''')
sub('''        tail_cache_on = false;
        int source = 0''','''        if (best_normal < 1e17) {
            start_plan(st0);
            auto alternative = best_normal_opt;
            alternative.value_prelift = true;
            run_plan(u, alternative);
            if (!invalid && ops.size() <= 2 * K && display() == A[u] && fillers_reachable()) {
                ++pre_value_plans;
                const double cost = plan_cost(ops.size());
                record_future(cost);
                if (cost < best) {
                    ++pre_value_better;
                    pre_value_gain += best - cost;
                    best = cost; best_ops = ops; best_state = save();
                    OP_TAG(best_tags = op_tags;)
                }
            }
        }
        pre_value = false;
        tail_cache_on = false;
        int source = 0''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "pre_value_trials = " << solver.pre_value_trials
              << "\\npre_value_stacks = " << solver.pre_value_stacks
              << "\\npre_value_plans = " << solver.pre_value_plans
              << "\\npre_value_better = " << solver.pre_value_better
              << "\\npre_value_gain = " << solver.pre_value_gain << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-req-filldp-positive

R2の継続検証。通常の持ち上げ前DPにも状態価値を加える。最良の通常計画の返却方法で追加計画を1つ作り、元の計画は全て残す。新規フィラー1枚だけでなく2枚重ねについても仮配置後の状態価値の増分を区間の即時利得から引く。元の正利得の閾値を維持し、目的関数・設計・連鎖・後処理の予算を変えない。

追加計画はDPの重みが異なるので既存の尾部キャッシュを使わない。仮実行では積層・操作・ラベルを復元し、完成計画では通常の可視性・表示・回収可能性の検査を通す。

既存ログ・スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは削除。pre_value_trials/stacksは評価した単独/2枚重ねの区間数、plans/better/gainは有効な追加計画数・初期計画の最良値を改善した数・改善量の合計。新規環境変数はない。
''')
