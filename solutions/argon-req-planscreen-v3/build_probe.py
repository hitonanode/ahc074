from pathlib import Path
import sys
sys.path.insert(0,'solutions/argon-req-oldfull-v2')
from build_seedcore import add_seed_core
p=Path('solutions/argon-req-planscreen-probe');assert not p.exists();p.mkdir()
s=add_seed_core(Path('solutions/argon-req-planscreen-v3/main.cpp').read_text())
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100]);s=s.replace(a,b,1)
sub('            if (cache_plans) collect_future(unprocessed_candidates, size_t(-1), cost);','            if (!seed && cache_plans) collect_future(unprocessed_candidates, size_t(-1), cost);')
sub('    struct ProcessSeed {','''    struct ExtraProbe { long long trials, same, better, saved; double gain, sec; };
    inline static std::array<std::array<ExtraProbe, 6>, 2> extra_probe{};
    inline static std::array<std::array<double, 6>, 2> extra_order_gain{};
    struct ProcessSeed {''')
a=s.index('            for (const auto& candidate : unprocessed_candidates) {')
b=s.index('            if (chosen_path != baseline_path) {',a)
s=s[:a]+'''            if (!seed) {
                const auto incumbent = save();
                const double value = plan_cost(chosen_path.size());
                std::array<std::array<double, 6>, 2> best_gain{};
                const std::array<double,6> gates = {0, .25, .5, 1, 2, 1e30};
                for (const auto& c : unprocessed_candidates) {
                    if (find_cached_plan(c) || c.state.order == incumbent.order) continue;
                    restore(c.state);
                    canonicalize();
                    OP_TAG(auto tags = c.tags;)
                    const double began = elapsed_sec();
                    auto path = post_optimize(st0, c.path, u OP_TAG(, tags), false, true);
                    const double edited_value = plan_cost(path.size());
                    const double edit_sec = elapsed_sec() - began;
                    const auto edited_state = save();
                    const ProcessSeed candidate{edited_state, path OP_TAG(, tags), 1};
                    for (int stage=0; stage<2; ++stage) {
                        const double start = elapsed_sec();
                        bool ok = true;
                        if (stage == 0) {
                            path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4, true);
                        } else {
                            restore(st0);
                            path = process(u, &candidate, &ok);
                        }
                        const double duration = edit_sec + elapsed_sec() - start;
                        const bool valid = ok && display() == A[u] && fillers_reachable();
                        const double next = valid ? plan_cost(path.size()) : value;
                        for (int g=0; g<int(gates.size()); ++g) if (edited_value <= value + gates[g]) {
                            auto& q = extra_probe[stage][g];
                            ++q.trials; q.same += order == incumbent.order; q.sec += duration;
                            if (valid && next < value - 1e-9) {
                                ++q.better; q.gain += value - next;
                                q.saved += int(chosen_path.size()) - int(path.size());
                                best_gain[stage][g] = std::max(best_gain[stage][g], value-next);
                            }
                        }
                    }
                    restore(incumbent);
                }
                for (int stage=0;stage<2;++stage) for (int g=0;g<6;++g)
                    extra_order_gain[stage][g] += best_gain[stage][g];
                restore(incumbent);
            }
'''+s[b:]
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    for (int st=0;st<2;++st) for (int g=0;g<6;++g) {
        const auto& q = solver.extra_probe[st][g];
        const std::string prefix = "extra_probe_" + std::to_string(st) + '_' + std::to_string(g) + '_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "same = " << q.same << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "saved = " << q.saved << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "best_gain = " << solver.extra_order_gain[st][g] << '\\n'
                  << prefix << "sec = " << q.sec << '\\n';
    }
''')
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-des-perf-latew105

元の計画生成から漏れた未編集候補を全て保存し、同じ開始状態で独立に仕上げる測定版。通常の候補一覧・最終出力は変えず、必ず基準の状態と経路へ戻す。将来の注文は読まない。

全候補を安い削除編集した後、stage0ではejectだけ、stage1では通常の中立探索まで完了する。extra_probe_<stage>_<gate>_*は削除後の値差上限0/.25/.5/1/2/無制限ごとの試行、同じ積層、改善数、即時手数差、評価改善、注文ごとの最大評価改善、処理秒。best_gainは同じ注文の複数候補の利得を重複加算しない。既存統計は仮試行の分も含むが、全ログ・スイッチ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・目次・節は保持する。

固定設計で評価する。時間超過する測定版を通常評価するときだけ--no-recordを使う。
''')
