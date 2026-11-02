// Structural diagnostic, not an AtCoder submission. Build with C++23 -O2.
// The optional comparison witnesses form an undirected graph on six sheets.
// A sheet is safely visible iff a witness neighbour is below it. The program
// computes the exact directed insertion graph over all 720 permutations.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using Perm = std::array<int, 6>;
int code(const Perm& p) {
    int x = 0;
    for (int v : p) x = x * 6 + v;
    return x;
}

int main() {
    std::vector<Perm> perm;
    Perm p{0, 1, 2, 3, 4, 5};
    do perm.push_back(p); while (std::next_permutation(p.begin(), p.end()));
    std::array<int, 46656> index;
    index.fill(-1);
    for (int s = 0; s < 720; ++s) index[code(perm[s])] = s;

    struct Graph { std::string name; std::array<unsigned, 6> adj; bool top_only = false; };
    auto complete = [] {
        std::array<unsigned, 6> a{};
        for (int i = 0; i < 6; ++i) a[i] = 63U ^ (1U << i);
        return a;
    };
    std::vector<Graph> graph{{"complete15", complete()}};
    for (int k = 1; k <= 3; ++k) {
        auto a = complete();
        for (int i = 0; i < k; ++i) {
            a[2 * i] &= ~(1U << (2 * i + 1));
            a[2 * i + 1] &= ~(1U << (2 * i));
        }
        graph.push_back({"matching_minus" + std::to_string(k), a});
    }
    std::array<unsigned, 6> bipartite{}, cycle{}, star{};
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) if ((i < 3) != (j < 3)) bipartite[i] |= 1U << j;
        cycle[i] = (1U << ((i + 1) % 6)) | (1U << ((i + 5) % 6));
        star[i] = i == 0 ? 62 : 1;
    }
    graph.push_back({"bipartite9", bipartite});
    graph.push_back({"cycle6", cycle});
    graph.push_back({"star5", star});
    graph.push_back({"top_only", {}, true});

    // Synthetic goal sets test the distance metric in isolation. They are not
    // barcode requirements and must not be interpreted as contest scores.
    std::mt19937_64 rng(0x591edba4ULL);
    std::vector<std::array<int, 16>> goals(1024);
    for (auto& g : goals) {
        std::array<int, 720> order{};
        std::iota(order.begin(), order.end(), 0);
        for (int i = 0; i < 16; ++i) {
            const int j = i + int(rng() % (720 - i));
            std::swap(order[i], order[j]);
            g[i] = order[i];
        }
    }
    std::cout << "graph,witness_edges,visible_mean,diameter,unreachable,mean_distance,goal4,goal8,goal16\n";
    for (const auto& gr : graph) {
        std::array<std::vector<int>, 720> next;
        int visible = 0, witness_edges = 0;
        for (unsigned a : gr.adj) witness_edges += __builtin_popcount(a);
        witness_edges /= 2;
        for (int s = 0; s < 720; ++s) {
            unsigned below = 0;
            for (int i = 5; i >= 0; --i) {
                const bool vis = gr.top_only ? i == 0 : (gr.adj[perm[s][i]] & below) != 0;
                below |= 1U << perm[s][i];
                if (!vis) continue;
                visible++;
                for (int d = 0; d < 6; ++d) if (d != i) {
                    auto v = perm[s];
                    const int x = v[i];
                    if (i < d) for (int j = i; j < d; ++j) v[j] = v[j + 1];
                    else for (int j = i; j > d; --j) v[j] = v[j - 1];
                    v[d] = x;
                    next[s].push_back(index[code(v)]);
                }
            }
        }
        std::vector<std::uint8_t> distance(720 * 720, 255);
        long long total = 0, unreachable = 0;
        int diameter = 0;
        for (int s = 0; s < 720; ++s) {
            auto* dist = distance.data() + s * 720;
            std::array<int, 720> queue;
            int begin = 0, end = 0;
            queue[end++] = s;
            dist[s] = 0;
            while (begin < end) {
                const int v = queue[begin++];
                for (int w : next[v]) if (dist[w] == 255) {
                    dist[w] = dist[v] + 1;
                    queue[end++] = w;
                }
            }
            for (int t = 0; t < 720; ++t) {
                if (dist[t] == 255) unreachable++;
                else total += dist[t], diameter = std::max(diameter, int(dist[t]));
            }
        }
        std::array<double, 3> means{};
        for (const auto& g : goals) for (int s = 0; s < 720; ++s) {
            int best = 255;
            for (int i = 0; i < 16; ++i) {
                best = std::min(best, int(distance[s * 720 + g[i]]));
                if (i == 3) means[0] += best;
                if (i == 7) means[1] += best;
                if (i == 15) means[2] += best;
            }
        }
        std::cout << gr.name << ',' << witness_edges << ',' << std::fixed << std::setprecision(9)
                  << visible / 720.0 << ',' << diameter << ',' << unreachable << ','
                  << total / (720.0 * 720) << ','
                  << means[0] / (720.0 * goals.size()) << ','
                  << means[1] / (720.0 * goals.size()) << ','
                  << means[2] / (720.0 * goals.size()) << '\n';
    }
}
