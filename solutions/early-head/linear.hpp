#include "../anchor-match/matching.hpp"
#include "../head-prob/prob.hpp"

struct LinearHead {
    Design& d;
    ProbabilityHead head;
    std::array<std::array<int, 256>, 256> pair_index{};
    std::vector<Design::Unit> types;
    std::vector<std::vector<float>> target, donor;
    std::vector<double> utility;
    double target_sum = 0, donor_sum = 0;
    int accepted = 0;

    explicit LinearHead(Design& design) : d(design), head(d, 2, true) {
        for (auto& row : pair_index) row.fill(-1);
        for (int a = 0; a < P; a++) types.push_back({a, -1, 0});
        for (int a = 0; a < P; a++)
            for (int b = a + 1; b < P; b++) if (d.ok[a][b]) {
                pair_index[a][b] = pair_index[b][a] = types.size();
                types.push_back({a, b, 0});
            }
        target.assign(types.size(), std::vector<float>(d.H));
        donor.assign(types.size(), std::vector<float>(d.H));
        for (int i = 0; i < int(types.size()); i++)
            for (int c = 0; c < d.H; c++) {
                auto u = types[i]; u.c = c;
                if (!d.valid(u, c)) continue;
                target[i][c] = head.target(u.a, u);
                if (u.b >= 0) target[i][c] += head.target(u.b, u);
                donor[i][c] = head.donor(u);
            }
        rebuild();
    }
    int index(const Design::Unit& u) const {
        return u.b < 0 ? u.a : pair_index[u.a][u.b];
    }
    double target_value(const Design::Unit& u) const { return target[index(u)][u.c]; }
    double donor_value(const Design::Unit& u) const { return donor[index(u)][u.c]; }
    double column_value(int c) const {
        std::array<int, 2> weight{};
        std::array<double, 2> best{};
        for (const auto& u : d.unit) if (u.c == c) {
            int b = d.color(u, c), w = d.weight(u);
            double v = donor_value(u);
            if (w > weight[b]) weight[b] = w, best[b] = v;
            else if (w == weight[b]) best[b] = std::max(best[b], v);
        }
        return head.prob[c][0] * best[0] + head.prob[c][1] * best[1];
    }
    void rebuild() {
        target_sum = donor_sum = 0;
        for (const auto& u : d.unit) target_sum += target_value(u);
        utility.resize(d.H);
        for (int c = 0; c < d.H; c++) donor_sum += utility[c] = column_value(c);
    }
    double merit(double weight) const { return d.cur - weight * (target_sum + donor_sum); }

    void run(int iterations, double weight, double temperature) {
        double best_value = merit(weight);
        auto best = d.unit;
#ifdef CHECK_LINEAR_PATH
        auto exact_value = [&]() {
            auto copy = std::make_unique<Design>(d);
            copy->refresh_reset();
            ProbabilityHead exact(*copy, 2, true);
            return copy->cur - weight * exact.rebuild();
        };
        double actual_best = exact_value();
#endif
        double temp = temperature;
        for (int it = 0; it < iterations; it++) {
            if ((it & 255) == 0) temp = temperature * std::pow(.01, double(it) / iterations);
            int x = d.rng.below(d.U), y = d.rng.below(d.U);
            if (x == y) continue;
            auto ox = d.unit[x], oy = d.unit[y], nx = ox, ny = oy;
            int kind = d.rng.below(4);
            if (kind == 0) {
                if (nx.c == ny.c) continue;
                std::swap(nx.c, ny.c);
            } else if (kind == 1) {
                if (nx.c == ny.c || d.nc[nx.c] <= 2) continue;
                nx.c = ny.c;
            } else {
                if (nx.b < 0) { std::swap(x, y); nx = d.unit[x]; ny = d.unit[y]; }
                if (nx.b < 0) continue;
                int side = d.rng.below(2), fixed = side ? nx.a : nx.b;
                if (d.partners[fixed].empty()) continue;
                int b = d.partners[fixed][d.rng.below(d.partners[fixed].size())];
                y = d.owner[b];
                if (x == y) continue;
                ny = d.unit[y];
                std::swap(side ? nx.b : nx.a, ny.a == b ? ny.a : ny.b);
            }
            ox = d.unit[x]; oy = d.unit[y];
            if ((nx.b >= 0 && !d.ok[nx.a][nx.b]) || (ny.b >= 0 && !d.ok[ny.a][ny.b]) ||
                !d.valid(nx, nx.c) || !d.valid(ny, ny.c)) continue;
            const int a = ox.c, b = oy.c;
            const double old_cur = d.cur;
            const double old_merit = merit(weight);
            const double dt = target_value(nx) + target_value(ny) - target_value(ox) - target_value(oy);
            d.update(ox, -1); d.update(oy, -1);
            d.unit[x] = nx; d.unit[y] = ny;
            d.update(nx, 1); d.update(ny, 1);
            const double va = column_value(a), vb = a == b ? 0 : column_value(b);
            const double dd = va - utility[a] + (a == b ? 0 : vb - utility[b]);
            const double next = d.cur - weight * (target_sum + dt + donor_sum + dd);
            if (next < old_merit || (temp > 0 && d.rng.real() < std::exp((old_merit - next) / temp))) {
                target_sum += dt; donor_sum += dd;
                utility[a] = va; if (a != b) utility[b] = vb;
                d.owner[nx.a] = x; if (nx.b >= 0) d.owner[nx.b] = x;
                d.owner[ny.a] = y; if (ny.b >= 0) d.owner[ny.b] = y;
                accepted++;
                if (next < best_value) {
                    best_value = next;
#ifdef CHECK_LINEAR_PATH
                    double actual = exact_value();
                    if (actual < actual_best) actual_best = actual, best = d.unit;
#else
                    best = d.unit;
#endif
                }
            } else {
                d.update(nx, -1); d.update(ny, -1);
                d.unit[x] = ox; d.unit[y] = oy;
                d.update(ox, 1); d.update(oy, 1);
                d.cur = old_cur;
            }
        }
#ifdef VERIFY_LINEAR_HEAD
        const double value = merit(weight);
        rebuild(); d.rebuild();
        assert(std::abs(value - merit(weight)) < 1e-4);
#endif
        d.unit = std::move(best); d.rebuild(); rebuild();
    }
};

struct LinearStats { int cycles = 0, proposals = 0; double decrease = 0; };
LinearStats optimize_linear(Design& d, int rounds, int steps, double weight, double temperature) {
    LinearStats stats;
    d.refresh_reset(); ProbabilityHead original(d, 2, true);
    double start = d.cur - weight * original.rebuild(), value = start;
    for (int round = 0; round < rounds; round++) {
        auto before = d.unit;
        LinearHead model(d);
        model.run(steps, weight, temperature);
        stats.proposals += model.accepted;
        d.refresh_reset();
        ProbabilityHead actual(d, 2, true);
        double next = d.cur - weight * actual.rebuild();
        if (next < value - 1e-8) value = next, stats.cycles++;
        else { d.unit = std::move(before); d.rebuild(); d.refresh_reset(); }
    }
    stats.decrease = (value - start) / P;
    return stats;
}
