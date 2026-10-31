// AHC074 -- verified experimental solver, C++17.
// This is NOT a 12-move solution. It uses 16 independent four-bit controllers.
// Each controller has eight papers, and its full legal state graph is solved.
// The other 64 papers are holes. No future requests are read.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <numeric>
#include <string>
#include <stdexcept>
#include <vector>
using namespace std;

namespace {
constexpr int N = 64, K = 192, P = 256, BLOCKS = 16;
constexpr int LOCAL_K = 8, STATES = 40320, GOALS = 16;
// Bit 0 is the first character of a block, not the most significant character.
constexpr array<int, LOCAL_K> MASK  = {1, 1, 3, 3, 7, 7, 15, 15};
constexpr array<int, LOCAL_K> COLOR = {0, 1, 1, 2, 3, 7, 7, 15};

struct Edge { int to; uint8_t action; }; // action = old_position * 8 + insertion_position

class Controller {
public:
    vector<array<uint8_t, LOCAL_K>> permutation;
    vector<vector<Edge>> edges;
    vector<int> display;
    array<vector<uint8_t>, GOALS> distance;
    array<vector<uint8_t>, GOALS> policy;
    int maximum_distance = 0;
    int iterations_done = 0; // Port: number of completed value-iteration rounds (stats only).

    explicit Controller(const array<double, GOALS>& goal_probability) {
        const auto build_started = chrono::steady_clock::now();
        vector<int> lookup(1u << 24, -1);
        array<int, LOCAL_K> order{};
        iota(order.begin(), order.end(), 0);
        permutation.reserve(STATES);
        do {
            uint32_t packed = 0;
            array<uint8_t, LOCAL_K> row{};
            for (int i = 0; i < LOCAL_K; ++i) {
                row[i] = uint8_t(order[i]);
                packed |= uint32_t(order[i]) << (3 * i);
            }
            lookup[packed] = int(permutation.size());
            permutation.push_back(row);
        } while (next_permutation(order.begin(), order.end()));

        edges.resize(STATES);
        vector<vector<int>> reverse_edges(STATES);
        display.assign(STATES, 0);
        for (int state = 0; state < STATES; ++state) {
            const auto& row = permutation[state];
            int covered = 0;
            for (int from = 0; from < LOCAL_K; ++from) {
                const int paper = row[from];
                const int visible = MASK[paper] & ~covered;
                display[state] |= COLOR[paper] & visible;
                covered |= MASK[paper];
                if (!visible) continue; // Legality is enforced before creating an edge.
                for (int to_position = 0; to_position < LOCAL_K; ++to_position) {
                    if (to_position == from) continue;
                    auto next = row;
                    if (from < to_position)
                        for (int j = from; j < to_position; ++j) next[j] = next[j + 1];
                    else
                        for (int j = from; j > to_position; --j) next[j] = next[j - 1];
                    next[to_position] = uint8_t(paper);
                    uint32_t packed = 0;
                    for (int j = 0; j < LOCAL_K; ++j)
                        packed |= uint32_t(next[j]) << (3 * j);
                    const int next_state = lookup[packed];
                    edges[state].push_back({next_state, uint8_t(from * 8 + to_position)});
                    reverse_edges[next_state].push_back(state);
                }
            }
        }
        // The 64 MiB ranking lookup is no longer needed.
        vector<int>().swap(lookup);

        array<vector<int>, GOALS> bfs_order;
        for (int goal = 0; goal < GOALS; ++goal) {
            distance[goal].assign(STATES, uint8_t(255));
            policy[goal].assign(STATES, uint8_t(255));
            auto& queue = bfs_order[goal];
            queue.reserve(STATES);
            for (int s = 0; s < STATES; ++s) {
                if (display[s] == goal) {
                    distance[goal][s] = 0;
                    queue.push_back(s);
                }
            }
            // Reverse BFS: distance to ANY order displaying the requested four bits.
            for (size_t head = 0; head < queue.size(); ++head) {
                const int s = queue[head];
                for (int previous : reverse_edges[s]) {
                    if (distance[goal][previous] != 255) continue;
                    distance[goal][previous] = uint8_t(distance[goal][s] + 1);
                    queue.push_back(previous);
                }
            }
            if (queue.size() != STATES) throw runtime_error("Unreachable local target");
            for (int s = 0; s < STATES; ++s)
                maximum_distance = max(maximum_distance, int(distance[goal][s]));
        }
        vector<vector<int>>().swap(reverse_edges);

        // Relative value iteration, restricted to shortest paths for the current goal.
        // This is a heuristic for future requests, NOT a proof of globally optimal
        // average cost. Every selected action still reduces an exact distance by one.
        vector<double> value(STATES, 0.0), next_value(STATES), continuation(STATES);
        constexpr int ITERATIONS = 18;
        for (int iteration = 0; iteration < ITERATIONS; ++iteration) {
            // Stop only BETWEEN complete iterations; the previous policy remains valid.
            if (iteration >= 2 &&
                chrono::duration<double>(chrono::steady_clock::now() - build_started).count() > 0.95)
                break;
            fill(next_value.begin(), next_value.end(), 0.0);
            for (int goal = 0; goal < GOALS; ++goal) {
                for (int s : bfs_order[goal]) {
                    if (distance[goal][s] == 0) {
                        continuation[s] = value[s];
                    } else {
                        double best = numeric_limits<double>::infinity();
                        int best_action = -1;
                        for (const Edge& e : edges[s]) {
                            if (int(distance[goal][e.to]) + 1 != distance[goal][s]) continue;
                            const double candidate = continuation[e.to];
                            if (candidate < best - 1e-12 ||
                                (abs(candidate - best) <= 1e-12 && e.action > best_action)) {
                                best = candidate;
                                best_action = e.action;
                            }
                        }
                        if (best_action < 0) throw runtime_error("Missing shortest-path edge");
                        continuation[s] = 1.0 + best;
                        policy[goal][s] = uint8_t(best_action);
                    }
                    next_value[s] += goal_probability[goal] * continuation[s];
                }
            }
            const double reference = next_value[0];
            for (int s = 0; s < STATES; ++s) value[s] = next_value[s] - reference;
            ++iterations_done;
        }
    }

    int successor(int state, int action) const {
        for (const Edge& edge : edges[state]) if (edge.action == action) return edge.to;
        throw runtime_error("Invalid policy action");
    }
};
} // namespace

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, k, p, rounds;
    if (!(cin >> n >> k >> p >> rounds)) return 0;
    if (n != N || k != K || p != P) return 0;
    vector<string> products(p);
    array<double, GOALS> probability{};
    vector<array<int, BLOCKS>> target(p);
    for (int product = 0; product < p; ++product) {
        cin >> products[product];
        if (products[product].size() != N) return 0;
        for (int block = 0; block < BLOCKS; ++block) {
            int bits = 0;
            for (int j = 0; j < 4; ++j)
                bits |= int(products[product][4 * block + j] == '1') << j;
            target[product][block] = bits;
            probability[bits] += 1.0 / (p * BLOCKS);
        }
    }
    // Port: the original printed these only with -DLOCAL_DIAGNOSTICS; now always
    // printed to stderr in the "name = value" form read by scripts/observe.py.
    const auto start = chrono::steady_clock::now();
    Controller controller(probability);
    cerr << "precompute_seconds = "
         << chrono::duration<double>(chrono::steady_clock::now() - start).count() << '\n'
         << "local_max_distance = " << controller.maximum_distance << '\n'
         << "value_iterations = " << controller.iterations_done << '\n';
    for (int paper = 0; paper < K; ++paper) {
        string row(N, '.');
        if (paper < BLOCKS * LOCAL_K) {
            const int block = paper / LOCAL_K, local = paper % LOCAL_K;
            for (int j = 0; j < 4; ++j)
                if ((MASK[local] >> j) & 1)
                    row[4 * block + j] = char('0' + ((COLOR[local] >> j) & 1));
        }
        cout << row << '\n';
    }
    cout.flush();

    array<int, BLOCKS> state{}; // Lexicographically first order is state 0.
    for (int round = 0; round < rounds; ++round) {
        int request;
        if (!(cin >> request) || request == -1) return 0;
        if (request < 0 || request >= p) return 0;
        vector<pair<int, int>> operations;
        operations.reserve(128);
        for (int block = 0; block < BLOCKS; ++block) {
            const int goal = target[request][block];
            while (controller.display[state[block]] != goal) {
                const int action = controller.policy[goal][state[block]];
                const int from = action / 8, to_position = action % 8;
                const int local_paper = controller.permutation[state[block]][from];
                // Blocks remain contiguous; moving within a block does not affect
                // any other block's local order or visibility.
                operations.emplace_back(8 * block + local_paper, 8 * block + to_position);
                state[block] = controller.successor(state[block], action);
            }
        }
        if (operations.size() > 2u * K) return 0; // Unreachable with this construction.
        cout << operations.size() << '\n';
        for (auto [paper, insertion] : operations) cout << paper << ' ' << insertion << '\n';
        cout.flush();
    }
    return 0;
}
