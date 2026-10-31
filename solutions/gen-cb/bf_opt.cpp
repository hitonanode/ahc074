// Offline (not a solution): minimum moves per order for the "base + flip papers" layer, by BFS over
// stack orders, compared with the greedy policy of gen-bf and with complementary blocks (t/2).
// Items: 0 = base, 1..k = flip papers. Flip i is on iff it is above the base. Moves: the base to
// any position if visible (some flip below it), or an on flip (above the base) to any position.
// Each order touches each flip with probability q and needs it on/off with probability 1/2.
// Ties among the end states of minimum moves are broken at random (no lookahead).
// Build: g++ -std=c++23 -O2 bf_opt.cpp -o bf_opt ; run: bf_opt K Q ORDERS
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <random>
#include <vector>

using State = std::vector<int>;

int main(int argc, char** argv) {
    int k = argc > 1 ? std::atoi(argv[1]) : 7;
    double q = argc > 2 ? std::atof(argv[2]) : 0.5;
    int orders = argc > 3 ? std::atoi(argv[3]) : 20000;
    std::mt19937_64 rng(1);
    State st(k + 1);
    for (int i = 0; i <= k; i++) st[i] = i;  // base on top: all off
    long long total = 0, touched = 0;
    for (int o = 0; o < orders; o++) {
        std::vector<int> need(k + 1, -1);
        for (int i = 1; i <= k; i++)
            if ((rng() >> 11) * 0x1.0p-53 < q) need[i] = rng() & 1, touched++;
        auto ok = [&](const State& s) {
            int pb = std::find(s.begin(), s.end(), 0) - s.begin();
            for (int p = 0; p <= k; p++) {
                int i = s[p];
                if (i == 0 || need[i] < 0) continue;
                if ((p < pb) != (need[i] == 1)) return false;
            }
            return true;
        };
        // BFS by layers.
        std::map<State, int> seen;
        std::vector<State> layer = {st};
        seen[st] = 0;
        int depth = 0;
        std::vector<State> goals;
        while (true) {
            for (auto& s : layer) if (ok(s)) goals.push_back(s);
            if (!goals.empty()) break;
            std::vector<State> nxt;
            for (auto& s : layer) {
                int pb = std::find(s.begin(), s.end(), 0) - s.begin();
                for (int p = 0; p <= k; p++) {
                    int i = s[p];
                    bool movable = (i == 0) ? (pb < k) : (p < pb);
                    if (!movable) continue;
                    State r = s;
                    r.erase(r.begin() + p);
                    for (int np = 0; np <= k; np++) {
                        if (np == p) continue;
                        State t = r;
                        t.insert(t.begin() + np, i);
                        if (seen.emplace(t, depth + 1).second) nxt.push_back(t);
                    }
                }
            }
            layer.swap(nxt);
            depth++;
        }
        total += depth;
        st = goals[rng() % goals.size()];
    }
    std::printf("k=%d q=%.2f: optimal moves/order %.4f, touched/order %.4f, CB %.4f, ratio %.3f\n", k, q,
                (double)total / orders, (double)touched / orders, touched / 2.0 / orders,
                (double)total / (touched / 2.0));
}
