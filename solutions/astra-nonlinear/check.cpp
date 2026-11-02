#define main nonlinear_submission_main
#include "main.cpp"
#undef main

static void refresh_displays(Comparator& c) {
    c.generic_display.assign(c.perms.size(), 0);
    for (int s = 0; s < int(c.perms.size()); s++) {
        u64 covered = 0;
        for (int k : c.perms[s]) {
            c.generic_display[s] |= c.black[k] & ~covered;
            covered |= c.opq[k];
        }
    }
}

int main() {
    std::mt19937_64 rng(1701);
    std::vector<u64> a(P);
    for (auto& x : a) {
        x = 0;
        while (__builtin_popcountll(x) < 32) x |= 1ULL << (rng() % 64);
    }
    Comparator c;
    c.init(6, 36, rng);
    c.build_tables();
    c.optimize_rules(a, 1, 1e100);
    long long checked_pairs = 0, checked_paths = 0;
    for (int variant = 0; variant < 2; variant++) {
        if (variant) {
            // Window 35 is not one of the original 15 visibility witnesses.
            // Force a 2-black/2-white gate to exercise nonlinear paths even if
            // a particular hill-climb accepts only ordinary comparisons.
            for (int k = 0; k < 6; k++) {
                c.opq[k] &= ~(1ULL << 35);
                c.black[k] &= ~(1ULL << 35);
                if (k < 4) c.opq[k] |= 1ULL << 35;
                if (k < 2) c.black[k] |= 1ULL << 35;
            }
            c.nonlinear = true;
            refresh_displays(c);
        }
        for (int u = 0; u < P; u++) for (int v = u + 1; v < P; v++) {
            if (__builtin_popcountll(a[u] ^ a[v]) > 26) continue;
            u64 mask = (a[u] ^ a[v]) & low_bits(36);
            std::vector<int> goals[2];
            for (int t = 0; t < 720; t++) {
                u64 covered = 0, shown = 0;
                for (int k : c.perms[t]) {
                    shown |= c.black[k] & ~covered;
                    covered |= c.opq[k];
                }
                assert(shown == c.generic_display[t]);
                if (!((shown ^ a[u]) & mask)) goals[0].push_back(t);
                if (!((shown ^ a[v]) & mask)) goals[1].push_back(t);
            }
            bool ok = !goals[0].empty() && !goals[1].empty();
            assert(c.compatible(a[u], a[v]) == ok);
            checked_pairs++;
            if (!ok || checked_paths >= 300 * (variant + 1)) continue;
            for (int side = 0; side < 2; side++) {
                const u64 target = side ? a[v] : a[u];
                assert(c.satisfying(target, mask) == goals[side]);
                int direct_sum = 0, ball_sum = 0;
                for (int s = 0; s < 720; s++) {
                    int best = 255;
                    for (int t : goals[side]) best = std::min(best, c.distance(s, t));
                    direct_sum += best;
                    for (int k = 0; k < 6; k++) {
                        bool covered = false;
                        for (int t : goals[side]) covered |= c.distance(s, t) <= k;
                        ball_sum += !covered;
                    }
                }
                assert(direct_sum == ball_sum);
                assert(std::abs(c.mean_moves(target, mask) - double(direct_sum) / 720) < 1e-9);
                int s = rng() % 720, optimum = 255;
                for (int t : goals[side]) optimum = std::min(optimum, c.distance(s, t));
                auto plan = c.plan(c.perms[s], target, mask);
                assert(int(plan.size()) == optimum);
                auto order = c.perms[s];
                for (auto [k, d] : plan) {
                    auto it = std::find(order.begin(), order.end(), k);
                    u64 covered = 0;
                    for (auto p = order.begin(); p != it; p++) covered |= c.opq[*p];
                    assert(c.opq[k] & ~covered);
                    order.erase(it);
                    order.insert(order.begin() + d, k);
                }
                int t = c.order_index(order);
                assert(!((c.generic_display[t] ^ target) & mask));
                checked_paths++;
            }
        }
    }
    std::cerr << "checked_pairs = " << checked_pairs << "\nchecked_paths = " << checked_paths << '\n';
}
