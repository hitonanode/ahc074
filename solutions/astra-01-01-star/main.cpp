// AHC074: independent star displays, exact shortest paths, learned partition.
// C++17. Uses only the initial catalogue and the current request.
// Compile: g++ -O2 -std=c++17 ahc074_star.cpp -o main
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;
using U64 = uint64_t;

namespace {
constexpr int N = 64, K = 192, P = 256;
constexpr int L = 16, GROUPS = 4, M = L + 1;
constexpr int WORDS = 1 << L, STATES = WORDS * M;

struct Random {
    U64 state = 0x123456789abcdefULL;
    U64 operator()() {
        state ^= state << 7;
        state ^= state >> 9;
        return state;
    }
    double unit() { return ((*this)() >> 11) * (1.0 / 9007199254740992.0); }
} rng;

clock_t started;
double cpu_seconds() { return double(clock() - started) / CLOCKS_PER_SEC; }
array<U64, P> catalogue;
vector<uint8_t> distance_table;
array<uint32_t, M + 1> low_mask;
double average_distance[M][M]{};

// A state is (x,b). In the order of the 16 leaf cards, bit i of x says
// whether that leaf must finish ABOVE the base. The base currently has b
// leaves above it. Leaf identities are irrelevant for shortest distance.
void build_distances() {
    for (int i = 0; i <= M; ++i) low_mask[i] = (1u << i) - 1;
    distance_table.assign(STATES, 255);
    vector<uint8_t> expanded_word(WORDS);
    vector<uint32_t> queue;
    queue.reserve(STATES);
    for (int w = 0; w <= L; ++w) {
        int state = low_mask[w] * M + w;
        distance_table[state] = 0;
        queue.push_back(state);
    }
    auto visit = [&](uint32_t x, int b, int d) {
        uint32_t state = x * M + b;
        if (distance_table[state] == 255) {
            distance_table[state] = uint8_t(d);
            queue.push_back(state);
        }
    };
    for (size_t head = 0; head < queue.size(); ++head) {
        uint32_t state = queue[head], x = state / M;
        int b = state % M, next_d = distance_table[state] + 1;
        // Reverse of a base move. Its predecessor must have b < L,
        // because otherwise the base is invisible.
        if (!expanded_word[x]) {
            expanded_word[x] = true;
            for (int previous_b = 0; previous_b < L; ++previous_b)
                visit(x, previous_b, next_d);
        }
        // Reverse of a leaf move. The leaf must be before the base in
        // the predecessor, exactly the condition j <= remaining_b.
        for (int i = 0; i < L; ++i) {
            int remaining_b = b - (i < b);
            int previous_b = remaining_b + 1;
            uint32_t bit = (x >> i) & 1;
            uint32_t removed = (x & low_mask[i]) | ((x >> (i + 1)) << i);
            for (int j = 0; j <= remaining_b; ++j) {
                uint32_t previous_x = (removed & low_mask[j]) |
                    ((removed >> j) << (j + 1)) | (bit << j);
                visit(previous_x, previous_b, next_d);
            }
        }
    }
    array<int, M> count{};
    for (int x = 0; x < WORDS; ++x) {
        int w = __builtin_popcount(unsigned(x));
        ++count[w];
        for (int b = 0; b <= L; ++b)
            average_distance[b][w] += distance_table[x * M + b];
    }
    for (int b = 0; b <= L; ++b)
        for (int w = 0; w <= L; ++w)
            average_distance[b][w] /= count[w];
#ifdef LOCAL
    assert(queue.size() == STATES);
    assert(*max_element(distance_table.begin(), distance_table.end()) == 10);
#endif
}

struct Group {
    array<int, L> columns{};
    array<int, M> histogram{};
    U64 mask = 0;
    double score = 0;
};
array<Group, GROUPS> groups;
U64 base_pattern;

void evaluate(Group& group) {
    group.mask = 0;
    group.histogram.fill(0);
    for (int j : group.columns) group.mask |= U64(1) << j;
    for (U64 target : catalogue)
        ++group.histogram[__builtin_popcountll((target ^ base_pattern) & group.mask)];
    double score = 0;
    for (int b = 0; b <= L; ++b)
        for (int w = 0; w <= L; ++w)
            score += group.histogram[b] * group.histogram[w] * average_distance[b][w];
    group.score = score / (double(P) * P);
}

// This objective averages over random leaf orders conditional on target
// weight. It is a proxy, not an exact model of the finite-catalogue process.
void optimize_partition() {
    double best_score = 1e100;
    array<Group, GROUPS> best_groups;
    U64 best_base = 0;
    constexpr int ITERATIONS = 20000, RESTARTS = 3;
    for (int restart = 0; restart < RESTARTS; ++restart) {
        array<int, N> order;
        iota(order.begin(), order.end(), 0);
        for (int i = N - 1; i > 0; --i) swap(order[i], order[rng() % (i + 1)]);
        base_pattern = rng();
        double current_score = 0;
        for (int g = 0; g < GROUPS; ++g) {
            for (int j = 0; j < L; ++j) groups[g].columns[j] = order[g * L + j];
            evaluate(groups[g]);
            current_score += groups[g].score;
        }
        auto remember = [&]() {
            if (current_score < best_score) {
                best_score = current_score;
                best_groups = groups;
                best_base = base_pattern;
            }
        };
        remember();
        for (int it = 0; it < ITERATIONS; ++it) {
            if ((it & 255) == 0 && cpu_seconds() > 0.70) break;
            double temperature = 0.035 * pow(0.00015 / 0.035, double(it) / ITERATIONS);
            int g = rng() % GROUPS, h = rng() % GROUPS;
            int j = rng() % L, k = rng() % L;
            bool flip = rng() % 3 == 0;
            if (!flip && g == h) continue;
            Group old_g = groups[g], old_h = groups[h];
            U64 old_base = base_pattern;
            double old_score = groups[g].score + (flip ? 0 : groups[h].score);
            if (flip) {
                base_pattern ^= U64(1) << groups[g].columns[j];
                evaluate(groups[g]);
            } else {
                swap(groups[g].columns[j], groups[h].columns[k]);
                evaluate(groups[g]);
                evaluate(groups[h]);
            }
            double new_score = groups[g].score + (flip ? 0 : groups[h].score);
            double change = new_score - old_score;
            if (change <= 0 || rng.unit() < exp(-change / temperature)) {
                current_score += change;
                remember();
            } else {
                groups[g] = old_g;
                if (!flip) groups[h] = old_h;
                base_pattern = old_base;
            }
        }
        if (cpu_seconds() > 0.70) break;
    }
    groups = best_groups;
    base_pattern = best_base;
}

array<array<uint8_t, M>, GROUPS> local_order;
vector<int> global_order;
array<U64, K> opaque{}, black{};
vector<pair<int, int>> operations;

uint32_t target_word(int g, int product) {
    uint32_t x = 0;
    int position = 0;
    for (int leaf : local_order[g]) if (leaf != L) {
        int column = groups[g].columns[leaf];
        if (((catalogue[product] ^ base_pattern) >> column) & 1)
            x |= 1u << position;
        ++position;
    }
    return x;
}

void execute_move(int g, int from, int to) {
    auto& order = local_order[g];
    int leaf = order[from], paper = g * M + leaf;
    auto it = find(global_order.begin(), global_order.end(), paper);
#ifdef LOCAL
    U64 covered = 0;
    for (auto p = global_order.begin(); p != it; ++p) covered |= opaque[*p];
    assert(opaque[paper] & ~covered);
#endif
    global_order.erase(it);
    if (from < to) for (int i = from; i < to; ++i) order[i] = order[i + 1];
    else for (int i = from; i > to; --i) order[i] = order[i - 1];
    order[to] = uint8_t(leaf);
    int depth = K - 1;
    if (to < L) {
        int successor = g * M + order[to + 1];
        depth = int(find(global_order.begin(), global_order.end(), successor) - global_order.begin());
    }
    global_order.insert(global_order.begin() + depth, paper);
    operations.emplace_back(paper, depth);
}

void solve_group(int g, int product, int samples) {
    for (;;) {
        int b = 0;
        while (local_order[g][b] != L) ++b;
        uint32_t x = target_word(g, product);
        int distance = distance_table[x * M + b];
        if (!distance) return;

        array<uint32_t, 16> future{};
        for (int i = 0; i < samples; ++i) {
            int next;
            do next = rng() % P; while (next == product);
            future[i] = target_word(g, next);
        }
        int best_score = INT_MAX, best_from = -1, best_to = -1;
        U64 best_tie = 0;
        auto offer = [&](int from, int to, uint32_t next_x, int next_b) {
            if (distance_table[next_x * M + next_b] != distance - 1) return;
            int score = 0;
            for (int s = 0; s < samples; ++s) {
                uint32_t next = future[s];
                if (from != b) {
                    int destination = to - (to >= next_b);
                    uint32_t bit = (next >> from) & 1;
                    uint32_t removed = (next & low_mask[from]) | ((next >> (from + 1)) << from);
                    next = (removed & low_mask[destination]) |
                        ((removed >> destination) << (destination + 1)) | (bit << destination);
                }
                score += distance_table[next * M + next_b];
            }
            U64 tie = rng();
            if (score < best_score || (score == best_score && tie < best_tie)) {
                best_score = score;
                best_from = from;
                best_to = to;
                best_tie = tie;
            }
        };

        if (b < L) for (int next_b = 0; next_b <= L; ++next_b)
            if (next_b != b) offer(b, next_b, x, next_b);
        for (int from = 0; from < b; ++from) {
            uint32_t bit = (x >> from) & 1;
            uint32_t removed = (x & low_mask[from]) | ((x >> (from + 1)) << from);
            for (int to = 0; to <= L; ++to) if (from != to) {
                int next_b = b - (to >= b);
                int destination = to - (to >= next_b);
                uint32_t next_x = (removed & low_mask[destination]) |
                    ((removed >> destination) << (destination + 1)) | (bit << destination);
                offer(from, to, next_x, next_b);
            }
        }
        assert(best_from >= 0);
        execute_move(g, best_from, best_to);
    }
}
}  // namespace

int main() {
    started = clock();
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, k, p, rounds;
    if (!(cin >> n >> k >> p >> rounds)) return 0;
    if (n != N || k != K || p != P) return 0;  // Fixed contest constraints.
    for (int a = 0; a < P; ++a) {
        string text;
        cin >> text;
        for (int j = 0; j < N; ++j) if (text[j] == '1') catalogue[a] |= U64(1) << j;
        rng.state ^= catalogue[a];
        if (!rng.state) rng.state = 0x123456789abcdefULL;
        rng();
    }
    build_distances();
    optimize_partition();

    array<string, K> design;
    for (string& paper : design) paper.assign(N, '.');
    for (int g = 0; g < GROUPS; ++g) {
        iota(local_order[g].begin(), local_order[g].end(), 0);
        for (int leaf = 0; leaf < L; ++leaf) {
            int j = groups[g].columns[leaf], c = (base_pattern >> j) & 1;
            design[g * M + leaf][j] = char('0' + (1 - c));
            design[g * M + L][j] = char('0' + c);
        }
    }
    global_order.resize(K);
    iota(global_order.begin(), global_order.end(), 0);
    for (int paper = 0; paper < K; ++paper) {
        for (int j = 0; j < N; ++j) if (design[paper][j] != '.') {
            opaque[paper] |= U64(1) << j;
            if (design[paper][j] == '1') black[paper] |= U64(1) << j;
        }
        cout << design[paper] << '\n';
    }
    cout.flush();

    long long total = 0;
    int maximum = 0;
    for (int r = 0; r < rounds; ++r) {
        int product;
        if (!(cin >> product) || product == -1) return 0;
        if (product < 0 || product >= P) return 0;
        operations.clear();
        int samples = cpu_seconds() < 1.40 ? 16 : 0;
        for (int g = 0; g < GROUPS; ++g) solve_group(g, product, samples);
#ifdef LOCAL
        U64 covered = 0, actual = 0;
        for (int paper : global_order) {
            actual |= black[paper] & ~covered;
            covered |= opaque[paper];
        }
        assert(actual == catalogue[product]);
        assert(operations.size() <= 40);
#endif
        total += operations.size();
        maximum = max(maximum, int(operations.size()));
        cout << operations.size() << '\n';
        for (auto [paper, depth] : operations) cout << paper << ' ' << depth << '\n';
        cout.flush();
    }
#ifdef LOCAL
    cerr << "T=" << total << " E=0 max=" << maximum << " cpu=" << cpu_seconds() << '\n';
#endif
}
