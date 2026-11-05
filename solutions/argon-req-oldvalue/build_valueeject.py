from pathlib import Path
p=Path('solutions/argon-req-valueeject');p.mkdir()
s=Path('/home/sato/ahc074/runs/20261106-005414_argon-des-perf-condbound/src/main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n','                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n','              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n','              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
 sub(line,'')
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;','long long value_filler_trials = 0;')
sub('''    Moves process(int u) {''','''    long long value_seed_trials = 0, value_seed_valid = 0, value_seed_accepts = 0, value_seed_saved = 0;
    double value_seed_gain = 0;
    Moves process(int u) {''')
sub('''        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;''','''        FutureCandidate weighted_raw{};
        bool weighted_ready = false;
        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;''')
sub('''            if (o.value_fillers) {
                ++value_filler_plans;''','''            if (o.value_fillers) {
                weighted_raw = {cost, save(), ops OP_TAG(, op_tags)};
                weighted_ready = true;
                ++value_filler_plans;''')
sub('''        post_secondary_saved += original_length - int(chosen_path.size());''','''        // The value-weighted joint plan can lose before ejection. Reuse its paid
        // edit pass, but do not repeat a plan already ejected as the main winner.
        // A whole neutral search here costs more than the extra improvements buy.
        if (weighted_ready) if (const auto* cached = find_cached_plan(weighted_raw)) {
            const auto& c = cached->edited;
            const double value = plan_cost(chosen_path.size());
            if (!cached->complete && c.state.order != order && c.cost <= value + .5) {
                const auto incumbent = save();
                restore(c.state);
                canonicalize();
                OP_TAG(auto tags = c.tags;)
                ++value_seed_trials;
                auto path = polish_ejects(st0, c.path, u OP_TAG(, tags), 4, true);
                const double next = plan_cost(path.size());
                const bool valid = display() == A[u] && fillers_reachable();
                value_seed_valid += valid;
                if (valid && next < value - 1e-9) {
                    ++value_seed_accepts;
                    value_seed_gain += value - next;
                    value_seed_saved += int(chosen_path.size()) - int(path.size());
                    chosen_path = std::move(path);
                    OP_TAG(best_tags = std::move(tags);)
                } else restore(incumbent);
            }
        }
        post_secondary_saved += original_length - int(chosen_path.size());''')
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "value_seed_trials = " << solver.value_seed_trials
              << "\\nvalue_seed_valid = " << solver.value_seed_valid
              << "\\nvalue_seed_accepts = " << solver.value_seed_accepts
              << "\\nvalue_seed_gain = " << solver.value_seed_gain
              << "\\nvalue_seed_saved = " << solver.value_seed_saved << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-des-perf-condbound

R2の状態価値付き共同DP計画が、通常の候補編集後に負けてejectを受けない場合を補う。既存のplan_cacheにある編集済み結果を使い、現在の完成結果とは積層が異なり、評価値差が0.5以内の候補だけに既存のpolish_ejectsを適用する。既に通常の勝者としてejectを受けた候補は繰り返さない。完成したplan_costを厳密に改善した場合だけ採用する。

候補のDP・編集を解き直さず、中立探索の追加実行もしない。通常の全候補と探索予算、目的関数、設計、将来注文を見ない性質は基準のまま。既存のログ、スイッチ、プロファイラ、DesignStore、section markerと目次を維持する。常に0のvalue_filler_zero/value_filler_zero_usefulのみ削除した。新しい環境変数はない。

追加のstderr指標はvalue_seed_trials（追加eject数）、value_seed_valid（完成計画の有効数）、value_seed_accepts（採用数）、value_seed_gain（完成評価値の改善合計）、value_seed_saved（採用時の即時手数差）。実現した総手数の差とは区別する。
''')
