from pathlib import Path
p=Path('solutions/argon-req-newfull-fast')
assert not p.exists()
p.mkdir()
s=Path('solutions/argon-req-newfull-only/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80])
 s=s.replace(a,b,1)
sub('''                        if (opt.full_old && returned_reference < 1e29) {
                            const double placed = joint_local_value(u, opt, {{lv, 0, c, 0, 0, f, post}});
                            gain = placed < 1e29 ? returned_reference - placed : -1e30;
                        } else if (opt.complete_value && completed_reference < 1e29)''','''                        if (opt.full_old && returned_reference < 1e29) {
                            // Complete all new-paper choices from one shared return/generic prefix below.
                        } else if (opt.complete_value && completed_reference < 1e29)''')
sub('''        const auto picks = best_intervals(cand);
        if (opt.value_fillers && !opt.complete_value)''','''        if (opt.full_old && returned_reference < 1e29)
            weight_new_joint(u, opt, returned_reference, cand);
        const auto picks = best_intervals(cand);
        if (opt.value_fillers && !opt.complete_value)''')
sub('''    void finish_joint(int u, const PlanOpt& opt, const std::vector<Cand>& picks) {
        const int d = ded[u], x0 = top_d;''','''    bool prepare_joint(int u, const PlanOpt& opt, const std::vector<Cand>& picks, u64& hh) {
        const int d = ded[u], x0 = top_d;''')
a=s.index('    bool prepare_joint('); b=s.index('    // ==== Request plans: one plan',a)
prefix=s[a:b]
prefix=prefix.replace('        u64 hh = hole_all & ~gmask;', '        hh = hole_all & ~gmask;',1)
prefix=prefix.replace('            if (invalid) return;', '            if (invalid) return false;',1)
needle='''        set_generic(u, hole_all);
        for (auto& cd : picks)'''
assert prefix.count(needle)==1
prefix=prefix.replace(needle,'''        set_generic(u, hole_all);
        return true;
    }
    void finish_joint_tail(int u, const std::vector<Cand>& picks, u64 hh) {
        const int d = ded[u];
        const bool d_out = is_filler(d);
        for (auto& cd : picks)''',1)
prefix+='''    void finish_joint(int u, const PlanOpt& opt, const std::vector<Cand>& picks) {
        u64 hh;
        if (prepare_joint(u, opt, picks, hh)) finish_joint_tail(u, picks, hh);
    }
    // New-paper trials all return every old paper and make the same generic edits.
    // Reuse that exact prefix, including its operations in each full plan's cost.
    void weight_new_joint(int u, const PlanOpt& opt, double reference,
                          std::vector<std::vector<Cand>>& candidates) {
        const auto initial = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        u64 hh;
        invalid = false;
        const bool ready = prepare_joint(u, opt, {}, hh);
        const auto prefix = save();
        const auto prefix_ops = ops;
        OP_TAG(const auto prefix_tags = op_tags; const auto prefix_tag = op_tag;)
        for (auto& choices : candidates) {
            for (auto& cd : choices) if (cd.kind == 0) {
                restore(prefix);
                ops = prefix_ops;
                OP_TAG(op_tags = prefix_tags; op_tag = prefix_tag;)
                invalid = !ready;
                if (ready) finish_joint_tail(u, {cd}, hh);
                ++old_full_calls;
                const bool valid = !invalid && display() == A[u] && fillers_reachable();
                old_full_invalid += !valid;
                cd.gain = valid ? reference - plan_cost(ops.size()-nops) : -1e30;
            }
            std::erase_if(choices, [](const Cand& cd) { return cd.gain <= 0; });
        }
        restore(initial);
        ops.resize(nops);
        invalid = was_invalid;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
    }
'''
s=s[:a]+prefix+s[b:]
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

新しいフィラーの共同DP重みを、旧紙をすべて返し、汎用層を編集し、要求紙を持ち上げ、残るハンドルを直した完成計画同士の差で計算する追加案。旧紙の保持・再配置の重みと既存の候補は変えない。候補ごとに共通な返却と汎用層編集を一度だけ実行し、その積層・操作列・ラベルを再利用する。各候補の評価値には共通操作の手数も含める。

比較用の非共有実装は solutions/argon-req-newfull-only。old_full_calls/invalidは局所完成計画の評価数と無効数、old_full_plans/better/gainは有効な追加計画数と初期候補最良値を更新した数・改善値。既存のログ、実験スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節は保持する。既定の探索予算は変更しない。
''')
print(p)
