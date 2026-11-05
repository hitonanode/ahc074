from pathlib import Path
p=Path('solutions/argon-req-oldvalue-gateprobe')
s=Path('solutions/argon-req-oldvalue-oracle/main.cpp').read_text()
s=s.replace('''    bool old_force_valid = false;''','''    bool old_force_valid = false;
    double old_force_raw_cost = 0;''',1)
s=s.replace('''        old_forced_order = best_state.order;''','''        old_forced_order = best_state.order;
        old_force_raw_cost = best;''',1)
s=s.replace('''    } probes[5];''','''    } probes[5];
    const std::array<double, 7> gates = {0, .25, .5, 1, 1.5, 2, 3};
    struct GateProbe { long long calls = 0, better = 0, moves = 0; double gain = 0; } gate_probe[5][7];''',1)
s=s.replace('''                auto& stats = probes[mode];''','''                for (int g = 0; g < int(gates.size()); g++) if (oracle->old_force_raw_cost <= actual + gates[g]) {
                    auto& q = gate_probe[mode][g];
                    q.calls++;
                    q.better += value < actual - 1e-9;
                    q.gain += std::max(0.0, actual - value);
                    if (value < actual - 1e-9) q.moves += int(moves.size()) - int(path.size());
                }
                auto& stats = probes[mode];''',1)
s=s.replace('''    for (int mode = 0; mode < 5; mode++) {
        const std::string prefix''','''    for (int mode = 0; mode < 5; mode++) for (int g = 0; g < int(gates.size()); g++) {
        const std::string prefix = "old_gate_" + std::to_string(mode) + '_' + std::to_string(g) + '_';
        const auto& q = gate_probe[mode][g];
        std::cerr << prefix << "calls = " << q.calls << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "moves = " << q.moves << '\\n';
    }
    for (int mode = 0; mode < 5; mode++) {
        const std::string prefix''',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(Path('solutions/argon-req-oldvalue-oracle/README.md').read_text()+'''
old_gate_<mode>_<g>は、初期候補のplan_costが基準の完成値から一定以内の場合だけ仕上げる条件の測定。g=0..6の幅は0, 0.25, 0.5, 1, 1.5, 2, 3。calls/better/gain/movesは条件に入る数、完成値の改善数・改善量、その時の即時手数差。ゲートは完成前にわかる値だけを使う。
''')
