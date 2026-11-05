from pathlib import Path

root=Path(__file__).resolve().parents[1]
d=root/'argon-des-perf-altcache';d.mkdir()
s=(root/'argon-des-perf-alternate/main.cpp').read_text()
s=s.replace('    std::vector<bool> first_heads(K, false);\n    const auto before_late_ded = state.ded;\n','')
s=s.replace('        for (const auto& head : perforation.heads) first_heads[head[0]] = first_heads[head[1]] = true;\n','')
s=s.replace('void run(double weight, bool revisit = false, const std::vector<bool>* focus = nullptr)', 'void run(double weight, bool revisit = false)')
s=s.replace('(k != heads[c][b] || (focus && !(*focus)[k]))','k != heads[c][b]')
begin=s.index('        std::vector<bool> focus(K, false);')
end=s.index('        auto refine =',begin)
s=s[:begin]+s[end:]
s=s.replace('            Perforation<Capacity> p(solver);\n            for (const auto& h : p.heads) for (int k : h) if (!first_heads[k]) focus[k] = true;',
'''            const double build_start = elapsed_sec();
            Perforation<Capacity> p(solver);
            const double build_sec = elapsed_sec() - build_start;''')
s=s.replace('            p.run(0.7, true, nullptr);', '''            const double search_start = elapsed_sec();
            p.run(0.7, true);
            const double search_sec = elapsed_sec() - search_start;''')
s=s.replace('            std::cerr << "d2_alt_trials = " << p.trials', '''            std::cerr << "d2_alt_build_sec = " << build_sec
                      << "\\nd2_alt_search_sec = " << search_sec << '\\n';
            std::cerr << "d2_alt_trials = " << p.trials''')
begin=s.index('        if constexpr (false) {')
end=s.index('    std::cerr << "d2_alt_passes',begin)
s=s[:begin]+'    }\n'+s[end:]
begin=s.index('        std::mt19937_64 random(731000003);')
end=s.index('        refresh_cache();',begin)
s=s[:begin]+'''        // The stratified uniforms depend only on H and the fixed seed. Reuse
        // them when the head probabilities are rebuilt after reassignment.
        static int sampled_h = -1;
        static std::vector<double> uniforms;
        if (sampled_h != H) {
            sampled_h = H;
            uniforms.resize(P * H * kSamples);
            std::mt19937_64 random(731000003);
            for (int u = 0; u < P; ++u) for (int c = 0; c < H; ++c) {
                std::array<int, kSamples> strata;
                std::iota(strata.begin(), strata.end(), 0);
                std::shuffle(strata.begin(), strata.end(), random);
                for (int sample = 0; sample < kSamples; ++sample)
                    uniforms[(u * H + c) * kSamples + sample] =
                        (strata[sample] + (random() >> 11) * 0x1.0p-53) / kSamples;
            }
        }
        samples.assign(P * kSamples, 0);
        for (int u = 0; u < P; ++u) for (int c = 0; c < H; ++c)
            for (int sample = 0; sample < kSamples; ++sample)
                if (uniforms[(u * H + c) * kSamples + sample] < probability[c][1])
                    samples[u * kSamples + sample] |= 1ULL << c;
'''+s[end:]
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''改良元: solutions/argon-des-perf-latew105

穿孔を反映した再割当の後に、全ての新しい列頭を対象として穿孔をもう一度行う。
現在の共有目標が両方同じ色を要求する窓だけを復元でき、新しい穴も許す。
既存の穴は非headでも復元候補に含める。自列ハンドル・汎用窓・capは変えない。
再評価の係数は0.7、32層化標本。ARGON_D2_ALT_PASSESの既定値は1（0で追加段を無効化）。
層化乱数は窓数と固定seedだけで決まるため、初回に作った一様乱数を再利用する。
再評価の値や候補順を変えず、乱数生成の重複を省く。

d2_alt_trials/acceptsは候補数/採用数、before/after/added/restoredは穴数、
cost/owner/donorは注文当たりの穴費用/所有目標の条件付き価値/他目標への価値の差。
build_sec/search_secは再評価の準備/探索時間、sec/end_secは段の時間/終了時刻。
全既存ログ・スイッチ・プロファイラ・DesignStoreを保持する。
design_papers: alternating perforation and reassignment の段と目次項目を追加する。
''')
