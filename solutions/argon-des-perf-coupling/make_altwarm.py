from pathlib import Path
root=Path(__file__).resolve().parents[1]
d=root/'argon-des-perf-altwarm';d.mkdir()
s=(root/'argon-des-perf-altcache/main.cpp').read_text()
s=s.replace('explicit Perforation(Solver& solver)', 'explicit Perforation(Solver& solver, Perforation* previous = nullptr)')
start=s.index('struct Perforation {');end=s.index('// ==== Design state:', start)
part=s[start:end]
part=part.replace('        rebuild();\n', '        rebuild(previous);\n', 1)
part=part.replace('    long long cache_rows = 0, cache_skips = 0;', '    long long cache_rows = 0, cache_skips = 0;\n    long long reused_rows = 0, verified_rows = 0;')
part=part.replace('    void rebuild() {', '    void rebuild(Perforation* previous = nullptr) {')
part=part.replace('        refresh_cache();\n        profit = cached_profit();', '        refresh_cache(true, previous);\n        profit = cached_profit();')
a=part.index('    void refresh_cache(bool all = true) {');b=part.index('    double cached_profit() const {',a)
part=part[:a]+'''    void refresh_cache(bool all = true, Perforation* previous = nullptr) {
        AF_SCOPE(perforation_cache, 1);
        const bool warm = previous && previous->H == H && previous->cache.size() == P * kSamples;
        std::array<int, P> previous_owner{};
        if (warm) {
            for (int k = kFirst; k < K; ++k)
                for (int u : previous->owners[k]) previous_owner[u] = k;
            // Preserve each old entry in place until its new edges require rebuilding.
            cache = std::move(previous->cache);
        }
        cache_opacity = opacity;
        cache.resize(P * kSamples);
        static const bool verify = std::getenv("ARGON_D2_WARM_VERIFY") != nullptr;
        for (int u = 0; u < P; u++) {
            if (!all && !cache_dirty[u]) {
                cache_skips += kSamples;
                continue;
            }
            bool same = warm;
            u64 relevant = 0;
            if (same) {
                const int own = s.ded[u], old_own = previous_owner[u];
                same = columns[own] == previous->columns[old_own] && opacity[own] == previous->opacity[old_own];
                const u64 holes = low_bits(H) & ~opacity[own];
                // edge_column uses only these donor intervals and their sampled colors.
                // Intervals with fewer than two possible wrong holes cannot pay the 1.6 cost.
                auto signature = [&](const Perforation& p, int c, int b) {
                    const int k = p.heads[c][b];
                    const u64 mask = p.opacity[k] & holes;
                    const u64 wrong = mask & (p.colors[k] ^ target[u]);
                    const int lo = wrong ? 64 - __builtin_clzll(wrong) : 0;
                    const u64 cover = mask & ~low_bits(lo) & low_bits(c + 1);
                    if (lo > c || __builtin_popcountll(cover) < 2) return std::pair<u64,int>{0,0};
                    return std::pair<u64,int>{cover,lo};
                };
                for (int c = 0; same && c < H; ++c) if (c != columns[own]) {
                    for (int b = 0; same && b < 2; ++b) {
                        const auto now = signature(*this, c, b);
                        same = now == signature(*previous, c, b);
                        if (now.first) relevant |= now.first | (u64(1) << c);
                    }
                }
            }
            for (int sample = 0; sample < kSamples; sample++) {
                const int i = u * kSamples + sample;
                if (same && !((samples[i] ^ previous->samples[i]) & relevant)) {
                    ++reused_rows;
                    if (verify) {
                        const auto q = make_cache(make_edges(u, samples[i]));
                        assert(q.value == cache[i].value && q.forward == cache[i].forward &&
                               q.backward == cache[i].backward && q.avoid == cache[i].avoid);
                        ++verified_rows;
                    }
                    continue;
                }
                cache[i] = make_cache(make_edges(u, samples[i]));
                ++cache_rows;
            }
        }
    }
''' +part[b:]
s=s[:start]+part+s[end:]
needle='    const double perforation_start = elapsed_sec();'
assert s.count(needle)==1
s=s.replace(needle,'''    std::unique_ptr<Perforation<25>> saved25;
    std::unique_ptr<Perforation<64>> saved64;
    auto saved_perforation = [&]<int Capacity>() -> std::unique_ptr<Perforation<Capacity>>& {
        if constexpr (Capacity == 25) return saved25;
        else return saved64;
    };
'''+needle)
s=s.replace('        Perforation<Capacity> perforation(solver);','''        auto& saved = saved_perforation.template operator()<Capacity>();
        saved = std::make_unique<Perforation<Capacity>>(solver);
        auto& perforation = *saved;''')
s=s.replace('            Perforation<Capacity> p(solver);','''            auto& saved = saved_perforation.template operator()<Capacity>();
            auto refined = std::make_unique<Perforation<Capacity>>(solver, saved.get());
            auto& p = *refined;''')
s=s.replace('            std::cerr << "d2_alt_trials = " << p.trials','''            std::cerr << "d2_alt_reused_rows = " << p.reused_rows
                      << "\\nd2_alt_verified_rows = " << p.verified_rows << '\\n';
            std::cerr << "d2_alt_trials = " << p.trials''')
s=s.replace('                      << "\\nd2_alt_donor = " << p.accepted_donor / P << \'\\n\';',
'''                      << "\\nd2_alt_donor = " << p.accepted_donor / P << '\\n';
            saved = std::move(refined);''')
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''改良元: solutions/argon-des-perf-latew105

穿孔後再割当の後に、現在のheadで穴の追加・復元を1巡行う。
元のペア穴・自列ハンドル・汎用窓・capは保つ。係数0.7、32層化標本。
再割当前後で所有紙の穴、headの有効区間、関係する標本の色が全て同じなら、
以前の区間DP表を再利用する。区間ごとの最大値・加算の順序は変えない。
同じ固定seedで作る層化一様乱数も再利用する。

ARGON_D2_ALT_PASSESの既定値は1（0で追加段なし）。ARGON_D2_WARM_VERIFYを定義すると、
再利用したDP表を全て独立に再計算し、forward/backward/avoid/valueを完全一致で照合する。
d2_alt_reused_rows/verified_rowsは再利用数/照合数（各段8192標本）。
d2_alt_build_sec/search_sec/sec/end_secは準備/探索/段全体/終了時刻。
d2_alt_trials/accepts、before/after/added/restored、cost/owner/donorは
候補/採用数、穴数、穴費用/所有目標の条件付き価値/他目標への価値の差（手/注文）。
既存ログ・スイッチ・プロファイラ・DesignStoreを全て保持。
追加段と目次項目はdesign_papers: alternating perforation and reassignment。
''')
