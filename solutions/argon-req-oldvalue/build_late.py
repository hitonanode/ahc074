from pathlib import Path
import sys
name=sys.argv[1] if len(sys.argv)>1 else 'argon-req-latejoint'
gap=float(sys.argv[2]) if len(sys.argv)>2 else .5
p=Path('solutions')/name
assert p.is_dir()
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
sub('//   Request processing (process)\n','//   Request processing (process)\n//   Request processing: finishing a competitive weighted seed\n')
sub('''    Moves process(int u) {
        CF_SCOPE(process);''','''    struct WeightedSeed {
        State state;
        Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
        double cost = 1e100;
        bool ready = false;
    } weighted_seed;
    bool seed_valid = false;
    long long late_seed_trials = 0, late_seed_valid = 0, late_seed_better = 0, late_seed_saved = 0;
    double late_seed_gain = 0;
    Moves process_core(int u, const WeightedSeed* seed = nullptr) {
        CF_SCOPE(process);
        seed_valid = false;
        if (!seed) weighted_seed.ready = false;''')
sub('''        OP_TAG(if (neutral_enabled) ++request_counter;)''','''        OP_TAG(if (neutral_enabled && !seed) ++request_counter;)''')
sub('''        if (d != top0) opts.push_back({1, 5, true, true});''','''        if (d != top0) opts.push_back({1, 5, true, true});
        if (seed) opts = {{1, 5, true, true}};''')
sub('''            const RepeatedPlan* repeated = nullptr;''','''            if (seed) {
                restore(seed->state);
                ops = seed->path;
                OP_TAG(op_tags = seed->tags;)
                placement_chains.clear();
            } else {
            const RepeatedPlan* repeated = nullptr;''')
sub('''            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double cost = plan_cost(ops.size());
            if (o.value_fillers) {''','''            }
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double cost = plan_cost(ops.size());
            if (!seed && o.value_fillers) {
                weighted_seed = {save(), ops OP_TAG(, op_tags), cost, true};''')
sub('''        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''','''        if (!seed && interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {''')
sub('''        if (best > 1e17) {
            plan_failures++;''','''        if (best > 1e17) {
            if (seed) return {};
            plan_failures++;''')
sub('''        check_vis = false;
        restore(best_state);''','''        seed_valid = true;
        check_vis = false;
        restore(best_state);''')
sub('''        return chosen_path;
    }
};

// ==== Emergency design ====''','''        return chosen_path;
    }

    // ==== Request processing: finishing a competitive weighted seed ====

    // The weighted joint plan may leave the short list before it receives neutral
    // rewrites. Finish it separately only when its raw value is competitive with
    // the completed incumbent. Exact ties keep the incumbent.
    Moves process(int u) {
        const auto initial = save();
        auto path = process_core(u);
        const double value = plan_cost(path.size());
        if (!weighted_seed.ready || weighted_seed.cost > value + GAP_LIMIT || weighted_seed.path == path) return path;
        const auto best = save();
        OP_TAG(const auto best_tags = op_tags;)
        restore(initial);
        ++late_seed_trials;
        auto alternative = process_core(u, &weighted_seed);
        if (seed_valid && display() == A[u] && fillers_reachable()) {
            ++late_seed_valid;
            const double next = plan_cost(alternative.size());
            if (next < value - 1e-9) {
                ++late_seed_better;
                late_seed_gain += value - next;
                late_seed_saved += int(path.size()) - int(alternative.size());
                return alternative;
            }
        }
        restore(best);
        OP_TAG(op_tags = best_tags;)
        return path;
    }
};

// ==== Emergency design ===='''.replace('GAP_LIMIT',str(gap)))
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "late_seed_trials = " << solver.late_seed_trials
              << "\\nlate_seed_valid = " << solver.late_seed_valid
              << "\\nlate_seed_better = " << solver.late_seed_better
              << "\\nlate_seed_gain = " << solver.late_seed_gain
              << "\\nlate_seed_saved = " << solver.late_seed_saved << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/argon-req-filldp-positive

R2の採用済み状態価値付き共同DP計画を保存し、通常の探索が完成した後、その計画だけでも後処理・中立探索を行う。元の初期評価値が完成した最良値から{gap:g}手以内で、同じ操作列ではない時だけ試す。初期計画は保存したものを使うので、DPをもう一度解かない。完成値が厳密に改善した時だけ使い、同値では元の結果を保つ。目的関数・設計・各探索の予算を変更せず、将来の注文も読まない。

既存のログ・予算スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは削除する。process_coreが共通の探索を担当し、processは条件付きの追加探索を行う。追加段のsection markerと目次を追加した。

late_seed_trials/valid/better/gain/savedは追加処理した数、有効な完成計画数、採用数、完成評価値改善の合計、その時点の即時手数節約。新規環境変数はない。
''')
