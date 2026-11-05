from pathlib import Path

root = Path('solutions')
base = root / 'argon-req-completefast-v3'
source = (base / 'main.cpp').read_text()
work = root / 'argon-req-completeold'

def write(name, s, explanation, metrics):
    p = root / name
    if p != work:
        p.mkdir()
    (p / 'main.cpp').write_text(s)
    (p / 'README.md').write_text('改良元: solutions/argon-req-completefast-v3\n\n' + explanation +
        '\n\n設計・目的関数・既存候補・予算を維持する。将来の注文を参照しない。既存のログ、環境変数、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次はすべて残す。新しい環境変数はない。\n\n' + metrics + '\n')

def replace(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:100])
    return s.replace(old, new)

# Complete local plans for the old papers, including their own column's repairs.
s = replace(source, '        bool complete_value = false;', '        bool complete_value = false;\n        bool complete_old = false;')
helper = '''    long long old_complete_calls = 0, old_complete_invalid = 0, old_complete_plans = 0, old_complete_better = 0;
    double old_complete_gain = 0;
    double old_completed_value(int x, int u, int level, bool keep, int return_mode, u64 holes) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;
        invalid = false;
        if (level < 0) return_paper(x, u, return_mode);
        else {
            if (x == top_d) {
                top_d = -1;
                move_to_level(x, level, true, gen_harm(x, ded[u], u));
                fillers.push_back({x, level, col_of[x]});
            } else {
                for (auto& f : fillers) if (f.paper == x) f.lvl = level, f.hi = col_of[x];
                if (!keep) move_to_level(x, level, true, gen_harm(x, ded[u], u));
            }
            holes &= ~shown_by({x, level, col_of[x]});
        }
        if (!invalid) fix_handles(u, holes);
        ++old_complete_calls;
        old_complete_invalid += invalid;
        const double cost = invalid ? 1e30 : plan_cost(ops.size() - nops);
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return cost;
    }
'''
s = replace(s, '    void run_joint(int u, const PlanOpt& opt) {', helper + '    void run_joint(int u, const PlanOpt& opt) {')
s = replace(s, '            if (lvl <= c) {\n                int sv = saved(x, lvl, c, false);', '''            const double returned = opt.complete_old && lvl <= c ?
                old_completed_value(x, u, -1, false, is_x0 ? opt.ret_mode : 1, hh) : 1e30;
            auto weighted = [&](int lv, double previous) {
                if (!opt.complete_old || returned >= 1e29) return previous;
                const double placed = old_completed_value(x, u, lv, !is_x0 && lv == L, 1, hh);
                return placed < 1e29 ? returned - placed : previous;
            };
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);''')
s = replace(s, '                if (!is_x0 && lvl == L) g = sv + 1 - kStay;\n                if (g > 0)', '                if (!is_x0 && lvl == L) g = sv + 1 - kStay;\n                g = weighted(lvl, g);\n                if (g > 0)')
s = replace(s, '                double g = saved(x, L, c, false) + 1 - kStay;', '                double g = weighted(L, saved(x, L, c, false) + 1 - kStay);')
s = replace(s, '                double g = saved(x, lv, c, false) - kRelevel;', '                double g = weighted(lv, saved(x, lv, c, false) - kRelevel);')
s = replace(s, '        if (d != top0) opts.push_back({1, 5, true, true, true});', '        if (d != top0) opts.push_back({1, 5, true, true, true});\n        if (d != top0) opts.push_back({1, 5, true, true, true, true});')
s = replace(s, 'q.opt.complete_value == o.complete_value)', 'q.opt.complete_value == o.complete_value && q.opt.complete_old == o.complete_old)')
s = replace(s, '            complete_value_plans += o.complete_value;', '''            complete_value_plans += o.complete_value;
            if (o.complete_old) {
                ++old_complete_plans;
                if (cost < best) ++old_complete_better, old_complete_gain += best - cost;
            }''')
s = replace(s, '    // ==== main: statistics ====\n', '''    // ==== main: statistics ====
    std::cerr << "old_complete_calls = " << solver.old_complete_calls
              << "\\nold_complete_invalid = " << solver.old_complete_invalid
              << "\\nold_complete_plans = " << solver.old_complete_plans
              << "\\nold_complete_better = " << solver.old_complete_better
              << "\\nold_complete_gain = " << solver.old_complete_gain << '\\n';
''')
write('argon-req-completeold', s, '旧フィラーと前の製品紙の再配置・据え置きを、返却して全ハンドルを直す局所計画と、残して未被覆ハンドルを直す局所計画のplan_cost差で評価する共同DP計画を追加する。返却紙の列の修正効果も仮実行で含める。従来の全計画は残し、完成時の合法性と表示を検査する。', 'old_complete_calls/invalidは旧紙の局所評価数と不成立数、plans/better/gainは有効な追加計画数、初期最良値の更新数、その改善合計。')

# A second, different set of papers: try the old and completed weights separately.
old = (root / 'argon-req-jointk2-v2/main.cpp').read_text()
start = old.index('    std::vector<std::vector<Cand>> joint_choices;')
end = old.index('    void run_joint(int u, const PlanOpt& opt)', start)
joint_helper = old[start:end]
for completed in [False, True]:
    s = replace(source, '        bool complete_value = false;', '        bool complete_value = false;\n        int joint_rank = 0;')
    s = replace(s, '    void run_joint(int u, const PlanOpt& opt) {', joint_helper + '    void run_joint(int u, const PlanOpt& opt) {')
    s = replace(s, 'opt.complete_value ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;', '(opt.complete_value && !opt.joint_rank) ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;')
    s = replace(s, 'if (opt.complete_value && completed_reference >= 1e29)', 'if (opt.complete_value && !opt.joint_rank && completed_reference >= 1e29)')
    s = replace(s, '        auto& cand = fresh_candidates();\n        auto mism_level', '''        std::vector<Cand> picks;
        if (opt.joint_rank) {
            if (opt.joint_rank >= int(joint_choices.size())) { invalid = true; return; }
            picks = joint_choices[opt.joint_rank];
        } else {
        joint_choices.clear();
        auto& cand = fresh_candidates();
        auto mism_level''')
    cond = 'opt.value_fillers && opt.complete_value' if completed else 'opt.value_fillers && !opt.complete_value'
    s = replace(s, '        const auto picks = best_intervals(cand);', '''        picks = best_intervals(cand);
        if (CONDITION) joint_alternatives(cand, [&](const Cand& cd) {
            return cd.kind == 0 ? cd.idx : cd.kind == 3 ? x0 : olds[cd.idx].paper;
        }, picks);
        }
'''.replace('CONDITION', cond))
    s = replace(s, 'if (opt.value_fillers && !opt.complete_value) joint_value_picks = picks;', 'if (opt.value_fillers && !opt.complete_value && !opt.joint_rank) joint_value_picks = picks;')
    # If complete's primary duplicates the previous plan, the alternatives are still valid.
    marker = '        if (d != top0) opts.push_back({1, 5, true, true, true});' if completed else '        if (d != top0) opts.push_back({1, 5, true, true});'
    value = 'true' if completed else 'false'
    s = replace(s, marker, marker + '\n        if (d != top0) opts.push_back({1, 5, true, true, ' + value + ', 1});')
    s = replace(s, 'q.opt.complete_value == o.complete_value)', 'q.opt.complete_value == o.complete_value && q.opt.joint_rank == o.joint_rank)')
    s = replace(s, '            complete_value_plans += o.complete_value;', '''            complete_value_plans += o.complete_value;
            if (o.joint_rank) {
                ++joint_extra_plans;
                if (cost < best) ++joint_extra_better, joint_extra_gain += best - cost;
            }''')
    s = replace(s, '    // ==== main: statistics ====\n', '''    // ==== main: statistics ====
    std::cerr << "joint_extra_plans = " << solver.joint_extra_plans
              << "\\njoint_extra_better = " << solver.joint_extra_better
              << "\\njoint_extra_gain = " << solver.joint_extra_gain << '\\n';
''')
    write('argon-req-completek2' + ('-local' if completed else ''), s, ('ハンドル修正後' if completed else '抽出直後') + 'の積層価値で重み付けした共同DPから、紙集合が異なる第2解を追加する。候補区間の価値計算を再利用し、既存の全初期計画と後処理を残す。', 'joint_extra_plans/better/gainは有効な第2解、初期最良値の更新数、改善合計。')

# Reuse the edited cache for both weighted plans, at most once per final stack.
s = replace(source, '    Moves process(int u) {', '''    long long value_seed_trials = 0, value_seed_valid = 0, value_seed_accepts = 0, value_seed_saved = 0;
    double value_seed_gain = 0;
    Moves process(int u) {''')
s = replace(s, '        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;', '        std::vector<FutureCandidate> weighted_raw;\n        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;')
s = replace(s, '            if (o.value_fillers) {\n                ++value_filler_plans;', '            if (o.value_fillers) {\n                weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});\n                ++value_filler_plans;')
old = (root / 'argon-req-valueeject/main.cpp').read_text()
a = old.index('        // The value-weighted joint plan can lose before ejection.')
b = old.index('        post_secondary_saved += original_length', a)
block = old[a:b]
block = block.replace('if (weighted_ready) if (const auto* cached = find_cached_plan(weighted_raw)) {', 'for (const auto& raw : weighted_raw) if (const auto* cached = find_cached_plan(raw)) {')
block = block.replace('        for (const auto& raw', '        std::vector<std::array<uint8_t, K>> ejected_orders;\n        for (const auto& raw')
block = block.replace('            if (!cached->complete && c.state.order != order && c.cost <= value + .5) {', '''            if (!cached->complete && c.state.order != order && c.cost <= value + .5 &&
                std::find(ejected_orders.begin(), ejected_orders.end(), c.state.order) == ejected_orders.end()) {
                ejected_orders.push_back(c.state.order);''')
s = replace(s, '        post_secondary_saved += original_length - int(chosen_path.size());', block + '        post_secondary_saved += original_length - int(chosen_path.size());')
s = replace(s, '    // ==== main: statistics ====\n', '''    // ==== main: statistics ====
    std::cerr << "value_seed_trials = " << solver.value_seed_trials
              << "\\nvalue_seed_valid = " << solver.value_seed_valid
              << "\\nvalue_seed_accepts = " << solver.value_seed_accepts
              << "\\nvalue_seed_gain = " << solver.value_seed_gain
              << "\\nvalue_seed_saved = " << solver.value_seed_saved << '\\n';
''')
write('argon-req-completeeject', s, '二つの状態価値付き共同DP計画のうち、編集済みだが通常の勝者としてejectを受けていない候補を再利用する。現行完成値との差が0.5以内の別積層にだけpolish_ejectsを追加し、厳密に改善すれば採用する。同じ編集済み積層は重複処理しない。', 'value_seed_trials/valid/acceptsは追加eject数、有効数、採用数。gain/savedは完成評価値差と採用時の即時手数差の和で、総実現手数の差とは区別する。')

for f in ['analyze.py', 'check_builds.py', 'metrics.py']:
    (work / f).write_text((root / 'argon-req-oldvalue' / f).read_text())
