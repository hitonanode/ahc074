from pathlib import Path
import sys
from build_seedcore import add_seed_core

name, donor = sys.argv[1:]
is_joint = 'k2' in donor
p = Path('solutions')/name
assert not p.exists()
p.mkdir()
s = add_seed_core((Path('solutions')/donor/'main.cpp').read_text())
def sub(old,new):
    global s
    if is_joint:
        old = old.replace('old_full_', 'joint_extra_')
        new = new.replace('old_full_', 'joint_extra_')
    assert s.count(old)==1,(s.count(old),old[:100])
    s=s.replace(old,new,1)
sub('    struct ProcessSeed {', '''    struct OldProbe {
        long long trials, valid, same, better, saved, ceiling;
        double gain, sec;
    };
    inline static std::array<std::array<OldProbe, 6>, 3> old_probe{};
    inline static long long old_probe_raw = 0, old_probe_duplicate = 0;
    struct ProcessSeed {''')
sub('        FutureCandidate weighted_raw{};', '''        FutureCandidate probe_raw{};
        bool probe_ready = false;
        std::vector<std::array<uint8_t,K>> ordinary_orders;
        FutureCandidate weighted_raw{};''')
sub('        auto record_future = [&](double cost) {', '''        auto record_future = [&](double cost) {
            if (!seed) ordinary_orders.push_back(order);''')
sub('''                if (cost < best) ++old_full_better, old_full_gain += best - cost;
            }
            record_future(cost);''', '''                if (cost < best) ++old_full_better, old_full_gain += best - cost;
                probe_raw = {cost, save(), ops OP_TAG(, op_tags)};
                probe_ready = true;
                continue;  // measure without changing the ordinary shortlist
            }
            record_future(cost);''')
sub('''            if (chosen_path != baseline_path) {''', '''            if (!seed && probe_ready) {
                ++old_probe_raw;
                old_probe_duplicate += std::find(ordinary_orders.begin(), ordinary_orders.end(), probe_raw.state.order) != ordinary_orders.end();
                const auto incumbent = save();
                const double value = plan_cost(chosen_path.size());
                const auto* cached = find_cached_plan(probe_raw);
                const auto& c = cached ? cached->edited : probe_raw;
                const int stage = cached ? (cached->complete ? 2 : 1) : 0;
                const double gap = c.cost - value;
                const ProcessSeed candidate{c.state, c.path OP_TAG(, c.tags), stage};
                restore(st0);
                bool ok = false;
                const double began = elapsed_sec();
                const auto path = process(u, &candidate, &ok);
                const double duration = elapsed_sec() - began;
                const bool valid = ok && display() == A[u] && fillers_reachable();
                const double next = valid ? plan_cost(path.size()) : value;
                const bool same = order == incumbent.order;
                const std::array<double,6> gates = {0, .25, .5, 1, 2, 1e30};
                for (int g=0; g<int(gates.size()); ++g) if (gap <= gates[g]) {
                    auto& q = old_probe[stage][g];
                    ++q.trials; q.valid += valid; q.same += same;
                    if (valid) q.ceiling += std::max(0, int(chosen_path.size())-int(path.size()));
                    if (valid && next < value-1e-9) {
                        ++q.better; q.gain += value-next;
                        q.saved += int(chosen_path.size())-int(path.size());
                    }
                    q.sec += duration;
                }
                restore(incumbent);
            }
            if (chosen_path != baseline_path) {''')
sub('    // ==== main: statistics ====\n', '''    // ==== main: statistics ====
    std::cerr << "old_probe_raw = " << solver.old_probe_raw
              << "\\nold_probe_duplicate = " << solver.old_probe_duplicate << '\\n';
    for (int st=0; st<3; ++st) for (int g=0; g<6; ++g) {
        const auto& q = solver.old_probe[st][g];
        const std::string prefix = "old_probe_" + std::to_string(st) + '_' + std::to_string(g) + '_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "valid = " << q.valid << '\\n'
                  << prefix << "same = " << q.same << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "saved = " << q.saved << '\\n'
                  << prefix << "ceiling = " << q.ceiling << '\\n'
                  << prefix << "sec = " << q.sec << '\\n';
    }
''')
if is_joint:
    s = s.replace('old_probe', 'joint_probe').replace('OldProbe', 'JointProbe')
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

旧紙の完成計画による追加DPを、通常の候補一覧へ入れずに独立して最後まで仕上げる測定版。基準の状態・出力を必ず復元し、将来の注文を読まない。追加計画の実装は solutions/'''+donor+''' と同じ。共通のprocessへ候補を渡し、編集済み・eject済みの結果がキャッシュにあれば引き継ぐ。測定用の仮の最終経路はheavy traceへ出さない。

old_probe_raw/duplicateは有効な追加元計画数と、通常計画のどれかと初期積層が同じ件数。old_probe_<stage>_<gate>_*のstageは0:未編集、1:編集済み、2:eject済み、gateは基準完成値との差の上限0/.25/.5/1/2/無制限。trials/valid/same/better/gain/saved/ceiling/secは試行数・有効数・同じ完成積層数・完成評価値改善数・改善合計・改善時の即時手数差・正の即時手数差の合計・仕上げ時間。ceilingはこの候補集合の局所的な手数機会を測るだけで将来の実現スコアの厳密な上界ではない。

既存の全ログ・スイッチ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節を保持する。固定設計で測定し、時間を超える測定専用版を通常評価する場合だけ--no-recordを使う。
''')
if is_joint:
    text = (p/'README.md').read_text().replace('旧紙の完成計画による追加DP', '異なる紙集合を持つDP第2解')
    (p/'README.md').write_text(text.replace('old_probe', 'joint_probe'))
print('Created',p)
