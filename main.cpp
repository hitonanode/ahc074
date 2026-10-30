#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <chrono>
#include <cmath>
#include <complex>
#include <deque>
#include <forward_list>
#include <fstream>
#include <functional>
#include <iomanip>
#include <ios>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <stack>
#include <string>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
using namespace std;
using lint = long long;
using pint = pair<int, int>;
using plint = pair<lint, lint>;
struct fast_ios { fast_ios(){ cin.tie(nullptr), ios::sync_with_stdio(false), cout << fixed << setprecision(20); }; } fast_ios_;
#define ALL(x) (x).begin(), (x).end()
#define FOR(i, begin, end) for(int i=(begin),i##_end_=(end);i<i##_end_;i++)
#define IFOR(i, begin, end) for(int i=(end)-1,i##_begin_=(begin);i>=i##_begin_;i--)
#define REP(i, n) FOR(i,0,n)
#define IREP(i, n) IFOR(i,0,n)
template <typename T> bool chmax(T &m, const T q) { return m < q ? (m = q, true) : false; }
template <typename T> bool chmin(T &m, const T q) { return m > q ? (m = q, true) : false; }
const std::vector<std::pair<int, int>> grid_dxs{{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
int floor_lg(long long x) { return x <= 0 ? -1 : 63 - __builtin_clzll(x); }
template <class T1, class T2> T1 floor_div(T1 num, T2 den) { return (num > 0 ? num / den : -((-num + den - 1) / den)); }
template <class T1, class T2> std::pair<T1, T2> operator+(const std::pair<T1, T2> &l, const std::pair<T1, T2> &r) { return std::make_pair(l.first + r.first, l.second + r.second); }
template <class T1, class T2> std::pair<T1, T2> operator-(const std::pair<T1, T2> &l, const std::pair<T1, T2> &r) { return std::make_pair(l.first - r.first, l.second - r.second); }
template <class T> std::vector<T> sort_unique(std::vector<T> vec) { sort(vec.begin(), vec.end()), vec.erase(unique(vec.begin(), vec.end()), vec.end()); return vec; }
template <class T> int arglb(const std::vector<T> &v, const T &x) { return std::distance(v.begin(), std::lower_bound(v.begin(), v.end(), x)); }
template <class T> int argub(const std::vector<T> &v, const T &x) { return std::distance(v.begin(), std::upper_bound(v.begin(), v.end(), x)); }
template <class IStream, class T> IStream &operator>>(IStream &is, std::vector<T> &vec) { for (auto &v : vec) is >> v; return is; }

template <class OStream, class T> OStream &operator<<(OStream &os, const std::vector<T> &vec);
template <class OStream, class T, size_t sz> OStream &operator<<(OStream &os, const std::array<T, sz> &arr);
template <class OStream, class T, class TH> OStream &operator<<(OStream &os, const std::unordered_set<T, TH> &vec);
template <class OStream, class T, class U> OStream &operator<<(OStream &os, const pair<T, U> &pa);
template <class OStream, class T> OStream &operator<<(OStream &os, const std::deque<T> &vec);
template <class OStream, class T> OStream &operator<<(OStream &os, const std::set<T> &vec);
template <class OStream, class T> OStream &operator<<(OStream &os, const std::multiset<T> &vec);
template <class OStream, class T> OStream &operator<<(OStream &os, const std::unordered_multiset<T> &vec);
template <class OStream, class T, class U> OStream &operator<<(OStream &os, const std::pair<T, U> &pa);
template <class OStream, class TK, class TV> OStream &operator<<(OStream &os, const std::map<TK, TV> &mp);
template <class OStream, class TK, class TV, class TH> OStream &operator<<(OStream &os, const std::unordered_map<TK, TV, TH> &mp);
template <class OStream, class... T> OStream &operator<<(OStream &os, const std::tuple<T...> &tpl);

template <class OStream, class T> OStream &operator<<(OStream &os, const std::vector<T> &vec) { os << '['; for (auto v : vec) os << v << ','; os << ']'; return os; }
template <class OStream, class T, size_t sz> OStream &operator<<(OStream &os, const std::array<T, sz> &arr) { os << '['; for (auto v : arr) os << v << ','; os << ']'; return os; }
template <class... T> std::istream &operator>>(std::istream &is, std::tuple<T...> &tpl) { std::apply([&is](auto &&... args) { ((is >> args), ...);}, tpl); return is; }
template <class OStream, class... T> OStream &operator<<(OStream &os, const std::tuple<T...> &tpl) { os << '('; std::apply([&os](auto &&... args) { ((os << args << ','), ...);}, tpl); return os << ')'; }
template <class OStream, class T, class TH> OStream &operator<<(OStream &os, const std::unordered_set<T, TH> &vec) { os << '{'; for (auto v : vec) os << v << ','; os << '}'; return os; }
template <class OStream, class T> OStream &operator<<(OStream &os, const std::deque<T> &vec) { os << "deq["; for (auto v : vec) os << v << ','; os << ']'; return os; }
template <class OStream, class T> OStream &operator<<(OStream &os, const std::set<T> &vec) { os << '{'; for (auto v : vec) os << v << ','; os << '}'; return os; }
template <class OStream, class T> OStream &operator<<(OStream &os, const std::multiset<T> &vec) { os << '{'; for (auto v : vec) os << v << ','; os << '}'; return os; }
template <class OStream, class T> OStream &operator<<(OStream &os, const std::unordered_multiset<T> &vec) { os << '{'; for (auto v : vec) os << v << ','; os << '}'; return os; }
template <class OStream, class T, class U> OStream &operator<<(OStream &os, const std::pair<T, U> &pa) { return os << '(' << pa.first << ',' << pa.second << ')'; }
template <class OStream, class TK, class TV> OStream &operator<<(OStream &os, const std::map<TK, TV> &mp) { os << '{'; for (auto v : mp) os << v.first << "=>" << v.second << ','; os << '}'; return os; }
template <class OStream, class TK, class TV, class TH> OStream &operator<<(OStream &os, const std::unordered_map<TK, TV, TH> &mp) { os << '{'; for (auto v : mp) os << v.first << "=>" << v.second << ','; os << '}'; return os; }
#ifdef HITONANODE_LOCAL
const string COLOR_RESET = "\033[0m", BRIGHT_CYAN = "\033[1;36m", NORMAL_FAINT = "\033[0;2m";
#define dbg(x) std::cerr << BRIGHT_CYAN << #x << COLOR_RESET << " = " << (x) << NORMAL_FAINT << " (L" << __LINE__ << ") " << __FILE__ << COLOR_RESET << std::endl
#define dbgif(cond, x) ((cond) ? std::cerr << BRIGHT_CYAN << #x << COLOR_RESET << " = " << (x) << NORMAL_FAINT << " (L" << __LINE__ << ") " << __FILE__ << COLOR_RESET << std::endl : std::cerr)
#else
#define dbg(x) ((void)0)
#define dbgif(cond, x) ((void)0)
#endif

// https://hitonanode.github.io/cplib-cpp/graph/shortest_path.hpp
#include <algorithm>
#include <cassert>
#include <deque>
#include <fstream>
#include <functional>
#include <limits>
#include <queue>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

template <typename T, T INF = std::numeric_limits<T>::max() / 2, int INVALID = -1>
struct shortest_path {
    int V, E;
    bool single_positive_weight;
    T wmin, wmax;

    std::vector<std::pair<int, T>> tos;
    std::vector<int> head;
    std::vector<std::tuple<int, int, T>> edges;

    void build_() {
        if (int(tos.size()) == E and int(head.size()) == V + 1) return;
        tos.resize(E);
        head.assign(V + 1, 0);
        for (const auto &e : edges) ++head[std::get<0>(e) + 1];
        for (int i = 0; i < V; ++i) head[i + 1] += head[i];
        auto cur = head;
        for (const auto &e : edges) {
            tos[cur[std::get<0>(e)]++] = std::make_pair(std::get<1>(e), std::get<2>(e));
        }
    }

    shortest_path(int V = 0) : V(V), E(0), single_positive_weight(true), wmin(0), wmax(0) {}
    void add_edge(int s, int t, T w) {
        assert(0 <= s and s < V);
        assert(0 <= t and t < V);
        edges.emplace_back(s, t, w);
        ++E;
        if (w > 0 and wmax > 0 and wmax != w) single_positive_weight = false;
        wmin = std::min(wmin, w);
        wmax = std::max(wmax, w);
    }

    void add_bi_edge(int u, int v, T w) {
        add_edge(u, v, w);
        add_edge(v, u, w);
    }

    std::vector<T> dist;
    std::vector<int> prev;

    // Dijkstra algorithm
    // - Requirement: wmin >= 0
    // - Complexity: O(E log E)
    using Pque = std::priority_queue<std::pair<T, int>, std::vector<std::pair<T, int>>,
                                     std::greater<std::pair<T, int>>>;
    template <class Heap = Pque> void dijkstra(int s, int t = INVALID) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF);
        prev.assign(V, INVALID);
        dist[s] = 0;
        Heap pq;
        pq.emplace(0, s);
        while (!pq.empty()) {
            T d;
            int v;
            std::tie(d, v) = pq.top();
            pq.pop();
            if (t == v) return;
            if (dist[v] < d) continue;
            for (int e = head[v]; e < head[v + 1]; ++e) {
                const auto &nx = tos[e];
                T dnx = d + nx.second;
                if (dist[nx.first] > dnx) {
                    dist[nx.first] = dnx, prev[nx.first] = v;
                    pq.emplace(dnx, nx.first);
                }
            }
        }
    }

    // Dijkstra algorithm
    // - Requirement: wmin >= 0
    // - Complexity: O(V^2 + E)
    void dijkstra_vquad(int s, int t = INVALID) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF);
        prev.assign(V, INVALID);
        dist[s] = 0;
        std::vector<char> fixed(V, false);
        while (true) {
            int r = INVALID;
            T dr = INF;
            for (int i = 0; i < V; i++) {
                if (!fixed[i] and dist[i] < dr) r = i, dr = dist[i];
            }
            if (r == INVALID or r == t) break;
            fixed[r] = true;
            int nxt;
            T dx;
            for (int e = head[r]; e < head[r + 1]; ++e) {
                std::tie(nxt, dx) = tos[e];
                if (dist[nxt] > dist[r] + dx) dist[nxt] = dist[r] + dx, prev[nxt] = r;
            }
        }
    }

    // Bellman-Ford algorithm
    // - Requirement: no negative loop
    // - Complexity: O(VE)
    bool bellman_ford(int s, int nb_loop) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF), prev.assign(V, INVALID);
        dist[s] = 0;
        for (int l = 0; l < nb_loop; l++) {
            bool upd = false;
            for (int v = 0; v < V; v++) {
                if (dist[v] == INF) continue;
                for (int e = head[v]; e < head[v + 1]; ++e) {
                    const auto &nx = tos[e];
                    T dnx = dist[v] + nx.second;
                    if (dist[nx.first] > dnx) dist[nx.first] = dnx, prev[nx.first] = v, upd = true;
                }
            }
            if (!upd) return true;
        }
        return false;
    }

    // Bellman-ford algorithm using deque
    // - Requirement: no negative loop
    // - Complexity: O(VE)
    void spfa(int s) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF);
        prev.assign(V, INVALID);
        dist[s] = 0;
        std::deque<int> q;
        std::vector<char> in_queue(V);
        q.push_back(s), in_queue[s] = 1;
        while (!q.empty()) {
            int now = q.front();
            q.pop_front(), in_queue[now] = 0;
            for (int e = head[now]; e < head[now + 1]; ++e) {
                const auto &nx = tos[e];
                T dnx = dist[now] + nx.second;
                int nxt = nx.first;
                if (dist[nxt] > dnx) {
                    dist[nxt] = dnx;
                    prev[nxt] = now;
                    if (!in_queue[nxt]) {
                        if (q.size() and dnx < dist[q.front()]) { // Small label first optimization
                            q.push_front(nxt);
                        } else {
                            q.push_back(nxt);
                        }
                        in_queue[nxt] = 1;
                    }
                }
            }
        }
    }

    // 01-BFS
    // - Requirement: all weights must be 0 or w (positive constant).
    // - Complexity: O(V + E)
    void zero_one_bfs(int s, int t = INVALID) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF), prev.assign(V, INVALID);
        dist[s] = 0;
        std::vector<int> q(V * 4);
        int ql = V * 2, qr = V * 2;
        q[qr++] = s;
        while (ql < qr) {
            int v = q[ql++];
            if (v == t) return;
            for (int e = head[v]; e < head[v + 1]; ++e) {
                const auto &nx = tos[e];
                T dnx = dist[v] + nx.second;
                if (dist[nx.first] > dnx) {
                    dist[nx.first] = dnx, prev[nx.first] = v;
                    if (nx.second) {
                        q[qr++] = nx.first;
                    } else {
                        q[--ql] = nx.first;
                    }
                }
            }
        }
    }

    // Dial's algorithm
    // - Requirement: wmin >= 0
    // - Complexity: O(wmax * V + E)
    void dial(int s, int t = INVALID) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF), prev.assign(V, INVALID);
        dist[s] = 0;
        std::vector<std::vector<std::pair<int, T>>> q(wmax + 1);
        q[0].emplace_back(s, dist[s]);
        int ninq = 1;

        int cur = 0;
        T dcur = 0;
        for (; ninq; ++cur, ++dcur) {
            if (cur == wmax + 1) cur = 0;
            while (!q[cur].empty()) {
                int v = q[cur].back().first;
                T dnow = q[cur].back().second;
                q[cur].pop_back(), --ninq;
                if (v == t) return;
                if (dist[v] < dnow) continue;

                for (int e = head[v]; e < head[v + 1]; ++e) {
                    const auto &nx = tos[e];
                    T dnx = dist[v] + nx.second;
                    if (dist[nx.first] > dnx) {
                        dist[nx.first] = dnx, prev[nx.first] = v;
                        int nxtcur = cur + int(nx.second);
                        if (nxtcur >= int(q.size())) nxtcur -= q.size();
                        q[nxtcur].emplace_back(nx.first, dnx), ++ninq;
                    }
                }
            }
        }
    }

    // Solver for DAG
    // - Requirement: graph is DAG
    // - Complexity: O(V + E)
    bool dag_solver(int s) {
        assert(0 <= s and s < V);
        build_();
        dist.assign(V, INF), prev.assign(V, INVALID);
        dist[s] = 0;
        std::vector<int> indeg(V, 0);
        std::vector<int> q(V * 2);
        int ql = 0, qr = 0;
        q[qr++] = s;
        while (ql < qr) {
            int now = q[ql++];
            for (int e = head[now]; e < head[now + 1]; ++e) {
                const auto &nx = tos[e];
                ++indeg[nx.first];
                if (indeg[nx.first] == 1) q[qr++] = nx.first;
            }
        }
        ql = qr = 0;
        q[qr++] = s;
        while (ql < qr) {
            int now = q[ql++];
            for (int e = head[now]; e < head[now + 1]; ++e) {
                const auto &nx = tos[e];
                --indeg[nx.first];
                if (dist[nx.first] > dist[now] + nx.second)
                    dist[nx.first] = dist[now] + nx.second, prev[nx.first] = now;
                if (indeg[nx.first] == 0) q[qr++] = nx.first;
            }
        }
        return *max_element(indeg.begin(), indeg.end()) == 0;
    }

    // Retrieve a sequence of vertex ids that represents shortest path [s, ..., goal]
    // If not reachable to goal, return {}
    std::vector<int> retrieve_path(int goal) const {
        assert(int(prev.size()) == V);
        assert(0 <= goal and goal < V);
        if (dist[goal] == INF) return {};
        std::vector<int> ret{goal};
        while (prev[goal] != INVALID) {
            goal = prev[goal];
            ret.push_back(goal);
        }
        std::reverse(ret.begin(), ret.end());
        return ret;
    }

    void solve(int s, int t = INVALID) {
        if (wmin >= 0) {
            if (single_positive_weight) {
                zero_one_bfs(s, t);
            } else if (wmax <= 10) {
                dial(s, t);
            } else {
                if ((long long)V * V < (E << 4)) {
                    dijkstra_vquad(s, t);
                } else {
                    dijkstra(s, t);
                }
            }
        } else {
            bellman_ford(s, V);
        }
    }

    // Warshall-Floyd algorithm
    // - Requirement: no negative loop
    // - Complexity: O(E + V^3)
    std::vector<std::vector<T>> floyd_warshall() {
        build_();
        std::vector<std::vector<T>> dist2d(V, std::vector<T>(V, INF));
        for (int i = 0; i < V; i++) {
            dist2d[i][i] = 0;
            for (const auto &e : edges) {
                int s = std::get<0>(e), t = std::get<1>(e);
                dist2d[s][t] = std::min(dist2d[s][t], std::get<2>(e));
            }
        }
        for (int k = 0; k < V; k++) {
            for (int i = 0; i < V; i++) {
                if (dist2d[i][k] == INF) continue;
                for (int j = 0; j < V; j++) {
                    if (dist2d[k][j] == INF) continue;
                    dist2d[i][j] = std::min(dist2d[i][j], dist2d[i][k] + dist2d[k][j]);
                }
            }
        }
        return dist2d;
    }

    void to_dot(std::string filename = "shortest_path") const {
        std::ofstream ss(filename + ".DOT");
        ss << "digraph{\n";
        build_();
        for (int i = 0; i < V; i++) {
            for (int e = head[i]; e < head[i + 1]; ++e) {
                ss << i << "->" << tos[e].first << "[label=" << tos[e].second << "];\n";
            }
        }
        ss << "}\n";
        ss.close();
        return;
    }
};


static constexpr int N = 64, K = 192, P = 256, R = 1024;

double Estimate_0_1(const array<string, P> &A, int j0) {
    int n0 = 0, n1 = 0;
    for (const auto &a : A) {
        if (a[j0] == '0') ++n0;
        if (a[j0] == '1') ++n1;
    }
    assert(n0 + n1 == P);
    const double p0 = static_cast<double>(n0) / (n0 + n1);
    const double p1 = static_cast<double>(n1) / (n0 + n1);
    return 2 * p0 * p1;
}

double Estimate_0x_x0_11(const array<string, P> &A, int j0, int j1) {
    int n00 = 0, n01 = 0, n10 = 0, n11 = 0;
    for (const auto &a : A) {
        if (a[j0] == '0' and a[j1] == '0') ++n00;
        if (a[j0] == '0' and a[j1] == '1') ++n01;
        if (a[j0] == '1' and a[j1] == '0') ++n10;
        if (a[j0] == '1' and a[j1] == '1') ++n11;
    }
    assert(n00 + n01 + n10 + n11 == P);
    const double p00 = static_cast<double>(n00) / (n00 + n01 + n10 + n11);
    const double p01 = static_cast<double>(n01) / (n00 + n01 + n10 + n11);
    const double p10 = static_cast<double>(n10) / (n00 + n01 + n10 + n11);
    const double p11 = static_cast<double>(n11) / (n00 + n01 + n10 + n11);

    double ret = 0.0;
    // 00 ->
    ret += p00 * (p01 + p10 + p11 * 2);
    // 01 ->
    // 0x, 11, x0
    ret += p01 * (p11 + p10 * 2 + p00);

    // 10 ->
    ret += p10 * (p11 + p01 * 2 + p00);

    // 11 ->
    ret += p11 * (p00 + p01 + p10 + min(p01, p10));

    return ret;
}
struct Strategy {
    vector<string> layers;
    vector<vector<int>> pattern2order;
    // vector<vector<vector<pint>>> ops;
    double expected_cost;
};

Strategy GenerateStrategy(vector<string> layers, const vector<double> &probs) {
    const int width = layers.front().size();
    const int num_layers = layers.size();
    assert((int)probs.size() == (1 << width));

    vector<vector<int>> all_orders;
    {
        vector<int> order(num_layers);
        iota(order.begin(), order.end(), 0);

        do {
            all_orders.push_back(order);
        } while (next_permutation(order.begin(), order.end()));
    }

    shortest_path<int> sp(all_orders.size());

    vector<vector<int>> pattern2orderids(1 << width);
    vector<int> order_to_pattern;

    {
        vector<int> order(num_layers);
        iota(order.begin(), order.end(), 0);

        do {
            int pattern = 0;
            int fixed = 0;
            for (int layer : order) {
                REP(idx, width) {
                    if (fixed & (1 << idx)) continue;
                    if (layers[layer][idx] == '0') pattern |= (0 << idx), fixed |= (1 << idx);
                    if (layers[layer][idx] == '1') pattern |= (1 << idx), fixed |= (1 << idx);

                    if (fixed & (1 << idx)) {
                        // dbg(make_tuple(order, layer, idx));
                        const int from = arglb(all_orders, order);
                        REP(dest, num_layers) {
                            auto to_order = order;
                            to_order.erase(find(to_order.begin(), to_order.end(), layer));
                            to_order.insert(to_order.begin() + dest, layer);
                            // dbg(make_tuple(order, to_order));
                            const int to = arglb(all_orders, to_order);
                            assert(all_orders.at(to) == to_order);
                            if (from != to) {
                                sp.add_edge(from, to, 1);
                                // dbg(make_tuple(from, to));
                            }
                        }
                    }
                }
            }
            assert(fixed == (1 << width) - 1);
            order_to_pattern.push_back(pattern);
            pattern2orderids.at(pattern).push_back(arglb(all_orders, order));
        } while (next_permutation(order.begin(), order.end()));
    }

    // dbg(sp.floyd_warshall());

    // dbgif(width == 4, pattern2orderids);
    dbg(all_orders.size());

    vector<vector<int>> distance_matrix(all_orders.size(), vector<int>(all_orders.size()));
    REP(i, all_orders.size()) {
        sp.solve(i);
        distance_matrix.at(i) = sp.dist;
    }
    // const auto distance_matrix = sp.floyd_warshall();
    // dbgif(width == 4, distance_matrix);

    // Strategy best{.expected_cost = 1e9};
    dbg(all_orders.size());

    vector<double> dp(all_orders.size(), 1.0 / all_orders.size());
    double last_cost = 0.0;
    vector<vector<int>> goal_2_ids(1 << width);
    REP(id, all_orders.size()) {
        goal_2_ids.at(order_to_pattern.at(id)).push_back(id);
    }

    REP(_, 100) {
        last_cost = 0.0;
        vector<double> dpnxt(dp.size());
        REP(id, dp.size()) {
            const double pnow = dp[id];
            REP(goal, 1 << width) {
                int best = 1e9;
                int argbest = -1;
                for (const auto &nxt_id : goal_2_ids.at(goal)) {
                    if (chmin(best, distance_matrix.at(id).at(nxt_id))) {
                        argbest = nxt_id;
                    }
                }
                dpnxt.at(argbest) += pnow * probs.at(goal);
                last_cost += pnow * probs.at(goal) * best;
            }

        }
        dp = dpnxt;
    }

    // vector<int> used_pattern2order_ids(1 << width);
    // auto rec = [&](auto &&self, int idx) -> void {
    //     if (idx == 1 << width) {
    //         double cost = 0.0;
    //         REP(from_pattern, 1 << width) {
    //             REP(to_pattern, 1 << width) {
    //                 cost += probs.at(from_pattern) * probs.at(to_pattern) * distance_matrix.at(used_pattern2order_ids.at(from_pattern)).at(used_pattern2order_ids.at(to_pattern));
    //             }
    //         }
    //         // dbg(make_tuple(used_pattern2order_ids, cost));
    //         if (cost < best.expected_cost) {
    //             best.expected_cost = cost;
    //             best.pattern2order.resize(1 << width);
    //             REP(i, 1 << width) {
    //                 best.pattern2order[i] = all_orders.at(used_pattern2order_ids.at(i));
    //             }
    //             best.layers = layers;
    //         }
    //     } else {
    //         for (const auto &order_id : pattern2orderids[idx]) {
    //             used_pattern2order_ids[idx] = order_id;
    //             self(self, idx + 1);
    //         }
    //     }
    // };
    // rec(rec, 0);

    return Strategy{.expected_cost = last_cost};
}

int main() {
    array<string, P> A;
    {
        int N_, K_, P_, R_;
        cin >> N_ >> K_ >> P_ >> R_;
        assert(N == N_);
        assert(K == K_);
        assert(P == P_);
        assert(R == R_);
        for (auto &a : A) cin >> a;
    }
    dbg(A);


    REP(i, N) {
        break;
        const auto f = Estimate_0_1(A, i);
        int n0 = 0, n1 = 0;
        for (const auto &a : A) {
            if (a[i] == '0') ++n0;
            if (a[i] == '1') ++n1;
        }
        const double p0 = static_cast<double>(n0) / A.size();
        const double p1 = static_cast<double>(n1) / A.size();
        const auto strategy = GenerateStrategy({"0", "1"}, {p0, p1});
        dbg(make_tuple(f, strategy.expected_cost));
    }

    vector<vector<string>> layer_cands;
    layer_cands.push_back({"0.", ".0", "11"});
    layer_cands.push_back({"0.", ".1", "10"});
    layer_cands.push_back({"1.", ".0", "01"});
    layer_cands.push_back({"1.", ".1", "00"});
    for (const auto &layers : layer_cands) {
        break;
        double best = 0;
        REP(i, N) REP(j, i) {
            const auto f = Estimate_0_1(A, i) + Estimate_0_1(A, j);
            int n00 = 0, n01 = 0, n10 = 0, n11 = 0;
            for (const auto &a : A) {
                if (a[i] == '0' and a[j] == '0') ++n00;
                if (a[i] == '0' and a[j] == '1') ++n01;
                if (a[i] == '1' and a[j] == '0') ++n10;
                if (a[i] == '1' and a[j] == '1') ++n11;
            }
            const double p00 = static_cast<double>(n00) / A.size();
            const double p01 = static_cast<double>(n01) / A.size();
            const double p10 = static_cast<double>(n10) / A.size();
            const double p11 = static_cast<double>(n11) / A.size();

            auto strategy = GenerateStrategy(layers, {p00, p01, p10, p11});

            const auto g = strategy.expected_cost;
            if (chmax(best, f - g)) {
                dbg(make_tuple(best, i, j, layers, f, g));
                dbg(strategy.expected_cost);
                dbg(strategy.pattern2order);
            }
        }
    }

    REP(i, N) REP(j, i) {
        break;
        const auto f = Estimate_0_1(A, i) + Estimate_0_1(A, j);
        vector<double> prob(4);
        for (const auto &a : A) {
            int idx = (a[i] - '0') * 2 + (a[j] - '0');
            prob[idx] += 1.0 / A.size();
        }

        const auto strategy = GenerateStrategy({"0.", "11", ".0"}, prob);
        if (strategy.expected_cost < f) {
            dbg(make_tuple((f - strategy.expected_cost) / f, f, strategy.expected_cost, i, j));
        }
    }

    REP(i, N) REP(j, i) REP(k, j) {
        break;
        const auto f = Estimate_0_1(A, i) + Estimate_0_1(A, j) + Estimate_0_1(A, k);
        vector<double> prob(8);
        for (const auto &a : A) {
            int idx = (a[i] - '0') * 4 + (a[j] - '0') * 2 + (a[k] - '0');
            prob[idx] += 1.0 / A.size();
        }

        const auto strategy = GenerateStrategy({"0..", "11.", ".00", "..1"}, prob);
        if (strategy.expected_cost < f) {
            dbg(make_tuple((f - strategy.expected_cost) / f, f, strategy.expected_cost, i, j, k));
        }
    }

    REP(i, N) REP(j, i) REP(k, j) REP(l, k) {
        break;
        const auto f = Estimate_0_1(A, i) + Estimate_0_1(A, j) + Estimate_0_1(A, k) + Estimate_0_1(A, l);
        vector<double> prob(16);
        for (const auto &a : A) {
            int idx = (a[i] - '0') * 8 + (a[j] - '0') * 4 + (a[k] - '0') * 2 + (a[l] - '0');
            prob[idx] += 1.0 / A.size();
        }

        const auto strategy = GenerateStrategy({"0...", "11..", ".00.", "..11", "...0"}, prob);
        if (strategy.expected_cost < f) {
            dbg(make_tuple((f - strategy.expected_cost) / f, f, strategy.expected_cost, i, j, k, l));
        }
    }

    REP(i, N) REP(j, i) REP(k, j) REP(l, k) REP(m, l) {
        break;
        const auto f =
            Estimate_0_1(A, i) + Estimate_0_1(A, j) + Estimate_0_1(A, k) + Estimate_0_1(A, l) + Estimate_0_1(A, m);
        vector<double> prob(32);
        for (const auto &a : A) {
            int idx = (a[i] - '0') * 16 + (a[j] - '0') * 8 + (a[k] - '0') * 4 + (a[l] - '0') * 2 + (a[m] - '0');
            prob[idx] += 1.0 / A.size();
        }

        const auto strategy = GenerateStrategy({"0....", "11...", ".00..", "..11.", "...00", "....1"}, prob);
        dbg(make_tuple((f - strategy.expected_cost) / f, f, strategy.expected_cost, i, j, k, l, m));
    }


    REP(i, N) REP(j, i) REP(k, j) REP(l, k) REP(m, l) REP(n, m) {
        break;
        const auto f =
            Estimate_0_1(A, i) + Estimate_0_1(A, j) + Estimate_0_1(A, k) + Estimate_0_1(A, l) + Estimate_0_1(A, m) + Estimate_0_1(A, n);
        vector<double> prob(64);
        for (const auto &a : A) {
            int idx = (a[i] - '0') * 32 + (a[j] - '0') * 16 + (a[k] - '0') * 8 + (a[l] - '0') * 4 + (a[m] - '0') * 2 + (a[n] - '0');
            prob[idx] += 1.0 / A.size();
        }

        const auto strategy = GenerateStrategy({"0.....", "11....", ".00...", "..11..", "...00.", "....11", ".....0"}, prob);
        dbg(make_tuple((f - strategy.expected_cost) / f, f, strategy.expected_cost, i, j, k, l, m, n));
    }

    vector<string> S(K, string(N, '.'));

    S.at(0).at(0) = '0';
    REP(i, N - 1) {
        S.at(i + 1).at(i) = '0' + (i + 1) % 2;
        S.at(i + 1).at(i + 1) = '0' + (i + 1) % 2;
    }
    S.at(N).at(N - 1) = '0';
    // REP(j, N) {
    //     S[j * 2][j] = A[0][j];
    //     S[j * 2 + 1][j] = A[0][j] ^ 1;
    //     // S[j * 2][j] = '0';
    //     // S[j * 2 + 1][j] = '1';
    // }

    for (auto s : S) cout << s << endl;

    vector<int> layer2depth(K);
    REP(d, K) layer2depth[d] = d;

    REP(_, R) {
        int type;
        cin >> type;
        assert(0 <= type and type < P);

        vector<pint> ops;

        auto Op = [&](int k, int d) {
            assert(0 <= k and k < K);
            assert(0 <= d and d < K);
            ops.emplace_back(k, d);

            const int current_depth = layer2depth[k];
            for (auto &depth : layer2depth) {
                if (depth > current_depth) --depth;
            }
            for (auto &depth : layer2depth) {
                if (depth >= d) ++depth;
            }
            layer2depth[k] = d;
        };


        // move
        vector<int> purge_done(N + 1);
        while (true) {
            // if (_ > 10) break;
            // purge
            bool purged = false;
            FOR(layer, 1, N) {
                const bool can_see = layer2depth[layer] < layer2depth[layer - 1] or layer2depth[layer] < layer2depth[layer + 1];
                const bool prev_bad = S[layer][layer - 1] != A[type][layer - 1];
                const bool next_bad = S[layer][layer] != A[type][layer];
                if (can_see and (prev_bad and next_bad) and chmax(purge_done[layer], 1)) {
                    Op(layer, N);
                    purged = true;
                }
            }
            if (purged) continue;

            vector<int> a(N + 1), b(N + 1);
            REP(layer, N + 1) {
                const bool prev_bad = layer > 0 and (layer2depth[layer] < layer2depth[layer - 1] and
                                                     S[layer][layer - 1] != A[type][layer - 1]);
                const bool next_bad = layer < N and (layer2depth[layer] < layer2depth[layer + 1] and
                                                     S[layer][layer] != A[type][layer]);

                // assert(!(prev_bad and next_bad));

                if (prev_bad) {
                    a[layer] = 1;
                    b[layer - 1] = 1;
                }

                if (next_bad) {
                    a[layer] = 1;
                    b[layer + 1] = 1;
                }
            }

            if (*max_element(ALL(a)) <= 0) break;

            bool done = false;
            REP(layer, N + 1) {
                if (!a[layer] and b[layer]) {
                    const bool prev_bad = layer > 0 and (layer2depth[layer] > layer2depth[layer - 1] and
                                            S[layer - 1][layer - 1] != A[type][layer - 1]);
                    const bool next_bad = layer < N and (layer2depth[layer] > layer2depth[layer + 1] and
                                            S[layer + 1][layer] != A[type][layer]);
                    assert(prev_bad or next_bad);
                    if (prev_bad) {
                        Op(layer - 1, layer2depth[layer]);
                    } else if (next_bad) {
                        Op(layer + 1, layer2depth[layer]);
                    }

                    done = true;
                    break;
                }
            }
            assert(done);
        }

        // REP(j, N) {
        //     int sheet0 = j * 2, sheet1 = j * 2 + 1;
        //     if (S[j * 2][j] == '1') {
        //         assert(S[j * 2 + 1][j] == '0');
        //         swap(sheet0, sheet1);
        //     } else {
        //         assert(S[j * 2][j] == '0');
        //         assert(S[j * 2 + 1][j] == '1');
        //     }
        //     const int p0 = layer2depth[sheet0];
        //     const int p1 = layer2depth[sheet1];

        //     if (p0 < p1 and (A[type][j] == '1')) {
        //         Op(sheet0, p1);
        //     } else if (p1 < p0 and (A[type][j] == '0')) {
        //         Op(sheet1, p0);
        //     }
        // }

        cout << ops.size() << endl;
        for (auto op : ops) cout << op.first << " " << op.second << endl;
    }
}
