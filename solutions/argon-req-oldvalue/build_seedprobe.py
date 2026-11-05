from pathlib import Path
import subprocess
p=Path('solutions/argon-req-seedprobe');p.mkdir()
subprocess.run(['python3','solutions/argon-req-oldvalue/build_late_cache.py',p.name,'10'],check=True)
s=p.joinpath('main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
sub('    bool seed_valid = false;','''    bool seed_valid = false, weighted_novel = false, weighted_best = false;
    struct SeedProbe { long long trials = 0, better = 0, moves = 0; double gain = 0, sec = 0; };
    std::array<std::array<SeedProbe, 7>, 12> seed_probe{};''')
sub('''        std::vector<RepeatedPlan> repeated_plans;''','''        std::vector<std::array<uint8_t, K>> previous_orders;
        std::vector<RepeatedPlan> repeated_plans;''')
sub('''                weighted_seed = {save(), ops OP_TAG(, op_tags), cost, true};''','''                weighted_seed = {save(), ops OP_TAG(, op_tags), cost, true};
                weighted_novel = std::find(previous_orders.begin(), previous_orders.end(), order) == previous_orders.end();
                weighted_best = cost < best;''')
sub('''            record_future(cost);
            if (cost < best)''','''            previous_orders.push_back(order);
            record_future(cost);
            if (cost < best)''')
sub('''        ++late_seed_trials;
        auto alternative''','''        ++late_seed_trials;
        const int bucket = (int(weighted_novel) * 2 + int(weighted_best)) * 3 + weighted_seed.stage;
        const double gap = weighted_seed.cost - value;
        const double t = elapsed_sec();
        auto alternative''')
sub('''                return alternative;''','''                // Measurement only: retain the base state and output below.''')
sub('''        restore(best);
        OP_TAG(op_tags = best_tags;)
        return path;''','''        const double elapsed = elapsed_sec() - t;
        const double next = seed_valid && display() == A[u] && fillers_reachable() ? plan_cost(alternative.size()) : value;
        const std::array<double, 7> gates = {0, .125, .25, .5, 1, 2, 10};
        for (int g = 0; g < int(gates.size()); ++g) if (gap <= gates[g]) {
            auto& q = seed_probe[bucket][g];
            ++q.trials;
            q.better += next < value - 1e-9;
            q.gain += std::max(0.0, value - next);
            if (next < value - 1e-9) q.moves += int(path.size()) - int(alternative.size());
            q.sec += elapsed;
        }
        restore(best);
        OP_TAG(op_tags = best_tags;)
        return path;''')
sub('''    std::cerr << "late_seed_cached = "''','''    for (int b = 0; b < 12; ++b) for (int g = 0; g < 7; ++g) {
        const auto& q = solver.seed_probe[b][g];
        const std::string prefix = "seed_probe_" + std::to_string(b) + '_' + std::to_string(g) + '_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "moves = " << q.moves << '\\n'
                  << prefix << "sec = " << q.sec << '\\n';
    }
    std::cerr << "late_seed_cached = "''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-req-filldp-positive

R2の測定専用版。既存の状態価値付き共同DP計画を、plan_cacheの編集・eject済み状態から最後まで仕上げ、基準の完成値を改善するかを数える。結果は出力に採用せず、元の積層・操作列を戻す。既存ログ・スイッチ・プロファイラを保持し、常に0のvalue_filler_zero/value_filler_zero_usefulのみ削除。

seed_probe_<b>_<g>_trials/better/gain/moves/secは条件を満たす追加処理数、完成値改善数、評価値改善合計、そのときの即時手数節約、追加処理の時間。b=(novel*2+best)*3+stage、novelは初期積層が通常の計画と異なるか、bestは初期値が通常計画の最良を更新したか、stageは0:未編集、1:編集済み、2:eject済み。g=0..6は完成した基準値との差の上限0, .125, .25, .5, 1, 2, 10。全紙順序が基準と同じ場合は省く。

時間超過する測定版なので固定設計評価で使う。通常評価をする場合は--no-record。将来の注文は参照しない。
''')
