from pathlib import Path
import sys

name=sys.argv[1] if len(sys.argv)>1 else 'argon-req-oldvalue'
mode=int(sys.argv[2]) if len(sys.argv)>2 else 1
p=Path('solutions')/name
assert p.is_dir()
s=Path('solutions/argon-req-filldp-positive/main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b,1)

# The merged version never measures a gain-zero candidate.
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;',
    'long long value_filler_trials = 0;')
for line in ['                        value_filler_zero += raw_gain == 0;\n',
             '                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n',
             '              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n',
             '              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
    sub(line,'')
sub('''        bool value_fillers = false;  // joint DP also tries the marginal stack value
''','''        bool value_fillers = false;  // joint DP also tries the marginal stack value
        int old_value = 0;  // 1: value old papers against a return; 2: also correct their own handle
''')
sub('''    void run_joint(int u, const PlanOpt& opt) {''','''    long long old_value_calls = 0, old_value_changed = 0, old_value_plans = 0, old_value_better = 0;
    double old_value_gain = 0;
    struct OldValue { double cost; int fixes; };
    // Compare returning one old paper with keeping/releveling it. Other papers
    // stay as they are in this local estimate; the full plan is verified later.
    OldValue old_paper_value(int x, int u, int level, bool keep, int return_mode) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;
        invalid = false;
        if (level < 0) {
            return_paper(x, u, return_mode);
        } else if (x == top_d) {
            top_d = -1;
            move_to_level(x, level, true, gen_harm(x, ded[u], u));
            fillers.push_back({x, level, col_of[x]});
        } else {
            for (auto& f : fillers) if (f.paper == x) f.lvl = level, f.hi = col_of[x];
            if (!keep) move_to_level(x, level, true, gen_harm(x, ded[u], u));
        }
        const double cost = invalid ? 1e30 : plan_cost(ops.size() - nops);
        const int fixes = handle_fix_cost(col_of[x], A[u] >> handle[col_of[x]] & 1);
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return {cost, fixes};
    }
    void run_joint(int u, const PlanOpt& opt) {''')
sub('''            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);''','''            OldValue returned{};
            if (opt.old_value && lvl <= c) returned = old_paper_value(x, u, -1, false, is_x0 ? opt.ret_mode : 1);
            auto weighted = [&](int lv, double previous) {
                if (!opt.old_value) return previous;
                ++old_value_calls;
                const auto placed = old_paper_value(x, u, lv, !is_x0 && lv == L, 1);
                double value = saved(x, lv, c, false) + returned.cost - placed.cost;
                if (opt.old_value == 2 && covers(x, c)) value += returned.fixes - fix[c];
                old_value_changed += std::abs(value - previous) > 1e-9;
                return value;
            };
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);''')
sub('''                if (!is_x0 && lvl == L) g = sv + 1 - kStay;
                if (g > 0)''','''                if (!is_x0 && lvl == L) g = sv + 1 - kStay;
                g = weighted(lvl, g);
                if (g > 0)''')
sub('''                double g = saved(x, L, c, false) + 1 - kStay;
                if (!harm && g > 0)''','''                double g = weighted(L, saved(x, L, c, false) + 1 - kStay);
                if (!harm && g > 0)''')
sub('''                double g = saved(x, lv, c, false) - kRelevel;
                if (g > 0)''','''                double g = weighted(lv, saved(x, lv, c, false) - kRelevel);
                if (g > 0)''')
sub('''        if (d != top0) opts.push_back({1, 5, true, true});''',f'''        if (d != top0) opts.push_back({{1, 5, true, true}});
        if (d != top0) opts.push_back({{1, 5, true, true, {mode}}});''')
sub('''q.opt.value_fillers == o.value_fillers) { repeated = &q; break; }''','''q.opt.value_fillers == o.value_fillers && q.opt.old_value == o.old_value) { repeated = &q; break; }''')
sub('''            record_future(cost);
            if (cost < best)''','''            if (o.old_value) {
                ++old_value_plans;
                if (cost < best) ++old_value_better, old_value_gain += best - cost;
            }
            record_future(cost);
            if (cost < best)''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "old_value_calls = " << solver.old_value_calls
              << "\\nold_value_changed = " << solver.old_value_changed
              << "\\nold_value_plans = " << solver.old_value_plans
              << "\\nold_value_better = " << solver.old_value_better
              << "\\nold_value_gain = " << solver.old_value_gain << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/argon-req-filldp-positive

R2の継続検証。共同DPで、新規フィラーだけでなく、旧フィラーと前の商品紙の再利用・据え置きにも状態価値を使う計画を1つ追加する。既存の計画は全て維持する。

旧紙を返した状態と残した状態を仮実行し、今回の操作数とplan_costの差を求め、被覆により省くハンドル修正の数に加える。モード{mode}（1はこの差のみ、2は返却した紙自身の列の修正手数の変化も補正）。仮実行の後で積層・操作・ラベルを復元し、完成計画では通常の可視性・表示・回収可能性を確認する。目的関数・設計・予算は変えない。

既存のログ、実験スイッチ、プロファイラは維持する。ただし基準で常に0のvalue_filler_zero/value_filler_zero_usefulはユーザー指示により削除する。新規の環境変数はない。

old_value_calls/changedは旧紙の区間を評価した数と従来の重みと異なった数。old_value_plans/better/gainは有効な追加計画数、最良の既存初期計画より良かった数、評価値差の和。いずれも後処理前の指標。
''')
