// ==== Final generic-layer optimization: potential measurement ====

// This probe never installs its candidates. Final units and column membership
// are fixed; all six sheets must still compare every pair of sheets.
struct FinalGenericProbe {
    const Design& d;
    const PosetSums& sums = PosetSums::get();
    std::vector<std::pair<int, int>> pairs;
    std::array<std::pair<int, int>, 15> edges{};
    std::array<int, 64> labels{};
    std::array<int, 15> counts{};
    std::vector<std::array<u64, 64>> original;
    // arc[physical window][new label][pair]. Physical windows include handles.
    std::array<std::array<std::vector<u64>, 30>, 63> arc;
    double baseline_gc = 0;
    mutable double best_delta = 0;
    mutable std::array<int, 64> best_labels{};
    mutable int best_swap_slot = -1, best_swap_window = -1;
    bool collect = env_int("ARGON_D1_STEADY") != 0;
    struct Candidate {
        std::array<int, 64> labels;
        std::array<int, 66> key;
        int slot, window;
        double uniform_delta, extra;
    };
    mutable std::vector<Candidate> candidates;
    struct Stats {
        long long blocks = 0, candidates = 0, feasible = 0, improved = 0;
        double best_delta = 0;
    } single, two, three, four, five, swap, swap_two;

    static u64 close(u64 r) {
        for (int k = 0; k < 6; ++k)
            r |= ((r >> k) & 0x010101010101ULL) * ((r >> (8 * k)) & 63);
        return r;
    }
    FinalGenericProbe(const Design& design, const Comparator& comp) : d(design) {
        int e = 0;
        for (int a = 0; a < 6; ++a)
            for (int b = a + 1; b < 6; ++b) edges[e++] = {a, b};
        for (const auto& u : d.unit) if (u.b >= 0) pairs.emplace_back(u.a, u.b);
        for (int j = 0; j < d.G; ++j) {
            int k = int(std::find(edges.begin(), edges.end(), comp.edge[j]) - edges.begin());
            labels[j] = 2 * k + comp.polarity[j];
            ++counts[k];
        }
        best_labels = labels;
        for (int w = 0; w < 63; ++w) for (int k = 0; k < 30; ++k) {
            auto& a = arc[w][k];
            a.resize(pairs.size());
            for (size_t p = 0; p < pairs.size(); ++p) {
                auto [u, v] = pairs[p];
                if (!((d.A[u] ^ d.A[v]) >> w & 1)) continue;
                auto [lo, hi] = edges[k / 2];
                if (int(d.A[u] >> w & 1) != (k & 1)) std::swap(lo, hi);
                a[p] = 1ULL << (8 * lo + hi);
            }
        }
        original.resize(pairs.size());
        for (size_t p = 0; p < pairs.size(); ++p) {
            u64 r = 0;
            for (int j = 0; j < d.G; ++j) r |= original[p][j] = arc[j][labels[j]][p];
            const u64 c = close(r);
            assert(!(c & kDiagonal));
            baseline_gc += sums.both_of(c) / 720.0;
        }
        if (collect) remember(labels, -1, -1, 0, 0);
    }

    // Do not count the 6! ways to rename all sheets as different comparators.
    void remember(const std::array<int, 64>& codes, int slot, int window, double delta, double extra) const {
        std::array<int, 6> rename; rename.fill(-1);
        std::array<int, 66> key{};
        int used = 0;
        for (int w = 0; w < d.G; ++w) {
            auto [a, b] = edges[codes[w] / 2];
            if (codes[w] & 1) std::swap(a, b);
            if (rename[a] < 0) rename[a] = used++;
            if (rename[b] < 0) rename[b] = used++;
            key[w] = 6 * rename[a] + rename[b];
        }
        key[64] = slot; key[65] = slot < 0 ? -1 : window;
        for (const auto& c : candidates) if (c.key == key) return;
        candidates.push_back({codes, key, slot, window, delta, extra});
    }

    // Swapping generic x and the handle of column h changes only that column's
    // dig/color term and that handle's hole term. All other columns and holes stay.
    double handle_delta(int x, int h) const {
        int n1 = 0, p1 = 0;
        std::array<int, 2> hn{};
        for (const auto& u : d.unit) {
            const int a = int(d.A[u.a] >> x & 1);
            const int b = u.b < 0 ? a : int(d.A[u.b] >> x & 1);
            if (u.c == h) {
                if (a != b) return 1e100;
                n1 += a;
                p1 += (u.b >= 0) * a;
            }
            if (u.c < h || a != b) {
                ++hn[a];
                if (u.b >= 0) ++hn[b];
            }
        }
        if (!n1 || n1 == d.nc[h]) return 1e100;
        return Design::colcost_of(d.nc[h], d.nt[h], n1, p1) - d.colcost(h)
             + Design::hole_cost_of(hn[0], hn[1], d.reset_targets[h]) - d.hcost(h);
    }

    // Change labels of slots x,y (y < 0: only x), and optionally replace the
    // physical window of x by wx. For two-label moves both labels must change.
    void enumerate(int x, int y, int wx, double extra, Stats& stat) const {
        ++stat.blocks;
        std::vector<u64> rest(pairs.size()), left(pairs.size());
        for (size_t p = 0; p < pairs.size(); ++p) {
            u64 r = 0;
            for (int j = 0; j < d.G; ++j) if (j != x && j != y) r |= original[p][j];
            rest[p] = close(r);
        }
        for (int a = 0; a < 30; ++a) {
            if (wx == x && a == labels[x]) continue;
            bool possible = true;
            for (size_t p = 0; p < pairs.size(); ++p) {
                left[p] = close(rest[p] | arc[wx][a][p]);
                if (left[p] & kDiagonal) { possible = false; break; }
            }
            // Adding y's arc cannot repair a cycle already present here.
            if (!possible) continue;
            for (int b = 0; b < (y < 0 ? 1 : 30); ++b) {
                if (y >= 0 && b == labels[y]) continue;
                bool complete = true;
                for (int e = 0; e < 15; ++e) {
                    const int n = counts[e] - int(labels[x] / 2 == e) + int(a / 2 == e)
                        + (y < 0 ? 0 : -int(labels[y] / 2 == e) + int(b / 2 == e));
                    if (!n) { complete = false; break; }
                }
                if (!complete) continue;
                ++stat.candidates;
                double gc = 0;
                bool feasible = true;
                for (size_t p = 0; p < pairs.size(); ++p) {
                    const u64 c = y < 0 ? left[p] : close(left[p] | arc[y][b][p]);
                    if (c & kDiagonal) { feasible = false; break; }
                    gc += sums.both_of(c) / 720.0;
                }
                if (!feasible) continue;
                ++stat.feasible;
                const double delta = (gc - baseline_gc + extra) / P;
                stat.improved += delta < -1e-10;
                stat.best_delta = std::min(stat.best_delta, delta);
                if (collect) {
                    auto codes = labels; codes[x] = a;
                    if (y >= 0) codes[y] = b;
                    remember(codes, wx == x ? -1 : x, wx, delta, extra / P);
                }
                if (delta < best_delta - 1e-10) {
                    best_delta = delta;
                    best_labels = labels;
                    best_labels[x] = a;
                    if (y >= 0) best_labels[y] = b;
                    best_swap_slot = wx == x ? -1 : x;
                    best_swap_window = wx;
                }
            }
        }
    }
    void enumerate_block(const std::array<int, 5>& slots, int size, Stats& stat) const {
        ++stat.blocks;
        std::array<std::array<u64, 72>, 6> closed{};
        u64 omitted = 0;
        auto left_counts = counts;
        for (int i = 0; i < size; ++i) {
            omitted |= 1ULL << slots[i];
            --left_counts[labels[slots[i]] / 2];
        }
        for (size_t p = 0; p < pairs.size(); ++p) {
            u64 r = 0;
            for (int j = 0; j < d.G; ++j) if (!(omitted >> j & 1)) r |= original[p][j];
            closed[0][p] = close(r);
        }
        std::array<std::vector<int>, 5> allowed;
        std::array<int, 5> visit{};
        std::array<int, 5> chosen{};
        for (int i = 0; i < size; ++i) {
            visit[i] = i;
            for (int c = 0; c < 30; ++c) {
                if (c == labels[slots[i]]) continue;
                bool ok = true;
                for (size_t p = 0; p < pairs.size(); ++p)
                    if (close(closed[0][p] | arc[slots[i]][c][p]) & kDiagonal) { ok = false; break; }
                if (ok) allowed[i].push_back(c);
            }
            if (allowed[i].empty()) return;
        }
        std::sort(visit.begin(), visit.begin() + size,
                  [&](int a, int b) { return allowed[a].size() < allowed[b].size(); });
        auto dfs = [&](auto&& self, int level) -> void {
            if (level == size) {
                ++stat.candidates;
                for (int n : left_counts) if (!n) return;
                ++stat.feasible;
                double gc = 0;
                for (size_t p = 0; p < pairs.size(); ++p) gc += sums.both_of(closed[level][p]) / 720.0;
                const double delta = (gc - baseline_gc) / P;
                stat.improved += delta < -1e-10;
                stat.best_delta = std::min(stat.best_delta, delta);
                if (collect) {
                    auto codes = labels;
                    for (int i = 0; i < size; ++i) codes[slots[i]] = chosen[i];
                    remember(codes, -1, -1, delta, 0);
                }
                if (delta < best_delta - 1e-10) {
                    best_delta = delta; best_labels = labels; best_swap_slot = -1;
                    for (int i = 0; i < size; ++i) best_labels[slots[i]] = chosen[i];
                }
                return;
            }
            const int i = visit[level], w = slots[i];
            for (int c : allowed[i]) {
                bool ok = true;
                for (size_t p = 0; p < pairs.size(); ++p) {
                    closed[level + 1][p] = close(closed[level][p] | arc[w][c][p]);
                    if (closed[level + 1][p] & kDiagonal) { ok = false; break; }
                }
                if (!ok) continue;
                chosen[i] = c;
                ++left_counts[c / 2];
                self(self, level + 1);
                --left_counts[c / 2];
            }
        };
        dfs(dfs, 0);
    }
    void blocks(int size, Stats& stat) const {
        std::array<int, 5> slots{};
        auto choose = [&](auto&& self, int used, int next) -> void {
            if (used == size) { enumerate_block(slots, size, stat); return; }
            for (int w = next; w <= d.G - (size - used); ++w) {
                slots[used] = w;
                self(self, used + 1, w + 1);
            }
        };
        choose(choose, 0, 0);
    }
    // Coherent moves permute whole edge groups, so windows already sharing an
    // edge stay together. This reaches changes of many windows without creating
    // opposite requirements merely by moving one member of a group.
    void anneal_groups(int iterations) {
        if (!iterations) return;
        const int n = int(pairs.size());
        std::array<std::array<unsigned char, 15>, 72> need{};
        std::array<double, 72> reference{};
        auto bit = [&](int code, int direction) -> u64 {
            if (!direction) return 0;
            auto [a, b] = edges[code / 2];
            if ((direction == 2) ^ bool(code & 1)) std::swap(a, b);
            return 1ULL << (8 * a + b);
        };
        for (int p = 0; p < n; ++p) {
            u64 r = 0;
            for (int w = 0; w < d.G; ++w) r |= original[p][w];
            reference[p] = sums.both_of(close(r)) / 720.0;
            for (int e = 0; e < 15; ++e) {
                if (r & bit(2 * e, 1)) need[p][e] = 1;
                if (r & bit(2 * e, 2)) need[p][e] = 2;
            }
        }
        XorShift random{0x864d2993e5ULL};
        long long trials = 0, accepted = 0, feasible = 0, improved = 0;
        double group_best = 0;
        const std::array<double, 4> starts{1, 3, 10, 30};
        for (double start : starts) {
            std::array<int, 15> map{};
            for (int e = 0; e < 15; ++e) map[e] = 2 * e;
            std::array<u64, 72> current{}, next{};
            for (int p = 0; p < n; ++p)
                for (int e = 0; e < 15; ++e) current[p] |= bit(map[e], need[p][e]);
            double value = baseline_gc, temperature = start;
            for (int it = 0; it < iterations; ++it) {
                if (!(it & 255)) temperature = start * std::pow(.015 / start, double(it) / iterations);
                std::array<int, 3> groups{}, codes{};
                const int count = 1 + int(random.mod(4) != 0) + int(random.mod(4) == 0);
                for (int j = 0; j < count; ++j) {
                    do { groups[j] = random.mod(15); }
                    while (std::find(groups.begin(), groups.begin() + j, groups[j]) != groups.begin() + j);
                }
                for (int j = 0; j < count; ++j)
                    codes[j] = map[groups[(j + 1) % count]] ^ (count == 1 ? 1 : int(random.next() & 1));
                double candidate = 0;
                int broken = 0;
                for (int p = 0; p < n; ++p) {
                    u64 r = current[p];
                    for (int j = 0; j < count; ++j) r &= ~bit(map[groups[j]], need[p][groups[j]]);
                    for (int j = 0; j < count; ++j) r |= bit(codes[j], need[p][groups[j]]);
                    next[p] = r;
                    const u64 c = close(r);
                    const int cycle = __builtin_popcountll(c & kDiagonal);
                    broken += cycle != 0;
                    candidate += cycle ? reference[p] + 4.0 * cycle / 3 : sums.both_of(c) / 720.0;
                }
                ++trials;
                if (!broken) {
                    ++feasible;
                    const double delta = (candidate - baseline_gc) / P;
                    improved += delta < -1e-10;
                    group_best = std::min(group_best, delta);
                    if (collect) {
                        auto chosen = map;
                        for (int j = 0; j < count; ++j) chosen[groups[j]] = codes[j];
                        auto labels_next = labels;
                        for (int w = 0; w < d.G; ++w)
                            labels_next[w] = (chosen[labels[w] / 2] & ~1) | ((labels[w] ^ chosen[labels[w] / 2]) & 1);
                        remember(labels_next, -1, -1, delta, 0);
                    }
                    if (delta < best_delta - 1e-10) {
                        best_delta = delta; best_swap_slot = -1;
                        auto chosen = map;
                        for (int j = 0; j < count; ++j) chosen[groups[j]] = codes[j];
                        for (int w = 0; w < d.G; ++w)
                            best_labels[w] = (chosen[labels[w] / 2] & ~1) | ((labels[w] ^ chosen[labels[w] / 2]) & 1);
                    }
                }
                if (candidate <= value || random.real() < std::exp((value - candidate) / temperature)) {
                    current = next; value = candidate; ++accepted;
                    for (int j = 0; j < count; ++j) map[groups[j]] = codes[j];
                }
            }
        }
        std::cerr << "d1_group_trials = " << trials << "\nd1_group_accepted = " << accepted
                  << "\nd1_group_feasible = " << feasible << "\nd1_group_improved = " << improved
                  << "\nd1_group_best_delta = " << group_best << '\n';
    }
    // Exact transition probabilities for the current set_generic policy, with
    // independent uniform targets. Singles leave this isolated layer unchanged.
    // This probe uses no real order sequence and does not model helpers/fillers.
    void steady_select() {
        if (!collect) return;
        const double start = elapsed_sec();
        Comparator graph;
        graph.M = 6; graph.G = d.G;
        graph.build_tables();
        std::array<u64, 720> orders{};
        for (int s = 0; s < 720; ++s)
            for (int i = 0; i < 6; ++i) orders[s] |= u64(graph.below[s][i]) << (8 * i);
        double worst_error = 0, worst_residual = 0;
        int max_rounds = 0, dominated = 0, dominated_better = 0, selected_dominated = 0;
        bool last_dominated = false;
        std::vector<u64> old_relations(pairs.size());
        for (size_t p = 0; p < pairs.size(); ++p) {
            for (int w = 0; w < d.G; ++w) old_relations[p] |= original[p][w];
            old_relations[p] = close(old_relations[p]);
        }
        auto evaluate = [&](const Candidate& c, bool baseline = false) {
            std::vector<std::vector<int>> sat;
            int weaker = 0;
            for (size_t p = 0; p < pairs.size(); ++p) {
                u64 relation = 0;
                for (int w = 0; w < d.G; ++w)
                    relation |= arc[w == c.slot ? c.window : w][c.labels[w]][p];
                relation = close(relation);
                assert(!(relation & kDiagonal));
                weaker += (old_relations[p] & ~relation) != 0;
                for (u64 r : {relation, transpose8(relation)}) {
                    sat.emplace_back();
                    for (int s = 0; s < 720; ++s) if (!(r & ~orders[s])) sat.back().push_back(s);
                    assert(!sat.back().empty());
                }
            }
            last_dominated = !weaker && c.extra >= -1e-12;
            if (!baseline) dominated += last_dominated;
            const int nq = int(sat.size());
            std::vector<std::array<unsigned char, 720>> distance(nq);
            std::array<int, 720> future{};
            for (int q = 0; q < nq; ++q) for (int s = 0; s < 720; ++s) {
                int m = 255;
                for (int t : sat[q]) if ((m = std::min(m, graph.distance(s, t))) == 0) break;
                distance[q][s] = static_cast<unsigned char>(m);
                future[s] += m;
            }
            double uniform = 0;
            for (int x : future) uniform += x / (720.0 * P);
            worst_error = std::max(worst_error, std::abs(uniform - (baseline_gc / P + c.uniform_delta - c.extra)));
            std::vector<std::array<uint16_t, 720>> destination(nq);
            for (int q = 0; q < nq; ++q) for (int s = 0; s < 720; ++s) {
                int chosen = -1, value = 1000000;
                for (int t : sat[q])
                    if (graph.distance(s, t) == distance[q][s] && future[t] < value) {
                        chosen = t; value = future[t];
                    }
                destination[q][s] = uint16_t(chosen);
            }
            std::array<double, 720> probability{}, next{}, flow{};
            probability.fill(1.0 / 720);
            double residual = 1;
            int round = 0;
            for (; round < 200 && residual > 1e-12; ++round) {
                next.fill(0);
                for (int s = 0; s < 720; ++s) flow[s] = probability[s] / nq;
                for (int q = 0; q < nq; ++q)
                    for (int s = 0; s < 720; ++s) next[destination[q][s]] += flow[s];
                residual = 0;
                for (int s = 0; s < 720; ++s) residual += std::abs(next[s] - probability[s]);
                probability = next;
            }
            max_rounds = std::max(max_rounds, round);
            worst_residual = std::max(worst_residual, residual);
            double average = 0;
            for (int s = 0; s < 720; ++s) average += probability[s] * future[s] / P;
            // Repeating the last target is forbidden. Its transition is the
            // identity and costs zero, so the marginal stationary distribution
            // is unchanged; mean moves are multiplied by P/(P-1).
            return average * P / (P - 1);
        };
        const double base = evaluate(candidates.front(), true);
        best_delta = 0; best_labels = labels; best_swap_slot = -1;
        double selected_uniform = 0;
        int better = 0;
        for (size_t i = 1; i < candidates.size(); ++i) {
            const auto& c = candidates[i];
            const double delta = evaluate(c) - base + c.extra;
            better += delta < -1e-10;
            dominated_better += last_dominated && delta < -1e-10;
            if (delta < best_delta - 1e-10) {
                best_delta = delta; best_labels = c.labels;
                best_swap_slot = c.slot; best_swap_window = c.window;
                selected_uniform = c.uniform_delta;
                selected_dominated = last_dominated;
            }
        }
        std::cerr << "d1_steady_candidates = " << candidates.size() << "\nd1_steady_better = " << better
                  << "\nd1_steady_baseline = " << base << "\nd1_steady_best_delta = " << best_delta
                  << "\nd1_steady_selected_uniform_delta = " << selected_uniform
                  << "\nd1_steady_uniform_error = " << worst_error << "\nd1_steady_residual = " << worst_residual
                  << "\nd1_steady_rounds = " << max_rounds << "\nd1_steady_sec = " << elapsed_sec() - start << '\n';
        std::cerr << "d1_steady_dominated = " << dominated
                  << "\nd1_steady_dominated_better = " << dominated_better
                  << "\nd1_steady_selected_dominated = " << selected_dominated << '\n';
    }
    void install(Design& out, Comparator& comp, std::vector<u64>& targets, std::vector<int>& permutation) const {
        std::cerr << "d1_best_delta = " << best_delta << "\nd1_applied = " << (best_delta < -1e-10) << '\n';
        if (best_delta >= -1e-10) return;
        if (best_swap_slot >= 0) {
            const int a = best_swap_slot, b = best_swap_window;
            for (int u = 0; u < P; ++u) {
                const u64 bit = ((out.A[u] >> a) ^ (out.A[u] >> b)) & 1;
                out.A[u] ^= (bit << a) | (bit << b);
                targets[u] = out.A[u];
            }
            std::swap(permutation[a], permutation[b]);
            for (int u = 0; u < P; ++u) {
                out.hb[u] = 0;
                for (int h = 0; h < out.H; ++h) out.hb[u] |= ((out.A[u] >> out.handle[h]) & 1) << h;
            }
        }
        for (int w = 0; w < d.G; ++w) {
            comp.edge[w] = edges[best_labels[w] / 2];
            comp.polarity[w] = best_labels[w] & 1;
        }
        comp.rebuild(); assert(comp.complete);
        for (auto [u, v] : pairs) {
            auto rows = comp.closure(out.A[u], out.A[u] ^ out.A[v]);
            u64 rel = 0;
            for (int i = 0; i < 6; ++i) rel |= u64(rows[i]) << (8 * i);
            assert(!(rel & kDiagonal));
            out.gcost[u][v] = out.gcost[v][u] = float(sums.both_of(rel) / 1440.0);
        }
        out.rebuild();
    }
    void run() {
        for (int x = 0; x < d.G; ++x) {
            enumerate(x, -1, x, 0, single);
            for (int y = x + 1; y < d.G; ++y) enumerate(x, y, x, 0, two);
        }
        for (int x = 0; x < d.G; ++x) for (int h = 0; h < d.H; ++h) {
            const double delta = handle_delta(x, h);
            if (delta > 1e50) continue;
            enumerate(x, -1, d.handle[h], delta, swap);
            if (env_int("ARGON_D1_EXTENDED"))
                for (int y = 0; y < d.G; ++y) if (y != x)
                    enumerate(x, y, d.handle[h], delta, swap_two);
        }
        const int block = std::min(5, env_int("ARGON_D1_BLOCK"));
        if (block >= 3) blocks(3, three);
        if (block >= 4) blocks(4, four);
        if (block >= 5) blocks(5, five);
        anneal_groups(env_int("ARGON_D1_GROUP_ITERS"));
        auto emit = [](const char* name, const Stats& s) {
            std::cerr << "d1_" << name << "_blocks = " << s.blocks
                      << "\nd1_" << name << "_candidates = " << s.candidates
                      << "\nd1_" << name << "_feasible = " << s.feasible
                      << "\nd1_" << name << "_improved = " << s.improved
                      << "\nd1_" << name << "_best_delta = " << s.best_delta << '\n';
        };
        std::cerr << "d1_baseline_gc = " << baseline_gc / P << '\n';
        emit("single", single); emit("two", two); emit("swap", swap); emit("swap_two", swap_two);
        emit("three", three); emit("four", four); emit("five", five);
        steady_select();
        std::cerr << "d1_oracle_delta = " << best_delta << '\n';
    }
};

