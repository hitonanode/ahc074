// Offline check of the generic layer (base paper + nb flip papers): replays the wanted orientation
// patterns of one case (REQ lines of the audit2-probe stderr: want_set / want_pat) through
//   (a) the minimum number of moves per request (BFS over the 720 orders, visibility respected),
//   (b) the same, choosing among the end states of minimum cost the one with the best expected cost
//       for the next pattern (one-step lookahead; the next pattern is drawn from the case's own
//       patterns),
//   (c) an MDP policy by value iteration (expected total moves per request, exact for this model),
// and prints the moves per request of each against the solver's own (sum of the block moves).
// usage: blk_sim <err file of audit2-probe with REQ_PROBE=1>
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

int nb;                                   // flips; papers 0 = base, 1..nb = flips
std::vector<std::vector<int>> states;     // orders (top first)
std::map<std::vector<int>, int> idx;
std::vector<std::vector<int>> adj, radj;  // legal single moves

bool visible(const std::vector<int>& o, int pos) {
    int k = o[pos];
    if (k == 0) {  // base: visible iff some flip is below it
        for (int i = pos + 1; i < (int)o.size(); i++) if (o[i] != 0) return true;
        return false;
    }
    for (int i = 0; i < pos; i++) if (o[i] == 0) return false;  // flip below the base: hidden
    return true;
}
int orient(const std::vector<int>& o, int b) {  // 1 iff flip b above the base
    for (int k : o) {
        if (k == b) return 1;
        if (k == 0) return 0;
    }
    return 0;
}

int main(int argc, char** argv) {
    std::ifstream in(argv[1]);
    std::string line;
    nb = -1;
    struct Req { unsigned set, pat; int moves; };
    std::vector<Req> reqs;
    while (std::getline(in, line)) {
        if (line.rfind("blocks = ", 0) == 0) nb = std::atoi(line.c_str() + 9);
        if (line.rfind("REQ ", 0) != 0) continue;
        std::istringstream ss(line);
        std::vector<std::string> f;
        std::string t;
        while (ss >> t) f.push_back(t);
        if (f.size() < 26) continue;
        Req r;
        r.moves = std::atoi(f[15].c_str());
        r.set = std::strtoul(f[24].c_str(), nullptr, 16);
        r.pat = std::strtoul(f[25].c_str(), nullptr, 16);
        reqs.push_back(r);
    }
    if (nb < 1 || nb > 6) { std::cerr << "nb = " << nb << " unsupported\n"; return 1; }
    std::vector<int> o(nb + 1);
    for (int i = 0; i <= nb; i++) o[i] = i;
    do {
        idx[o] = states.size();
        states.push_back(o);
    } while (std::next_permutation(o.begin(), o.end()));
    int S = states.size();
    adj.assign(S, {});
    radj.assign(S, {});
    for (int s = 0; s < S; s++) {
        const auto& st = states[s];
        for (int i = 0; i <= nb; i++) {
            if (!visible(st, i)) continue;
            for (int d = 0; d <= nb; d++) {
                if (d == i) continue;
                auto o2 = st;
                int k = o2[i];
                o2.erase(o2.begin() + i);
                o2.insert(o2.begin() + d, k);
                int t = idx[o2];
                adj[s].push_back(t);
                radj[t].push_back(s);
            }
        }
    }
    // Distinct wants: key = set * 64 + pat
    std::map<unsigned, int> wid;
    std::vector<unsigned> wset, wpat;
    std::vector<int> wcount;
    for (auto& r : reqs) {
        unsigned key = r.set * 64 + r.pat;
        if (!wid.count(key)) {
            wid[key] = wset.size();
            wset.push_back(r.set);
            wpat.push_back(r.pat);
            wcount.push_back(0);
        }
        wcount[wid[key]]++;
    }
    int W = wset.size();
    auto sat = [&](int s, int w) {
        for (int b = 0; b < nb; b++)
            if (wset[w] >> b & 1)
                if (orient(states[s], b + 1) != (int)(wpat[w] >> b & 1)) return false;
        return true;
    };
    // dsat[w][s]: moves from s to some state satisfying w (backward multi-source BFS)
    std::vector<std::vector<int>> dsat(W, std::vector<int>(S, 1 << 20));
    for (int w = 0; w < W; w++) {
        std::vector<int> q;
        for (int s = 0; s < S; s++) if (sat(s, w)) dsat[w][s] = 0, q.push_back(s);
        for (size_t h = 0; h < q.size(); h++) {
            int s = q[h];
            for (int p : radj[s])
                if (dsat[w][p] > dsat[w][s] + 1) dsat[w][p] = dsat[w][s] + 1, q.push_back(p);
        }
    }
    double total_w = 0;
    for (int w = 0; w < W; w++) total_w += wcount[w];
    // V0[s] = expected moves of the next pattern from s (one-step value)
    std::vector<double> V(S, 0.0);
    for (int s = 0; s < S; s++)
        for (int w = 0; w < W; w++) V[s] += wcount[w] * dsat[w][s] / total_w;
    // (c) value iteration: J[s] = E_w min_{s' sat w} (dist(s, s') + J[s'])  (relative values)
    std::vector<std::vector<int>> dist(S, std::vector<int>(S, 1 << 20));
    for (int s = 0; s < S; s++) {
        std::vector<int> q{s};
        dist[s][s] = 0;
        for (size_t h = 0; h < q.size(); h++)
            for (int t : adj[q[h]])
                if (dist[s][t] > dist[s][q[h]] + 1) dist[s][t] = dist[s][q[h]] + 1, q.push_back(t);
    }
    std::vector<double> J(S, 0.0);
    double gain = 0;
    for (int it = 0; it < 200; it++) {
        std::vector<double> J2(S, 0.0);
        for (int s = 0; s < S; s++) {
            double e = 0;
            for (int w = 0; w < W; w++) {
                double best = 1e18;
                for (int t = 0; t < S; t++)
                    if (dist[s][t] < (1 << 20) && sat(t, w)) best = std::min(best, dist[s][t] + J[t]);
                e += wcount[w] * best / total_w;
            }
            J2[s] = e;
        }
        gain = J2[0];
        double mx = 0;
        for (int s = 0; s < S; s++) mx = std::max(mx, std::abs(J2[s] - J2[0] - J[s]));
        for (int s = 0; s < S; s++) J[s] = J2[s] - J2[0];
        if (mx < 1e-9) break;
    }
    // Simulations (a), (b), (c) along the request sequence from the initial order (base on top? the
    // solver starts with the base first, then the flips in block order: orientation 0 everywhere).
    std::vector<int> init(nb + 1);
    for (int i = 0; i <= nb; i++) init[i] = i;
    int s0 = idx[init];
    long long solver = 0;
    for (auto& r : reqs) solver += r.moves;
    auto run = [&](int mode) {
        int s = s0;
        long long tot = 0;
        for (auto& r : reqs) {
            int w = wid[r.set * 64 + r.pat];
            int best_t = -1;
            double best_v = 1e18;
            int dmin = dsat[w][s];
            for (int t = 0; t < S; t++) {
                if (!sat(t, w) || dist[s][t] != dmin) continue;
                double v = mode == 0 ? 0 : mode == 1 ? V[t] : J[t];
                if (v < best_v) best_v = v, best_t = t;
            }
            if (mode == 2) {  // MDP: not restricted to minimum cost now
                for (int t = 0; t < S; t++)
                    if (sat(t, w) && dist[s][t] + J[t] < dist[s][best_t] + J[best_t]) best_t = t;
            }
            tot += dist[s][best_t];
            s = best_t;
        }
        return tot;
    };
    long long a = run(0), b = run(1), c = run(2);
    printf("requests %zu patterns %d solver %.4f min_now %.4f lookahead1 %.4f mdp %.4f (mdp gain %.4f)\n",
           reqs.size(), W, (double)solver / reqs.size(), (double)a / reqs.size(), (double)b / reqs.size(),
           (double)c / reqs.size(), gain);
    return 0;
}
