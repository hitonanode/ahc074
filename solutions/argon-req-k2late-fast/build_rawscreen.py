from pathlib import Path
for name,both in [('argon-req-rawscreen',False),('argon-req-rawscreen-both',True)]:
 p=Path('solutions')/name;assert not p.exists();p.mkdir()
 s=Path('solutions/argon-req-ejectstats-v2/main.cpp').read_text()
 def sub(a,b):
  global s
  assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b,1)
 sub('    Moves process(int u) {','''    inline static long long raw_joint_trials = 0, raw_joint_promising = 0;
    // Existing DP plans outside the ordinary shortlist have not received even
    // cheap deletions. Complete only those already competitive after that pass.
    template<class Candidate>
    [[gnu::noinline]] bool screen_raw_joint(const State& initial, const Candidate& c,
                                            int u, double value, Moves& chosen
                                            OP_TAG(, std::vector<uint8_t>& chosen_tags)) {
        const auto incumbent = save();
        restore(c.state);
        canonicalize();
        OP_TAG(auto tags = c.tags;)
        F3_DIAG(f3_stage = 3; f3_round = 0;)
        ++raw_joint_trials;
        auto path = post_optimize(initial, c.path, u OP_TAG(, tags), false, true);
        const double next = plan_cost(path.size());
        if (next > value) { restore(incumbent); return false; }
        ++raw_joint_promising;
        const Candidate edited{next, save(), std::move(path) OP_TAG(, std::move(tags))};
        restore(incumbent);
        return finish_weighted_plan(initial, edited, u, value, chosen OP_TAG(, chosen_tags));
    }
    Moves process(int u) {''')
 if both:
  sub('''        FutureCandidate weighted_raw{};
        bool weighted_ready = false;''','''        FutureCandidate completed_raw{};
        bool completed_ready = false;
        FutureCandidate weighted_raw{};
        bool weighted_ready = false;''')
  sub('''                ++value_filler_plans;''','''                if (cache_plans && o.complete_value) {
                    completed_raw = {cost, save(), ops OP_TAG(, op_tags)};
                    completed_ready = true;
                }
                ++value_filler_plans;''')
 insertion=''
 for raw,ready in [('weighted_raw','weighted_ready')]+([('completed_raw','completed_ready')] if both else []):
  insertion+='''            if ('''+ready+''' && !find_cached_plan('''+raw+''') && '''+raw+'''.state.order != order) {
                const double value = plan_cost(chosen_path.size());
                if ('''+raw+'''.cost <= value + 1.0 &&
                    screen_raw_joint(st0, '''+raw+''', u, value, chosen_path OP_TAG(, best_tags))) {
                    winning_operator = 4; winning_round = 0; winning_escape = false;
                }
            }
'''
 sub('''            if (chosen_path != baseline_path) {''',insertion+'''            if (chosen_path != baseline_path) {''')
 sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "raw_joint_trials = " << solver.raw_joint_trials
              << "\\nraw_joint_promising = " << solver.raw_joint_promising << '\\n';
''')
 (p/'main.cpp').write_text(s)
 (p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

既に生成済みの状態価値付き共同DP計画のうち、通常の編集対象に入らなかった計画へ削除だけの安い編集を行う。元の最終計画からの値差1以内で別積層のものに限り、編集後の評価値が元の最終値以下なら既存のeject処理で仕上げる。既存候補を押し出さず、元の探索を終えた後で改善した計画だけを採る。新たなDP解や区間の状態価値を計算し直さない。

対象は'''+('抽出直後とハンドル修正後の2種類のDP' if both else '抽出直後の価値を使うDP')+'''。raw_joint_trials/promisingは安い編集の試行数、編集後に最終値以下となった数。追加ejectの結果は既存のvalue_seed_*にも含む。全ログ、実験スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、節と目次を保持する。
''')
 print(p)
