// Structural probe only. Reuses the standalone probe's headers and bit helpers.
#define main independent_triple_probe_main
#include "probe.cpp"
#undef main
#include <iomanip>
#include <limits>
#include <queue>

namespace constrained {
constexpr int S = 720, G = 36, H = 28;
struct Rule {
    int opaque = 0, black = 0;
    std::array<std::uint8_t, S> out{};
};
struct Unit {
    std::vector<int> targets;
    int column = -1, paper = -1;
};
struct Goal { u64 mask, value; int target; };
struct Candidate {
    int u, v, single, triple_column, single_column, lack;
    int extra = -1, released = -1, released_column = -1;
    double nongeneric;
    std::vector<int> triple;
};

struct Probe {
    std::array<u64, 256> original{}, a{};
    std::vector<int> windows, handles;
    std::array<std::array<int, 6>, S> permutations{};
    std::array<std::array<std::uint8_t, S>, S> distance{};
    std::vector<Rule> rules;
    std::array<int, G> initial{};
    std::vector<Unit> units;
    std::array<std::string, 192> sheets;
    std::mt19937_64 rng{0x64993e015ULL};

    explicit Probe(std::istream& in) {
        for (auto& v : original) {
            std::string s; in >> s;
            assert(s.size() == 64);
            for (int j = 0; j < 64; j++) if (s[j] == '1') v |= 1ULL << j;
        }
        for (auto& s : sheets) { in >> s; assert(s.size() == 64); }
        u64 gm = 0;
        for (int j = 0; j < 64; j++) for (int k = 0; k < 6; k++)
            if (sheets[k][j] != '.') gm |= 1ULL << j;
        assert(pc(gm) == G);
        for (int j = 0; j < 64; j++) if (gm >> j & 1) windows.push_back(j);
        for (int t = 0; t < 256; t++) for (int j = 0; j < G; j++)
            if (original[t] >> windows[j] & 1) a[t] |= 1ULL << j;
        std::array<int, 256> ownership{};
        u64 seen = gm;
        int column = -1;
        for (int k = 6; k < 192; k++) {
            u64 opaque = 0, black = 0;
            for (int j = 0; j < 64; j++) if (sheets[k][j] != '.') {
                opaque |= 1ULL << j;
                if (sheets[k][j] == '1') black |= 1ULL << j;
            }
            const u64 new_handle = opaque & ~seen;
            if (new_handle) {
                assert(pc(new_handle) == 1);
                handles.push_back(__builtin_ctzll(new_handle));
                seen |= new_handle; column++;
            }
            Unit unit; unit.column = column; unit.paper = k;
            for (int t = 0; t < 256; t++) if (!((original[t] ^ black) & opaque)) {
                unit.targets.push_back(t); ownership[t]++;
            }
            assert(unit.targets.size() == 1 || unit.targets.size() == 2);
            units.push_back(unit);
        }
        assert(handles.size() == H);
        for (int n : ownership) assert(n == 1);
        std::array<int, 6> p{0, 1, 2, 3, 4, 5};
        int ns = 0;
        do { permutations[ns++] = p; } while (std::next_permutation(p.begin(), p.end()));
        assert(ns == S);
        auto rank = [](const auto& q) {
            int r = 0;
            for (int i = 0; i < 6; i++) {
                int n = 0; for (int j = i + 1; j < 6; j++) n += q[j] < q[i];
                r = r * (6 - i) + n;
            }
            return r;
        };
        std::array<std::vector<int>, S> next;
        for (int s = 0; s < S; s++) for (int from = 0; from < 5; from++)
            for (int to = 0; to < 6; to++) if (from != to) {
                auto q = permutations[s]; int moved = q[from];
                if (from < to) std::move(q.begin() + from + 1, q.begin() + to + 1, q.begin() + from);
                else std::move_backward(q.begin() + to, q.begin() + from, q.begin() + from + 1);
                q[to] = moved; next[s].push_back(rank(q));
            }
        for (int s = 0; s < S; s++) {
            distance[s].fill(255); distance[s][s] = 0;
            int q[S], begin = 0, end = 1; q[0] = s;
            while (begin < end) {
                int x = q[begin++];
                for (int y : next[x]) if (distance[s][y] == 255) {
                    distance[s][y] = distance[s][x] + 1; q[end++] = y;
                }
            }
            assert(end == S);
        }
        for (int opaque = 1; opaque < 64; opaque++)
            for (int black = (opaque - 1) & opaque; black; black = (black - 1) & opaque) {
                Rule r; r.opaque = opaque; r.black = black;
                for (int s = 0; s < S; s++) for (int k : permutations[s]) if (opaque >> k & 1) {
                    r.out[s] = black >> k & 1; break;
                }
                rules.push_back(r);
            }
        assert(rules.size() == 602);
        for (int j = 0; j < G; j++) {
            int opaque = 0, black = 0;
            for (int k = 0; k < 6; k++) if (sheets[k][windows[j]] != '.') {
                opaque |= 1 << k;
                if (sheets[k][windows[j]] == '1') black |= 1 << k;
            }
            initial[j] = -1;
            for (int r = 0; r < int(rules.size()); r++)
                if (rules[r].opaque == opaque && rules[r].black == black) initial[j] = r;
            assert(initial[j] >= 0 && pc(opaque) == 2);
        }
    }

    u64 differences(const Unit& u, bool generic = false) const {
        u64 d = 0;
        for (int t : u.targets) d |= generic ? a[u.targets[0]] ^ a[t] : original[u.targets[0]] ^ original[t];
        return d;
    }
    std::vector<Goal> goals(const std::vector<Unit>& us) const {
        std::vector<Goal> gs;
        for (const auto& u : us) if (u.targets.size() > 1) {
            u64 d = differences(u, true);
            for (int t : u.targets) gs.push_back({d, a[t], t});
        }
        return gs;
    }
    std::array<u64, S> displays(const std::array<int, G>& wr) const {
        std::array<u64, S> out{};
        for (int j = 0; j < G; j++) for (int s = 0; s < S; s++)
            if (rules[wr[j]].out[s]) out[s] |= 1ULL << j;
        return out;
    }
    double nongeneric(const std::vector<Unit>& us) const {
        std::array<std::vector<std::pair<int, int>>, H> columns;
        int hn[H][2]{};
        for (const auto& u : us) {
            const u64 d = differences(u);
            if (d >> handles[u.column] & 1) return 1e100;
            columns[u.column].emplace_back(int(u.targets.size()), original[u.targets[0]] >> handles[u.column] & 1);
            for (int j = 0; j < H; j++) if (j > u.column || (d >> handles[j] & 1))
                for (int t : u.targets) hn[j][original[t] >> handles[j] & 1]++;
        }
        double total = 0;
        for (int c = 0; c < H; c++) {
            const auto& col = columns[c];
            int n = col.size(), nt = 0, n1 = 0;
            for (auto [w, color] : col) nt += w, n1 += color;
            if (!n1 || n1 == n) return 1e100;
            int biggest[2]{}, weight_count[4]{};
            for (auto [w, color] : col) biggest[color] = std::max(biggest[color], w), weight_count[w]++;
            // The first two have opposite colors. Within each color an exchange
            // argument puts its largest weight there; remaining weights descend.
            weight_count[biggest[0]]--; weight_count[biggest[1]]--;
            int least = std::min(biggest[0], biggest[1]), position = 2;
            for (int w = 3; w >= 1; w--) {
                int count = weight_count[w];
                least += w * (2 * position + count - 1) * count / 2;
                position += count;
            }
            int imbalance = std::max(0, std::abs(n - 2 * n1) - 1);
            total += 0.85 * least + 0.15 * nt * (n - 1) / 2.0 + 0.1 * imbalance * imbalance;
            if (hn[c][0] + hn[c][1]) total += 1.6 * hn[c][0] * hn[c][1] / (hn[c][0] + hn[c][1]);
        }
        return total;
    }
    double generic(const std::vector<Goal>& gs, const std::array<int, G>& wr) const {
        const auto out = displays(wr);
        double sum = 0;
        for (const auto& goal : gs) {
            std::vector<int> ok;
            for (int s = 0; s < S; s++) if (!((out[s] ^ goal.value) & goal.mask)) ok.push_back(s);
            if (ok.empty()) return 1e100;
            int total = 0;
            for (int from = 0; from < S; from++) {
                int d = 255; for (int to : ok) d = std::min(d, int(distance[from][to]));
                total += d;
            }
            sum += double(total) / S;
        }
        return sum;
    }
    std::vector<Unit> replace(const Candidate& c) const {
        auto us = units;
        us[c.u].targets = c.triple; us[c.u].column = c.triple_column;
        us[c.v].targets = {c.single}; us[c.v].column = c.single_column;
        if (c.extra >= 0) {
            us[c.extra].targets = {c.released}; us[c.extra].column = c.released_column;
        }
        return us;
    }
    std::vector<Candidate> candidates() const {
        std::vector<Candidate> cs;
        // NEAR=0 preserves the original 16-candidate diagnostic, including its
        // duplicate same-column assignments and tie order, for exact replay.
        const bool legacy = std::getenv("CONSTRAINED_NEAR") && !std::atoi(std::getenv("CONSTRAINED_NEAR"));
        const auto out = displays(initial);
        for (int u = 0; u < int(units.size()); u++) if (units[u].targets.size() == 2)
            for (int v = u + 1; v < int(units.size()); v++) if (units[v].targets.size() == 2) {
                std::vector<int> ts = units[u].targets;
                ts.insert(ts.end(), units[v].targets.begin(), units[v].targets.end());
                for (int single : ts) for (int swap = 0; swap < 2; swap++) {
                    if (!legacy && swap && units[u].column == units[v].column) continue;
                    Candidate c; c.u = u; c.v = v; c.single = single;
                    c.triple_column = units[swap ? v : u].column;
                    c.single_column = units[swap ? u : v].column;
                    for (int t : ts) if (t != single) c.triple.push_back(t);
                    u64 d = 0, od = 0;
                    for (int t : c.triple) d |= a[t] ^ a[c.triple[0]], od |= original[t] ^ original[c.triple[0]];
                    if (od >> handles[c.triple_column] & 1) continue;
                    c.lack = 0;
                    for (int t : c.triple) {
                        int lack = G;
                        for (u64 shown : out) lack = std::min(lack, pc((shown ^ a[t]) & d));
                        c.lack += lack;
                    }
                    c.nongeneric = nongeneric(replace(c));
                    if (c.nongeneric < 1e50) cs.push_back(c);
                }
            }
        if (std::getenv("CONSTRAINED_FIVE")) {
            struct Seed { int u, w, lack, holes; std::vector<int> triple; };
            std::vector<Seed> pool;
            for (int u = 0; u < int(units.size()); u++) if (units[u].targets.size() == 2)
                for (int w = 0; w < int(units.size()); w++) if (units[w].targets.size() == 1) {
                    Seed s{u,w,0,0,units[u].targets}; s.triple.push_back(units[w].targets[0]);
                    u64 d = 0, od = 0;
                    for (int t : s.triple) d |= a[t] ^ a[s.triple[0]], od |= original[t] ^ original[s.triple[0]];
                    s.holes = pc(od); if (s.holes > 38) continue;
                    for (int t : s.triple) {
                        int lack = G; for (u64 shown : out) lack = std::min(lack, pc((shown ^ a[t]) & d));
                        s.lack += lack;
                    }
                    if (s.lack <= 4) pool.push_back(s);
                }
            std::sort(pool.begin(), pool.end(), [](const auto& a, const auto& b) {
                return std::array<int,3>{a.lack*3+a.holes,a.u,a.w} < std::array<int,3>{b.lack*3+b.holes,b.u,b.w};
            });
            if (pool.size() > 128) pool.resize(128);
            std::cerr << "five_target_seed_pool = " << pool.size() << '\n';
            for (const auto& s : pool) for (int v = 0; v < int(units.size()); v++)
                if (v != s.u && units[v].targets.size() == 2) {
                    std::array<int,3> cols{units[s.u].column,units[v].column,units[s.w].column};
                    std::sort(cols.begin(),cols.end());
                    do {
                        for (int which = 0; which < 2; which++) {
                            Candidate c; c.u=s.u;c.v=v;c.extra=s.w;c.triple=s.triple;c.lack=s.lack;
                            c.triple_column=cols[0];c.single_column=cols[1];c.released_column=cols[2];
                            c.single=units[v].targets[which];c.released=units[v].targets[1-which];
                            c.nongeneric = nongeneric(replace(c));
                            if (c.nongeneric < 1e50) cs.push_back(c);
                        }
                    } while (std::next_permutation(cols.begin(),cols.end()));
                }
        }
        std::sort(cs.begin(), cs.end(), [legacy](const auto& a, const auto& b) {
            const double ka = a.lack * 2.0 + a.nongeneric, kb = b.lack * 2.0 + b.nongeneric;
            if (legacy) return ka != kb ? ka < kb : std::array<int, 4>{a.u,a.v,a.single,a.triple_column} < std::array<int, 4>{b.u,b.v,b.single,b.triple_column};
            return ka != kb ? ka < kb : std::array<int, 7>{a.u,a.v,a.extra,a.single,a.triple_column,a.single_column,a.released_column} < std::array<int, 7>{b.u,b.v,b.extra,b.single,b.triple_column,b.single_column,b.released_column};
        });
        return cs;
    }
    void run(int limit, int steps) {
        const double base_h = nongeneric(units), base_g = generic(goals(units), initial);
        const auto cs = candidates();
        const double start_temperature = std::getenv("CONSTRAINED_TEMP") ? std::atof(std::getenv("CONSTRAINED_TEMP")) : 2.0;
        const bool nearby = !std::getenv("CONSTRAINED_NEAR") || std::atoi(std::getenv("CONSTRAINED_NEAR"));
        std::vector<std::vector<int>> neighbors(rules.size());
        std::vector<std::vector<int>> rule_distance(rules.size(), std::vector<int>(rules.size()));
        if (nearby) for (int r = 0; r < int(rules.size()); r++) {
            for (int q = 0; q < int(rules.size()); q++) {
                int d = 0; for (int s = 0; s < S; s++) d += rules[r].out[s] != rules[q].out[s];
                rule_distance[r][q] = d;
                if (r != q) neighbors[r].push_back(q);
            }
            std::sort(neighbors[r].begin(), neighbors[r].end(), [&](int x, int y) {
                return rule_distance[r][x] != rule_distance[r][y] ? rule_distance[r][x] < rule_distance[r][y] : x < y;
            });
        }
        std::cerr << std::setprecision(12) << "baseline_nongeneric = " << base_h / 256
                  << "\nbaseline_generic = " << base_g / 256 << "\ncandidates = " << cs.size() << '\n';
        for (int ci = 0; ci < std::min(limit, int(cs.size())); ci++) {
            const auto& candidate = cs[ci];
            const auto us = replace(candidate); const auto gs = goals(us);
            auto wr = initial;
            std::array<int, 64> witnesses{};
            for (int j = 0; j < G; j++) if (pc(rules[wr[j]].opaque) == 2) witnesses[rules[wr[j]].opaque]++;
            std::vector<std::array<std::int8_t, S>> miss(gs.size());
            std::vector<int> minima(gs.size()), multiplicity(gs.size());
            std::array<std::vector<int>, G> affected;
            auto init_display = displays(wr);
            for (int z = 0; z < int(gs.size()); z++) {
                for (int j = 0; j < G; j++) if (gs[z].mask >> j & 1) affected[j].push_back(z);
                for (int s = 0; s < S; s++) miss[z][s] = pc((init_display[s] ^ gs[z].value) & gs[z].mask);
            }
            std::array<double, S + 1> smooth{};
            for (int i = 1; i <= S; i++) smooth[i] = -0.006 * std::log(double(i));
            auto recalc = [&](int z) {
                int best = 64, count = 0;
                for (int s = 0; s < S; s++) best = std::min(best, int(miss[z][s]));
                for (int s = 0; s < S; s++) count += miss[z][s] == best;
                minima[z] = best; multiplicity[z] = count;
                return best + smooth[count];
            };
            double energy = 0; for (int z = 0; z < int(gs.size()); z++) energy += recalc(z);
            int best_lack = 100000, accepted = 0, feasible = 0;
            double best_total = 1e100;
            std::array<int, G> best_wr = initial;
            for (int it = 0; it < steps; it++) {
                std::vector<int> bad;
                int lack = 0;
                for (int z = 0; z < int(gs.size()); z++) {
                    lack += minima[z]; if (minima[z]) bad.push_back(z);
                }
                best_lack = std::min(best_lack, lack);
                if (!lack) {
                    feasible++;
                    const double value = candidate.nongeneric + generic(gs, wr);
                    if (value < best_total) { best_total = value; best_wr = wr; }
                    if (value < base_h + base_g) break;
                }
                int j = rng() % G, forced_state = -1, forced_bit = 0;
                if (!bad.empty() && rng() % 5) {
                    int z = bad[rng() % bad.size()], pick = rng() % multiplicity[z];
                    for (int s = 0; s < S; s++) if (miss[z][s] == minima[z] && !pick--) { forced_state = s; break; }
                    u64 errors = 0;
                    for (int w = 0; w < G; w++) if ((gs[z].mask >> w & 1) && rules[wr[w]].out[forced_state] != (gs[z].value >> w & 1)) errors |= 1ULL << w;
                    int skip = rng() % pc(errors); while (skip--) errors &= errors - 1;
                    j = __builtin_ctzll(errors); forced_bit = gs[z].value >> j & 1;
                }
                const int old = wr[j];
                int nr = rng() % rules.size();
                if (nearby && rng() % 8) {
                    std::vector<int> options;
                    for (int r : neighbors[old]) if (forced_state < 0 || rules[r].out[forced_state] == forced_bit) {
                        options.push_back(r); if (options.size() == 12) break;
                    }
                    if (!options.empty()) nr = options[rng() % options.size()];
                }
                if (forced_state >= 0) {
                    for (int retry = 0; retry < 50 && rules[nr].out[forced_state] != forced_bit; retry++) nr = rng() % rules.size();
                }
                if (nr == old) continue;
                int k = -1, oldk = -1;
                const int om = rules[old].opaque, nm = rules[nr].opaque;
                if (pc(om) == 2 && witnesses[om] == 1 && nm != om) {
                    std::vector<int> available;
                    for (int w = 0; w < G; w++) if (w != j && (pc(rules[wr[w]].opaque) > 2 || witnesses[rules[wr[w]].opaque] > 1)) available.push_back(w);
                    if (available.empty()) continue;
                    if (nearby) std::sort(available.begin(),available.end(),[&](int x,int y){
                        return rule_distance[old][wr[x]] != rule_distance[old][wr[y]] ? rule_distance[old][wr[x]] < rule_distance[old][wr[y]] : x < y;
                    });
                    k = available[rng() % (nearby ? std::min(4,int(available.size())) : int(available.size()))]; oldk = wr[k];
                }
                std::array<std::int8_t, S> delta{}, delta_k{};
                for (int s = 0; s < S; s++) {
                    delta[s] = rules[nr].out[s] - rules[old].out[s];
                    if (k >= 0) delta_k[s] = rules[old].out[s] - rules[oldk].out[s];
                }
                std::vector<int> changed = affected[j];
                if (k >= 0) {
                    changed.insert(changed.end(), affected[k].begin(), affected[k].end());
                    std::sort(changed.begin(), changed.end()); changed.erase(std::unique(changed.begin(), changed.end()), changed.end());
                }
                std::vector<int> oldmin, oldmult;
                double next_energy = energy;
                for (int z : changed) {
                    oldmin.push_back(minima[z]); oldmult.push_back(multiplicity[z]);
                    next_energy -= minima[z] + smooth[multiplicity[z]];
                    int sgn = (gs[z].mask >> j & 1) ? (gs[z].value >> j & 1) ? -1 : 1 : 0;
                    int sgnk = (k >= 0 && (gs[z].mask >> k & 1)) ? (gs[z].value >> k & 1) ? -1 : 1 : 0;
                    for (int s = 0; s < S; s++) miss[z][s] += sgn * delta[s] + sgnk * delta_k[s];
                    next_energy += recalc(z);
                }
                const double temp = start_temperature * std::pow(0.01, double(it) / std::max(1, steps - 1));
                const double u = (rng() >> 11) * 0x1.0p-53;
                if (next_energy <= energy || u < std::exp((energy - next_energy) / temp)) {
                    energy = next_energy; accepted++; wr[j] = nr;
                    if (pc(om) == 2) witnesses[om]--;
                    if (pc(nm) == 2) witnesses[nm]++;
                    if (k >= 0) {
                        if (pc(rules[oldk].opaque) == 2) witnesses[rules[oldk].opaque]--;
                        witnesses[om]++; wr[k] = old;
                    }
                } else {
                    for (int i = 0; i < int(changed.size()); i++) {
                        int z = changed[i];
                        int sgn = (gs[z].mask >> j & 1) ? (gs[z].value >> j & 1) ? -1 : 1 : 0;
                        int sgnk = (k >= 0 && (gs[z].mask >> k & 1)) ? (gs[z].value >> k & 1) ? -1 : 1 : 0;
                        for (int s = 0; s < S; s++) miss[z][s] -= sgn * delta[s] + sgnk * delta_k[s];
                        minima[z] = oldmin[i]; multiplicity[z] = oldmult[i];
                    }
                }
            }
            // Recompute every final displayed pattern independently for any claimed feasible result.
            if (best_total < 1e50) {
                assert(std::abs(best_total - candidate.nongeneric - generic(gs, best_wr)) < 1e-8);
                std::array<int, 64> witness{};
                for (int r : best_wr) if (pc(rules[r].opaque) == 2) witness[rules[r].opaque]++;
                for (int x = 0; x < 6; x++) for (int y = x + 1; y < 6; y++) assert(witness[(1 << x) | (1 << y)] > 0);
            }
            std::cout << std::setprecision(12) << "{\"candidate\":" << ci << ",\"steps\":" << steps
                      << ",\"old_papers\":[" << units[candidate.u].paper << ',' << units[candidate.v].paper << "]"
                      << ",\"triple\":[" << candidate.triple[0] << ',' << candidate.triple[1] << ',' << candidate.triple[2] << "]"
                      << ",\"single\":" << candidate.single << ",\"triple_column\":" << candidate.triple_column
                      << ",\"single_column\":" << candidate.single_column << ",\"initial_lack\":" << candidate.lack
                      << ",\"extra_paper\":" << (candidate.extra >= 0 ? units[candidate.extra].paper : -1)
                      << ",\"released\":" << candidate.released << ",\"released_column\":" << candidate.released_column
                      << ",\"temperature\":" << start_temperature << ",\"nearby_rules\":" << nearby
                      << ",\"best_lack\":" << best_lack << ",\"accepted\":" << accepted << ",\"feasible_visits\":" << feasible
                      << ",\"nongeneric_difference\":" << (candidate.nongeneric - base_h) / 256
                      << ",\"baseline_total\":" << (base_h + base_g) / 256
                      << ",\"total\":" << (best_total < 1e50 ? best_total / 256 : -1)
                      << ",\"difference\":" << (best_total < 1e50 ? (best_total - base_h - base_g) / 256 : 1e100)
                      << ",\"changes\":[";
            bool comma = false;
            if (best_total < 1e50) for (int j = 0; j < G; j++) if (best_wr[j] != initial[j]) {
                if (comma) std::cout << ','; comma = true;
                std::cout << '[' << windows[j] << ',' << rules[best_wr[j]].opaque << ',' << rules[best_wr[j]].black << ']';
            }
            std::cout << "]}\n" << std::flush;
            if (best_total < base_h + base_g) break;
        }
    }
};
} // namespace constrained

int main(int argc, char** argv) {
    constrained::Probe p(std::cin);
    p.run(argc > 1 ? std::atoi(argv[1]) : 16, argc > 2 ? std::atoi(argv[2]) : 10000);
}
