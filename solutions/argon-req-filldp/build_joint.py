from pathlib import Path
import sys
name = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else 'model'
p = Path('solutions') / name
assert p.is_dir()
s = Path('solutions/esw-slim/main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s, a[:80]
    s=s.replace(a,b,1)
sub('''        bool use_filler = false;
    };''','''        bool use_filler = false;
        bool value_fillers = false;  // joint DP also tries the marginal stack value
    };''')
sub('''    void run_joint(int u, const PlanOpt& opt) {''','''    long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;
    long long value_filler_plans = 0, value_filler_better = 0;
    double value_filler_gain = 0;
    // Marginal future cost of taking one paper out: its return charge, the column
    // left after digging, and the coverage credit at this level. Keep the immediate
    // extraction moves separate. The interval DP adds these local estimates; the
    // completed plan is still checked and scored by the unchanged plan_cost.
    double filler_value_increment(int c, int depth, int level, double before) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;  // a post-lift placement is evaluated before D is lifted
        invalid = false;
        u64 hh = 0;
        place_filler(c, depth, level, hh);
        const double delta = invalid ? 1e30 : plan_cost(0) - before;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return delta;
    }
    void run_joint(int u, const PlanOpt& opt) {''')
sub('''        const int l = col_of[d];
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;''','''        const int l = col_of[d];
        const double before_value = opt.value_fillers ? plan_cost(0) : 0;
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;''')
minimum = 1 if kind == 'positive' else 0
weight = 'filler_value_increment(c, depth, lv, before_value)'
if kind == 'charge':
    weight = '(kFillerCharge + kStayStrength * (.3 - stay_table[f][lv].probability))'
sub('''                    int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    if (g >= kFillerCost) cand[c].push_back({lv, (double)g, c, 0, 0, f, post});''',f'''                    const int raw_gain = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    double gain = raw_gain;
                    if (opt.value_fillers) {{
                        if (raw_gain < {minimum}) continue;
                        ++value_filler_trials;
                        value_filler_zero += raw_gain == 0;
                        gain -= {weight};
                        value_filler_zero_useful += raw_gain == 0 && gain > 0;
                    }}
                    if (opt.value_fillers ? gain > 0 : raw_gain >= kFillerCost)
                        cand[c].push_back({{lv, gain, c, 0, 0, f, post}});''')
sub('''        double best = 1e18, best_normal = 1e18;''','''        if (d != top0) opts.push_back({1, 5, true, true});
        double best = 1e18, best_normal = 1e18;''')
sub('''if (q.opt.fret_mode == o.fret_mode && q.opt.use_filler == o.use_filler) { repeated = &q; break; }''','''if (q.opt.fret_mode == o.fret_mode && q.opt.use_filler == o.use_filler &&
                        q.opt.value_fillers == o.value_fillers) { repeated = &q; break; }''')
sub('''            double cost = plan_cost(ops.size());
            record_future(cost);''','''            double cost = plan_cost(ops.size());
            if (o.value_fillers) {
                ++value_filler_plans;
                if (cost < best) ++value_filler_better, value_filler_gain += best - cost;
            }
            record_future(cost);''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "value_filler_trials = " << solver.value_filler_trials
              << "\\nvalue_filler_zero = " << solver.value_filler_zero
              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful
              << "\\nvalue_filler_plans = " << solver.value_filler_plans
              << "\\nvalue_filler_better = " << solver.value_filler_better
              << "\\nvalue_filler_gain = " << solver.value_filler_gain << '\\n';
''')
if kind == 'charge':
    s=s.replace('const double before_value = opt.value_fillers ? plan_cost(0) : 0;', '[[maybe_unused]] const double before_value = 0;',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/esw-slim

R2の共同区間DPに、取り出した後の状態価値を含めて新規フィラーを選ぶ計画を1つ追加する。既存の全計画は残し、plan_costは変えない。今回は {kind} 版。

新規フィラーの即時節約 `save - 1 - depth` から、将来の返却費用と列の状態価値の増分を引く。試しに紙を取り出して計算し、積層・操作・ラベルは元に戻す。後から置く候補もあるのでこの仮計算では可視性を要求せず、完成した実計画では従来の可視性・表示・回収可能性の検査を通す。共同DPの旧フィラーの重み、通常DP、ヘルパー、連鎖、後処理は変えない。

既存のスイッチ・stderr指標・プロファイラ・分析ラベルは維持する。追加指標 `value_filler_trials/zero/zero_useful` は追加DPで調べた区間数、そのうち即時利得0、状態価値を含めて正になった数。`value_filler_plans/better/gain` は有効な追加計画数、既存の最良初期計画を上回った数、評価値改善の合計（後処理前）。新しい環境変数はない。

検証条件と結果は solutions/argon-req-filldp/REPORT.md に記す。
''')
