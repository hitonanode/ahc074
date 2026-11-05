from pathlib import Path
p=Path('solutions/argon-req-completevalue');p.mkdir()
s=Path('solutions/argon-req-filldp-positive/main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n','                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n','              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n','              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
 sub(line,'')
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;','long long value_filler_trials = 0;')
sub('        bool value_fillers = false;  // joint DP also tries the marginal stack value','        bool value_fillers = false;  // joint DP also tries the marginal stack value\n        bool complete_value = false;')
sub('    void run_joint(int u, const PlanOpt& opt) {','''    long long complete_value_calls = 0, complete_value_invalid = 0, complete_value_plans = 0;
    double completed_filler_cost(int u, u64 hh, int c = -1, int depth = 0, int level = 0) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;
        invalid = false;
        if (c >= 0) place_filler(c, depth, level, hh);
        if (!invalid) fix_handles(u, hh);
        const double cost = invalid ? 1e30 : plan_cost(ops.size() - nops);
        ++complete_value_calls;
        complete_value_invalid += invalid;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return cost;
    }
    void run_joint(int u, const PlanOpt& opt) {''')
sub('''        auto fix = fix_costs(u, hh);
        const bool d_out''','''        auto fix = fix_costs(u, hh);
        const double completed_reference = opt.complete_value ? completed_filler_cost(u, hh) : 1e30;
        const bool d_out''')
sub('                        gain -= filler_value_increment(c, depth, lv, before_value);','''                        if (opt.complete_value && completed_reference < 1e29)
                            gain = completed_reference - completed_filler_cost(u, hh, c, depth, lv);
                        else gain -= filler_value_increment(c, depth, lv, before_value);''')
sub('        if (d != top0) opts.push_back({1, 5, true, true});','''        if (d != top0) opts.push_back({1, 5, true, true});
        if (d != top0) opts.push_back({1, 5, true, true, true});''')
sub('q.opt.value_fillers == o.value_fillers) { repeated = &q; break; }','q.opt.value_fillers == o.value_fillers && q.opt.complete_value == o.complete_value) { repeated = &q; break; }')
sub('''            record_future(cost);
            if (cost < best)''','''            complete_value_plans += o.complete_value;
            record_future(cost);
            if (cost < best)''')
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "complete_value_calls = " << solver.complete_value_calls
              << "\\ncomplete_value_invalid = " << solver.complete_value_invalid
              << "\\ncomplete_value_plans = " << solver.complete_value_plans << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-req-filldp-positive

R2の追加検証。新規フィラーの価値を、取り出した直後ではなく、そのフィラーが覆わないハンドルを修正した後の積層で比べる。全ハンドルを修正する仮計画と、その候補を配置して残りを修正する仮計画のplan_cost差を共同DPの重みとする。元の整数利得が正の候補だけを対象にし、基準の全計画も残す。

仮計画では表示・可視性の最終検査を省くが、状態・操作列・ラベルは復元する。基準側の仮修正が不可能な場合は従来の重みに戻す。実際の追加計画は通常の可視性・表示・回収可能性検査を通す。目的関数・設計・後処理予算は変更しない。

complete_value_calls/invalid/plansは完成後の局所価値を調べた数、仮修正ができなかった数、有効な追加計画数。既存ログ・スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは削除する。新規環境変数はない。
''')
