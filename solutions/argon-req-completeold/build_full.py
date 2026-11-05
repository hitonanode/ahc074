from pathlib import Path
r=Path('solutions');base=(r/'argon-req-completefast-v3/main.cpp').read_text()
a=base.index('        std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);')
b=base.index('    // ==== Request plans: one plan (run_plan) and its shared tail ====',a)
tail=base[a:b]
intro='''    void finish_joint(int u, const PlanOpt& opt, const std::vector<Cand>& picks) {
        const int d = ded[u], x0 = top_d;
        const bool d_out = is_filler(d);
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        std::vector<Filler> olds;
        for (const auto& f : fillers) if (f.paper != d) olds.push_back(f);
'''
s=base[:a]+'        finish_joint(u, opt, picks);\n    }\n'+intro+tail+base[b:]
# The choice code still needs every original local except hole_all can stay as before.
p=r/'argon-req-jointfinish';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/argon-req-completefast-v3\n\n共同DPの区間選択後の実行をfinish_jointへ切り出すだけの検証用。元と同じ状態・順序で返却、再配置、持ち上げ、ハンドル修正を行う。ログ・スイッチ・プロファイラ・設計・目的関数・予算・段の目印と目次は維持する。新しい指標やスイッチはない。\n')
s=s.replace('        bool complete_value = false;', '        bool complete_value = false;\n        bool full_old = false;')
point='    void run_joint(int u, const PlanOpt& opt) {'
helper='''    long long old_full_calls = 0, old_full_invalid = 0, old_full_plans = 0, old_full_better = 0;
    double old_full_gain = 0;
    // Finish exactly the same joint-plan tail for a local set of selected papers.
    // This includes returns of the other old papers, generic edits and D's lift.
    double joint_local_value(int u, const PlanOpt& opt, const std::vector<Cand>& picks) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        invalid = false;
        finish_joint(u, opt, picks);
        ++old_full_calls;
        const bool valid = !invalid && display() == A[u] && fillers_reachable();
        old_full_invalid += !valid;
        const double value = valid ? plan_cost(ops.size() - nops) : 1e30;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return value;
    }
'''
s=s.replace(point,helper+point,1)
point='        const double completed_reference = opt.complete_value ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;'
assert point in s
s=s.replace(point,point+'\n        const double returned_reference = opt.full_old ? joint_local_value(u, opt, {}) : 1e30;',1)
point='            if (lvl <= c) {\n                int sv = saved(x, lvl, c, false);'
s=s.replace(point,'''            auto weighted = [&](int lv, int kind, double previous) {
                if (!opt.full_old || returned_reference >= 1e29) return previous;
                const double placed = joint_local_value(u, opt, {{lv, previous, c, 0, kind, idx}});
                return placed < 1e29 ? returned_reference - placed : previous;
            };
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);''',1)
s=s.replace('                if (!is_x0 && lvl == L) g = sv + 1 - kStay;','                if (!is_x0 && lvl == L) g = sv + 1 - kStay;\n                g = weighted(lvl, is_x0 ? 3 : lvl == L ? 2 : 1, g);',1)
s=s.replace('                double g = saved(x, L, c, false) + 1 - kStay;', '                double g = weighted(L, 2, saved(x, L, c, false) + 1 - kStay);',1)
s=s.replace('                double g = saved(x, lv, c, false) - kRelevel;', '                double g = weighted(lv, is_x0 ? 3 : 1, saved(x, lv, c, false) - kRelevel);',1)
s=s.replace('        if (d != top0) opts.push_back({1, 5, true, true, true});','        if (d != top0) opts.push_back({1, 5, true, true, true});\n        if (d != top0) opts.push_back({1, 5, true, true, true, true});',1)
s=s.replace('q.opt.complete_value == o.complete_value)', 'q.opt.complete_value == o.complete_value && q.opt.full_old == o.full_old)',1)
s=s.replace('            complete_value_plans += o.complete_value;', '''            complete_value_plans += o.complete_value;
            if (o.full_old) {
                ++old_full_plans;
                if (cost < best) ++old_full_better, old_full_gain += best - cost;
            }''',1)
s=s.replace('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "old_full_calls = " << solver.old_full_calls
              << "\\nold_full_invalid = " << solver.old_full_invalid
              << "\\nold_full_plans = " << solver.old_full_plans
              << "\\nold_full_better = " << solver.old_full_better
              << "\\nold_full_gain = " << solver.old_full_gain << '\\n';
''',1)
p=r/'argon-req-completeold-full';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/argon-req-completefast-v3\n\n旧紙の重みを、全旧紙返却の完成計画と、1枚だけ保持・再配置する完成計画の差で評価する共同DP案を追加する。各局所計画は通常と同じfinish_jointで実行し、他の旧紙の返却、汎用層の並べ替え、要求紙の持ち上げ、ハンドル修正を含める。元の全計画は残す。局所比較は現在注文だけを使い、将来を参照しない。\n\nログ・スイッチ・プロファイラ・設計・目的関数・予算・段の目印と目次は維持する。old_full_calls/invalid/plans/better/gainは局所完成計画数、不成立数、有効な追加計画数、初期最良値の更新数、その改善合計。新しい環境変数はない。\n')
