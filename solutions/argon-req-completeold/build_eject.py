from pathlib import Path
r=Path('solutions'); src=(r/'argon-req-completeeject/main.cpp').read_text()
def write(name,s,desc):
 p=r/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/argon-req-completefast-v3\n\n'+desc+'\n\n既存の計画・目的関数・設計・予算・ログ・スイッチ・プロファイラ・DesignStore・段の目印と目次を維持する。追加処理だけを変更し、既存の処理を減らさない。新しい環境変数はない。value_seed_trials/valid/accepts/gain/savedは追加処理数、有効数、採用数、完成値の改善、採用時の即時手数差。\n')
for kind in ['old','local','once','tight']:
 s=src
 if kind in ['old','local']:
  s=s.replace('                weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});',
   '                if ('+('!o.complete_value' if kind=='old' else 'o.complete_value')+') weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});')
 if kind=='once':
  s=s.replace('auto path = polish_ejects(st0, c.path, u OP_TAG(, tags), 4, true);','auto path = polish_ejects(st0, c.path, u OP_TAG(, tags), 1, true);')
 if kind=='tight':s=s.replace('c.cost <= value + .5','c.cost <= value + .25')
 descriptions={'old':'抽出直後の重みを使う共同DP計画だけに追加ejectを行う。', 'local':'ハンドル修正後の重みを使う共同DP計画だけに追加ejectを行う。','once':'2種の共同DP計画の編集済みキャッシュへejectを1回だけ適用する。成功後の再編集とejectの繰り返しは追加しない。','tight':'2種の共同DP計画の編集済みキャッシュを使い、現在の完成値との差が0.25以内に限って追加ejectを行う。'}
 write('argon-req-completeeject-'+kind,s,descriptions[kind])

s=src.replace('    Moves process(int u) {', '''    struct EjectYield { long long calls=0, wins=0, saved=0; double gain=0, seconds=0; };
    std::array<EjectYield, 8> eject_yield{};
    Moves process(int u) {''')
s=s.replace('        std::vector<FutureCandidate> weighted_raw;','        std::vector<FutureCandidate> weighted_raw;\n        std::vector<int> weighted_kind;')
s=s.replace('                weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});','                weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});\n                weighted_kind.push_back(o.complete_value);')
s=s.replace('        for (const auto& raw : weighted_raw) if (const auto* cached = find_cached_plan(raw)) {','        for (size_t raw_i=0; raw_i<weighted_raw.size(); ++raw_i) if (const auto* cached = find_cached_plan(weighted_raw[raw_i])) {')
s=s.replace('                const auto incumbent = save();\n                restore(c.state);', '''                const auto incumbent = save();
                const int bucket = 4 * weighted_kind[raw_i] + (c.cost > value + .25 ? 3 : c.cost > value ? 2 : c.cost > value - .25 ? 1 : 0);
                auto& y = eject_yield[bucket];
                ++y.calls;
                const auto tick = Clock::now();
                restore(c.state);''')
s=s.replace('                const double next = plan_cost(path.size());\n                const bool valid', '                y.seconds += scaled_since(tick);\n                const double next = plan_cost(path.size());\n                const bool valid')
s=s.replace('                    ++value_seed_accepts;', '                    ++y.wins;\n                    y.gain += value - next;\n                    y.saved += int(chosen_path.size()) - int(path.size());\n                    ++value_seed_accepts;')
s=s.replace('    // ==== main: statistics ====\n', '''    // ==== main: statistics ====
    for (int i=0;i<8;++i) {
        const auto& y=solver.eject_yield[i];
        std::cerr << "eject_yield_" << i << "_calls = " << y.calls
                  << "\\neject_yield_" << i << "_wins = " << y.wins
                  << "\\neject_yield_" << i << "_saved = " << y.saved
                  << "\\neject_yield_" << i << "_gain = " << y.gain
                  << "\\neject_yield_" << i << "_sec = " << y.seconds << '\\n';
    }
''')
write('argon-req-completeeject-profile',s,'2種の共同DPへの追加ejectを、元のDPと現行完成値との差で分類する測定版。eject_yield_i_calls/wins/saved/gain/secは呼び出し、採用、即時手数差、評価値差、追加処理時間。i=0..3は抽出直後、4..7は修正後のDPで、各4区分は値差≤−0.25、≤0、≤0.25、≤0.5。通常の全計画は保持し、測定のために将来注文を参照しない。')
