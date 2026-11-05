from pathlib import Path
for suffix,cheap in [('edit',False),('cheap',True)]:
 p=Path('solutions/argon-req-k2late-'+suffix)
 assert not p.exists()
 p.mkdir()
 s=Path('solutions/argon-req-k2-v3/main.cpp').read_text()
 def sub(a,b):
  global s
  assert s.count(a)==1,(s.count(a),a[:90])
  s=s.replace(a,b,1)
 sub('    Moves process(int u) {','''    inline static long long joint_late_trials = 0, joint_late_ejects = 0, joint_late_accepts = 0, joint_late_saved = 0;
    inline static double joint_late_gain = 0;
    template<class Candidate>
    [[gnu::noinline]] bool finish_joint_alternative(const State& initial, const Candidate& c,
                                                   bool edited, int u, double value, Moves& chosen
                                                   OP_TAG(, std::vector<uint8_t>& chosen_tags)) {
        ++joint_late_trials;
        const auto incumbent = save();
        restore(c.state);
        canonicalize();
        auto path = c.path;
        OP_TAG(auto tags = c.tags;)
        F3_DIAG(f3_stage = 3; f3_round = 0;)
        if (!edited) path = post_optimize(initial, std::move(path), u OP_TAG(, tags), false, '''+('true' if cheap else 'false')+''');
        double next = plan_cost(path.size());
        if (next <= value + .5 && order != incumbent.order) {
            ++joint_late_ejects;
            path = polish_ejects(initial, std::move(path), u OP_TAG(, tags), 4, true);
            next = plan_cost(path.size());
        }
        if (next < value - 1e-9 && display() == A[u] && fillers_reachable()) {
            ++joint_late_accepts;
            joint_late_gain += value - next;
            joint_late_saved += int(chosen.size()) - int(path.size());
            chosen = std::move(path);
            OP_TAG(chosen_tags = std::move(tags);)
            return true;
        }
        restore(incumbent);
        return false;
    }
    Moves process(int u) {''')
 sub('        FutureCandidate weighted_raw{};','''        FutureCandidate extra_raw{};
        bool extra_ready = false;
        FutureCandidate weighted_raw{};''')
 sub('''                if (cost < best) ++joint_extra_better, joint_extra_gain += best - cost;
            }
            record_future(cost);''','''                if (cost < best) ++joint_extra_better, joint_extra_gain += best - cost;
                if (neutral_enabled) {
                    extra_raw = {cost, save(), ops OP_TAG(, op_tags)};
                    extra_ready = true;
                    continue;  // preserve every original post-processing candidate
                }
            }
            record_future(cost);''')
 sub('''            if (chosen_path != baseline_path) {''','''            if (extra_ready) {
                const auto* cached = find_cached_plan(extra_raw);
                const auto& c = cached ? cached->edited : extra_raw;
                const double value = plan_cost(chosen_path.size());
                if (!(cached && cached->complete) && c.state.order != order && c.cost <= value + 1.0)
                    if (finish_joint_alternative(st0, c, bool(cached), u, value, chosen_path OP_TAG(, best_tags))) {
                        winning_operator = 4; winning_round = 0; winning_escape = false;
                    }
            }
            if (chosen_path != baseline_path) {''')
 sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "joint_late_trials = " << solver.joint_late_trials
              << "\\njoint_late_ejects = " << solver.joint_late_ejects
              << "\\njoint_late_accepts = " << solver.joint_late_accepts
              << "\\njoint_late_gain = " << solver.joint_late_gain
              << "\\njoint_late_saved = " << solver.joint_late_saved << '\\n';
''')
 (p/'main.cpp').write_text(s)
 (p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

抽出直後の状態価値付き共同DPから、紙集合が異なる第2解を保存する。元の後処理候補を押し出さず、通常探索の後に評価する。既にeject済み・同じ最終積層の候補は省き、評価値差1以内の候補だけを'''+('削除だけの安い編集' if cheap else '通常の編集')+'''で整える。編集後の差が0.5以内ならejectを行い、完成評価値が改善した場合だけ採用する。既存の編集済みキャッシュを再利用し、中立探索全体の繰り返しは行わない。

joint_extra_plans/better/gainは第2解の有効数、初期最良値を上回る数と改善量。joint_late_trials/ejects/accepts/gain/savedは追加編集、追加eject、最終採用の件数、完成評価値の改善合計、即時手数差。既存の全ログ、実験スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節は保持。NEUTRAL=0では追加候補を通常候補として扱う。
''')
 print(p)
