from pathlib import Path
p=Path('solutions/argon-req-seedfinish-probe')
assert not (p/'main.cpp').exists()
p.mkdir(exist_ok=True)
s=Path('solutions/argon-req-seedfinish/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100])
 s=s.replace(a,b,1)
sub('''    inline static long long seed_finish_trials''','''    struct SeedFinishProbe { long long trials, valid, better, saved, ceiling; double gain, sec; };
    inline static std::array<SeedFinishProbe, 4> seed_finish_probe{};
    inline static long long seed_finish_trials''')
sub('''            auto alternative = process(u, &candidate, &ok);''','''            const double started = elapsed_sec();
            auto alternative = process(u, &candidate, &ok);
            const double seconds = elapsed_sec() - started;''')
sub('''                path = std::move(alternative);
                OP_TAG(tags = op_tags;)
            } else restore(ejected);''','''            }
            const double reference = std::min(value, ejected_value);
            const int baseline_moves = ejected_value < value - 1e-9 ? int(path.size()) : int(chosen.size());
            const std::array<double,4> gates = {0, .1, .25, .5};
            for (int g=0; g<int(gates.size()); ++g) if (ejected_value - value <= gates[g]) {
                auto& q = seed_finish_probe[g];
                ++q.trials; q.valid += valid; q.sec += seconds;
                if (valid) q.ceiling += std::max(0, baseline_moves-int(alternative.size()));
                if (valid && completed < reference - 1e-9) {
                    ++q.better; q.gain += reference-completed;
                    q.saved += baseline_moves-int(alternative.size());
                }
            }
            restore(ejected);  // output the base's extra-eject decision, not the oracle
''')
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    for (int g=0; g<4; ++g) {
        const auto& q = solver.seed_finish_probe[g];
        const std::string prefix = "seed_probe_" + std::to_string(g) + '_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "valid = " << q.valid << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "saved = " << q.saved << '\\n'
                  << prefix << "ceiling = " << q.ceiling << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "sec = " << q.sec << '\\n';
    }
''')
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

採用済みの追加ejectの先に、中立探索を追加した場合の残余利得を同じ開始状態から測る。試行後は必ず基準のeject後の状態・経路へ戻すため、実際の操作列と次の要求の開始状態は基準を保つ。未来の注文は読まない。

seed_probe_<gate>_* は追加eject後と基準最終計画との評価値差の上限0/0.1/0.25/0.5別の試行数trials、正当な計画数valid、基準を改善する件数better、改善時の即時手数差saved、正の即時手数差ceiling、完成評価改善gain、追加仕上げ時間sec。ceilingはこの候補集合で観測した即時手数機会であり、任意の将来スコアに対する厳密な上界ではない。既存の全ログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、節と目次を保持する。
''')
print(p)
