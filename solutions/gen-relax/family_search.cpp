// Offline (not a solution): which papers on one block of s windows let the most pairs be served?
// The block has a base paper (color Y on every window) and m extra papers, each with any pattern
// of hole / Y / ~Y per window. Over all stack orders, the displayed patterns (relative to Y, bit =
// ~Y) form a set Dsp. A pair with differing windows D (each window independently with probability
// p) and u's relative pattern B on D (uniform) can be served iff some X in Dsp has X & D == B and
// some X' in Dsp has X' & D == D & ~B. Prints the best probability for each m, and the partition
// of the block into m flip papers (gen-bf) for comparison.
// Build: g++ -std=c++23 -O2 family_search.cpp -o family_search ; run: family_search S M P
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <vector>

int s, m;
double p;

// Probability that a random pair is consistent with the display set (bitset over 2^s patterns).
double consistency(const std::vector<char>& dsp) {
    int T = 1 << s;
    double tot = 0;
    for (int D = 0; D < T; D++) {
        int c = __builtin_popcount(D);
        double w = 1;
        for (int i = 0; i < s; i++) w *= (D >> i & 1) ? p : 1 - p;
        // projections of Dsp on D
        std::vector<char> proj(T, 0);
        for (int X = 0; X < T; X++) if (dsp[X]) proj[X & D] = 1;
        int ok = 0;
        for (int B = D;; B = (B - 1) & D) {
            if (proj[B] && proj[D & ~B]) ok++;
            if (B == 0) break;
        }
        tot += w * ok / (double)(1 << c);
    }
    return tot;
}

int main(int argc, char** argv) {
    s = std::atoi(argv[1]);
    m = std::atoi(argv[2]);
    p = std::atof(argv[3]);
    int T = 1 << s;
    // Paper patterns: (opaque mask, color mask subset of opaque), opaque != 0.
    std::vector<std::pair<int, int>> pats;
    for (int o = 1; o < T; o++)
        for (int c = o;; c = (c - 1) & o) {
            pats.push_back({o, c});
            if (c == 0) break;
        }
    int np = pats.size();
    double best = -1;
    std::vector<int> best_idx;
    std::vector<int> idx(m, 0);
    // Enumerate multisets of m papers (non-decreasing indices).
    std::vector<int> order(m + 1);
    long long count = 0;
    while (true) {
        // display set over all orders of base (id m) and papers 0..m-1
        std::vector<char> dsp(T, 0);
        std::iota(order.begin(), order.end(), 0);
        do {
            int cov = 0, col = 0;
            for (int k : order) {
                int o, c;
                if (k == m) o = T - 1, c = 0;
                else o = pats[idx[k]].first, c = pats[idx[k]].second;
                col |= c & ~cov;
                cov |= o;
            }
            dsp[col] = 1;
        } while (std::next_permutation(order.begin(), order.end()));
        double v = consistency(dsp);
        count++;
        if (v > best + 1e-12) {
            best = v;
            best_idx = idx;
        }
        int i = m - 1;
        while (i >= 0 && idx[i] == np - 1) i--;
        if (i < 0) break;
        idx[i]++;
        for (int j = i + 1; j < m; j++) idx[j] = idx[i];
    }
    std::printf("s=%d m=%d p=%.2f: best consistency %.4f over %lld families; papers:", s, m, p, best, count);
    for (int k : best_idx) {
        std::printf(" ");
        for (int i = 0; i < s; i++)
            std::printf("%c", !(pats[k].first >> i & 1) ? '.' : (pats[k].second >> i & 1) ? '1' : '0');
    }
    std::printf("  (1 = ~Y, 0 = Y)\n");
}
