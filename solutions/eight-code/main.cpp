// Eight-sheet comparison code; exact offline table, no six-sheet fallback. See README.md.
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <immintrin.h>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <string>
#include <utility>
#include <vector>

using u64 = std::uint64_t;

namespace {

constexpr int N = 64, K = 192, P = 256;
constexpr int kCapWindow = 63, kCapPaper = 8;
constexpr u64 kCapBit = 1ULL << kCapWindow;
constexpr u64 kActiveWindows = kCapBit - 1;

// Every clock reading is multiplied by CLOCK_SCALE (CLAUDE.md, the clock scale): the local
// evaluation compiles with -DCLOCK_SCALE=1.1 so that it searches as much as the judge.
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
const auto kStartTime = std::chrono::steady_clock::now();
double elapsed_sec() {
    return CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - kStartTime).count();
}

// Fixed iteration counts for experiments (MAP_ITERS, GOPT_STEPS, ANNEAL_ITERS, CLIMB_ITERS; 0 or
// unset: until the time limits; GOPT_STEPS / CLIMB_ITERS = -1: no climb). The output then does not
// depend on the machine.
int env_int(const char* name) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : 0;
}


u64 low_bits(int n) { return n == 64 ? ~0ULL : (1ULL << n) - 1; }  // bits 0..n-1

// xorshift (7, 9); `mod` and `below` are the two mappings to [0, n) of the two original generators.
struct XorShift {
    u64 x;
    u64 next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int mod(int n) { return int(next() % n); }
    int below(int n) { return int(((unsigned __int128)next() * unsigned(n)) >> 64); }
    double real() { return (next() >> 11) * 0x1.0p-53; }
};

// The generic layer. Generic window j compares the sheets edge[j] = (a, b): a has color polarity[j]
// there, b the other color, and the other sheets have a hole, so the window shows the color of the
// upper of a and b. With every pair of sheets compared (complete), every sheet but the bottom one is
// visible somewhere.
struct Comparator {
    int M = 0, G = 0;
    bool complete = false;
    std::vector<std::pair<int, int>> edge;
    std::vector<int> polarity;
    std::vector<u64> opq, black;  // per sheet

    void init(int m, int g, std::mt19937_64& rng) {  // random pairs (each used about equally)
        M = m;
        G = g;
        std::vector<std::pair<int, int>> all;
        for (int a = 0; a < M; ++a)
            for (int b = a + 1; b < M; ++b) all.emplace_back(a, b);
        std::shuffle(all.begin(), all.end(), rng);
        edge.resize(G);
        polarity.resize(G);
        for (int j = 0; j < G; ++j) {
            edge[j] = all[j % all.size()];
            polarity[j] = int(rng() & 1);
        }
        rebuild();
    }

    // The sheets' patterns from edge / polarity.
    void rebuild() {
        assert(1 < M && M <= 12 && 0 < G && G <= 64);
        assert(int(edge.size()) == G && int(polarity.size()) == G);
        opq.assign(M, 0);
        black.assign(M, 0);
        std::array<unsigned, 12> adj{};
        for (int j = 0; j < G; ++j) {
            auto [a, b] = edge[j];
            assert(a != b && 0 <= a && a < M && 0 <= b && b < M);
            u64 bit = 1ULL << j;
            opq[a] |= bit;
            opq[b] |= bit;
            black[polarity[j] ? a : b] |= bit;
            adj[a] |= 1U << b;
            adj[b] |= 1U << a;
        }
        complete = true;
        for (int i = 0; i < M; ++i) complete &= (adj[i] | (1U << i)) == (1U << M) - 1;
    }

    // Transitive closure of the relations asked for by the colors `target` on the windows `holes`:
    // bit b of reach[a] means that a must be above b. A bit on the diagonal: impossible.
    std::array<unsigned, 12> closure(u64 target, u64 holes) const {
        std::array<unsigned, 12> reach{};
        holes &= low_bits(G);
        while (holes) {
            int j = __builtin_ctzll(holes);
            holes &= holes - 1;
            auto [a, b] = edge[j];
            if (int((target >> j) & 1) != polarity[j]) std::swap(a, b);
            reach[a] |= 1U << b;
        }
        for (int k = 0; k < M; ++k)
            for (int a = 0; a < M; ++a)
                if ((reach[a] >> k) & 1) reach[a] |= reach[k];
        return reach;
    }

    // Can a paper with holes where a and b differ serve both? (The relations for b are those for a
    // reversed, so one acyclicity test suffices.)
    bool compatible(u64 a, u64 b) const {
        auto reach = closure(a, a ^ b);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return false;
        return true;
    }

    // Expected moves to show a partial display (generic estimate of the design): the mean over the
    // M! orders of the sheets of the distance (the least number of moves, the bottom sheet fixed) to
    // the nearest order satisfying the relations. Tables built once (orders: perms;
    // below[s][a]: the sheets below a in order s; dist).
    std::vector<std::vector<int>> perms, next;
    std::vector<std::vector<unsigned>> below;
    std::vector<uint8_t> dist;
    int order_index(const std::vector<int>& o) const {
        return int(std::lower_bound(perms.begin(), perms.end(), o) - perms.begin());
    }
    int distance(int a, int b) const { return dist[a * perms.size() + b]; }
    // Moves (sheet, position in the layer) of a shortest way from order a to order b.
    std::vector<std::pair<int, int>> path(int a, int b) const {
        std::vector<std::pair<int, int>> ans;
        while (a != b)
            for (int code = 0; code < M * M; code++) {
                const int y = next[a][code];
                if (y >= 0 && distance(y, b) + 1 == distance(a, b)) {
                    ans.push_back({perms[a][code / M], code % M});
                    a = y;
                    break;
                }
            }
        return ans;
    }
    void build_tables() {
        if (!perms.empty()) return;
        std::vector<int> o(M);
        std::iota(o.begin(), o.end(), 0);
        do perms.push_back(o);
        while (std::next_permutation(o.begin(), o.end()));
        const int n = perms.size();
        below.assign(n, std::vector<unsigned>(M, 0));
        for (int t = 0; t < n; t++)
            for (int i = M - 1, acc = 0; i >= 0; i--) {
                below[t][perms[t][i]] = acc;
                acc |= 1 << perms[t][i];
            }
        // next[a][pos * M + d]: the order after the sheet at position pos (not the bottom one: it is
        // not visible) moves to position d; dist[a * n + b]: least moves from order a to order b, by a
        // BFS from every order
        next.assign(n, std::vector<int>(M * M, -1));
        for (int a = 0; a < n; a++)
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d) {
                        auto o2 = perms[a];
                        const int k = o2[pos];
                        o2.erase(o2.begin() + pos);
                        o2.insert(o2.begin() + d, k);
                        next[a][pos * M + d] = int(std::lower_bound(perms.begin(), perms.end(), o2) - perms.begin());
                    }
        dist.assign(n * n, 255);
        std::vector<int> q(n);
        for (int a = 0; a < n; a++) {
            uint8_t* da = &dist[a * n];
            int qb = 0, qe = 0;
            q[qe++] = a;
            da[a] = 0;
            while (qb < qe) {
                const int x = q[qb++];
                for (int y : next[x])
                    if (y >= 0 && da[y] == 255) da[y] = da[x] + 1, q[qe++] = y;
            }
        }
    }
    // The orders (indices of perms) showing `target` on `holes` (tables built).
    std::vector<int> satisfying(u64 target, u64 holes) const {
        const auto reach = closure(target, holes);
        std::vector<int> sat;
        for (int t = 0; t < (int)perms.size(); t++) {
            bool ok = true;
            for (int a = 0; a < M && ok; a++) ok = !(reach[a] & ~below[t][a]);
            if (ok) sat.push_back(t);
        }
        return sat;
    }
    std::vector<std::pair<u64, double>> memo;  // closure (6 rows of 6 bits) -> mean_moves, sorted
    double mean_moves(u64 target, u64 holes) {
        build_tables();
        auto reach = closure(target, holes);
        u64 key = 0;
        for (int a = 0; a < M; a++) key |= u64(reach[a]) << (6 * a);
        auto it = std::lower_bound(memo.begin(), memo.end(), std::make_pair(key, -1.0));
        if (it != memo.end() && it->first == key) return it->second;
        const int n = perms.size();
        std::vector<int> sat;
        for (int t = 0; t < n; t++) {
            bool ok = true;
            for (int a = 0; a < M && ok; a++) ok = !(reach[a] & ~below[t][a]);
            if (ok) sat.push_back(t);
        }
        double mean = 0;
        if (!sat.empty()) {
            double sum = 0;
            for (int s = 0; s < n; s++) {
                int m = M;
                for (int t : sat)
                    if ((m = std::min<int>(m, dist[s * n + t])) == 0) break;
                sum += m;
            }
            mean = sum / n;
        }
        memo.insert(it, {key, mean});
        return mean;
    }

    // Moves (sheet, depth within the layer) taking the layer from the order `current` (top first) to an
    // order showing `target` on `holes`, keeping the largest subsequence of the sheets that is already
    // consistent and moving the others; {{-1, -1}} if impossible. The caller keeps the generic sheets
    // contiguous with no opaque paper above them while applying the moves.
    std::vector<std::pair<int, int>> plan(const std::vector<int>& current, u64 target, u64 holes) const {
        if (!complete || int(current.size()) != M) return {{-1, -1}};
        auto reach = closure(target, holes);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return {{-1, -1}};
        bool satisfied = true;
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) satisfied = false;
        if (satisfied) return {};

        std::array<unsigned, 12> conflict{};
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) {
                    conflict[current[i]] |= 1U << current[j];
                    conflict[current[j]] |= 1U << current[i];
                }

        // A kept subsequence is compatible iff it has no inversion of the closure. If it keeps the bottom
        // sheet, every moved sheet is visible until its move; otherwise a moved witness must end below
        // every kept sheet and below the old bottom sheet, exposing that sheet before its move.
        std::array<unsigned char, 1 << 12> valid{};
        valid[0] = 1;
        unsigned kept = 0;
        int best_count = -1, witness = -1;
        const int bottom = current.back();
        const unsigned bottom_bit = 1U << bottom;
        const unsigned end = 1U << M;
        for (unsigned mask = 1; mask < end; ++mask) {
            unsigned rest = mask & (mask - 1);
            int a = __builtin_ctz(mask);
            valid[mask] = valid[rest] && !(rest & conflict[a]);
            if (!valid[mask]) continue;
            int count = __builtin_popcount(mask);
            if (count <= best_count) continue;
            bool legal = mask & bottom_bit;
            int w = -1;
            if (!legal) {
                for (int b = 0; b < M; ++b) {
                    if ((mask >> b & 1) || b == bottom) continue;
                    if (!(reach[b] & (mask | bottom_bit))) {
                        w = b;
                        legal = true;
                        break;
                    }
                }
            }
            if (legal) {
                kept = mask;
                best_count = count;
                witness = w;
            }
        }
        if (best_count < 0) return {{-1, -1}};

        auto required = reach;
        int last = -1;
        for (int a : current)
            if (kept >> a & 1) {
                if (last >= 0) required[last] |= 1U << a;
                last = a;
            }
        if (witness >= 0) {
            required[last] |= 1U << witness;
            required[bottom] |= 1U << witness;
        }
        std::array<unsigned, 12> pred{};
        for (int a = 0; a < M; ++a)
            for (int b = 0; b < M; ++b)
                if (required[a] >> b & 1) pred[b] |= 1U << a;

        std::vector<int> goal;
        unsigned placed = 0;
        for (int step = 0; step < M; ++step) {
            int next = -1;
            for (int a : current)
                if (!(placed >> a & 1) && !(pred[a] & ~placed)) {
                    next = a;
                    break;
                }
            if (next < 0) return {{-1, -1}};
            goal.push_back(next);
            placed |= 1U << next;
        }

        std::vector<int> order = current;
        std::vector<std::pair<int, int>> moves;
        for (int a : current)
            if (!(kept >> a & 1)) {
                u64 covered = 0;
                bool visible = false;
                for (int b : order) {
                    if (b == a) {
                        visible = (opq[a] & ~covered) != 0;
                        break;
                    }
                    covered |= opq[b];
                }
                if (!visible) return {{-1, -1}};
                int successor = -1;
                bool passed = false;
                for (int b : goal) {
                    if (passed && (kept >> b & 1)) {
                        successor = b;
                        break;
                    }
                    if (b == a) passed = true;
                }
                int old = int(std::find(order.begin(), order.end(), a) - order.begin());
                order.erase(order.begin() + old);
                int depth =
                    successor < 0 ? M - 1 : int(std::find(order.begin(), order.end(), successor) - order.begin());
                order.insert(order.begin() + depth, a);
                if (old != depth) moves.emplace_back(a, depth);
                kept |= 1U << a;
            }
        if (order != goal) return {{-1, -1}};
        return moves;
    }
};

// Closure of a relation bit matrix of m <= 8 sheets (bit 8a + b: a above b).
u64 closure8(u64 r, int m) {
    for (int k = 0; k < m; k++) r |= ((r >> k) & 0x0101010101010101ULL) * ((r >> (8 * k)) & 255);
    return r;
}
constexpr u64 kDiagonal = 0x8040201008040201ULL;

u64 transpose8(u64 r) {
    u64 t = (r ^ (r >> 7)) & 0x00AA00AA00AA00AAULL;
    r ^= t ^ (t << 7);
    t = (r ^ (r >> 14)) & 0x0000CCCC0000CCCCULL;
    r ^= t ^ (t << 14);
    t = (r ^ (r >> 28)) & 0x00000000F0F0F0F0ULL;
    r ^= t ^ (t << 28);
    return r;
}
u64 canonical8(u64 r){
    constexpr int n=8;
    unsigned out[8]{},in[8]{};int key[8]{},order[8]{};
    for(int a=0;a<n;++a){
        out[a]=(r>>(8*a))&255;
        for(int b=0;b<n;++b)if(out[a]>>b&1)in[b]|=1u<<a;
    }
    for(int a=0;a<n;++a)key[a]=std::popcount(out[a])*9+std::popcount(in[a]);
    u64 best=~u64(0);
    auto dfs=[&](auto&&self,int depth,unsigned used)->void{
        if(depth==n){
            u64 x=0;
            for(int i=0;i<n;++i)for(int j=0;j<n;++j)if(out[order[i]]>>order[j]&1)x|=u64(1)<<(8*i+j);
            best=std::min(best,x);return;
        }
        int minimum=1000;
        for(int a=0;a<n;++a)if(!(used>>a&1))minimum=std::min(minimum,key[a]);
        unsigned tried=0;
        for(int a=0;a<n;++a)if(!(used>>a&1)&&key[a]==minimum){
            bool twin=false;
            for(int b=0;b<a;++b)if(tried>>b&1)twin|=out[a]==out[b]&&in[a]==in[b];
            if(twin)continue;
            tried|=1u<<a;order[depth]=a;self(self,depth+1,used|(1u<<a));
        }
    };
    dfs(dfs,0,0);return best;
}

constexpr char kPoset8Packed[] =
"00WeWYmWaWXeW2mwf2Wu-XmW4emz3WWWWWWWW1Wtw3WWWWWWWWW8ukh3WWWy-W8Wrp4WWWWWWWW2iXh4WWWWW_FWmz4WWWaWXe-z--1mje2WWWy-WeW2ans3"
"WWWWWWWWWGuwe3WWWWW_lW4ila4WWWaWXe-ud-1WfX4WWWWWWWW1mWz3WWWy-W8WoW5WWWaW-t--7mmi3WWWy-WeW2ecn4WWWaW-p-y7mbb4WWWWWW4itZ4W"
"WWWWWWW1mm_3WWWWWWyVysd4WWWWWW4ijb4WWWWm-3mgg4WWWWGmlf4WWWWGWbi4WWW2WXk4W8mam4Wu-zl1mug5WWWWWWCmeu5WWW_-zFyje5WWW2szc5WW"
"Wy-WeVmxx4WeWYmWaW1ahx5Wu-zl-3iop5WWWYW-Fabc6WWW_-WeValg5WWWaWX8mnu5WWWWW_FiaZ6WWWy-W8urd6WWWYW-t-3iyr5WWW2egn5WWWy-_dW2"
"Way5WWWWW2mvf6WWWaW-p_4Wxa5WWWWm-ZW1Yta5WWWWGeiW5WWWy-WeW2ysx5WWWWWWWWm7Was3WWWWW_lW4mWo4WWWWWYm-v7ujb5WeWYmWaW3uwj5Wu-z"
"lW4WZu5WWWWW-lVWxi5WWWWWW8mre5WWWWWW8yvm5WWWWW1mbr5WWWWW-Nahd6WeWYm_p-2ybd6Wu--lWaW1qql6WWW_-_7mpY6WWWWWXW-9rzX6WWWWWXWW"
"k7aax4WWWWWWWW2gpp4WWWWWWq-1aWj5WWWWWWCyb_4WWWWWW8aqZ5WWWaW1mgh5WWWy-_Ni-_5WWWaW-t-3crZ6WWWy-_t-1w-o5WWWWWYGwvZ6WWWWW--_"
"7z_v5WWWWW1wYr5WWWam_t-zNbjW6WWW_lWWXu7cks5WWW2oed5WWWy-_dW2ifw5WWWYWXu_5_bW6WWW2_dr5WWWy-_tWoFalz4WWWWWWWW4irq4WWWWWWe-"
"3mtn5WWWWWWOeXY5WWWWWWGuwd5WWWWW2ial5WWWWW_l_3Wrp4WWWWWYmW4q-x5WWWWW_lW4aso5WWWYmWe-vl1iWo5WWW2icl5WWWWGakW5WWWy--dWYGqe"
"-5WWWWW1qfe5WWWWW_l-3WoW5WWWaWXeWfd3su_4WWWWm-x-W8cfX5WWWWGyi_4WWWWWW4i_m4WWWy--x-XGoev5WWWWWX4Zdn5WWWWWW8yvv4WWWWW_--ZW"
"1uYj5WWWWWYWWy-s1mnc2WWWWW_lW4Wol3WWWWWWWWWW1uya3WWWWWWW-7Was3WWWWWYmWol_1urr4WWWWWWWW2Ygi4WWWWWWu-zNixa5WeWYmWiW3uak4Wu"
"-zl-pVkig5WWWWW-Feom5WWWWW1Wcj5WWWWW1Wzp5WeWYmzhW3Wbq5Wu--lWaW1mWu6WWW_-WW-7gsz5WWWWWWWWl7mdd5WWWWWWeW1sfw4WWWWWWWW2Wxj4"
"WWWWWWu-1mdW5WWWWWW8iwy4WWWWm_7_zm5WWWWm1qcZ5WWWWW1exc5WWWWW-Ny_z5WWWWW_l-1alz4WWWWWYmW4is_5WWWWW--_7fyv5WWWWW1kmm5WWWWW"
"_lW4oev5WeWYmWaWnNwuf5WWWWWWW-7csu5Wu-zl-xWp7Whd5WWWYWXeW6ueh6WWW_-_t-1_lj5WWWWWWGais5WWWYWXu_5asr6WWW_--dW2pdi6WWWWW-lW"
"kFmjf5WWWWWXm-nW2c-x5WWWWWXWWkl3ojl5WWWWW-t-XGYfn5WWWWW1Wzj5WWWWWWeW_dt1squ4WWWWWWWWW8uvy3WWWWWWWW2szv3WWWWWWWWWGecg3WWW"
"WW_lW4eqg4WWWWWYe-uFah_4WWWWWW8mcx4WWWWWWWW1ukW4WWWWWWWW2i_x3WWWWm_p-1m_g5WWWWm1qmX5WWWWWW4ifa4WWWWWW8ivY4WWWWm_7mXb5WWW"
"Wm1muc4WWWWW1Whf4WWW4uei4WWWylzBqqZ6WWWWmXCYfZ5WWWWW_l-1mfr4WWWaWXeW2urn5WWWy-WeW2moj5WWWWm_-_7_ax5WWWWGYWW5WWWWW1czy4WW"
"WWW_lW4mnl5WWWWWWWWmFyjo3WWWWWWW-7ila4WWWWWWmXw7_az5WWWWWWm-v7ely4WWWaWXeW6_kd5WWWy-_x_1qms5WWWWWWSgZY5WWWWWWGmof5WWWaWX"
"u_5wlr5WWWy--dW2gZv5WWWWW-lWqFsnk4WWWWWWWW4mou4WWWWWYGY_Z5WWWWWWW-7kgm5WWWWW_lW4fli5WWWWWXm-x-1kjg5WWWWW1oXz4WWWWW_l-xVe"
"qg4WWWWWWWW8mfr4WWWWWWW1WyX5WWWWWYm-fl2cfw4WWWWW-p-XGlws5WWWWWX4gXw4WWWWWW8ssj4WWWWW_--ZW1eya5WWWWWWGuzp4WWWWWYm-vds1qaa"
"5WWWWWWWWW8WWt4WWWWWWWW2eun4WWWWWWWW_7cwe5WWWam-xVuch5WWWWm1gyw5WWWy-_3Wrl5WeWYmW4mfX6Wu-XmW4mg_5WWW_-zFaxc6WWW2mpa6WWWy"
"-W8qzh6WWWWWWWVyez4WWWWWWuVuun5WeWYmWCoa_5Wu-zl-3aZs5WWWWW1u_w5WWWWW-tV_ji5WWWWWW8Wzo5WWWaW1ujx5WWWy-_Nlyg6WWWYW-t-3gmm6"
"WWW2idf6WWWy-_t-1ifw5WWWWWYGWwi6WWWWW--_7tva6WWWWW1kY_5WWWWWWWWm7Wds3WWWWW_lW4irq4WWWWWYm-v7eXd5WeWYmWaW3Wfk5Wu-zl_3aas5"
"WWWWW2uov5WWWWW-lVgtk5WWWWWW8mmf5WWWWWW8Y_n5WWWWW1_ks5WWWWW-Nmre6WeWYm_p-2Wvi6Wu--lWaW1any6WWW_--d-9aqa6WWWWWXu-i7ijh5WW"
"WWWWeW1cwx4WWWWWWWW2syp4WWWWWWq-1icl5WWWWWW4WXX5WWWWWW8uo_4WWWWm_7alp5WWWWm1gZa5WWWWW1mid5WWW4ezh5WWWy-_Nks-5WWWWW_l-1eX"
"Y5WWWaWXeW2qnf6WWWy-WeW2kka6WWWWW--_7Zgx5WWWWW1vpr5WWWWW_lW4gsz5WWWWWYe-e7acm5WWWWWWeW1ypg5WWWam-xVmfy5WWWWm1ilX6WWWy-_3"
"u-n5WeWYmW4upa6Wu-zFua_5WWWWW-3_yu5WWWaW1atX6WWWy-_NWul6WWWWWWWVu-z4WWWWWWuVeeq5WeWYmWCar-5Wu-zl-3ent5WWWWW1Wqy5WWWWW-lV"
"ytm5WWWWWW8ykj5WWWWm_7uWv5WWWWm1qaq5WWWWW1Wxt5WWW4aXz5WWWy-_Nsli6WWWWWWuUizs5WWWam-3ehZ6WWWyFuYy5WeWYGyfe6Wu-XGWeb6WWWy-"
"_3uep5WeWYmW4eqc6Wu-zFiWW6WWWWW-3amw5WWWWW1Wj_5WWW4yvZ6WWWWm_3eid6WWWyFmyz5WeWYGWpg6Wu-zFmWY6WWW4Wpd6WWWyFmba6WeW2mYj6Wu"
"-1ezf6WWW2mnj6W8WYn6Wu-z-zFiv-6WWWylW4utn6WeWYmW4sda7Wu-zl-3gqp6WWWWW1u_u6WWW4oeW7WWWy-ydVuwd5WeWYmWaW1mXt6Wu--lWaW1im_6"
"WWW2Wlp6WWW_---VYaZ7WWW2kd_6WWWWm-3ubb7WWWWGucY7WWWWGa_e7WWW2Wzi7W8Wko7Wu-vlWaW1mYk6WWWWWWeVajl6WeWYmWSe-j7Wu-zl-3Wkz6WW"
"WWWWqUgon6WWWWWWCock6WWWWWWOczt6WWWWWW8epx6WWWWW1WzX7WWW4qyf7WWWWm_p_4Wgv6WWWWm1acz6WWWy-zZW1kxd6WWWWW1yb-5WWWWW--V_ug6W"
"eWYmW4WjX7WWWWW1cyz6Wu-zl-pVckf6WWWWWW8gca6WWWWm_7imn6WWWaW1uhz6WWWyFayj6WWWWGuos6WWWWGecp6WWW4odw6WWWy-ydW2qqZ6WeWYmWaW"
"1uuk7Wu--lWaW1inp7WWW2wgg7WWWy-We-1Wph6WWWWWWW1mgZ7WWWWW_l-h7uou3WWWWWWW-7iXh4WeWYmWaXv7qor5Wu-zl-hV_az5WWWWWWW1iwb6WeWY"
"mWq_6qpb6Wu-XWWaW1fyu6WWWyl-tWo7_lj5WWWYWXeW6yXi6WWW2aZp5WWWy-_t-1avo5WWWWWWGsky5WWWYWXu_5Y-s6WWW2maY6WWWy--dW2cWl6WWWam"
"-x-k7and6WWWWGuwb6WWW_--Rtdq6WWW2Zrm6WWWy-_tVais5WeWYmWaW1azy6Wu--lW4kZX7WWWYWWWW1YZv6WWW_----3qor6WWW2ogi6WWWWm-ZVaas6W"
"WWWGs_p6WWW_--Ryaw6WWW2aor6WWWWm-3aqy6WWWWG_-v6WWWWGinW7WWW2qyZ7W8exe7Wu-zl-Bqja7WWWy-_dVsky5WWWWWWGWlb6WeWYmWqVyqX7WWWW"
"WWGute7Wu-zl-3Wvp6WWWaWXqUqcz6WWWWWWShuz6WWWy-_7mdk6WWWaWX8iua7WWWWWWi_2Wkx6WWWWm-ZW1dbw6WWWWGyth6WWWWWWyV_sy6WWWWWW4ado"
"6WWWWm-3etZ7WWWWGukW7WWWWGkyd7WWW2qgi7W8yXp7Wu-vl-ZW1zWs6WWWWWWWW1atw6WeWYmW4szt7Wu-XWWaW1soo7WWW_l-lW4bwk7WWW2psb7WWWy-"
"_t-1mig6WWWWWWGuyt6WWWWWWm-h7eau4WWWWWWWW4WdZ5WWWWWYGWjl5WWWWWWW-7yoy5WWWWW_lW4Wfs5WWWWWYu-g7wsj6WWWWm_--2Wrj6WWWWm1qoc6"
"WWWWWWOwuo6WeWYm_p-2wnl6Wu-zl-hW1Yrf6WeWYmWq-2wdv6WWWWWYGWab7Wu-zl-tUmqx6WWWWWWCrWt6WWWWW_7gdZ6WWWWWYGyyt6WWWWWW8qa_6WeW"
"YmWy_6s_j7Wu-zl-pVlnu6WWWWWW8__k6WWWWm_7-qZ7WWWWm1fc_6WWWWGoag7WeWYW_hW3z_f7Wu-zlXq-f7boi6WWWaW-Fpqu6WWWy-W8kis6WWWWWWe-"
"1m_g6WWWWWWWW1m_W6WWWWWWOugh6WWWWW_l-1WdZ5WWWaWXeW2khi6WWWy-_7gdZ6WWWWWWm-1_ws5WWWWWYGmqd6WWWWWWy_1kzv6WWWWWW8Yrt6WWWWWW"
"4ikk6WWWWW_7eY_5WWWWWW4uzk6WWWaWX4ywr6WWWy-W8Wjm6WWWWWW8soq6WWWWW1yrw6WWW4WoX7WWWy-zt_5bon6WWWWW1-cc6WWWWWWu-1aaq6WWWWWW"
"8_si6WWWWWW8a_v6WWWWW1upW7WWW4qpf7WWWy-ydW2kiW6WWWaWXeW2lWc7WWWy-_t-1rod6WWWWWYGyl-6WWWWWWu_ed1rod6WWWam-ZWEWov6WWWWm1_t"
"c7WWW_-zx-6yeX7WWW2asq6WWWy--dWw7yxW6WWWWW1mpe5WWWWW---n7ifY6WWWWW1_dz5WWWWW---Dolk6WeWYmWaW1snh7WWWWW1oa_6Wu-zl_xVsfo6W"
"WWWW1sof6WWWWWWWWj7aXZ6WWWWWWu-1zhc6WWWWW-7zsc6WWWWWXuVtmy5WWWWm_7Z_c6WWWWm1wku5WWWWW---DZZd6WWWWW1Wjz5WWWWWWu-1cyf6WWWW"
"m_7ucp6WWWWm1gga6WWWWm_7a_w6WWWaW1mgd7WWWyFgok6WWWWGww-6WWWWGysp6WWW4cpw6WWWy-_t-5wcl6WWWWW_l-pFecn4WWWWWWWW8mxx4WWWWWWW"
"1ebe5WWWWWWWWk7urd6WeWYmWa-Aq-f6WWWWWWWW8W-p6WWWWWWW1ixX7Wu--lWa-f7ylj6WWW2kmc6WWWy-_tW9orW6WWWYWXe-5eey6WWW2qpc6WWW_---"
"-7uZc7WWW2ylm6WWW_--Vghq7WWW2sg_6WWWy-_t_1iop5WWWWWWW1qig6WWWWWYm-cFylg6WWWWWWWW3iaY6WWWWW_lW6yov5WWWWWYm-7_cX6WWWWW_l-3"
"alg5WWWWWWW1sry5WWWWWYm-3W_g6WWWWW_FauZ6WWWWWYGepu6WWWWWWW-bl1ajo5WWWWWWWWW8yov5WWWam-xVwkg6WWWWm1zgt6WWWy-_3auZ6WeWYmW4"
"sgy6Wu-XmW4yju6WWW_-zFojY7WWW2bxz6WWWy-W8kuW7WWWWW-p_W8Ws-5WWWWWX4neo5WWWWWW8iXw4WWWWWWu--7o_v5WeWYmWaW1stx6WWWWWW8iyk6W"
"u-zl_3zlj6WWWWW2aco6WWWWW-h-y7kvX6WWWWWWCgop5WWWWWWu-1i_q5WWWWWW8mga5WWWWWWq-1kvc6WWWWWW4sdy5WWWam-3qfu6WWWyFvgi6WWWWG_k"
"q6WWWaGi-t6WWWy-_3m-s5WWWWWW4olg6WWWWW1ngn6WWWWmz3kWj6WWWWm1tlW6WWWWW1agb6WWW4gth6WWWy-_Noft6WWWWW_-_XGojl5WWWWWWGojw4We"
"WYmWq-W8kra7WWWWWWGcaq6Wu-zl-h-_7z_v5WWWYWXy-1xgc7WWW2dcW7WWW_--7u-m7WWWYWW4rtW7WWW_--FuXd7WWW2jxm6WWWy-_t-zFi_b5WWWWWYi"
"-3cpX7WWWWWWCXZw6WWWWW_7yav5WWWWWW8irl6WWWWWY8Wsh6WWWWW--_t-1mv_5WWWWW1qyc5WWWWW---FWar6WWWWW1iv-5WWWWW_l-hVemz3WWWWWWWX"
"8Whd5WWWWWWW-7ikx4WWWWWWWW8Wqg5WWWWWWW1qYz5WWWWWWWWm-p1mzZ2WWWWWWW-dW2ug_2WWWWWWWXqly1iWY5WeWYmWaWbu1mhh4Wu-zl-x-w7crb5W"
"WWWWWm-7wdl5WWWWWWGqlf5WWWWWWGu_r5WWWWWWu_-Foin5WeWYmWy-ae1m-Y5Wu----ZWX8okf6WWW2sba6WWWyl-tWsly1qpc4WWWYWXeWYm1uvf5WWW2"
"mlf4WWWy-_d-1seY5WWWWWWW1eYd5WWWWWWm-tFyip4WWWWWWWW4qXf4WWWWWWWW4Ylt4WWWWWWGumz4WWWWWWm-Baje5WWWYWXe-vl1ujX6WWW2YrW5WWWy"
"--dWYGqYz5WWWWW-l-3ely4WWWWWWmWm-4gkZ5WWWamWy-wts1_xe5WWWWGksd5WWW_--RYju5WWW2mYs5WWW_----1jhp6WWWYWWWW1tkk6WWW_----3qWy"
"5WWW2Yis5WWWy-_dW2WgY6WWWaWXq_4XuX6WWWWm-ZW1rYX6WWW_FkpX6WWW2YXw5WWWy-_tWs7mko4WWWWWXu-y7mig6WeWYm-hW4ire6Wu--lWaW1avq6W"
"WW_-_7e_b6WWWWWXW-9g_o6WWWaWWuWs7emb6WWWy-_t-1elq5WWWWWXm-7Yfb6WWWYWWuWsVwjv5WWW2uce5WWWy-_d-1cxq5WWWWWWW1kqx5WWWamWy_s7"
"muv5WWWWGufu5WWWWm-Bkdr6WWWWGWfo6WWW_--FyX-5WWW2uXy5WWW_----1qgv6WWWYWWWW1_so6WWW_----3qk-5WWW2uvu5WWWWm-ZVcxW6WWWWG_Y-5"
"WWWWm-Bavx6WWWWGsau6WWW_--FaxY6WWW2qg-5WWWWm-3uya6WWWWGuwY6WWWWGWYe6WWW2Wsg6W8mck6Wu-zl-BcYw6WWWy-_tUyZz5WWWWWWW1Wma6WeW"
"YmWaVihY7WWWWWWW1Wqc7Wu-XmWuU_dr6WWWWWWCkh_6WWWWWWGmkq6WWWWWWGqoY7WWWWm-p_4iWs6WWWWGqgp6WWW_--xW7ijw6WWW2mzp6WWWy-_d-1qz"
"h6WWWWWWW1qfs6WWWWWWm-d7ye_4WWWWWWWW4mZr4WWWWWWe-3gur5WWWWWWOirY5WWWWWWGene5WWWWWWm-Ba-p5WeWYmWaWj7snq6Wu-z--pVuyt6WWWWm"
"-7op-5WeWYmWaW3Wzf6Wu-zl-hVajW6WWWWWWW1ade6WeWYmWq-2uXu6WWWWWWGy_z6Wu-zl-hVseX6WWWWWWGYki6WWWWWW8aWo6WWWWmWW-7efh7WeWYWW"
"iW3osb7Wu-XmWe-f7uoh6WWWWWWSsum6WWWy-_tVaom5WWWaWXeW2_Yn6WWWWWWWW4uuc6WWWy-_t-1rxr5WWWWWWGwi_5WWWaWXy_1eY_6WWWWWWSaoq6WW"
"Wy-_7ekc6WWWaWX8qmw6WWWWWWq_4tya7WWWWWWyW7rpX7WWWy-_t-1Yqb6WWWWWWGhoo6WWWYmWu_rVYlh6WWW2_Wb6WWW_Fwwc6WWW2shi5WWWWWWy-m7n"
"jY6WWW_--3qvY6WWW2qwy5WWWWWWy-Dc_k6WWWWm-ZW1n-i6WWW_Fwxj6WWW2vYY6WWWWWWyVyrm6WWWWm-3gjm6WWW_Fe-m6WWW2wcf6WWWWm-3Wes6WWWW"
"Gaxp6WWWWGWiv6WWW2qyy6W8_xX7Wu-xl-x-6kdw6WWW2iuk6WWWy--dWw7Yze6WWWWW-l-3ujb5WWWWWXmWk7mml6WWWWWWWWEzow6WeWYmWaW1iez7Wu-z"
"l-xV-X-6WeWYm-p-2eiu6Wu-zlWiWi7aZs6WWWWm--VzWs6WWWWmWWWEh_l6WWWWm---1kuW7WWWaWX8yWu7WWWWm-l-3W_q6WWW_----tVoxr6WWW2oWY6W"
"WW_---W8kka7WWW2ynq6WWWy-_t-hFg-Z6WWWWWWm-3tva6WWWWWWmW2ynu5WWWWWWW-3aax4WWWWWWWX8mev5WWWWWWWW4q_X6WWWWWWGqlj6WWWamWy_ct"
"1mcd6WWWWGWbb6WWW_--Rvaq6WWW2bvl6WWWy--l-XG-X-6WWWWW-t-YOilk5WeWYmWaWX8-WZ7Wu--lWu-W8wgr6WWW2bZm6WWW_--7aqj7WWWYWW4ez_6W"
"WW_--Fkgr6WWW2rYc6WWWy-_t-vFajo5WWWWWWm-3ero5WWWWWWGiaX5WWWWWWe-3zeb6WWWWWW4iWp6WWWWWWKuzt5WWWWWW8ubk6WWWWWW8WmX6WWWYmWu"
"_rl1mwe6WWW2gvX6WWW_Fcba6WWW2uig5WWW_l---Fpk-6WWW2uex6WWW_FYYz6WWW2fka6WWWy--dWoFgnd6WWWWWWWWGwxy6WWWWW-lWmlp1sgm4WWWWWW"
"WWaGibr3WWWWWWWWWW1avc3WWWWWWe-uVmei5WWWWWWuW1wrq4WWWWWWWW2egx3WWWWWWWW4WZu3WWWWWWe-3mnw4WWWWWWOew_3WWWWWWGWpY4WWWWW2mxc"
"4WWWWW_l-Bybt4WWWWWWW-tVWfi3WWWWWYmWaW1mbz4WWWWW_l-3ewp4WWWWWWWWuVmgb4WWWWWWWX8imt4WWWWWWm-l-3_ko4WWWWWWGWme4WWWWWWW-t-1"
"Wol3WWWWWWWWGmbe4WWWWWWWXqlq1crb5WeWYmWaWX8ogo6Wu-zlXqVqrb6WWWWWWOvsn6WWWWWWe--FcqZ6WeWYm_hW3cYv5Wu-zlXa-8onn6WWWWm_lWq7"
"kgb6WWWWm1ixk5WWWWWWOezZ6WWWWW_l-1ye_4WWWWWWmW2op-5WWWWWWm-1aom5WWWWWYGmsW6WWWWWWW-7i-y5WWWWW_lW4Xgx5WeWYmWaWnNong5Wu-zl"
"-x-w7oof5WWWWWWWW8zlk5WWWWWWGsut5WWWWWWm-rFwng5WWWWWWe-9ucp5WeWYmWyWt7mhs6WWWWWWWW2mz_5Wu-zlXqVimj6WWWWW_FaZg6WeWYmWy-2m"
"ix5WWWWWWe-3yYy6WWWWWWOgZY6WWWWWWGmub6WWWWW2Whh6Wu-zlzpUioa6WWWWWYGiYu6WWWWW_Fmyi6WWWWWWGmgm6WWWWW2Wpy6WWWWWWW-7_uY7WeWY"
"m_hW3qit6Wu-zlXq-f7ttr6WWWWW_NaZg6WWWWW2kzs6WWWWW_lVeyh5WWWWWYuVmgo6WWWWW_Fyxf6WWWWWYmVmnc6WWWWW_7ejw5WWWWWYG-rh6WWWWW_l"
"-1ay_4WWWWWWmW2edY6WWWWWWu_1Wex5WWWWWWOsqn5WWWWWWGecv5WWWWW2egY6WWWWWWy_1kxy6WWWWWWCgWm6WWWWW_7yky5WWWWWWGmcb6WWWWW2wil6"
"WWWWW_7meg6WWWWW2axq6WWWWWWW-7mm_6WWWWW_dW2ywy5WWWWWWWW4kiZ6WWWWWWGqnk6WWWWW2anx6WeWYm_p_qNuxk5Wu----ZWX8unr6WeWWWYiWZOy"
"zz6WWWWW_l-3mdo6Wu-zlXiWg7sdk6WWWWWWu-1qXq6WWWWWWWW1rqc6WWWWWW8jjX6WWWWWWWWExWY6WWWWWWu-1qWp6WWWWm_7qiz6WWWWm1ugh6WWWWm_"
"7mof7WWWWm1qXu6WWWWGyol7WWWWmzd-1Wxi5WWWWWYmW4ull6WeWYm_p-qNWcb6WWWWWWWX8s_t6Wu-zl-x-o7cxv5WWWWWWWWGawb6WWWWWWWWgFkvX6WW"
"WWWWWW4vpz5WWWWWWW-7aWj5WWWWWYiWql2d_y6WWWWWW8uXv6WWWWm_3jgz6WWWWm1zxg6WWWWWWOkov6WeWYm_Z-YOuqp6WWWWWWGyZf6Wu-zl-h-_7qyp"
"5WWWWWWu--F_fu5WWWWWWWW4oqa6WWWWWYGxou6WWWWW_F-ai6WeWYmWy_qd1Wwi5WWWWWWWWGyjd6Wu----ZWn7Wcq6WWWWWWWWGudf7WWW_l-tWo-p1ghw"
"4WWWaWXi-_7mto5WWWWWWS_we6WWWy-W8iWp6WWWWW_lVwdl5WWWWWYuVZof6WWWWWWWW1gdW6WWWaW-Fwgk6WWWy-W8img6WWWaW-t-3gdb6WWWy-_t-1cx"
"q5WWWWWWGyZz5WWWWW2_Zd6WWWaW-p_4qwi6WWWWWWaW1ibY6WWWy--dW2wjl6WWWWW1Xob6WWWWW_lWq7mvh4WWWWWXu-y7_ef6WWWWWXWW1om-5WWWWWWO"
"ite6WWWWW_--3ajW6WWWWWXW-9Zvk6WWWWW-lWj7oin5WWWWWYu-4iYa5WWWWWWOsWo5WWWWW_l-1eut4WWWWWWWW1gur5WWWaWXeW1kls5WWWy-_7wek5WW"
"WWWWm-1prb5WWWWWYGspo5WWWWW--_7xkw5WWWWW1xcr5WWWWW_lW4gmq5WWWWWWWWmFypo3WWWWWWm-X8otu5WWWWWWW1mn-5WWWWWWm-v7bi-4WWWaWXeW"
"6eee5WWWy-_x_1unv5WWWWWWSokZ5WWWWWWGmkh5WWWWWWm-tF_xq4WWWWWWWW4yYl4WWWWWWe-3auc5WWWWWWOygv4WWWWWWGWk_4WWWWW2g_a5WWWWW_l-"
"Bzqj5WWWWWWWWfFucp5WWWaWXi-1u_o6WWWy-W8qhs6WWWWWW4Ynj6WWWaW-Fcjo6WWWy-_7ioa6WWWWW2grl6WWWWW_lVqpY5WWWWWXqVefs6WWWWWX4cki"
"6WWWWW_7Wex5WWWWWYGcaj6WWWWWWeVmaq5WWWWW_7qvg5WWWaWX8egy5WWWy-W8aZu5WWWWW_l-1eyu4WWWWWWWW1mlt5WWWWWWGmcZ6WWWaWXuVqvu5WWW"
"y-_7evm5WWWWWWq_1uXz5WWWWWWScgd5WWWWWWGWmj5WWWWW2uYr5WWWWW_p_1ujX6WWWaWX8uZu6WWWyVwrp6WWWWWW8ggo6WWWWWW4qWx5WWWWW_7ywi5W"
"WWWWW4eXe6WWWaWX4Wn-5WWWy-_7yop5WWWWW2qlx5WWWWW_7Wws5WWWaW1mdZ6WWWyVuy_5WWWWW1myZ6WWW4Wwe6WWWWW_p_4yqf7WWWy--dW2cre7WWWW"
"WXaW1sWk6WWWWW_dW2eps5WWWWWWWW1iqY6WWWaWXeW1Yfq6WWWy-_t-1isx5WWWWWWGaja6WWWWW2mXl6WWWWW_l_pFyjo3WWWaWXeWYGaoi5WWWWWWy-_7"
"W-u6WWWWWWaW1eWd6WWWWWWyVyrw6WWWWWW4qpm6WWWWWW4evz6WWWWW2ovt7WWWy-zZWX8ea-5WWWWW1oxe5WWWWW_l-3gZY5WWWWWXmWy7sjq6WWWWWWWW"
"2ayu6WWWWW1mil6WWWWWWWWj7mWi6WWWWWWu-1g-n6WWWWWW8Wpc6WWWWWWuViwx5WWWWWW8oYu5WWWWW---Dsdc6WWWWW1zlz5WWWWWWu-1ehf6WWWWWW8_"
"ga6WWWWWW8kmk6WWWWW1mqp6WWW4yuw6WWWy-yd-1mof5WWWaWXeW2ebl6WWWy-WeW2suf6WWWWW_l-pFsnk4WWWWWWWX8WuY5WWWWWWWWk7soW6WWWWWWWW"
"-7mZa6WWWWWWWW7eir5WWWaWXe-5nbY6WWWWWWWX8awq6WWWy-_t-1wqW6WWWWWWWWgFinv5WWWWWWWW6jpm5WWWWWWW-3mou4WWWWWYmW4xbz5WWWWW_lW4"
"zfr5WWWWWWWW4Wsx5WWWWWWGeXb6WWWWW2kpl6WWWaW-x_ct1sbm6WWWWWWSxs-6WWWy-W8YWa7WWWWW-d-XGZwy6WWWWWXq-W8mxu6WWWWWW8qgt6WWWWWW"
"4waW6WWWWWWOYrg6WWWWW_-_XGond5WWWWWWGikq4WWWWWWm--Fqil5WWWaWXy-1is_6WWWWWWCqnm6WWWWWWGyac6WWWy-_t-vFidg5WWWWWWWW4xt_4WWW"
"WWWe-3ofw5WWWWWW4chm6WWWWW2vq_6WWWWWWCych6WWWWW_7xXm5WWWWWW8mkX6WWWWWW8cYu5WWWWW2_pX6WWWWW_l_pVans3WWWWWWWWGmtk4WWWaWXeW"
"oFmmg5WWWWWWWWGyra6WWWy--dWoFagy5WWWWW1yzc5WWWWW---Fuhp6WWWWW1XWW6WWWWW_lWqVqfX5WWWWWWW-7cfw4WWWWWWWX8yut5WWWWWWWWilo1ql"
"f5WWWamWi-_7Wfq5WWWWGW-o5WWW_--RoWj6WWW2mbg6WWWy-W8qfs6WWWWW_lVu_r5WWWWWYuVqch6WeWYm_BWux6Wu--lW4mX_6WWW_-WmVuec6WWWaW-F"
"umt6WWWy-W8Ybq6WWWYW-t-3emo6WWW2Yrg6WWWy-_t-1kqx5WWWWWWGWma6WWWWW2qel6WWWaW-p_4Yfj6WWWWm-ZW1mwi6WWWWGYla6WWWy--dW2qXq6WW"
"WWW1ewf6WWWWW_lWq7mZr4WWWWWXu-y7kbh6WWWWWXWW1sXb6WWWWWWOmen6WeWYm_p-2sZk6Wu--lWaW1uiW7WWW_-_7ade6WWWWWXW-9o-p6WWWWm-dWo7"
"icc6WWWWm1cal5WWWWWWOYeb6WWWWW_l-1irY5WWWaWXeW2o-g6WWWy-_7seX6WWWWWWm-1rxr5WWWWWYGsYc6WWWWW--_7bvb6WWWWW1lk-5WWWWW_lW4qd"
"-5WWWWWYu-g7hnk6WWWYW-Fvo-6WWW2olx6WWWy-W8m-v6WWWWWWe-1eri6WWWWm_-VWok6WWWWm1acd6WWWWWWOkjr6WWWWWWyUano6WWWWWWCkem6WWWam"
"-3iwW7WWWyFiqq6WeWYGkcb7Wu-zFe_v6WWW4ucX7WWWWm_Fubj7WWWylW4itx6WeWYmW4kdo7Wu-zl-3ub-6WWWWW1ypb7WWW4szj7WWWy-ydVene5WeWYm"
"WaW1awu6Wu--lWaW1aWY7WWW2air6WWWy-_7Yki6WWWamWyUqaX7WWWWGyn_6WWW_--RuYd7WWW2dgX7WWWWm-3cnf7WWWWGoec7WWWWGYrj7WWW2Wnn7W8k"
"bt7Wu-vl_3aWo6WeWYmW4ofj7Wu-XmW4cXf7WWWy-_dVwi_5WWWWWYGqdm6WWWWWWeVekw6WeWYm_Bvib7WWWWWYGywo7Wu-zl-3YdY7WWWWWWqUfez6WWWW"
"WWCmgu6WWWWW_7ekc6WWWaWX8joX7WWWy-W8Whx6WWWWWW8_z-6WWWWW1qwc7WWW4cyk7WWWWm_p_4_jj7WWWWm1g_p7WWWy-zZW1iZt6WWWWW1ipg6WWWWW"
"--Vwwx6WeWYmW4ghv7WWWWW1ogp7Wu-zl-pV_pv6WWWWWW8lvn6WWWWm_7YYb7WWWaW1zYq7WWWyFog-6WWWWGwmh7WWWWGo_b7WWW4uxk7WWWy-ydW2kgb6"
"WeWYmWaW1iYo7Wu--lWaW1rav7WWW2luj7WWWy-_t-1Wrj6WWWWWYGszc7WWWWW_l-h7Wru3WeWYmWaWX8awr5Wu-zl-hVmn-5WWWWWWW1ixc6WWWWWWm-v7"
"zlk5WWWYWXeW6cXj6WWW2_hp5WWWy-_t-1qdp5WWWWWWGqZz5WWWamWy_s7k_j6WWWWGyai6WWW_--Rxgs6WWW2lio6WWWy-_tVsut5WeWYmWaW1Xy-6Wu--"
"lW4Ykb7WWWYWWWW1xXy6WWW_----3eps6WWW2e_i6WWWWm-ZVkgu6WWWWGqXs6WWWWm-Bgxd7WWWWGynY7WWW_--Fodx6WWW2wjs6WWWWm-3guz6WWWWGoWx"
"6WWWWGorX7WWW2W_a7W8iwf7Wu-zl-Bckc7WWWy-_dVqZz5WWWWWWGejc6WeWYmWqViYZ7WWWWWWGWtg7Wu-zl-3etr6WWWaWXqUx-W7WWWWWWSvd-6WWWy-"
"_7ssl6WWWaWX8qwc7WWWWm-p_4skf7WWWWGz_b7WWW_--xW7ilm7WWW2wxc7WWWy-_t-1kbh6WWWWWWGagv6WWWWWWm-d7ay_4WWWWWWWW4ugu4WWWWWWe-3"
"mlt5WWWWWWOqmZ5WWWWWWGeze5WWWWW2uvl5WWWWW_l-Bews5WWWWWYu-g7_zu6WeWYm_hW2ybs6Wu-z--pVagv6WWWWm1ugl6WWWWW_7edY6WWWWWYGW-r6"
"WeWYm_p-2Yam6Wu-zl-hW1qwg6WWWWWWu_1mcZ6WeWYmWaW1mvc7WWWWWWOuXw6WWWWWWGqz_6WWWWW2gcc7Wu-zl-tUoqW7WWWWWWCcWx6WWWWW_7oaa6WW"
"WWWWGiuj6WWWWW2Yov6WWWWW_7etp6WWWWW2kiW7WWWWm_-_7wdj7WWWWm1tWc7WeWYm_hW3zXh7Wu-XmWe-f7etq6WWWy-WCi_s6WWWaW-Fhsx6WWWy-_7m"
"yi6WWWWW2bZw6WWWWW_lVsqn5WWWWWYuV-Zr6WWWWWWWW1yad6WWWWW_7yky5WWWaWX8_zo6WWWy-W8yjj6WWWWW_l-1qmZ5WWWaWXeW2kWj6WWWy-_7oaa6"
"WWWWWWm-1kht5WWWWWWGWZ-5WWWWW2qje6WWWWW_p_1eXe6WWWaWX8qnY7WWWyVql_6WWWWWW8cZy6WWWWWW4Wzm6WWWWW_7es_5WWWWWW4Wim6WWWaWX4yv"
"s6WWWy-_7qkd6WWWWW2onn6WWWWW_7ikh6WWWaW1irx6WWWyVkzr6WWWWW1qZy6WWW4YxY7WWWWW_p_4Yzi7WWWy-WiW3lp-6WWWWW_dW2aaX6WWWaWXeW2_"
"cd7WWWy-_t-1Yhe6WWWWWWGetp6WWWWW2hyW7WWWam_x_c7umt6WWWWGWor6WWWy-WCefw6WWWYW-FshZ7WWW2qr_6WWWy-_7mgm6WWWWW2ag_6WWWWW_lVe"
"cv5WWWWWYuVuXu6WeWYm_Be-Y7Wu--lW4arg7WWW_l-lVuvw6WWWWm1ucm6WWWWW_7mcb6WWWaWX8ye-6WWWy-W8Wzu6WWWWWWyUi__6WWWWWWC_yx6WWWam"
"-3ygl7WWWyFWWX7WeWYGugq7Wu-zFeld7WWW4yyl7WWWy-y3meg6WeWYmW4alg7Wu--lW4iwi7WWW2ehc7WWWWm-3aXl7WWWWGeih7WWWWGoXp7WWW2mgt7W"
"8uWz7Wu-vlW4qw-6WeWYmW4scu7Wu-zl-3kka7WWWWW1ioh7WWW4o_p7WWWy-ydVeze5WeWYmWaW1Wrv6Wu--lWaW1iuZ7WWW2ufs6WWWy-_7iuj6WWWamWy"
"Uieb7WWWWG_lY7WWW_--Rkaf7WWW2m_Y7WWWWm-3yvh7WWWWGqhe7WWWWGmam7WWW2mzp7W8qnv7Wu-vl_3etp6WeWYmW4ywl7Wu-XmW4mqh7WWWy-_dVWZ-"
"5WWWWWWGWid6WWWWW2Whn6WWWWWWeVan-6WeWYm_Ba-c7WWWWWWGuui7WWWWW2qgr7Wu-zlz3mvt6WWWWW2u-a7WWWaW-pUiYc7WWWyVosY7WWWWWWCkmy6W"
"WWWW_7qkd6WWWaWX8oeZ7WWWy-_7udn6WWWWW2mdz6WWWWW_7Wor6WWWaW1mWf7WWWyVmfY7WWWWW1Wnf7WWW4uln7WWWWmzpUW_g7WWWWGezd7WWWyVi_a7"
"WWWWWWCygX7WWWam-3uWs7WWWyFyxc7WeWYGsZx7Wu-zFeZk7WWW4Wrs7WWWy-y3ikh6WeWYmW4yii7Wu--lW4_nl7WWW2eie7WWWWm-3sZo7WWWWGwck7WW"
"WWGgjs7WWW2upw7W8wfW8Wu-vl_3Wor6WWWWW2qZY7WeWYm_3Wqo7WWWWW2epx7Wu-zlz3eXw6WWWaW1imk7WWWyVwkd7WWWWW1WYl7WWW4ijt7WWWy-y3Wm"
"y6WeWYGWwr7Wu-1mrr7WWWWGmkn7WWWWGmyv7WWW2Wk_7W8mZa8Wu-vFmdg7WeWYGWW-7Wu-zFmWo7WWW4eow7WWWyFmms7WeW2mZa8Wu-1md-7WWW2Wka8W"
"8u-f8Wu-z-yl_3yfo7WWWWGmik7WWWyl-hW3ejl7WWWWm1_md7WWWWWWqVWym7WWWWWWCgci7WWWam-3mnb8WWWyFmlp7WeWYG_rh8Wu-zFyyx7WWW4ubc8W"
"WWy-yZW1icc6WeWYmWaW1uop7Wu--lWaW1yyx7WWW2cil7WWWWm-ZVwmt7WWWWGkkp7WWW_--Rysz7WWW2weq7WWWWm-3qZX8WWWWGY-x7WWWWGydc8WWW2y"
"ah8W8mco8Wu-vl_pVWok6WWWWWWGuvw6WWWWW2eue7WeWYm_pVasu7WWWWWWGaZX8WWWWW2uoi8Wu-zl-ZVYki7WWWWW_7ano6WWWaWX8ijq7WWWy-_7i__6"
"WWWWW2umj7WWWWW_7i_a7WWWaW1iqy7WWWyVarq7WWWWW1quz7WWW4std8WWWy-yd_n7Was3WeWYmWaWX8yvq5Wu----ZWX8mis6WWW2mam6WWWWGajo5WWW"
"WWWy-m7g_j6WWWWm-3jbk6WWWWGipd6WWWy-WWW2lnu6WWWaW-x-Buvv6WWWWm-ZW1-Zu6WWWWGkxg6WWWWWWyVqmx6WWWWm-3cox6WWWWGq_o6WWWWm-3ei"
"X7WWWWGiq_6WWWWGkua7WWW2Wje7W8Wjj7Wu-zl1yov7WWW_-zx-6xWf7WWW2uhw6WWWy-_t-1WZu5WWWWWXmWu7Wuf6WWWWW1muk5WWWWW_l-3mre5WWWWW"
"XmWk7oYm6WWWWW1-xf6WWWWW---Dvrx6WeWYmWaW1kb-7WWWWW1igf7Wu-zl_xVrbW7WWWWW1yzq6WeWYm_p-2uzz6Wu-zlXiWg7t_m6WWWWWWu-1sns6WWW"
"WW-7iat6WWWWWXuVuad6WWWWm_7iZt6WWWWm1YrY6WWWWW---DZwm6WWWWW1eWc6WWWWWWu-1_yp6WWWWm_7aWY7WWWWm1uvj6WWWWm_7Wjh7WWWaW1u_v7W"
"WWyFk-u6WWWWGeen7WWWWGil_6WWW4_ub7WWWy-yd-1yvm5WWWaWXeW2oow6WWWy-WeW2uzq6WWWWWWWWd7WXq6WWWWWWu-1_pv6WWWWWWWW1qqm6WWWWWW8"
"mjh6WWWWWWuVm_y6WWWam-3owm7WWWyFahc7WeWYGovw7Wu-XGflr7WWWy-_3e-q6WeWYmW4sns7Wu-zF_zi7WWWWW-3loY7WWWWW1ebf7WWW4m-n7WWWWmz"
"p-3ffn7WWWWGuqj7WWWy-WiW2png7WWWWWWqVark7WWWWWWCbyc7WWWam-p-4cmr7WWWWm1eb-7WWWy-zZW1vzz6WWWWW1c-k6WWWWW--Vlza7WeWYmW4aya"
"8WWWWW1elx7Wu-zl-pVYdX7WWWWWW8eeu6WWWWm_7ghl7WWWaW1zg-7WWWyF_Yd7WWWWGyas7WWWWGg-j7WWW4fct7WWWy-_lVahc7WWWam-3_wx7WWWyFWe"
"n7WeWYGkmd8Wu-XGWxX8WWWy-_3yly6WeWYmW4e-X8Wu-zFkku7WWWam_3gvX8WWWyFmji7WWWWW1Wrp7WWW4ifz7WWWWm_3yyb8WWWyFadq7WeWYGuXi8Wu"
"-zFmfy7WWW4coc8WWWyFmhW8WeW2mYn8Wu-1qXh8WWW2Wln8W8ipu8Wu-vlyZVmbr5WeWYmWaW1Wua7Wu--lWaW1e_o7WWW2geX7WWWWWWyVqfq7WWWWWW4g"
"kb7WWWWm-3ahy7WWWWGa_t7WWWWGiuW8WWW2Wrb8W8qxi8Wu-vlWaW1yox6WeWYmWaW1kZd8Wu-zl-pVqkg7WWWWWW8wt-6WWWWWW8com7WWWWW1ifu7WWW4"
"giY8WWWy-yd-n7gpp4WWWWWWWX8mpe5WWWWWWWWk7_ef6WeWYmWa-AYyj6WWWWWWWX8qsY7Wu-zl-x-o7tdX6WWWYWXe-5oyZ7WWW2tqg6WWW_---W8ios7W"
"WW2se-6WWWy-_t-1cah6WWWYWXeWh7Yzw7WWW2bmo7WWWWm-Z-3xzi7WWWWGZjf7WWW_--RYwn7WWW2iXg7WWWy-_tVuec6WeWYmWaW1jvo7Wu-XmWeV_vn7"
"WWWWWWSesk7WWWWWWy_2jje7WWWWm-ZW1okc7WWW_Fopc7WWW2-cq6WWWWWWyVYWg7WWWWm-3zzf7WWW_Fxcg7WWW2suz6WWWWm-3kin7WWWWGvrj7WWWWGs"
"hr7WWW2Yyv7W8elW8Wu-xl-xW7ipx7WWW2zpk7WWWWm-ZVmst7WWWWGqmp7WWW_--Rqzz7WWW2edq7WWWWm-3gsX8WWWWGYmy7WWWWGevc8WWW2anh8W8kpo"
"8Wu-vl_pVegn6WeWYmWaW1edz7Wu-XmWaW1mvu7WWWy-_t-d7zhc6WWWWWWWW6maw5WWWWWWW-3yb_4WWWWWYmW4mjb6WWWWW_lW4yez5WWWWWWWW4eka6WW"
"WWWWGulk6WWWWW2utv6WWWWW_l-f7boi6WeWYmWaW1rWt7WWWWWWWW6ghk7Wu-zl-xVhnk6WWWWWWGefw6WWWWW2vbe7WeWYm_p_2qpt6WWWWWYmW4xax7Wu"
"-zl-xVpnx6WeWYm_pW3wro7WWWWWWWW4gqu7WWWWWWGqoX8WWWWW2qYj8Wu-zlzhVyhr6WWWWWWGeoY7WWWWW2avn7WWWWW_l-d7ckf6WWWWWYuVsrc7WWWW"
"W_7gon6WWWaWX8apo7WWWy-W8Zlh7WWWaW-t-3vlk7WWWy-_7fez6WWWWWWmVzxY6WWWWWYuVwtg7WWWWWWWW1raZ7WWWWW_7ynh6WWWaWX8hng7WWWy-_7_"
"_s6WWWWW2hYa7WWWWW_l_1aqZ5WWWaWXeW2yfq6WWWWWWWW1yaX7WWWy--dW1snz6WWWWW1Yyk6WWWWW--V_af7WWWWWXuVdyW7WWWWWW8mfu6WWWWWW8hyc"
"7WWWWW1qrj7WWW4kys7WWWy-ydW2yjb6WWWaWXeW2yqk7WWWy-_t-1lfk6WWWWWWGwkw6WWWWW2wce7WWWWWWe-1qpi7WWWWW_7Wio6WWWaWX8ulq7WWWy-_"
"7ed-6WWWWW2gpj7WWWWW_7ivb7WWWaW1qdz7WWWyVigr7WWWWW1uh_7WWW4qge8WWWWmzp_ad1uzo6WWWWGgqm6WWW_--Rhxd7WWW2cgY7WWWy-W8cre7WWW"
"WW-d-XGwYW7WWWWWXq-W8fX_6WWWWWW8sux6WWWWm_3ar_6WWWWm1xih6WWWWWWOaZy6WWWWWWe-y7YdX7WWWYW-Fupl7WWW2Xyf7WWWy-W8uWg7WWWWWWe-"
"1so_6WWWWWWqVnWX7WWWWm_BYnX7WWWWm1fer6WWWWWWOceZ7WWWWWWyUwtc7WWWWWWCxeZ7WWWam-3r_u7WWWyFy-e7WeWYGeq_7Wu-zFsbm7WWW4lkv7WW"
"WWm_FkkY8WWWylW4sai7WeWYmW4uoe8Wu-zl-3uXn7WWWWW1efv7WWW4zfZ8WWWy-yt_W8qom5WWWWWWGsqw4WeWYmWq-W8Xgd7WWWWWWG_oq6Wu-zl-h-_7"
"jbx5WWWYWXy-1xxf7WWW2h_Y7WWW_--7--s7WWWYWW4wkZ7WWW_--Fppe7WWW2nin6WWWWm-Z-u7-az6WWWWGoww6WWW_--RhWh7WWW2ifb7WWWy-_d-4gdW"
"6WeWYmWaW1mzk7Wu-XWW4duu7WWW_lWqVdXh7WWW2iqb7WWWWWWCYwg7WWW_--FWqh7WWW2xjx6WWWWm-ZVwgj7WWWWGsbg7WWWWm-Bftx7WWWWGv_p7WWWW"
"m-3xzz7WWWWGwcv7WWWWGrtY8WWW2ird8W8ypk8Wu-xl-Bq-n7WWW2Wmg7WWWWm-3gYr7WWWWGyum7WWWWGwyv7WWW2gb_7W8rqa8Wu-zl-Bqiv7WWWy-_d-"
"u7gop5WWWWWWWW4Ycc5WWWWWWe-3yzd6WWWWWW4efs6WWWWW2eob7WWWWWWCq-y6WWWWW_7kov5WWWWWW8srm6WWWWWW8WcY6WWWWW2eki6WeWYm_p-u7kZg"
"7WWWWWWWW4py_6Wu-zl-Z-2Ynj6WWWWWYGn-Z7WWWWW_Fi_s6WeWYmWaVavu7WWWWWYGb-e8WWWWW_7pyk7WWWWWW8ah_7WWWWWW8gqr7WWWWW2pv-7Wu-zl"
"zh-s7tmy5WWWWWYi-1yeb7WWWWWW8exY7WWWWWW4bgr6WWWWW_7cyf6WWWWWW4kzv6WWWaWX4hec7WWWy-W8bb-6WWWWW_l-1ayh5WWWaWXi-1rfg7WWWWWW"
"S_nx6WWWy-_7ikp6WWWWWYy_1dXg7WWWWWWCiq-6WWWWW_7_sY6WWWWWWGmrh6WWWWW2sgs6WWWWW_p_1wrp6WWWaWX8i_p7WWWyVi_l7WWWWWW8dni7WWWW"
"WW4yzZ7WWWWWW4orn7WWWWW1mcw7WWW4oYa8WWWy-y3uki6WWWWWW4ql_6WWWaWX4xXh7WWWWWW4ouv7WWWy-_3gwt6WWWWW2ena7WWWWW_3osY7WWWWW2_a"
"o7WWWWW_3Yoy6WWWaW1_sn7WWWyVljg7WWWWW1kpo7WWW4Ypx7WWWy-yd_nFWtw3WWWWWWWWGmro4WeWYmWaWn7qdp5WWWWWWWWGupj6Wu----ZWn7upq6WW"
"W2iuj6WWWWGeym5WWW_l---Fifg7WWW2anc7WWWWGWug6WWWWWWy-k7mXr6WWWWm-3Wcq6WWWWGqXl6WWWWWWWW1mss5WWWWWWyVi-v6WWWWm-3ynv6WWWWG"
"iln6WWWWm-3ef-6WWWWGu_y6WWWWGqpY7WWW2Wac7W8mXh7Wu-zl1W-s7WWWWW_t-DWhh7WWWWm-ZW1gjf7WWWWGetr6WWWWWWyVWfj7WWWWm-3smj7WWWWG"
"alW7WWWWm-3avq7WWWWGivm7WWWWGzzu7WWW2qlz7W8epZ8Wu-zl1lbh8WWWy-zZWn7e-d6WWWWW1ygj5WWWWW---F-zz6WWWWW1kac6WWWWW---l7Yfj6We"
"WYmWaW1ihy7WWWWW1Wad7Wu-zl_x-Ecic7WeWYmWaW1enn8WWWWW1Yi_7Wu-z-zx-i7Wkx6WWWWm1nwe6WWWWW---1kef6WWWWW1wap5WWWWWWu-1foo6WWW"
"Wm_7sYX7WWWWm1pni6WWWWm_7ekf7WWWaW1oht7WWWyFqit6WWWWG_Wl7WWWWGeqy6WWW4utZ7WWWy-zt-DymW7WWWWW1fqm6WWWWWWu-1xea7WWWWm_7a_k"
"7WWWWm1gYx6WWWWm_7uXw7WWWaW1-nh8WWWyFacg7WWWWGbhX8WWWWGYfn7WWW4vcw7WWWy-ydWoFaod5WWWWWWW-7su_4WWWWWWWX8ysz5WeWYmWaWn7iWX"
"7WWWWWWW-7oyu6WWWWWWWX8ujr7Wu--lWaWn7aZq7WWW2kqz6WWW_---_7tnl7WWW2vqr6WWW_---W8hmd8WWW2hnn7WWWy-_t-fFWkz5WWWWWWWW4uhj5WW"
"WWWWWW4aYa6WWWWWWGeij6WWWWW2qiu6WWWWW_l_3Wxa5WWWWWYmW4wfm6WWWWW_lW4mcd6WWWWWWWW4gWn6WWWWWWGahz6WWWWW2cYh7WWWWW_l_p-q1m--"
"1WWWWWWWWm-3Wuk2WeWYmWaWney1qbd4WWWWWWWWm-3ydp4Wu-XWWWWX8cZx5WWWWGcuq5WWW_l-ZWmWy1azo5WWW2wtb5WWWWGqfb4WWWy-_t-rFsgm4WWW"
"WWWWWGghw4WWWYmWeWgl3qyw5WWW2YXp5WWWWGi_m4WWWyl---XGugd6WWWWm1-pk5WWWaW-x-_tt1yeb5WWWWm-3klb5WWWWGa_X5WWWWWWy-D_iq5WWWWm"
"-ZW1cvp5WWWWGaij5WWWy-WWWqForW6WWWWWWy--7kiW6WWWam_ZWiOZai6WWWWmWy-_7Yzi6WWW_--ZW1svh6WWW2rlw5WWWy-_--vFysx5WWWWWWu-3urr"
"4WWWYmWeWYm1agu5WWW2yjq5WWWWGWeY5WWWWWWy-m7Wsr5WWWWm-3e_r5WWWWGagn5WWWWm---5unl6WWWWmWyViqk6WWW_--3_il6WWW2oda6WWWWWWy-6"
"mcx5WWWWm-ZW1kxv5WWWWGWon5WWWWWWyVyxy5WWWWm-3_ty5WWWWGilt5WWWWm-3ecX6WWWWGyo-5WWWWGssZ6WWW2mgc6W8uxf6Wu-zl1Ws-6WWW_-zx-6"
"sho6WWW2wff6WWWy-_t-j7squ4WWWWWWWWGqaa5WeWYmWaWn7qkl6WWWWWWWWGias6Wu-zlXaWi7irl6WWWam_--3iXW7WWWWmWWW1m-h6WWWy-WWW2jas6W"
"WWaW---DYro6WWW_----eVhre6WWW2quX6WWW_----Egak6WWW2vhz5WWW_----7yex6WWW2aif6WWWy-_t-rFWWt4WWWWWWWW8cwe5WWWWWWWW4Wrl5WWWa"
"WXeWbd1__t5WWWWm-x-W8wiy5WWWWGcjr5WWW_l-3yey5WWW2urt5WWWWGmnz4WWWWWWy-_7Wkz5WWWWm-3ksz5WWWWG_pu5WWWWm--Vkhw5WWWWGyxd5WWW"
"WWWyVcoX6WWWWm-3kcY6WWWWGkXx5WWWWm-3iyc6WWWWGyda6WWWWGsYg6WWW2Wmj6W8mdo6Wu-zl1Woc7WWWy-zt-W8pdi6WWWWWX4qyw5WWWWWWWWW8Yfb"
"6WeWYmWaW1mbl7Wu-zl-x-_7kZ_5WWWWWWy-1jas6WWWam-7k-f7WWWWm1cig7WWW_-z--ZW1wYc7WWW2gf_6WWWy-_x-XGokf6WWWWWW4mWu6WWWWW2Wbh7"
"WWWYm_x-bm1udm6WWW2xpj6WWWWGmqx5WWWy-_t-zlr1uxx3WWWWWXmWaW3wvX5WWWWW1qrY4WWWWW_l-xVinW4WWWWWWWW8amj4WWWWWXmWi-2cyi5WWWWW"
"1amj4WWWWW_--ZW1mjY5WWWWWYWW_ts1soy5WWWWW---D-Yi6WWWWWWWWoFtr-5WWWWWXq--7qd-5WWWWm_B_lW6WWWWGyph5WWWWW1ooe5WWWWW---Dvw-5"
"WWWWW1Wur5WeWYm_p-yNemz5Wu-zlWiWZ8bsn6WWWWWWWWWm2iW_5WWWWWWWWo7sff6WWWWWWWW4Wnw6WeWYmWaWBkea7WWWWW1kWd6Wu-zl_xVcWq6WWWWW"
"XWWj7Wve6WWWWW---1_gk6WWWWWWWW1lcY6WWWWW1Waz5WWWWWWWW6mrc6WWWWW---7vWe6WWWWW1Yav5WWWWW---1quh6WWWWW1aoa6WWWWWWWW6khj6WeW"
"Ym_p-qNugW6WWWWWWWW8uqi6Wu-zl-x-Y8uun5WWWWWYmWgFiwc6WWWWWWWWyl1uxw5WWWWW---XGWtv5WeWYmWaWX8ipi7WWWWW1Yjk6Wu-zl-l-y7cWl6W"
"WWWm_Bwjl6WWWWm1hby5WWWWW---1nzz5WWWWW1mvc5WWWWWWq-1-up6WWWWm_BWsq6WWWWGnec6WWWWW1fn-5WWWWW-3emy6WWWWGayd7WWWWG_Xu6WWWWW"
"1moY7WeWYmz--YOopY7Wu-zl-x-_7cZx5WWWYWXaW2Wx_7WWW_--x-fm2fmq6WWWWWXWWltp1soW6WWWWWWu-1g-Z6WWWWm_dW1mZa6WWWWm1ezt5WWWWW--"
"-Dzeb6WWWWW1lzy5WWWWWWu-nFjbx5WWWWW-7ugx5WWWWW1rhr5WWWWW---Doab6WWWWWXu-n7wuW5WWWWm_7ouy5WWWWm1om_4WWWWm_--Dxib6WWWWGnmk"
"5WWWWW1Zmf5WWWWW_l-xFqpc4WWWWWWmWw7rzX6WWWamWu-7uWx6WWWWmWWWW8gjw5WWWy--dW2sba6WWWWWXWWWGuwr5WWWWW-----1mwl5WWWWW1iW-4WW"
"WWm_--kFchm6WWWWm1stZ6WWWWWWu-1yzd6WWWWW-7aje6WWWWW1ke-5WWWWWWuVslm5WWWWm_7WXf6WWWWm1_hj5WWWWWWu-5Wfd6WWWWWW8_f-5WWWWm_-"
"-7Wzf6WWWWGsvq5WWWWW1Yvj5WWWWWWu-1uit5WWWWm_7ozk6WWWWm1wmp5WWWWm_7eZs6WWWaW1miW7WWWyFumx5WWWWG_pv6WWWWGuk-5WWW4yka6WWWy-"
"_t-5ela6WWWWW_l-pFmvh4WWWWWWWW8eut4WWWaWXeWhFcWi6WWWWWWWWFagz5WWWWWWWW8qnf6WWWy-_t-1wek5WWWWWYmWdFYok6WWWWWWWW3hYz5WWWWW"
"WWWEowu5WWWWW_l-3prb5WWWWWYmW4wja6WWWWWWWWcl1own5WWWWWWWWX8h_l6WWWWm_t-W8kog6WWWWm1nzl5WWWWW-7Xon5WWWWW1qYw4WWWWm_--zFaw"
"j6WWWWm1aap5WWWWm_--1ilZ6WWWWGodq5WWWWW1_ia5WWWWWWu-1oix5WWWWm_7Yjp6WWWWm1qus5WWWWm_7yuw6WWWaW1qWe7WWWyFin-5WWWWGqe-6WWW"
"WGiva6WWW4Wkh6WWWy-yt-XG-pk5WWWWWWWWWGgZv5WWWaWXeW2Wa-6WWWy-WWWYGrhu6WWWWW-t-dW2mhd6WWWWW1mpt5WWWWW_l-xVkfs4WWWWWWWW8opd"
"5WWWWWYmWhto1iqY6WWWWWWu-1Yqb6WWWWWWeW1jxz5WWWWW---Dubk6WWWWW1sca6WWWWWWu-nFtdX6WWWWW-7--W6WWWWW1ahw5WWWWW---Dnhj6WWWWWX"
"q-n7aaX6WWWWWW4ayh5WWWWm_7eWY6WWWWm1Ydf5WWWWW---De_W6WWWWW1lmw5WWWWWWWWl7Wbb6WWWWWWu-1Yhe6WWWWW-7-le6WWWWWXuVzxY6WWWWWW8"
"wn_5WWWWWWuVynh6WWWam-3Wix6WWWyFWio6WeWYGkgY7Wu-XGsb_6WWWy-_3uhc6WeWYmW4Ww-6Wu-zFymt6WWWam_3qe_6WWWyFo_l6WWWWW1acr6WWW4m"
"ay6WWWy-_--5vhX7WWWWWWqVlza7WWWWWWCrf-6WWWam-p-4Wta7WWWWm1hng7WWWy-zZW1yvm6WWWWW1iXb6WWWWW--Vprr6WeWYmW4rfl7WWWWW1svf7Wu"
"-zl-pVikp6WWWWWW8jki6WWWWm_7iuz6WWWaW1jyg7WWWyFXfu6WWWWGkcZ7WWWWGca_6WWW4w_b7WWWy-_t-5uyq6WWWWW_l-p7Ygi4WWWWWWmWw7ahd6We"
"WYmWq-6szd6Wu-XWWaW1omz6WWWWmWy-_7Wb_6WWW_--ZW1_iy6WWW2aqa6WWWy--dW2-up6WWWam-x-s7_hX7WWWWGwp_6WWWWm-Bwdr7WWWWGeyk7WWWWW"
"Wq-2yii7WWWWWWu-2vyW7WWWWm-ZW1Yu_6WWW_Fsn-6WWW2iXl6WWWWWWyVhkY7WWWWm-3cgY7WWW_FinY7WWW2ojt6WWWWm-3snf7WWWWGbcc7WWWWGypj7"
"WWW2azn7W8uku7Wu-vl-ZW1Zwy6WWWWWWWW1-qZ7WeWYmW4YzY8Wu-XWWaW1-gz7WWWylWu-z7wm-5WWWWWWy-v7ari7WWWWWWCYqb7WeWYmWy-6inp7Wu-z"
"l-pVwYW7WWWWWW8szq6WWWWm_7ulj7WWWWm1qyb7WWWWGtjq7WWWWm-p-t7uWg7WWWWWW8ead7WWWWWW4iuu6WWWaWXq-4Wgz7WWWy-zZW1sms6WWWWW1-zf"
"6WWWWW--VdcW7WWWWWXuV-vv6WWWWWW8gYo6WWWWWW8nu-6WWWWW1Ylc7WWW4gll7WWWy-_l-kd1hoo6WWWam_--3sYX7WWWWmWyVos-6WWW_--3ZXW7WWW2"
"gem6WWWy-WWW2jgz6WWWam-ZW7gux6WWWWm1ixh7WWW_-zx-6fya7WWW2ypt6WWWy--dWw7YvY6WWWWW1mlf5WWWWW---n7nyg6WWWWW1aXb6WWWWW---DXY"
"o6WeWYmWaW1gym7WWWWW1_dW7Wu-zl_xVgns6WWWWW1ovi6WWWWWWWWj7nlh6WWWWWWu-1srm6WWWWW-7pwm6WWWWWXuV_sY6WWWWm_7-Zn6WWWWm1Zk_5WW"
"WWWWu-5aYt6WWWWWW8Wzg6WWWWW---7Xjf6WWWWW1WW-5WWWWWWu-1uki6WWWWm_7k-t6WWWWm1wsc6WWWWm_7ekW7WWWaW1isi7WWWyFgdn6WWWWGqWb7WW"
"WWGqes6WWW4Y-y6WWWy-_t-5jfo6WWWWWWWWd7mrk6WWWWWWu-1etp6WWWWW-7stp6WWWWWXuVmrh6WWWWWW8mwc6WWWWWWuV__s6WWWam-3yse7WWWyFed-"
"6WeWYGgbn7Wu-XGeli7WWWy-_3uvl6WeWYmW4Ytj7Wu-zFoya7WWWam_3wqi7WWWyFovx6WWWWW1utX7WWW4usf7WWWWm_p-3sps7WWWWWWCot-7WWWylWmV"
"ar_6WWWWWW8ecm6WWWWWWuVYYb7WeWYmW4slb8WWWWWW8cty7Wu-zl-3cXh7WWWWWWmVYnX7WWWWWW4ghl7WWWaW1W_-7WWWy-_3mnu6WWWWWX4ors7WWWWW"
"-3ard7WWWWW1Wvk7WWW4qcu7WWWWm_p-4iXf7WWWWm1cqm7WWWy-zZW1epq6WWWWW1ibd6WWWWW--VWWx6WeWYmW4inr7WWWWW1aak7Wu-zl-pVgwt6WWWWW"
"W8kam6WWWWm_7u_Z7WWWaW1sZn7WWWyFsyy6WWWWGyef7WWWWGmrY7WWW4ijg7WWWy-_lVYoy6WWWam-3csk7WWWyFivb7WeWYGmWu7Wu-XG_cp7WWWy-_3i"
"eq6WeWYmW4_up7Wu-zFumh7WWWam_3yjp7WWWyFssX7WWWWW1ysd7WWW4Yvl7WWWWm_3uXt7WWWyFupe7WeWYGk-x7Wu-zFeal7WWW4ykt7WWWyFaco7WeW2"
"ys-7Wu-1qxw7WWW2iXW8W8_ob8Wu-z-zl-3uzx7WWWylWaW1uuu6WeWYmWaW1sYY8Wu-zl-pVwtc7WWWWWW8eqy6WWWWWW8yxi7WWWWW1iWq7WWW4Yoz7WWW"
"y-yd-n7eun4WWWWWWWW8yez4WeWYmWaWv7_Yh6WWWWWWWW8qgs6Wu--lWaWg7Xft6WWW2qZl6WWW_----Ejn-6WWW2wxd6WWW_----7iah7WWW2u-o6WWWy-"
"_t-1aZs5WWWaWXaWd7Ypt6WWWWm-3kvt6WWWWGkmm6WWWWmWaW4bhr7WWWWW---3jdn7WWWWGwjj7WWWWWWWW3yms7WWWWWWu-2wla7WWWWm-ZW1tXY7WWWW"
"Gkpm6WWWWWWyVmec7WWWWm-3w_b7WWWWGosw6WWWWm-3gcj7WWWWGgWg7WWWWGXan7WWW2ugr7W8ysx7Wu-xl-x-6mkk7WWW2czz6WWWWWWyVeYm7WWWWm-3"
"uvl7WWW_FuWm7WWW2idY7WWWWm-3wtt7WWWWGqwp7WWWWGcXy7WWW2ypW8W8gld8Wu-vl_pVu_w5WeWYmWaW1qXf7Wu-XmWaW1Wnb7WWWy-WeWb7aYq6WWWW"
"WWWW3iZg6WWWWWWWWEiyY6WWWWW_l-3_ji5WWWWWYmW4apj6WWWWWWWWg7cXl6WeWYmWaW1kfx7WWWWWWWWEuys7Wu-zl-xVniu6WeWYm_p-2_jX7WWWWWYm"
"W4cYY8Wu-zl-xVey-6WWWWWWWWb7Wft6WWWWWWu-1fX_6WWWWW-7hzz6WWWWWXuVynm6WWWWWW8enh6WWWWWWuVnWX7WWWWWW8jau6WWWWWW8esc7WWWWW1c"
"pj7WWW4dvs7WWWy-_--5dYl7WWWWWWWW1ipc7WWWWW-t-5yZw6WWWWW1woh6WWWWW--Vfgb7WWWWWXuVgrz6WWWWWW8bir6WWWWWW8ypZ7WWWWW1aZg7WWW4"
"pyo7WWWy-yd-1Wzo5WWWaWXeW2cY_6WWWy-WeW2gku6WWWWWWu-1Yoc7WWWWWW8gty6WWWWWW8iui7WWWWW1uZq7WWW4sqz7WWWy-_t-ZVhby5WWWWWWWWW8"
"rqc6WWWam-xVWds6WWWWm1oth7WWWy-_3qWp6WeWYmW4kko7Wu-XW-3sbh7WWWWm1coj7WWWy-zh-W8Zvk6WWWWWX4ugx5WWWWW-7d-x5WWWWW1kjW5WWWWW"
"Wu--7bvb6WWWWW-7dnc6WeWYmXyVakm7WWWWW-7ion7WWWWW1iqw6Wu-zl_3ew-6WWWWW2gwb7WWWWW-h-y7bon6WWWWm_Bg-n6WWWWm1_kz5WWWWWWu-1on"
"_5WWWWW-7W-_5WWWWW1gWi5WWWWWWq-1aYt6WWWWWW4mtc6WWWam-3gij7WWWyFsnz6WWWWG_af7WWWaGjth7WWWylz3cnt6WWWWm1_-W6WWWWWW4Wcx6WWW"
"WW1pvZ7WWWWmz3_f-6WWWaW1uyi7WWWyFrbh6WWWWGefa7WWWWGWmm6WWW4iht6WWWy-_l-w7aaq6WWWWWWeW1uad6WWWam-xVilW7WWWWm1uvk7WWWy-_3_"
"yp6WeWYmW4ktp7Wu-zFqkg7WWWam_3Ypk7WWWyFdyW7WWWaW1wzk7WWWy-ztVkyd6WWWWW1atn5WWWWWWuV-vv6WWWWW-7Xzv6WeWYmW4akq7WWWWW1iWb7W"
"u-zl-3eg_6WWWWW1_Xd7WWWWW-lVynm6WWWWWW8asg6WWWWm_7avX7WWWaW1wrl7WWWyFmYr6WWWWGycd7WWWWGyjw6WWW4mlX7WWWy-_lVgrz6WWWam-3jX"
"n7WWWyFYoc7WeWYGZWx7Wu-XGerr7WWWy-_3kdr6WeWYmW4dis7Wu-zFffj7WWWam_3uvr7WWWyFuwY7WWWWW1Ymf7WWW4twn7WWWWm_3mZv7WWWyFWXf7We"
"WYGwp_7Wu-zFqkm7WWW4Wlv7WWWyFixp7WeW2iYZ8Wu-1klz7WWW2qhZ8W8Yzf8Wu-vlyp-W8cuq5WeWYmWaWX8YZk7Wu-zl-x-_7bjW6WWWYWXy-1ptn7WW"
"W2lrf7WWW_--7s-W8WWWYWW4kYg7WWWWm-p-u7eg-6WWWWGmoy6WWWy-_ZW5abc6WeWYmWaW1iYu7Wu-XWW4iaZ8WWW_lWqVvxo7WWW2Wvi7WWWWWWCorp7W"
"WWWm-pVz_q7WWWWGoZn7WWWWm-Bwac8WWWWGhzy7WWWWm-3qcf8WWWWGmpZ8WWWWGcjk8WWW2qaq8W8qvx8Wu-vlWm-W8axi7WWWWWWCcYZ7WWWWWWWWW8ty"
"h7WeWYmWaW1zYr8Wu-zl-l-u7jje7WWWWWW8_ub7WWWWWW4zat6WWWaW-p-3m-o7WWWy-WWW2Xso7WWWWWWCvXc7WWWWWWq-1duu7WWWWWW8ntq7WWWWWW4w"
"cg7WWWWWW4cXx7WWWWW1oja8WWW4jjl8WWWWm_l-ae1ahn7WWWWm1hiW8WWWy-zZWX8hfu6WWWWW1ymX6WWWWW----7hb-6WeWYmWaW1_jc8WWWWW1qts7Wu"
"-zl-p-m7oom6WWWWm_7wg_6WWWWm1cpg6WWWWW---Dnqw6WWWWW1bYh6WWWWWWu-1si_6WWWWm_7Yjd7WWWWm1apr6WWWWm_7Wvn7WWWaW1qeX8WWWyFtzZ7"
"WWWWGZzt7WWWWGung7WWW4vwo7WWWy-yd-vFWcy4WWWWWWWW8kxi5WeWYmWaWv7W_q6WWWWWWWW8uWa7Wu--lWaWv7qlf7WWW2etn6WWW_----7vXv7WWW2k"
"rW7WWWy-WeWwFsui6WWWWW_l-3_iq5WWWWWYmW4cbx6WWWWW_l-p-o1ixi3WWWWWWWWWW2efX3WWWWWWWWq-1Wnc4WWWWWWWWCqpn3WWWWWWWW8WZu3WWWWW"
"WW1qt_3WWWWWWW-d-1ug_2WWWWWWWXeW2iud4WWWWWWW-dW2qt_3WWWWWWWXylr1nru5WWWWWWW-Bixa5WWWWWWW1iyt5WeWYmWa-uNaYm5Wu-zl-xWx7eYr"
"5WWWWWWW-7mdd5WeWYmWaWzt1ina5WWWWWWWWq-1Wqd6WWWWWWWWCeZq5WWWWWWWW8Wcw5WWWWWWW1arY6Wu-zl-x_g7ah_4WWWWWWWX8wW_5WWWWWWW-7ij"
"h5WWWWWWWW8acm5WWWWWWW1yha6WWWWWWWWgFXea6WeWYmWa-wd1u_-4Wu-XWWWWX8gnd6WeW_---Wdu1iZe6WWWWWWW-dW2qj_5Wu--lWaWolq1mnm5WWW2"
"mei5WWW_----EXWc6WWW2eaw5WWWy-_tWwNuXq5WWWYWXe-bW1_uh6WWW2ajj5WWWy-_--vFgmq5WWWWWWOcwY5WWWWWWW-3yip4WWWWWWWX8f-j5WWWYWXe"
"-vl1iXZ6WWW2keY5WWWy-_t-bGbi-4WWWWWWWWiVwrq4WWWYWXeW-FaYm6WWW2eaa6WWW_----1uxa7WWWYWWWW1yka6WWW_----Bqyl6WWW2skn5WWW_---"
"-7mpr6WWW2amt5WWW_--Ve-z6WWW2kYW6WWWy-_t-hFq-_5WWWWWWWW6vyq5WWWWWWW-3_xq4WWWWWWWW8qpY5WWWWWWW1Yun5WWWWWWW-3qvg5WWWWWWW1Y"
"by5WWWaWXe-ad1oaX6WWW_----W8m_-5WWW2erz4WWW_----W8kej6WWW2qYa6WWW_---Wdu1i_a7WWW2afb6WWWy-_t-vFown5WWWWWWWW4WWX5WWWWWWe-"
"3sba6WWWWWWOuvt5WWWWWW8s-i6WWWYWXW-bm1lvx6WWW2dtx5WWWWWWy-mdq1Wsm5WWW_--3yum5WWW2iwi5WWWWWWy-Da_d6WWWWm-ZW1med6WWW_Fafd6"
"WWW2YX-5WWWy-_tWwNsoy5WWWamXi-w7mva7WWWWW---3ugf7WWWWGfXc7WWW_--Rfam7WWW2uve7WWWy-_tVqrb6WeWYmWaW1smn7Wu-XmWaW1dgj7WWWWm"
"Wa-4_mj7WWW_l-x-6_df7WWW2Ylw6WWW_--Vogv7WWW2rij7WWWy-_t-1ylm6WWWamWe-rFggs6WWW_lWWWW8Wwq6WWW2_g-5WWWWm-ZWv7gbu6WWWWGelr6"
"WWW_--Rafx6WWW2mzr6WWWWWWa-2qee7WWWWWWSpyc7WWWWWWy_2kiv6WWWWm-ZW1kvt6WWW_Fdpu6WWW2wYg6WWWWWWyV_xw6WWW_--3_mx6WWW2srn6WWW"
"Wm-3dZX7WWWWGaX_6WWWWG_ma7WWW2Wle7W8yWk7Wu-z-_x-2bze7WWWWGknw6WWW_---W4Ywd7WWW2ru_6WWWy-_-_n7kY_5WWWWWWOqse5WWWWWWW-3sfw"
"4WWWWWWWX8uXt5WWWWWWWWk7Zof6WWWWWWe-5lyg6WeWYmWaW1Wmp7WWWWWWOyrY7Wu-zl-xVqch6WeWYmWa-2koo6WWWWWWWX8Xgh7Wu-zl-x-o7jxz5WWW"
"aWXi-1ugk7WWWWWWSgb-6WWWWWWy_2mgd7WWWWWWaW1ffl6WWWWWWaW1Woi7WWWWWWyW7bjd7WWWy-_t-1l_g6WWWYmWe-rVquj6WWW2qWd6WWW_Fahe6WWW"
"2cWj5WWWWWWy-m7xwe6WWWWm-3Y_e6WWW_FXdf6WWW2ZWZ6WWWWWWy-Drgn6WWWWm-ZW1jYl6WWW_Fhrl6WWW2cjZ6WWWWWWyVyap6WWWWm-3ero6WWW_FyZ"
"p6WWW2gjh6WWWWm-3_lu6WWWWGags6WWWWGgnx6WWW2W-_6W8awZ7Wu-xl-x-6ZZ_6WWW2iwn6WWWy-_t-z7eXd5WeWYmWaWX8scx6Wu-XmWaWX8kwt6WWWy"
"-_t-fFmcx4WeWYmWaWX8Yxp6Wu--lWaW_7_un6WWW2yzf6WWW_----1_-d7WWWYWWWW1kkm6WWW_----BvWv6WWW2hiZ6WWW_----7yx-6WWW2qph6WWW_--"
"Vg_f7WWW2uZt6WWWWWWy_e7gco6WWW_--3apo6WWW2qqh6WWW_----1ekf7WWWYWWyVq-d7WWWWWW4Wvr6WWWWWWyVqxg7WWW_--3esg7WWW2ma_6WWWWm-3"
"gjo7WWWWGWqk7WWWWGWus7WWW2mfx7W8aaY8Wu-xl-Repx7WWW2qvo7WWWWm-Z-3ybb7WWWWGawX7WWW_--R_lf7WWW2wgY7WWWWWWa-2wco7WWWWWWSsol7"
"WWWWWWy_2ukz6WWWWm-ZW1YZx6WWW_Fmyx6WWW2yzh6WWWWWWyV_d-6WWWWm-3cu_6WWW_Fen-6WWW2gdr6WWWWm-3Wkb7WWWWGWoY7WWWWGove7WWW2asi7"
"W8uco7Wu-z-_x-2ynk7WWWWGyh_6WWW_----3ueZ7WWW2eir6WWW_--VwYk7WWW2qhZ7WWWWWWyU_la7WWW_--3iXb7WWW2upv6WWWWm-3cah7WWWWGcud7W"
"WWWGytk7WWW2mro7W8Weu7Wu-xl-Rydm7WWW2ige7WWWWm-3knp7WWWWGWkl7WWWWGust7WWW2uqx7W8ibX8Wu-zl-x_2qgY7WWWWWWW1wrq7WWWy-_t-d7v"
"cf6WWWWWWWW6_ry5WWWWWWW-3cwx4WWWWWWWW8ypg5WWWWWWW1cex5WWWWWWW-3u-n5WWWWWWW1eua6WWWWWWWWg7sql6WeWYmWaW1Yvx7WWWWWWWW6uio7W"
"u-zl-xVkjn6WeWYmWa-2q-p6WWWWWWWW8ii_6WWWWWWW1YXl7WWWWWWW-3uxb7WWWWWWW1g-u7Wu-zl-xUua_5WWWWWWW1_rr6WWWaWXe-a7saq6WWWWWWWX"
"4adt7WWWWWWWW4dck7WWWy-_tVy-b6WWWaWXeW2dhk7WWWWWWW-3ptm6WWWWWWWW1lxz6WWWWWWWW7aWx6WWWWWWW1oah7WWWy-_t_1_yu5WWWWWWW1xrk6W"
"WWaWXe-1mlY7WWWWWWW1euq7WWWWWWW-YNujY6WWWWm-x-W8e-d6WWW_Fymd6WWW2yaX6WWW_--3gcY6WWW2w_Z5WWWWWWy-_7nwe6WWW_--3kef6WWW2mYZ"
"6WWWWWWyVxha6WWW_--3ecb6WWW2sol5WWWWWWyVqfj6WWW_--3osj6WWW2Wkb6WWWWm-3e-o6WWWWGafm6WWWWGmds6WWW2esv6W8um_6Wu-xl-Rycd7WWW"
"2shX7WWWy--x_W8asr6WWWamWeWYGqur7WWWWWWWWX8ybv7WWW_l---YObpf7WWW2yoX7WWW_--Ryqf7WWW2fZn6WWWWm-Z-u7gdz6WWWWG_lw6WWW_--Rtt"
"g7WWW2jra7WWW_----6gei7WWW2ybx6WWWWm-ZVXYj7WWWWGuff7WWW_--Rk_n7WWW2rsf7WWWWm-3qWr7WWWWGkem7WWWWGynv7WWW2eZ_7W8cga8Wu-vl_"
"p-u7__t5WWWWWWWW4uid5WWWWWWe-3Yzi6WWWWWW4any6WWWWWWKyzz5WWWWWW8ggs6WeWYmWy-u7dgn7WWWWWWWW4WqW7Wu-zl-Z-2jhp6WWWWWWW1mX_6W"
"eWYmWaV_vX8WWWWWWOnxr7WWWWWW8s_e8Wu-zl-p-s7XuX6WWWaWXeW2mej7WWWWWWa-3Yoi7WWWWWWSrgz6WWWy-_t-1a_d6WWWaWXi-1Yoy7WWWWWWSawn"
"7WWWWWW4yxZ8WWW_l-x_ZW1WcZ7WWW2dv_6WWW_Ftz-6WWW2lzb6WWWWWWy-m7rmt6WWWWm-3Ylt6WWW_Ffyt6WWW2Xll6WWWWWWy-Dxea7WWWWm-ZW1grX7"
"WWW_FwjY7WWW2Zvl6WWWWWWyVYic7WWWWm-3kXc7WWW_Fetc7WWW2huw6WWWWm-3ngj7WWWWGY_f7WWWWGu-m7WWW2yfr7W8ocx7Wu-xl-x-_t1Zcd7WWW2c"
"vl6WWW_----7atm7WWW2YWx6WWW_--V-sz7WWW2dxg7WWWy-_t-nFwfd6WWWWWWW-3cXY5WWWWWWWW8iZo5WWWWWWW1eha6WWWWWWW-3mcx5WWWWWWW1ken6"
"WWWWWYm-ctn1Wbe6WWWWWWWW3opX6WWWWW_lW6oft5WWWWWYm-7iqW6WWWWWWWWoFyjz5WWWWW_lW4bey5WWWWWYm-x7ewe5WWWWW_lW6qil5WWWWWYm-7ai"
"r5WWWWW_l-3seY5WWWWWWW1tZq5WWWWWWW-tFinW4WWWWWWmWw7Ws-5WWWWWWmWY8mjj5WWWWWWWWWGayu4WWWWWWW-3amj4WWWWWYmW4yZf5WWWWW_lW4cp"
"Y5WWWWWWW-tVWti3WWWWWYmWaW1ux_4WWWWW_l-3mps4WWWWWWWWuVamc4WWWWWWWW8mpl4WWWWWWW1uwv4WWWWWWW-fVmnw4WWWWWWWW1m_g5WWWWWYGWhg"
"6WWWWW_FalW6WWWWWYm-2qe-5WWWWW_Fofw5WWWWWWWW4e-s5WWWWWWWW2Wec5WWWWWWW-3mpl4WWWWWWWW2auc5WWWWWYmW2ecj5WWWWW_l-3mZw4WWWWWW"
"W1Wad5WWWWWWW-3ml_4WWWWWYGWbp5WWWWW_Fahi5WWWWWWGmaq5WWWWW2mWy5WWWWW_l_ZVuya3WWWWWYmWYGWXx5WWWWWWWWX8unr6WWWWWWWWX8Wdw4WW"
"WWWWWWYGiu-5WWWWW_--XGypb5WWWWWWGWgq4WWWWWWWWyVewe5WWWWWWWW4uq_4WWWWWWWW4acl5WWWWWWGuzs5WWWWW2uuW6WWWWW_l_ZW1uqf4WWWWWYm"
"WaW1_jt5WWWWW_l-xViWq4WWWWWWWW8ajX5WWWWWWW1omm5WWWWWYm-jto1Wkb6WWWWWWq--Newf6WWWWWWCqqk5WWWWW_lW6o_v5WWWWWYm-7bn-5WWWWW_"
"l-3kig5WWWWWWW1kY-5WWWWWYm-j7gWc6WeWYmWaW1iif7WWWWW_lW6Xcj7Wu-zl-xVwsj6WWWWWYGboc7WeWYmWa-6yjp7Wu-zl-xVlrq6WeWYm_p-2wZ_6"
"WWWWWWW1hnn7WWWWWWW-tFkjY6Wu-zl-xWx7ipt5WeWYmWaWX8vZh7Wu-zl-hW1_zu6WeWYmWq-_Fqjv6WWWWWWW-3Wkj6WWWWWYmW4kkf7WWWWW_lW4yiY7"
"Wu-zl-x-i7aXZ6WWWWWWWW6Zbx5WWWWWWa-1Wul6WWWWWYGsdd7WWWWW_BWbb6WWWWWW4m-v6WWWWWWCmrk6WWWWW2ytv6WWWWW_l_1mdW5WWWWWYmW4szf6"
"WWWWWWWW2_xq6WWWWW_lW2boW6WWWWWWWW4vje6WWWWWWGWYq6WWWWW2zcX7WeWYm_p_qNqjl5WWWWWYmWaW1o--6WWWWW_l-3cer6Wu-zlXiWg7j_p6WWWW"
"m_--2xdx6WWWWm1Wmb6WWWWWWWWEjhZ6WWWWm_--1whY7WWWWm1myj6WWWWW_l-1gtk5WWWWWYmW4iio6WeWYm_p-qNxjc6WWWWWWWW8Wvk6WWWWWWW1khw6"
"Wu-zl-x-o7vaX6WWWWWWW-Feeq5WWWWWWW1WWf6WWWWWWW-bFqmX5WWWWWYmW4ceh6WWWWW_Fkvc6WWWWWWWW4vaY6WWWWWWW-7icl5WeWYmWaWn7qfv6WWW"
"WWYmW4izy7WWWWW_Foft7WWWWWWWW4ayp7WWWWWWWW2eZc7WWWWWWW-3abl6WWWWWWWW2qyX7WWWWWYmW2Ysj7WWWWW_l-3muu6WWWWWWW1k_c7WWWWWWW-3"
"eaz6WWWWWYGurp7WWWWW_FsZi7WWWWWWGurp7WWWWW2iry7Wu-zl-x_b7muw6WWWWWWWW3cZl6WWWWW_Fvgi6WWWWWYmValx6WWWWW_F_kq6WWWWWYGs_l7W"
"WWWW_--3WXX7WWWWWWmVWtY6WWWWWWWW2vfk6WWWWWWGsbw6WWWWW2nxd7WWWWW_l_1WXX5WWWWWYmW4qoh6WWWWWWWW2wku6WWWWW_l-1ytm5WWWWWWW1ux"
"Y6WWWWWWW-3izs5WWWWWYGWqr6WWWWW_Fsyh6WWWWWWGq_t6WWWWW2WZb7WWWWW_l_1uYy5WWWWWYGuyy6WWWWW_Fqso6WWWWWWGeu-6WWWWW2eYk7WeWYm_"
"p_YNcgc5Wu-zlXiWX8oaX6WWWWWWWWW8qwi6WeWYmWaW1sYx7WWWWWWWWYGyqw6Wu-zl-l-y7fyu6WWWWWWCujY6WWWWWWWW2gfj5WWWWWWq-1Wb_6WWWWWW"
"Cuwb6WWWWWW4_mY7WWWWWWSnoY7WWWWWWW--7_qm6WeWYmWaW1qt_7WWWWW_--XGnvb7WWWWWWGqdq6Wu-zl-h-_7wiy5WeWYmWqWzNq-e7WWWWWWWW4eo_6"
"WWWWWWWW4xxj7WWWWWWGWyq7WWWWW2_Y-7Wu-zlzh-s7ksz5WWWWWYq-1uhh7WWWWW_Bc_k6WWWWWW4kZX7WWWWWYC-Xc7WWWWW_l-1Wej5WWWWWWmW2kiv6"
"WWWWWWm-1qca6WWWWWWGmej6WWWWW2ebu6WWWWW_p_1qgv6WWWWWYGqsq7WWWWW_Brgn6WWWWWW4Ykb7WWWWWWCukz6WWWWW2tah7WWWWW_3arg7WWWWW2mu"
"x7WeWYm_l_YOqve6WWWWWYmWaW1Xes7Wu-z-zx-m7dic7WWWWm1ilm6WWWWWWWWEozi6WWWWm_--1wZl7WWWWm1wbx6WeWYm_p-wNe_o6WWWWWWWW8Wh_6WW"
"WWWWW1gok7Wu-XmWa-flo1qco5WWWy-W8ylg6WWWWWWu-1sdk6WWWWWWeW1ysY6WWWWW_lW6tr-5WWWaWXe-5uma6WWWy--dW2Wsq6WWWWW1eWf6WWWWWWu-"
"nFdnc6WWWWWW8wu-5WWWWW---Dydq6WWWWWXu-n7y_h5WWWWWW8yif5WWWWW_lW3_lW6WWWWWWWW3eir5WWWWWXm-7qsW6WWWWW1ugw5WWWWW_l-3eYd5WWW"
"WWWW1Wpw5WWWWWYm-g7Wxi6WWWWWWu-1t_m6WWWWWWWW1kyd6WWWWWW8WeZ6WWWWWWuVWXq6WWWWWW8m_j6WWWWWW8gyu6WWWWW1Wk_6WWW4irb7WWWy-_Nu"
"od7WWWaW-t-3qZj7WWWy-_7mqx6WWWWWWmVifY6WWWWWYuVZhb7WWWWWWWW1yk-6WWWWW_7_ug6WWWaWX8xcf7WWWy-W8gnY7WWWWW--_5hWt6WWWWW1wpf6"
"WWWWW--VYx-6WWWWWXuVXzv6WWWWWW8n_n6WWWWWW8Xt-6WWWWW1idc7WWW4wZl7WWWy-yd-1eom5WWWWWWW1gta6WWWaWXe-1_qw6WWWWWWW1cij7WWWy-W"
"e-1mzq6WWWWW_Fzlj6WWWWWYGwtc7WWWWW_l_p7qXf4WWWWWWmWw7aqa6WWWWWWmWY8umo5WWWaWXe-5ii-5WWWy--dW2s-i6WWWaWWeWt7uyk7WWWWWWGaZ"
"-6WWWy-_tV--W6WWWaWXeW2-Wd7WWWy-_7prr6WWWaWXu_3jbl6WWWWWWWW1iew6WWWy--dW1emy6WWWWWWWW1ayd7WWWaWWuW5hed7WWWy-_t-1cah6WWWW"
"WWGycv6WWWWWWu_l7eps5WWWWWWOWnZ5WWWWWWW-3Ylt4WWWWWYmW4wmw5WWWWW_lW4Wjo5WWWWWWWWk7zsc6WWWWWWe-5kxd6WWWWWYmW2vzX7WWWWW_7-l"
"e6WWWWWWGstp6WWWWW2kvW7WWWWWWu_7ew-6WWWWWW8fXr6WWWWWW8orb7WWWWW_dWl7Z_c6WWWWWWWW1isx5WWWWWWWW3eWY6WWWWWWWW3ous5WWWWWYu-1"
"ghm6WWWWW_7mzz5WWWaWX8qis6WWWy-_7upc6WWWWW2qZn6WWWWW_l_1umz4WWWWWWWW1_zm5WWWaWXeW1Yig6WWWy--dW2-zl6WWWWW1xab6WWWWWWu-1qy"
"o6WWWWWW8mqi6WWWWWW8sYu6WWWWW1a-z6WWW4ezb7WWWy-ydW2qfy5WWWWWWWW1gZh6WWWaWXeW1y__6WWWy-_t-1hiZ6WWWWWWGwhj6WWWWW2vev6WWWWW"
"_l_pFypo3WWWaWXeWYGuaj5WWWWWWWWn7Wkg6WWWy-WWW2d_y6WWWaW---Cgae6WWWWWWWW1y-o6WWWWWWWW7dut6WWWy-_t-1aas5WWWWWXmWu7YlX6WWWW"
"W1iof5WWWWW_l-3okZ5WWWWWXmWk7oWm6WWWWW1x-f6WWWWW---DeWu6WWWWWWWW2qsy6WWWWW1Who6WWWWWWWWj7afn6WWWWWWu-1cnt6WWWWW-7Zvt6WWW"
"WW1gZh6WWWWWWuVwgY6WWWWWW8vg_5WWWWW---Dmre6WWWWW1yy_5WWWWWWu-1oyh6WWWWWW8ipc6WWWWWW8uXn6WWWWW1eWs6WWW4ozy6WWWy-yd-1mkh5W"
"WWaWXeW2obo6WWWy-WeW2ywi6WWWWW_l-pFyYl4WWWWWWWW8eyu4WWWWWWW1W_Z5WWWWWWWWk7kdf6WWWaWXe-y7mim6WWWy-_tW2Znf6WWWWWWWW7Xpy5WW"
"WaWXe-5jkZ6WWWWWWWW8qsh6WWWWWWW1Wet6WWWy-_t_1evm5WWWWWWW1o-Z6WWWWWYm-cFifq6WWWWWWWW3ibb6WWWWW_FmkX6WWWWWWWW6kds5WWWWWWW-"
"3ygv4WWWWWYmW4gq_5WWWWW_l-3cgd5WWWWWWW1cdt5WWWWWWW-3ywi5WWWWWYGmsc6WWWWW_Fed_5WWWWWWGexd6WWWWW2qdo6WWWWW_l_aFmXb5WWWaWXe"
"W2Wxr6WWWy-W8i_t6WWWWWWu-1_f-6WWWWWW8yom6WWWWW_FkWj6WWWWWYeVyhh6WWWWWW8ezc6WWWWW_Faja6WWWWWYeVavX7WWWWWW8epu6WWWWWW8_vd7"
"WWWWW1uWl7WWW4iiu7WWWy-y7imn6WWWaWX8W-o7WWWy-W8Wyh7WWWWW_l-1mgd6WWWaWXeW2mql7WWWy-_7iuz6WWWWWWmVaj_5WWWWWYuVobh7WWWWW_7y"
"rk6WWWWWWGmax6WWWWW2uYf7WWWWWWeVm-x6WWWWW_7upc6WWWaWX8osY7WWWy-_7etm6WWWWW2ivy6WWWWW_l_1Wk_4WWWWWWWW1alp5WWWaWXeW1iai6WW"
"WWWWWW1qj_6WWWy--dW1_np6WWWWW1uYd6WWWWW--Vmib7WWWWW1_xu6WWWWWWuVWWt6WWWWWW8ocm6WWWWWW8ily6WWWWW1ieY7WWW4yag7WWWy-yd-1Wmj"
"5WWWWWWW1qu_5WWWWWWWVuWv5WWWWWWW1iWl6WWWaWXeVurr6WWWWWWW1qjZ7WWWy-_t_1yop5WWWWWYGqim6WWWWW_Fqad6WWWWWWGevn6WWWWW2iuz6WWW"
"WW_l_1Wws5WWWaWX8eXw6WWWyVudy6WWWWWW8moq6WWWWWW8ypX7WWWWW1m-d7WWW4uWm7WWWy-y7qXh6WWWaWX8ane7WWWy-_7uXs6WWWWW2cmY7WWWWW_7"
"eWy6WWWaW1uWm7WWWyVycf7WWWWW1ium7WWW4ozu7WWWy-yd_XFuwe3WWWaWXeWX8ugd6WWWWWWWWX8sWa5WWWy-W8agy5WWWaW-t-_7i-d6WWWWWWWW1iwm"
"5WWWy-W8mwe6WWWaW-tVmeg6WWWy-W8W-u6WWWaWX8__r7WWWWW_Fnaf7WWWy-W8u-m7WWWWWWu_W8WXx5WWWWWW8emW5WWWWWWu--7ymd6WWWWW-lW1mgd7"
"WWWWW2iuj7WWWWW-t-y7epz5WWWWWWu-1wd_5WWWWWW8aai5WWWWWWu-1clc6WWWWWW8waX6WWWWWW8ueh6WWWWW1Wsm6WWW4mot6WWWy-_Nbgx6WWWWWWW-"
"y7uvv6WWWWWWu-1vyW7WWWWWWWW1sfo6WWWWWW8avi6WWWWWWuVwla7WWWWWW8_-w6WWWWWW8Zfg7WWWWW1yhn7WWW4Yaw7WWWy-_NWtq7WWWWW_-_W8nzl5"
"WWWWWWGoqw4WWWWWWm--Fxkw5WWWaWXeW2xeY7WWWWWWGien6WWWWWWm-W8xxy7WWWWWWGunn7WWWy-_t-u7aap5WWWWWWWW4odc5WWWWWWe-3Wfd6WWWWWY"
"GYtx6WWWWW_7nhv5WWWWWW8-zl6WWWWWW8w_X6WWWWW2rgi6WWWWW_t_-7unl6WWWWWWuWu7iwx5WWWWWYu-1cer6WWWWW_7ehf6WWWaWX8_jb7WWWy-W8yr"
"_6WWWWW_l-1y_h5WWWaWXeW2klx6WWWy-_7qyo6WWWWWWm-1wgY6WWWWWWGyhh6WWWWW2Wds6WWWWWWe-1ybZ7WWWWW_7oyh6WWWaWX8vhg7WWWy-_7WWt6W"
"WWWW2kxZ7WWWWW_7udy6WWWaW1qgn7WWWyVwXg7WWWWW1Who7WWW4Ygx7WWWy-yd_XGall4WWWaWXeWYGuYc6WWWWWWWWn7gkr6WWWWWWWWFiyn6WWWWWWWW"
"1wmW7WWWy--dWX8fat6WWWWW1loX6WWWWW----7hbX7WWWWWXu-n7_gm6WWWWWW8iug6WWWWW---Dttv6WWWWW1_Wh6WWWWWWu-1usz6WWWWWW8_rr6WWWWW"
"W8wtZ7WWWWW1gbg7WWW4vqo7WWWy-yd-vFiXx4WWWWWWWW8Wkf5WWWWWWW1cxv5WWWaWXe-vFY_l6WWWWWWWW8sdx6WWWWWWW1oXh7WWWy-_t-nFt-X6WWWW"
"WWW-3wuW5WWWWWYmW4vyg6WWWWW_l-3slm5WWWWWWW1noY6WWWWWWW-3uit5WWWWWYGmzr6WWWWW_FXei6WWWWWWGsbu6WWWWW2pYb7WWWaW-p_ctn1Wos5W"
"WWWWW4yko5WWWy-W8Wph6WWWWWWu-1__k6WWWWWWeW1gWc6WWWWW_lW6cqZ6WWWaWXa-4_qm6WWWWm-ZW1kbm6WWWWGWad6WWWy--dW2uXv6WWWWW1y_i6WW"
"WWWWu-nF-xf6WWWWWW8mjY6WWWWW---Dxtu6WWWWWXq-n7ipg6WWWWWW4atn5WWWWWW8W_k5WWWWW_lW6_dz5WWWWWXm-7cbf6WWWWW1pcY6WWWWW_l-3Wcj"
"5WWWWWWW1aoY6WWWWWYm-g7m_j6WWWWWWu-1lvn6WWWWWWWW1mjh6WWWWWW8apc6WWWWWWuVe-q6WWWam-3Wqb7WWWyFyly6WeWYGaXj7Wu-XGexe7WWWy-_"
"3mYl6WeWYmW4qag7Wu-zFmzX7WWWWW-3avv6WWWWW1We-6WWW4ijc7WWWy-_NWlf7WWWam_x_3qhk7WWWWGk_g7WWW_--R_cs7WWW2gnk7WWWy-_7Wkz6WWW"
"WWWmVqoc6WWWWWYuVkvc7WeWYm_BkWp7Wu-zlXeVpng7WWWWWWCjaa7WWWWW_7ajl6WWWaWX8zxk7WWWy-W8vWe7WWWam-x_4_mo7WWWWm1XZw7WWWy-zZW1"
"bwx6WWWWW1crj6WWWWW--VvhX7WeWYmW4mp-7WWWWW1umu7Wu-zl-pVso_6WWWWWW8qXs6WWWWm_7cXh7WWWaW1gfw7WWWyFgfa7WWWWGwjn7WWWWGoWh7WW"
"W4-Zq7WWWy-yd-1Wzp5WWWWWWW1wye6WeWYmWaVerY7WWWWWWW1m_t7Wu--lWaVWdl7WWW2mZ-6WWW_--VkdX8WWW2Zpp7WWWy-We-1qkv6WWWWW_Faco6WW"
"WWWYGaoi7WWWWW_l_p7Wxj4WWWWWWmWw7mre6WeWYmWq-6ang6Wu-XWWaW1_mY7WWWyl-tWw7ahw5WWWYWXe-5ibX7WWW2wfd6WWWy--dW2_Xu6WWWam-x-s"
"7gfY7WWWWGan-6WWWWm-Bijt7WWWWGozm7WWW_--Fotb7WWW2m_-6WWWy-_tVsXb6WeWYmWaW1aam7Wu-XmWeVp_j7WWWWWWSozh7WWWy-_7ekw6WWWaWXq_"
"2_ub7WWWWm-ZW1e_Z7WWW_Fasa7WWW2vbp6WWWWWWyVecd7WWW_--3ind7WWW2ipx6WWWWm-3skk7WWWWG-wg7WWWWGymo7WWW2e-s7W8upz7Wu-vl-ZW1mo"
"Y7WWWWWWWW1oag7WeWYmW4ojh8Wu-XWWaW1zlb8WWW_l-lW4lus7WWW2iuh7WWWy-_t-1_jl6WWWWWWGuh_6WWWWWWu_l7yb-5WWWWWWOyYf5WWWWWWW-3iw"
"y4WWWWWYmW4qaY6WWWWW_lW4iov5WWWWWWWWk7m_g6WWWWWWe-5sli6WeWYmWaW1mpr7WWWWWWOonZ7Wu-zlXeVexk7WWWWWWC_gd7WWWWW_7eri6WWWWWWG"
"uXu6WWWWW2arb7WeWYm_p_2mrs6WWWWWYmW4qhu7Wu-zl-pVgwb7WWWWWW8clv6WWWWm_7tjq7WWWWm1rth7WWWWGyxx7WeWYW_hW3Xyl7Wu-zl-x-i7gca6"
"WWWWWWWW6wn_5WWWWWWa-1utn6WWWaWX8ilm7WWWyVsai7WWWWWW8qdf7WWWWWW4g_v6WWWWW_7uhc6WWWWWW4itx6WWWaWX4sbW7WWWy-_7uvl6WWWWW2qt"
"w6WWWWW_l_1qcZ5WWWaWXaW1iuj7WWWWWWaW1sip6WWWWWWaW1ayo7WWWy--ZW1Wcx6WWWWW1qyj6WWWWWWu-1eg_6WWWWWW8ycs6WWWWWW8vca7WWWWW1qY"
"h7WWW4keq7WWWy-ydW2_da6WWWaWXeW2W-h7WWWy-_t-1ogi6WWWWWWGWZu6WWWWW2xob7WWWWW_l-f7ock6WWWWWYiVgci7WWWWWWCqbe7WWWWW_7gqp6We"
"WYmW4_dv7Wu--lW4ihz7WWW2ctq7WWWy-W8enj7WWWam_x_3Yzo7WWWWGYel7WWW_--Rnau7WWW2Y-l7WWWy-_7ub-6WWWWWWmVacd6WWWWWYuVswi7WeWYm"
"_Bugq7Wu-XmWeVgYq7WWWyVuXn7WWWWWWCase7WWWWW_7kem6WWWaWX8Zhm7WWWy-_7_yx6WWWWW2xtf7WWWam_xUezv7WWWWGqvr7WWWyVmlp7WWWWWWCkp"
"k7WWWam-3mXe8WWWyFWyr7WeWYGuak8Wu-zFmm_7WWW4ete8WWWy-y3iqq6WeWYmW4eWx7Wu--lW4kiW8WWW2aqs7WWWWm-3onZ8WWWWGme_7WWWWGgpe8WW"
"W2qoj8W8qnq8Wu-vl_3WWX7WWWWW2itl7WeWYm_3ygZ8WWWWW2ixk8Wu-zlz3yxc7WWWaW1qu_7WWWyVcus7WWWWW1qz-7WWW4ezf8WWWy-ydUexc5WeWYmW"
"aW1Wjy6Wu-XG_Wl7WWWWm-ZW1ubj7WWWWGiWv6WWWWWWyVolm7WWWWm-3qom7WWWWGWzY7WWWWm-3mdu7WWWWGwbq7WWWWGymy7WWW2WfX8W8Wee8Wu-zl1x"
"wd8WWWy-zZW1pvZ7WWWWW1Wnp6WWWWW--Vwmh7WeWYmW4uzj8WWWWW1tqY8Wu-zl-pV_Xd7WWWWWW8rfz6WWWWm_7ors7WWWaW1ZXe8WWWyFhaj7WWWWGsX_"
"7WWWWGwjq7WWW4ja_7WWWy-_lV_zi7WWWam-3enZ8WWWyFkku7WeWYGcmm8Wu-XGikg8WWWy-_3mzX7WeWYmW4_yf8Wu-zFufW8WWWWW-3pXp7WWWWW1qww7"
"WWW4cXb8WWWWm_3xnk8WWWyFgdx7WeWYGkZr8Wu-zFWaa8WWW4xel8WWWyFase8WeW2aww8Wu-1uhq8WWW2uex8W8gYZ9Wu-vlyZW1crf6WeWYmWaW1_ev7W"
"u--lWaW1nWa8WWW2tXr7WWWWm-ZVkb-7WWWWGgpw7WWW_--Rnfc8WWW2ygx7WWWWm-3yWg8WWWWGgaa8WWWWGail8WWW2Yoq8W8fdy8Wu-vl_pVoXp6WWWWW"
"WGuv-6WWWWW2mek7WeWYm_pVyy-7WWWWWWGukf8WWWWW2Xbs8Wu-zl-ZVdgp7WWWWW_7ymt6WWWaWX8wmx7WWWy-_7oya7WWWWW2jfq7WWWWW_7umh7WWWaW"
"1mxa8WWWyVlky7WWWWW1wbc8WWW4gXn8WWWy-yd_n7Wds3WeWYmWaWX8aYr5Wu----ZWX8Wot6WWW2qzm6WWWWGmso5WWWWWWy-m7ajn6WWWWm-3ntn6WWWW"
"Gw-g6WWWy-WWW2fc_6WWWaW-x-B_-w6WWWWm-ZW1z_u6WWWWGmkh6WWWWWWyVuty6WWWWm-3wmy6WWWWGaZq6WWWWm-3ygY7WWWWGmx-6WWWWGwrb7WWW2md"
"f7W8ebk7Wu-zl1mxx7WWW_-zx-6Xsg7WWW2nvx6WWWy-_t-1uov5WWWWWXmWu7wzg6WWWWW1ual5WWWWW_l-3mmf5WWWWWXmWk7Wrq6WWWWW1nWk6WWWWW--"
"-Dlnz6WeWYmWaW1enX8WWWWW1acg7Wu-zl_xVjcY7WWWWW1cks6WeWYm_p-2ig-6Wu-zlXiWg7bfr6WWWWWWu-1sux6WWWWW-7xby6WWWWWXuVasg6WWWWm_"
"7rpy6WWWWm1sZc6WWWWW---DcYo6WWWWW1Xtc6WWWWWWu-1kdr6WWWWm_7kla7WWWWm1eXl6WWWWm_7eck7WWWaW1qiy7WWWyF_fw6WWWWGkpp7WWWWGur-6"
"WWW4uvc7WWWy-yd-1Y_n5WWWaWXeW2eWy6WWWy-WeW2aks6WWWWWWWWd7gyu6WWWWWWu-1og-6WWWWW-7rf-6WWWWWXuVfer6WWWWWW8wwl6WWWWWWuVloY7"
"WWWam-3Xys7WWWyFmji7WeWYGWeX8Wu-XGjxx7WWWy-_3avv6WeWYmW4qty7Wu-zFpXp7WWWam_3wxx7WWWyFkce7WWWWW1YXl7WWW4xbu7WWWWmzp-3ueu7"
"WWWWGzbq7WWWy-WiW2wjn7WWWWWWqVyas7WWWWWWCeWj7WWWam-p-4pat7WWWWm1mrX8WWWy-zZW1tw-6WWWWW1_yl6WWWWW--Vhmd7WeWYmW4hjd8WWWWW1"
"sXz7Wu-zl-pVxeZ7WWWWWW8fXw6WWWWm_7geo7WWWaW1a_X8WWWyFtaf7WWWWGqtu7WWWWGaxl7WWW4-yu7WWWy-_lVy-e7WWWam-3qe_7WWWyFadq7WeWYG"
"ocg8Wu-XGuna8WWWy-_3mr_6WeWYmW4yha8Wu-zFgdx7WWWam_3gna8WWWyFeYl7WWWWW1acs7WWW4su-7WWWWm_3ase8WWWyFect7WeWYGavk8Wu-zFib-7"
"WWW4_hf8WWWyFqZZ8WeW2Wrp8Wu-1qsj8WWW2yXq8W8gYx8Wu-vlyZV_ks5WeWYmWaW1_nc7Wu--lWaW1knr7WWW2aZZ7WWWWWWyVWdt7WWWWm-3eWt7WWWW"
"Gusd7WWWWm-3uf-7WWWWGW-w7WWWWGwsZ8WWW2qoe8W8iwl8Wu-vlWaW1mlz6WeWYmWaW1WZg8Wu-zl-pVffj7WWWWWW8aYY7WWWWWW8Wop7WWWWW1qfx7WW"
"W4gjb8WWWy-yd-n7syp4WWWWWWWW8u-z4WWWWWWW1ahf5WWWWWWWWk7Wrj6WeWYmWa-AYkk6WWWWWWWW8ekt6WWWWWWW1yyZ7Wu--lWa-f7cXy6WWW2ucp6W"
"WWy-_tW9xXb6WWWYWXe-5uhb7WWW2reh6WWW_----7ujj7WWW2Wbq6WWW_--Vwcv7WWW2cnW7WWWy-_t_1ent5WWWWWWW1czi6WWWaWXa-c7khy6WWW_--3o"
"py6WWW2kyq6WWWWmWaW4Wqy7WWW_l-RgkZ8WWW2sqv7WWWWm-Z-3fyo7WWWWGj-k7WWW_--Rgeu7WWW2gql7WWWy-_tV_og6WeWYmWaW1ikv7Wu-XmWeVeYv"
"7WWWWWWSabr7WWWWWWy_2Zfg7WWWWm-ZW1Xud7WWW_FeZe7WWW2xWr6WWWWWWyVw_h7WWWWm-3anh7WWW_Fezh7WWW2Xl-6WWWWm-3xYp7WWWWGnql7WWWWG"
"oWt7WWW2ojx7W8Y_X8Wu-xl-x-6gxm7WWW2wp-6WWW_--Vph_7WWW2ppm7WWWWWWyUaio7WWW_--3Wmo7WWW2yga7WWWWm-3ubw7WWWWGWZs7WWWWGal_7WW"
"W2WWZ8W8uvf8Wu-xl-RuuW8WWW2ews7WWWWm-3kna8WWWWGYj-7WWWWGYpf8WWW2Wfk8W8wer8Wu-vl_pUWqy5WWWWWWW1ekp6WeWYmWaVifh7WWWWWWW1Wf"
"W8Wu-XmWaVyvd7WWWWWWW1qwx7WWWy-We-a7etu6WWWWWWWW3cck6WWWWW_Folg6WWWWWWWW6Yjz5WWWWWWW-3uo_4WWWWWYmW4_bc6WWWWW_l-3ykj5WWWW"
"WWW1cj_5WWWWWWW-3uep5WWWWWYGmxk6WWWWW_Fe_b6WWWWWWGuZm6WWWWW2ibx6WWWWWWW-f7Wwp6WWWWW_Fngn6WeWYmYqVuzY8WWWWW_Fxg_7WWWWWWWW"
"6ayp7Wu-zl-xVucp6WWWWWWGaw-6WWWWW2ojk7WeWYm_p_2ohu6WWWWWYmW4mty7Wu-zl-xVclz6WeWYm_p-2aZZ7WWWWWWW1lpq7WWWWWWW-3W_d7WWWWWY"
"GWka8WWWWW_Fobx7WWWWWWGWka8WWWWW2wvl8Wu-zlzhUiWW6WWWWWYGWdY7WWWWW_FYwt6WWWWWWGemb7WWWWW2mwq7WWWaW-t_a7c_u6WWWy-W8gmy6WWW"
"WWWu-1efa7WWWWWWWW1mYr6WWWWWW8azl6WWWWW_Fayj6WWWWWYeVycd7WWWWWW8qez6WWWWWW8saj7WWWWW1qoq7WWW4Yf_7WWWy-y7uos6WWWaWX8Wvv7W"
"WWy-W8lfo7WWWaW-t-3XZr7WWWy-_7kcZ7WWWWWWmVazc6WWWWWYuVfrn7WWWWWWWW1gje7WWWWW_7o_l6WWWaWX8w-l7WWWy-_7ovx6WWWWW2Zjf7WWWWW_"
"l_1gZa5WWWaWXeW2Yar6WWWWWWWW1eWZ7WWWy--dW1df-6WWWWW1qwl6WWWWW--Vizh7WWWWWXuVuwY7WWWWWW8oYw6WWWWWW8bye7WWWWW1ynl7WWW4equ7"
"WWWy-yd-1qaq5WWWWWWW1kwc6WWWaWXe-1su-6WWWWWWW1wpm7WWWy-_t_1amw5WWWWWYGidw6WWWWW_Fqfm6WWWWWWGory6WWWWW2rfg7WWWWW_l_1myz5W"
"WWaWX8apa7WWWyVWXf7WWWWWW8Wz_6WWWWWW8qal7WWWWW1eqs7WWW4uZW8WWWy-y7asq6WWWaWX8kXt7WWWy-_7ewX7WWWWW2scm7WWWWW_7upe7WWWaW1u"
"ZW8WWWyVicu7WWWWW1ieX8WWW4sbh8WWWWW_h_a7uwX7WWWWWW4ywv6WWWy-W8Wk_6WWWWWWu-1o_b7WWWWWWWW1yjw6WWWWWW8yuq6WWWWW_Fecp6WWWWWY"
"eVebf7WWWam-3up_7WWWyFWrp7WeWYGewf8Wu-XGuaa8WWWy-_3We-6WeWYmW4uwa8Wu-zFqww7WWWWW-3YXl7WWWWW1mjs7WWW4yZW8WWWy-y7u_u6WeWYm"
"W4qgX8Wu--lW4ixc8WWW2upy7WWWy-W8iWr7WWWam_x_3iiw7WWWWGybs7WWW_--RogW8WWW2m_s7WWWy-_7ypb7WWWWWWmVirh6WWWWWYuVoiq7WeWYm_BY"
"ix7Wu-XmWeVeXy7WWWyVefv7WWWWWWCedl7WWWWW_7acr6WWWaWX8gdt7WWWy-_7utX7WWWWW2shm7WWWam_xUmkY8WWWWGqsz7WWWyVyyx7WWWWWWCsbs7W"
"WWam-3Yho8WWWyFmm_7WeWYG_zu8Wu-zFmxd8WWW4eZp8WWWy-y3e_v6WeWYmW4WXZ8Wu--lW4yYg8WWW2wl_7WWWWm-3_pj8WWWWGoid8WWWWGmzo8WWW2y"
"gu8W8oWW9Wu-vl_3eld7WWWWW2ect7WeWYm_3asi8WWWWW2mrv8Wu-zlz3eZk7WWWaW1ezd8WWWyVsi-7WWWWW1Wgf8WWW4ahq8WWWy-ydUmid5WeWYmWaW1"
"yfz6Wu-XGyhn7WWWWm-ZW1k_k7WWWWGm-v6WWWWWWyVa_o7WWWWm-3sro7WWWWGe_a7WWWWm-3ujw7WWWWGiqs7WWWWGar_7WWW2WgZ8W8ecg8Wu-zl1oih8"
"WWWy-zZW1iWc7WWWWW1uqq6WWWWW--VYsk7WeWYmW4eon8WWWWW1ssa8Wu-zl-pVYmf7WWWWWW8ij-6WWWWm_7agw7WWWaW1_ph8WWWyFupl7WWWWGimX8WW"
"WWGius7WWW4YhW8WWWy-_lVsbm7WWWam-3Y-c8WWWyFmfy7WeWYGomq8Wu-XGWjk8WWWy-_3ema7WeWYmW4eij8Wu-zFWaa8WWWam_3eik8WWWyFmks7WWWW"
"W1me_7WWW4ine8WWWWm_3oso8WWWyFib-7WeWYGWhv8Wu-zFWbe8WWW4klp8WWWyFusi8WeW2mW-8Wu-1wmu8WWW2ml-8W8kgd9Wu-vlyZVWxt5WWWWWWW1q"
"dh6WeWYmWaVune7WWWWWWW1asx7Wu--lWaVqpu7WWW2aab7WWW_--Vssd8WWW2Ymt7WWWWWWyU_gw7WWW_--3icw7WWW2ydg7WWWWm-3opY8WWWWGmX_7WWW"
"WGuad8WWW2eWi8W8mfp8Wu-xl-Rueg8WWW2yu_7WWWWm-3sbk8WWWWGsbe8WWWWGiop8WWW2yuu8W8wnW9Wu-vl_pUWj_5WWWWWYGmo-6WWWWW_FWhr6WWWW"
"WWGWiY7WWWWW2ivm7WeWYm_pUmvj7WWWWWYGunj8WWWWW_FqhZ8WWWWWWGunj8WWWWW2gkw8Wu-zlzhUmWY6WWWaWX8ehg7WWWyVqkm7WWWWWW8Wra7WWWWW"
"W8urs7WWWWW1et_7WWW4aze8WWWy-y7Wcw6WWWaWX8m__7WWWy-_7mZe7WWWWW2est7WWWWW_7eal7WWWaW1aze8WWWyVwiW8WWWWW1yfg8WWW4ogr8WWWy-"
"ydUmba6WeWYmW4mpm7Wu-XGuY_7WWWWWW4WZj7WWWyVixp7WWWam_3eoc8WWWWGitX8WWWWGiZh8WWW2ubm8W8Wot8Wu-vFmhW8WeWYGqmv8Wu-XGWep8WWW"
"y-_3uid7WeWYmW4uon8Wu-zFase8WWWWW-3yYw7WWWWW1ufY8WWW4mti8WWWWm_3ult8WWWyFqZZ8WeWYGae_8Wu-zFusi8WWW4Wgu8WWWyFWrn8WeW2ela9"
"Wu-1Wxz8WWW2W-a9W8eWj9Wu-vly3exy6WeWYmW4uYd8Wu--lW4ezk8WWW2ulY8WWWWm-3uso8WWWWGeci8WWWWGYZu8WWW2eqz8W8onb9Wu-vl_3mYh7WWW"
"WW2aZx7WeWYm_3uon8WWWWW2YX-8Wu-zlz3aco7WWWaW1mti8WWWyVeXa8WWWWW1ydk8WWW4Wqv8WWWy-y3mms7WeWYGWot8Wu-1mlv8WWWWGqco8WWWWGWv"
"_8WWW2W-a9W8eWj9Wu-vFybf8WeWYGesb9Wu-zFqvp8WWW4yr-8WWWyFWnv8WeW2eWj9Wu-1kbc9WWW2Wmj9W8cur9Wu-vlyZ_W7ukh3WeWYmWaWX8eag5Wu"
"-XmW4i-d6WWWWm-x-W8iuj6WWWWGugd6WWWWWW4qvd5WWWy-W8gvX6WWWaW-p-_7qXl6WWWWWW4Wqe6WWWWWWyVyng6WWWWWW4q-p5WWWy-W8ylj6WWWaW-p"
"Vmlp6WWWWWW4q_g6WWWWm-3qav6WWWWGyjs6WWWWGWjy6WWW2iy-6W8ysa7Wu-zl1q_q7WWWy-_3yrw6WeWYmW4ely7Wu-XmW4qgt7WWW_-zFavm7WWW2mlg"
"7WWWy-W8inp7WWWWW-p_W8Y-s6WWWWWX4yaX6WWWWWW8qfa5WWWWWWu--7mwi6WeWYmWaW1Zyw7WWWWWW8iwW7Wu-zl_3bze7WWWWW2Wdl7WWWWW-h-y7dbw"
"6WWWWWWCmYZ6WWWWWWu-1xha6WWWWWW8Wlm5WWWWWWq-1os-6WWWWWW4aoi6WWWam-3iet7WWWyFokc7WWWWGe_o7WWWaGdXs7WWWy-_3koc6WWWWWW4e_Z7"
"WWWWW1ubj7WWWWmz3q-d7WWWWm1len6WWWWW1mrs6WWW4apz6WWWy-_N_zZ7WWWWWWu_w7_sy6WWWWWWeW1g_j6WWWam-xVe_d7WWWWm1omu7WWWy-_3qmx6"
"WeWYmW4_tz7Wu-zFqfq7WWWWW-3YWg7WWWaW1etu7WWW_-zFgzw7WWW2ciq7WWWy-W8wdr7WWWWWWuUjbk6WWWWWW8Wos5WWWWWWuVhkY7WeWYmW4vc_7WWW"
"WWW8qki7Wu-zl-3ecd7WWWWW1olm7WWWWW-lVYpt6WWWam-3uku7WWWyFzzf7WWWaW1-ev7WWWy-_3ajn6WWWWWX4qom7WWWWmz3qxg7WWWWm1khy6WWWWW1"
"uwX7WWW4u_e7WWWy-_Njfj7WWWWWWuUmec7WWWam-3mvw7WWWyFeYm7WeWYGiob8Wu-XGvZW8WWWy-_3uty6WeWYmW4qeW8Wu-zFWdt7WWWWW-3w_h7WWWWW"
"1a_o7WWW4Wqx7WWWWm_3YnZ8WWWyFaio7WeWYGpgf8Wu-zF_gw7WWW4dWa8WWWyFuY_7WeW2uZk8Wu-1ege8WWW2emk8W8ihr8Wu-z-zFiZn8WWWylW4ijt7"
"WeWYmW4kxt8Wu-zl-3ihz7WWWWW1ixc8WWW4_Wo8WWWy-yt_W8cjr5WWWWWWGuk_4WeWYmWq-W8zkl7WWWWWWGiiw6Wu-zl-h-_7rYX6WWWYWXy-1jhp7WWW"
"2sZh7WWW_--7_-Z8WWWYWW4nmh7WWW_--Fkto7WWW2het6WWWWm-Z-u7iqa7WWWWGiyX7WWW_--Rwkq7WWW2Xzj7WWWy-_d-4axc6WeWYmWaW1-lv7Wu-XWW"
"4wac8WWW_lWqVplq7WWW2ddk7WWWWWWCYbr7WWW_--FYur7WWW2WnY7WWWWm-ZVZss7WWWWGmwo7WWWWm-Bsjf8WWWWGfw-7WWWWm-3g-h8WWWWGYZc8WWWW"
"Gofn8WWW2m-s8W8iu_8Wu-xl-BwZy7WWW2ubp7WWWWm-3ge-7WWWWGnaw7WWWWGsXa8WWW2_ve8W8djl8Wu-zl-Bqfc8WWWy-_d-u7_pu5WWWWWWWW4epg5W"
"WWWWWe-3iqk6WWWWWW4im_6WWWWW2oYl7WWWWWWCzsa7WWWWW_7mv_5WWWWWW8kvt6WWWWWW8urd6WWWWW2ceo6WeWYm_p-u7Yso7WWWWWWWW4yzb7Wu-zl-"
"Z-2kdr6WWWWWYGwpj7WWWWW_Fvo-6WeWYmWaVoya8WWWWWYGYau8WWWWW_7tmt7WWWWWW8bmh8WWWWWW8W-_7WWWWW2a_f8Wu-zlzh-s7njY6WWWWWYi-1up"
"l7WWWWWW8sxi7WWWWWW4-hy6WWWWW_7yrm6WWWWWW4YaZ7WWWaWX4xsk7WWWy-W8rjd7WWWWW_l-1Wsm5WWWaWXi-1jmq7WWWWWWSdqY7WWWy-_7_xw6WWWW"
"WYy_1Y-q7WWWWWWCxsd7WWWWW_7xwe6WWWWWWGgco6WWWWW2Zfz6WWWWW_p_1avx6WWWaWX8cr-7WWWyVftx7WWWWWW8cqt7WWWWWW4mbi7WWWWWW4prz7WW"
"WWW1ijd8WWW4boo8WWWy-y3yap6WWWWWW4gxd7WWWaWX4lpp7WWWWWW4umc8WWWy-_3_d-6WWWWW2pxi7WWWWW_3iwi7WWWWW2gd_7WWWWW_3_la7WWWaW1s"
"_w7WWWyVtgp7WWWWW1mZy7WWW4tpb8WWWWmzp_q7mig7WWWWGeqd7WWWy-WCffn7WWWYW-FYqy7WWW2Zzr7WWWy-_7ubb7WWWWW2Yot7WWWWW_lVand6WWWW"
"WYuVqhk7WeWYm_Bozw7Wu--lW4qcf8WWW_l-lVyfo7WWWWm1s-X7WWWWW_7aas6WWWaWX8_qs7WWWy-W8-Wl7WWWWWWyUwmt7WWWWWWCYzo7WWWam-3ggi8W"
"WWyFezv7WeWYGqmo8Wu-zFmkY8WWW4m_i8WWWy-y3aqy6WeWYmW4qhc8Wu--lW4g-h8WWW2hjX8WWWWm-3Wwk8WWWWGqqe8WWWWGoXq8WWW2Wyv8W8auX9Wu"
"-vlW4mgv7WeWYmW4xzw8Wu-zl-3pXW8WWWWW1yyf8WWW4wcr8WWWy-ydVWfq5WeWYmWaW1urh7Wu--lWaW1kpz7WWW2aee7WWWy-_7qaX7WWWamWyUsl_7WW"
"WWG_ew7WWW_--RZqa8WWW2ixw7WWWWm-3izd8WWWWGqiY8WWWWGsWj8WWW2a_n8W8aXv8Wu-vl_3cnf7WeWYmW4aZk8Wu-XmW4w-e8WWWy-_dVk_j6WWWWWW"
"Gumt6WWWWW2ewY7WWWWWWeVYbv7WeWYm_Bfj-7WWWWWWGund8WWWWW2Yip8Wu-zlz3aXl7WWWWW2etW8WWWaW-pUgZX8WWWyVxzz7WWWWWWCXfp7WWWWW_7k"
"gu6WWWaWX8_cx7WWWy-_7ieb7WWWWW2pZq7WWWWW_7W_g7WWWaW1WdZ8WWWyVoax7WWWWW1qma8WWW4Wrk8WWWWmzpUizd8WWWWGaaZ8WWWyVqZX8WWWWWWC"
"afx7WWWam-3xlu8WWWyFonZ8WeWYG-f-8Wu-zF_pj8WWW4wdv8WWWy-y3guz6WeWYmW4mje8Wu--lW4jyl8WWW2yrZ8WWWWm-3gip8WWWWGcri8WWWWG--u8"
"WWW2av_8W8jsc9Wu-vl_3yvh7WWWWW2sWy7WeWYm_3_Xo8WWWWW2l_-8Wu-zlz3sZo7WWWaW1WYj8WWWyVYea8WWWWW1swk8WWW4uew8WWWy-y3mrr7WeWYG"
"mXt8Wu-1ucv8WWWWGmrn8WWWWGWx_8WWW2Wfb9W8ejj9Wu-vFaoe8WeWYGixb9Wu-zFarp8WWW4iq-8WWWyFmlv8WeW2ejj9Wu-1mhc9WWW2uZk9W8kss9Wu"
"-vlyZ_W8WZp4WeWYmWaWX8Ygk6Wu----ZWX8idi7WWW2yYe7WWWWG_lh6WWWWWWy-m7ey_6WWWWm-3my_6WWWWG_as6WWWWWWy-DWfj7WWWWm-ZW1Y-g7WWW"
"WGsls6WWWWWWyVyel7WWWWm-3_fl7WWWWGsdY7WWWWm-3ios7WWWWGevo7WWWWGZrw7WWW2eZ-7W8eab8Wu-zl1yok8WWWy-zZWX8my-6WWWWW1kWd6WWWWW"
"----7sle7WeWYmWaW1edr8WWWWW1mXW8Wu-zl-p-m7rmt6WWWWm_7oXe7WWWWm1cen6WWWWW---DvlY7WWWWW1inn6WWWWWWu-1Yic7WWWWm_7wYo7WWWWm1"
"uzy6WWWWm_7ksz7WWWaW1rel8WWWyFhfi7WWWWGxsa8WWWWGkfp7WWW4wXy7WWWy-_t-i7_hX7WWWWWWu-1skf7WWWWW-7ugf7WWWWWXuV-az6WWWWWW8Wxs"
"6WWWWWWuVxzi7WWWam-3ntY8WWWyFmst7WeWYGmnk8Wu-XGxte8WWWy-_3gfY7WeWYmW4pte8Wu-zFkb-7WWWam_3hve8WWWyFfyo7WWWWW1iiw7WWW4X_Z8"
"WWWWm_p-BXuY8WWWWm1r_m8WWWy-zZW1npf7WWWWW1mxs6WWWWW--Vfgp7WeWYmW4knt8WWWWW1_se8Wu-zl-pVwgj7WWWWWW8glY7WWWWm_7ef-7WWWaW1h"
"kn8WWWyF-kp7WWWWGnxc8WWWWGqzw7WWW4tha8WWWy-_lVgYr7WWWam-3_oi8WWWyFgsX8WeWYGgXx8Wu-XGzpq8WWWy-_3sge7WeWYmW4Wyo8Wu-zFyWg8W"
"WWam_3qsq8WWWyFomx7WWWWW1mqZ8WWW4Yyj8WWWWm_3WZv8WWWyFkna8WeWYGay-8Wu-zFsbk8WWW4uuv8WWWyFuso8WeW2kub9Wu-1bW-8WWW2qjc9W8np"
"k9Wu-vlyZ-u7ic-4WWWWWWWW8mXk5WWWWWWW1mW-5WeWYmWa-u7ipv6WWWWWWWW8qub7WWWWWWW1Wjt7Wu--lWa-u7mdn7WWW2xjs6WWW_----7mdy7WWW2u"
"kY7WWW_--Vqfh8WWW2yop7WWWWWWy_e7iqa7WWW_--3iqa7WWW2sxx6WWWWm-ZW8_i_7WWWWGyWw7WWW_--Ryta8WWW2Ypw7WWWWWWy_5z_q7WWWWm-ZW1ri"
"o7WWW_Fumo7WWW2pWy6WWWWWWyVZss7WWWWm-3pjs7WWW_Fprs7WWW2g-d7WWWWm-3ci_7WWWWGXhw7WWWWGXpY8WWW2qhd8W8pWk8Wu-xl-x-6coz7WWW2s"
"ae7WWW_--Vsdj8WWW2zbx7WWWWWWyUge-7WWW_--3_l-7WWW2cZk7WWWWm-3WYe8WWWWGmaZ8WWWWGsri8WWW2Wtn8W8kvu8Wu-xl-Rydm8WWW2lsZ8WWWWm"
"-3kcq8WWWWGkmj8WWWWGgwv8WWW2Yk-8W8Xhd9Wu-vl_p-m7aee6WWWWWWW-3yeb5WWWWWYmW4oen6WWWWW_l-3Wsr5WWWWWWW1cpe6WWWWWWW-3yxy5WWWW"
"WYGaXz6WWWWW_FqWp6WWWWWWGio-6WWWWW2wdj7WeWYm_p-m7WX-7WWWWWWW-3ag-6WWWWWYmW4wje8WWWWW_l-3uoh7WWWWWWW1ug-7WWWWWWW-3krn7WWW"
"WWYGeyo8WWWWW_Fbhe8WWWWWWGeyo8WWWWW2gtW9Wu-zl-p_e7gdz6WWWWWW8Yzs6WWWWW_FiWs6WWWWWWWW6auj6WWWWWYu-1cXp7WWWWW_7gbu6WWWaWX8"
"h_w7WWWy-_7ybb7WWWWW2typ7WWWWW_l_1_xe5WWWaWXeW2yYy6WWWy--dW2vff7WWWWW1Yvs6WWWWWWu-1XYj7WWWWWW8XnY7WWWWWW8rep7WWWWW1sqw7W"
"WW4taa8WWWy-yd-1muv5WWWWWWW1omj6WWWaWXe-1gee7WWWWWWW1dcx7WWWy-_t_1cxW6WWWWWYGyrY7WWWWW_FWhu6WWWWWWGctb7WWWWW2wiq7WWWWW_l"
"_1uya6WWWaWX8ogk7WWWyVqWr7WWWWWW8yoe7WWWWWW8Zpx7WWWWW1y-Z8WWW4kdk8WWWy-y7uyz6WWWaWX8yzZ8WWWy-_7cli7WWWWW2mjy7WWWWW_7knp7"
"WWWaW1kdk8WWWyVilb8WWWWW1kYm8WWW4nmx8WWWy-yd_Xlu1mjv1WeWYmWaWXeW2WbW4Wu-XmW4Wqg5WWWWm-x-WeW2unh5WWWWGqy_4WWWWWW4yd_3WWWW"
"WWy-_du1cXY5WWWWWW4ic-4WWWWWWyVYz-4WWWWWW4m-s4WWWy-WeWWGWfs5WWWWWWWWW8i_b5WWWaW-t-_t6kxi5WWWWm-x-W8mWm5WWWWGanh5WWWWWW4o"
"Xt4WWWWWWy-_7iZo5WWWWWW4mXk5WWWWWWyVugl5WWWWWW4qjX5WWWWWWyVuwr5WWWWWW4egm5WWWWm-3mwv5WWWWGaau5WWWWGegy5WWW2e__5W8qmY6Wu-"
"zl1Wru6WWWWWWCmxX7WWW_-zFair6WWW2uun6WWWy-We-_Nyav5WWWYm_t---2wmZ6WWW2jk-5WWWWGW-d5WWWy--x-Xmy1miv5WWWWWW4evZ5WWWWW1sww4"
"WWWWWW8enx3WWWWWWu--tt1nru5WWWWW----Foft5WWWWWXWWz7Xgx5WWWWW-x-2bey5WWWWWX4sub5WWWWWW8cfw4WWWWW_lWWW1Zdn5WWWWWXe--l6_-s5"
"WWWWW1qWp5WWWWW----7yYW6WeWYmWaW1mdc7WWWWW1idz6WWWWWW8mq-5Wu-zl_l-_7eyf6WWWWWX4nzv5WWWWWW8aka5WWWWW----l3xqZ6WWWWWXWW_tp"
"1ero5WWWWWWu-1qyp5WWWWWW8oXa5WWWWWWWW_Fqom5WWWWWWu-1olo5WWWWWWy-z7_fu5WWWWWWCiXx4WWWWWWq-1ixo5WWWWWW4-nx4WWWWWW8gvp4WWWW"
"W_lWWW1fli5WWWWWYm-z-5opd5WWWWW-p-XGnqX6WWWWWX4pxc5WWWWWW8_wp4WWWWWWq-zFoqa6WWWWWWCWkf5WWWWWWq-1wly5WWWWWW4gmg5WWWWWW8uZ"
"_4WWWWm_p-1Wkh6WWWWm1gmf6WWWWWW4esm5WWWam-3WXY7WWWyFYvj6WWWWGeW_6WWWaGsjv6WWWy-_3iti5WWWWm_3yts6WWWWm1Wji6WWWWGWjx6WWWWG"
"mro6WWWWmz3ucl6WWWWm1Yaq5WWWWW1uWu5WWW4qYz5WWWylzBWsb7WWWWmXCqii6WWWWW--_zl3imv5WWWWW1hna5WWWWW_l-xVuvy3WWWWWYmWYuo1ynu5"
"WWWWWWu-1cxv5WWWWWW8qse5WWWWWWWW_Fews5WWWWWWu-1ipt5WWWWWWWWz7ywy5WWWWWWyVvpz5WWWWWWCYcc5WWWWWWu-1tgc5WWWWWW8clz4WWWWWWu-"
"y7kiZ6WWWWWWeW1maw5WWWam-xV_zm6WWWWm1Wfv6WWWy-_3eka6WeWYmW4_bz6Wu-zFyhr6WWWWW-3lfk6WWWaW1_gv6WWWy-_NaWY7WWWWWWuUZbx5WWWW"
"WW8yYf5WWWWWWuVvje6WeWYmW4hnz6WWWWWW8egr6Wu-zl-3ogi6WWWWW1oXp6WWWWW-lVWtY6WWWam-3Yav6WWWyFvfk6WWWaW1euv6WWWy-_3Yjz5WWWWW"
"X4ucp6WWWWmz3yrk6WWWWm1azc6WWWWW1irh6WWW4kZo6WWWy-_Nrpy6WWWWW_l-zNwYr5WWWamWi-_7sgp6WWWWGldn6WWW_--Rcm-6WWW2h-w6WWWy-_tV"
"i-_5WeWYmWaW1uWi7Wu--lW4Xso7WWWYWWWW1nxd7WWWy-Wm-yFrbW7WWWWWWq-2Yx-6WWWWm_BdcW7WWWWm1Wrq6WWWWWWOwmW7WWWWWWe-y7vzz6WWWaW-"
"FoWd7WWWy-W8yfb7WWWWWWe-1bwx6WWWWWWqVhzz6WWWWWW8xby6WWWWWW4yvh6WWWWWWOsfr6WWWWWWu__d1ayu6WWWWW-dWXGoWm6WWWWW1cbf6WWWWWWW"
"Wz7Zwm6WWWWWWu-1sms6WWWWW-7hWt6WWWWWXuVr-c6WWWWm_7Zvt6WWWWm1-bY6WWWWW_lWWOqql6WWWYWXe-y7anv6WWW2qZm6WWWy-WeWWGmis6WWWWWW"
"WW3eih6WWWWWWWWyl1uzt5WWWWWWWWW8WmX6WWWam-xVaym6WWWWm1tYZ7WWWy-_3qlj6WeWYmW4kkf7Wu-XmW4Wbb7WWW_-zFkfe7WWW2miZ7WWWy-W8mof"
"7WWWWW-p_W8k_e6WWWWWX4dht5WWWWWW8ifz4WWWWWWu--7tvX6WeWYmWaW1kYe7WWWWWW8qcr6Wu-zl_3ycv6WWWWW2uh_6WWWWW-h-y7-ai6WWWWWWCkov"
"5WWWWWWu-1WXx5WWWWWW8yaf5WWWWWWq-1zmn6WWWWWW4omY6WWWam-3wYb7WWWyFZ_s6WWWWGWXX7WWWaGfXa7WWWy-_3cXz5WWWWWW4hbr6WWWWW1cmy6W"
"WWWmz3Yeu6WWWWm1muc6WWWWW1uph6WWW4_Yo6WWWy-_N_zy6WWWWWWu_w7qnk6WWWWWWeW1WcY6WWWam-xVqrw6WWWWm1osc7WWWy-_3ulk6WeWYmW4y-g7"
"Wu-zFeoY7WWWWW-3wkw6WWWaW1yuc7WWWy-_NWjh7WWWWWWuUciZ6WWWWWW8msk5WWWWWWuVWYq6WeWYmW4ooh7WWWWWW8yc-6Wu-zl-3WZu6WWWWW1uv-6W"
"WWWW-lVunh6WWWam-3qnc7WWWyFsbw6WWWaW1Yjd7WWWy-_3eqb6WWWWWX4aw-6WWWWmz3max6WWWWm1y_l6WWWWW1eWr6WWW4axx6WWWy-_Nopa7WWWWWWu"
"Uq_t6WWWam-3yZf7WWWyFeu-6WeWYGyqn7Wu-XGwYj7WWWy-_3uZm6WeWYmW4awj7Wu-zFemb7WWWWW-3ory6WWWWW1WiY7WWW4uvf7WWWWm_3iyl7WWWyFe"
"wX7WeWYGksq7Wu-zFmZe7WWW4aem7WWWyFmYh7WeW2mhu7Wu-1yop7WWW2Wsu7W8mb_7Wu-z-zFmrZ8WWWylW4eck7WeWYmW4ixf8Wu-zl-3geo7WWWWW1ag"
"w7WWW4qka8WWWWmzp_xVwbz6WWWWGarw6WWW_--Rzml7WWW2suf7WWWy-Wa-YOWfb7WWWWWW8uYZ7WWWWWW4Wdr6WWWWWWOq_Y7WWWam-x_yd1dlW7WWWWm1"
"pop7WWWy-zZWX8frc6WWWWW1Yai5WWWWW----7Zrh6WeWYmWaW1Xlv7WWWWW1WWb7Wu-z-zx-y7mxu6WWWWm1mtc6WWWWWWu-1r-c6WWWWW-7XWe6WWWWW1k"
"vn5WWWWWWu-1imm6WWWWm_7fr_6WWWWm1zhg6WWWWm_7crc7WWWaW1psq7WWWyFpZr6WWWWGhwh7WWWWGcmw6WWW4rpX7WWWy-yd-vFWfX4WeWYmWaWX8uZv"
"5Wu--lWaWX8mZp6WWW2ius5WWWy-WeWYGadp5WWWWW_--ZWx1Wrp4WWWWWWGiht3WWWWWWW-t-1ixi3WWWWWWWXemr1upW5WWWWWWm--Vlem5WeWYmWaWXu7"
"_xr6WWWWWWGecx5Wu-zl-h-_7aiu5WeWYmWq-ut1yig5Wu-zl-hWdus1db_4WWWWWWGqXr4WWWWWWm---6fue5WWWYWXy-XGaW-6WWW2geo6WWW_--7Wwo7W"
"WWYWW4yro6WWW_--FkXt6WWW2gru5WWWy-_d-zFmXl5WWWWWWG_x_4WWWYWXe-vl1mvf6WWW2_Ze5WWW_---WXer1jrd7WWW2wxY7WWW_--Z-6rld7WWW2rw"
"Y7WWW_--RXYg7WWW2iww6WWWWm-Z-uVauj6WWWWGgsh6WWWWm-BoXe7WWWWGkiZ7WWW_--FWcs6WWW2gsn6WWWWm-l-5a_k7WWW_lWqVjas6WWW2exn6WWWW"
"WWCvaa7WWW_--FbWt6WWW2fni6WWWy-_d-z7oXa5WWWWWWGcix4WeWYmWq-W8xw_6WWWWWWGhfr6Wu-zl-hVimg6WWWWWWW1Ybq6WWWaWXy_u7qfw6WWWWWW"
"SoqY7WWWy-_d-4ezt5WWWaWXy-1cjZ7WWWWWWCegx6WWWWWWGYWo6WWWWWWy_ud1gpj6WWWWm-3Yek6WWW_Fldk6WWW2-xc6WWWy-_dWde2Zai6WWWamWy-u"
"t1Xtj6WWWWGgoh6WWW_--Rpm-6WWW2exw6WWWy-_d-ae1kjn5WeWYmWaWX8mke7Wu--lWu-W8myX7WWW2hhx6WWW_--7cvt7WWWYWW4kma7WWW_--FhjX7WW"
"W2xji6WWWWm-Z-u7akt6WWWWGiZr6WWWWm-BqZn7WWWWGkph7WWW_--FsdZ7WWW2w_z6WWWWm-l-5uXw7WWW_lWqVefZ7WWW2sd_6WWWWWWCoki7WWW_--Fi"
"qa7WWW2szr6WWWWm-ZVctb7WWWWGauY7WWWWm-Bksz7WWWWGwks7WWWWm-3ef-7WWWWGolw7WWWWGcia8WWW2qcf8W8_fm8Wu-xl-BYyf7WWW2uXZ7WWWWm-"
"3cli7WWWWGeme7WWWWGmom7WWW2yiq7W8Wwv7Wu-zl-Bspw7WWWy-_t_y7_ls5WWWWWWGmec5WeWYmWq-W8jqk7WWWWWWGws_6Wu-zl-h-_7hw-5WWWaWXy-"
"1ucg7WWWWWWCjng7WWWWWWGWjx6WWW_l--_tViYo6WWW2zrh6WWW_F_wi6WWW2Ysl5WWWWWWy-_7foo6WWW_--3sfo6WWW2aoi6WWWWWWyVZXj6WWW_--3ub"
"k6WWW2Wir5WWWWWWyVznt6WWW_--3qst6WWW2eYl6WWWWm-3_cz6WWWWGbnw6WWWWGomW7WWW2q-Z7W8uze7Wu-xl-xWdu1ykn7WWW2sfx6WWWy-_d-zF_yW"
"6WWWWWWGyhj5WWWWWWWWytn1Yfn5WWWWWWe-ZGlws5WWWWWWuWW8db_4WWWWWWWWyVond5WWWWWWm-3qYe5WWWWWWmWyFiWq4WWWWWWe-3spe5WWWWWWOurk"
"4WWWWWWm---6oa_4WWWWWWGurk4WWWWWWWWyVajX5WWWWWWe-3wnn5WWWWWWOquu4WWWWWWe-3mry5WWWWWW4Wkh6WWWWW2ayt6WWWWWWCcej6WWWWW_7quc"
"5WWWWWW8eYZ6WWWWWW8mzi5WWWWW2ysq5WWWWW_l_pVibr3WWWWWYmWaW1Wta5WWWWW_lWaW1cy_4WWWWWWWWWmp1sub5WeWYmWaWX8nh_6Wu-zlXq-2muW7"
"WWWWW_Fttr6WWWWWWu-tNneo5WWWWWWm-3olo5WeWYmWqWz7ijd7WWWWWWm-3gxd7Wu-zl-p-_7ixo5WeWYmWyWz7-jr6WWWWWWe-3-ie7WWWWWWOkql6Wu-"
"zl-x-w7i_q5WWWWWYuVmw-6WWWWW_Fkis6WWWWWWu-2tgc5WWWWWWe-3stZ6WWWWWW4qhs6WWWWW2job7WWWWWWCqrr6WWWWW_7WXx5WWWWWW8nlh6WWWWWW"
"8ciZ6WWWWW2Whj6WWWWWWu_u-1omz6WWWWW_tWdW1poY6WeWYmWq-yt3Wa-6WWWWWWGwkl6Wu-zl-h-_7kWx5WWWWWWu--Fily5WWWWWWWW4gmf6WWWWWYGo"
"Y_6WWWWW_Fzmn6WeWYmWy-u7kZY7WWWWWWe-3ivm7WWWWWWOWcv6WWWWWWe-3anx7WWWWWYGcug8WWWWW_7gzc7WWWWWW8wq-7WWWWWW8ari7WWWWW2ikr7W"
"u-zlzh-s7sdy5WWWWWWWW4Wzh5WWWWWWe-3Yvj6WWWWWW4eW_6WWWWW2ovk7WWWWWWCexZ7WWWWW_7omY6WWWWWW8Z_s6WWWWWW8unh6WWWWW2ufs6WeWYm_"
"p_qNwXo5WWWWWYmWaW1uXb7Wu-z-zp-_7yZX7WWWWm1Y_i6WWWWWW8qdp5WeWYm_pWbOep_6Wu-zl-x-wlo1fyv5WWWWWWa-ZO_ax5WWWWWWScwY5WWWWWYi"
"-z7Wft6WWWWWW8bfr6WWWWWW4zhi6WWWWWWOvey6WWWWW_l-1yph5WWWaWXi-1bdd7WWWWWWSezw6WWWy-_7sfo6WWWWWYy_1Yvb7WWWWWWCepy6WWWWW_7l"
"cY6WWWWWYGdlr6WWWWW_l-tNzqj5WWWWWWm-3mjj5WWWWWWmWy7Zgx5WWWaWXeW2ojZ7WWWy-_d-1ugx5WWWaWXy-1XYx6WWWWWWCctZ7WWWWWWGtbo6WWWy"
"-_t-1e_W6WWWWWWGnyg6WWWWWWm-t7xt_4WWWWWWWW4Wgu4WWWWWYi-z7y-Z7WWWWWWCzrq6WWWWW_7ZZd6WWWWWYGwmy6WWWWW_--3yvm6WWWWWWu_1aje6"
"WWWWWYG-dz6WWWWW_Fpwm6WWWWWWu-t7jpm5WWWWWYi-1wg_6WWWWWW8-qy6WWWWWW4_rc6WWWWW_7Wsx5WWWWWW4ucp6WWWaWX4eio6WWWy-W8jti6WWWWW"
"_p_1ouy5WWWWWWSWnZ5WWWaWXi-1ozZ7WWWWWWSwri6WWWy-_7hiZ6WWWWWWq_1WXf6WWWWWY8YqX7WWWWWW8iqz6WWWWWW4h-i6WWWWW_7kds5WWWWWW4-Z"
"n6WWWWWWCaj_5WWWWW2hYe6WWWWWWq_vd1iXW7WWWWW-hWWGiYo6WWWWW1uWh6WWWWWWu--7sWd6WWWWWW8aaY6WWWWW_lWWOYlh6WWWWWWWWc8qsW6WWWWW"
"WWWwFsdc6WWWWWWWW6fwv5WWWWWYi-vl2fr_6WWWWWW8myy6WWWWWW4erc6WWWWWWOgzq6WWWWW_-_XGbqi5WWWWWWGuvt4WWWWWWm--Fuos5WWWaWXy-1la"
"a7WWWWWWCzqx6WWWWWWGini6WWWy-_t-vFxXm5WWWWWWWW4knZ5WWWWWWe-3eYZ6WWWWWW4yts6WWWWW2exb7WWWWWWCnwr6WWWWW_7kWs5WWWWWW8gog6WW"
"WWWW8yY_5WWWWW2dyd6WWWWW_l-tFcYu5WWWWWYi-1crc7WWWWWW8ipa7WWWWWW4s-l6WWWWW_7eXb6WWWWWW4a_w6WWWaWX4_q_6WWWy-W8yau6WWWWW_p_"
"1uqX6WWWWWWSqXf5WWWaWXi-1Wai7WWWWWWSsbs6WWWy-_7whj6WWWWWWq_1ucl6WWWWWY8oxg7WWWWWW8mnb7WWWWWW4kqu6WWWWW_7yY_5WWWWWW4Yeu6W"
"WWWWWCmwc6WWWWW2kcn6WWWWW_p_1eZs6WWWaWX8eqs7WWWyVWvn7WWWWWW8m-k7WWWWWW4k-y6WWWWWW4_Xp7WWWWW1mxx7WWW4swb8WWWy-y3exd6WWWWW"
"W4ekW7WWWaWX4imZ7WWWWWW4wZx7WWWy-_3evn6WWWWW2inz6WWWWW_3u_Z7WWWWW2mip7WWWWW_3uXs6WWWaW1edf7WWWyVkrY7WWWWW1y_f7WWW4Wyn7WW"
"Wy-yd_nFszv3WWWaWXeWYG_ul5WWWy--dWYGprb6WWWWW1mei5WWWWWWWW_Fclc6WWWWWWu-1sWd6WWWWWW8m_n5WWWWWWu-1akm6WWWWWW8mhg6WWWWWW8k"
"er6WWWWW1ivw6WWW4mzX7WWWy-ydWYGijc5WWWaWXeWYGwlx6WWWy-_t-vFoix5WWWWWWWW4_Yi5WWWWWWWW4tYY6WWWWWWGkdh6WWWWW2jfs6WWWWW_l-tt"
"n1y_z5WWWWWWWWaOooe5WWWWWYu-w7eeu6WWWYW-Fsxi7WWW2uzd7WWWy-W8ead7WWWWWWe-1qXs6WWWWWWqVjau6WWWWm_Bmnu6WWWWm1wwl6WWWWWWOyYX"
"7WWWWW_l-1ixk5WeWYmWaW1aaZ7Wu--lWeVjfj7WWW2bke7WWW_--RhYm7WWW2Yo-6WWWy-_7rWt6WWWWWYy_1uod7WWWWWWCc_X7WWWWW_7mnc6WWWWWYGa"
"Yw6WWWWW_l-tNvpr5WWWWWWm-3rhr5WWWamWy-w7Wxs6WWWWGttq6WWW_--RWiW7WWW2bux6WWWy-_tVks-5WeWYmWaW1cfj7Wu--lW4Wtq7WWWYWWWW1gaf"
"7WWWy-_d-1om-5WeWYmWaW1WXj7Wu-XWW4ntq7WWW_lWqVvjW7WWW2wux6WWWWWWCzue7WWW_--FuZX7WWW2tpr6WWWy-_t-1Yeb6WWWWWWGugl6WWWWWWm-"
"t7mga5WWWWWWWW4clz4WWWWWYu-w7Yqb7WeWYm_hW2xn-6Wu-zlXeVZhb7WWWWm_BtWc7WWWWm1agv6WWWWW_7ugh6WWWWWYGk-X7WeWYm_p-2buu6Wu-zl-"
"hW1kjr6WWWWWWu_1cki6WWWWWYGWaY7WWWWW_F-Zr6WWWaWXa-s7_X-6WWWy-WCceZ7WWWaW-Fkhe7WWWy-_7czt6WWWWW2rXd7WWWWW_lVwku5WWWWWYuVy"
"YX7WWWWWWqVexY7WWWWWW8gWX7WWWWWW4chl6WWWWW_7gga6WWWWWW4Yrt6WWWaWX4yay6WWWy-W8hgs6WWWWW_l-1Ydf5WWWaWXi-1zke7WWWWWWSqmr6WW"
"Wy-_7jki6WWWWWYy_1d_c7WWWWWWCjls6WWWWW_7Zk_5WWWWWWGmwc6WWWWW2fwm6WWWam_x_s7s-X7WWWWGYr-6WWWy-WCbyc7WWWYW-FnZn7WWW2sdh7WW"
"Wy-_7epx6WWWWW2y-h7WWWWW_lVm_W6WWWWWYuVjaa7WeWYm_Btcm7Wu--lW4cXx7WWW_-WaVsrc7WWWWm_B_md7WWWWm1oWw6WWWWW_7ikk6WWWaWX8vbi7"
"WWWy-W8-va7WWWWWWyUYki7WWWWWWCase7WWWam-3ke-7WWWyFkpk7WeWYGYZb8Wu-zFsbs7WWW4mx-7WWWy-y3soq6WeWYmW4gaw7Wu--lW4prz7WWW2ajr"
"7WWWWm-3pXW8WWWWGncx7WWWWGdqa8WWW2cuf8W8kqm8Wu-vlW4_wj7WeWYmW4wtg8Wu-zl-3kcp7WWWWW1gqx7WWW4iob8WWWy-ydVcal5WeWYmWaW1itZ7"
"Wu--lWeVfcn7WWW2knh7WWW_--Rcwn7WWW2_eW7WWWy-_7mgu6WWWamWyUXfp7WWWWGk_l7WWWWmWGcua8WWW_l-Bedu7WWW2lem7WWWWm-3afx7WWWWGnus"
"7WWWWGncW8WWW2eoa8W8jdh8Wu-vl_3_z-6WeWYmW4kfW8Wu-XmW4pjx7WWWy-WqUoWi7WWWWWWCueb7WWWWW_7yad6WWWWWWGucm6WWWWW2yWx6WWWWWWeV"
"cyj7WeWYmW4Yzg8WWWWW_7rvq7WWWWWWGmux7WWWWW2_ec8Wu-zlz3kka7WWWWW2bWq7WWWaW-pUydr7WWWyVorn7WWWWWWCsjf7WWWWWW4Wmp7WWWWW1oXy"
"7WWW4szb8WWWy-y3Wzm6WWWaWX8Zvm7WWWWWW4upx7WWWy-_3kmy6WWWWW2q-f7WWWWW_7ygX7WWWaW1ert7WWWyVvYm7WWWWW1_ou7WWW4dzX8WWWWW_h_q"
"Vqup6WWWWm-3mjq6WWWWGq-i6WWWy-WWW2yeX7WWWWW-dWXGXft6WWWWW1kbm6WWWWWWWWz7-Zu6WWWWWWu-1Yu_6WWWWW-7sn-6WWWWWXuVZXj6WWWWm_7Z"
"XW7WWWWm1zYe6WWWWWWWWz7cox6WWWWWWu-1cgY7WWWWW-7inY7WWWWWXuVkvt6WWWWWW8ntn6WWWWWWuVw_b7WWWam-3apw7WWWyFuvl7WeWYGnnb8Wu-XG"
"p_-7WWWy-_3wmy6WeWYmW4fiW8Wu-zFeWt7WWWam_3yYW8WWWyFanh7WWWWW1sro7WWW4ntx7WWWWmzp-3Yqy7WWWWGoju7WWWy-WiW2_cs7WWWWWWqVYzw7"
"WWWWWWCfcn7WWWWW_dWuFgmm6WWWWWWWWc8med6WWWYWXeWx7uqe8WWW2-k_7WWWWm-Z-3pjs7WWWWGiho7WWW_--RcYy7WWW2q-o7WWWy-_tVoWj6WeWYmW"
"aW1pqz7Wu-XmWeVd-z7WWWWWWSigv7WWWy-_t-t7n-i6WWWWWWWW6ah-5WWWWWWWWw7tdq6WeWYmWaW1WeZ8WWWWWWWW6wet7Wu-zl-xVxgs6WWWWWWGshZ7"
"WWWWW2ufo7WWWWW_l-t7gjm6WWWWWYuVnZn7WWWWW_7yaw6WWWaWX8ak_7WWWy-W8yos7WWWaW-t-3dav7WWWy-_7uYd7WWWWWWmVY_e6WWWWWYuVvcs7WWW"
"WWWWW1Wuh7WWWWW_7ero6WWWaWX8mhp7WWWy-_7cu_6WWWWW2poi7WWWam_x_qd1yls6WWWWGaZq6WWW_--Rv-i7WWW2imd7WWWy-W8yol7WWWWW-d-XGqyb"
"7WWWWWXq-W8uYZ7WWWWWW8s-W7WWWWm_3opa7WWWWm1d_k6WWWWWWObyW7WWWWWWe-y7_Yd7WWWYW-Fkts7WWW2ppm7WWWy-W8een7WWWWWWe-1gfa7WWWWW"
"WqVesc7WWWWm_Bard7WWWWm1_xv6WWWWWWOWkf7WWWWWWyUyxi7WWWWWWCtaf7WWWam-3_j-7WWWyFeYl7WeWYGkbb8Wu-zFmks7WWW4u--7WWWWm_Fzmh8W"
"WWylW4kpp7WeWYmW4dYo8Wu-zl-3qtu7WWWWW1imX8WWW4cji8WWWy-yt_W8snp5WWWWWWGyvy4WeWYmWq-W8Yli7WWWWWWGkWu6Wu-zl-h-_7r-_5WWWYWX"
"y-1oyl7WWW2gae7WWW_--7ka-7WWWYWW4kme7WWW_--Fazk7WWW2eyq6WWWWm-Z-u7Z-X7WWWWGoi-6WWW_--RyXn7WWW2s-g7WWWy-_d-4yla6WeWYmWaW1"
"ivr7Wu-XWW4bhX8WWW_lWqVibn7WWW2mgh7WWWWWWCikn7WWW_--FYbo7WWW2wXW7WWWWm-ZV-kp7WWWWGoWm7WWWWm-Bxsa8WWWWGuay7WWWWm-3nxc8WWW"
"WG_jX8WWWWGfXi8WWW2men8W8nyu8Wu-xl-Bsmu7WWW2shm7WWWWm-3omx7WWWWGxvs7WWWWGbfW8WWW2asa8W8fdh8Wu-zl-BqpX8WWWy-_d-u7m-s5WWWW"
"WWWW4yZf5WWWWWWe-3Wji6WWWWWW4Wjx6WWWWW2mhh7WWWWWWCi_X7WWWWW_7cXz5WWWWWW8hbr6WWWWWW8eqb6WWWWW2e_l6WeWYm_p-u7tul7WWWWWWWW4"
"pkZ7Wu-zl-Z-2mro6WWWWWYGehg7WWWWW_Fcmy6WeWYmWaVYfX8WWWWWYGowo8WWWWW_7ssq7WWWWWW8Zwc8WWWWWW8gpx7WWWWW2sZc8Wu-zlzh-s7tlW6W"
"WWWWYi-1hwh7WWWWWW8jkf7WWWWWW4yxv6WWWWW_7gok6WWWWWW4ww-6WWWaWX4Ywh7WWWy-W8zja7WWWWW_l-1mal5WWWaWXi-1qXn7WWWWWWSvaW7WWWy-"
"_7Xfu6WWWWWYy_1n_m7WWWWWWCtXb7WWWWW_7muc6WWWWWWGy_l6WWWWW2fyw6WWWWW_p_1_pv6WWWaWX8ify7WWWyVZzt7WWWWWW8gjq7WWWWWW4Ymf7WWW"
"WWW4pnv7WWWWW1ewY8WWW4Wqj8WWWy-y3gdn6WWWWWW4qWb7WWWaWX4xum7WWWWWW4gYY8WWWy-_3syy6WWWWW2_Yg7WWWWW_3yef7WWWWW2a-v7WWWWW_3s"
"sX7WWWaW1Wpt7WWWyV-Zm7WWWWW1snu7WWW4ewX8WWWWmzp_q7umd7WWWWGeya7WWWy-WCg-j7WWWYW-Fksu7WWW2eeo7WWWy-_7WzX7WWWWW2itp7WWWWW_"
"lVagb6WWWWWYuVoWh7WeWYm_Beht7Wu--lW4oja8WWW_-WaVcpj7WWWWm_BWvk7WWWWm1ed-6WWWWW_7ysp6WWWaWX8yZp7WWWy-W8sfh7WWWWWWyUiWq7WW"
"WWWWCaxl7WWWam-3yvd8WWWyFacs7WeWYGW_j8Wu-zFme_7WWW4mle8WWWy-y3yrw6WeWYmW4qWZ8Wu--lW4ijd8WWW2wW_7WWWWm-3yyf8WWWWGeca8WWWW"
"GWtk8WWW2uhq8W8e-x8Wu-vlW4mur7WeWYmW4Yfr8Wu-zl-3gqx7WWWWW1eua8WWW4yrl8WWWy-ydVaqo5WeWYmWaW1m_e7Wu--lWeVavu7WWW2Yoo7WWW_-"
"-Rstv7WWW2umb7WWWy-_7ca_6WWWamWyUqzw7WWWWGoct7WWWWmWGm_k8WWW_l-BWoW8WWW2got7WWWWm-3mqZ8WWWWGwl_7WWWWGoqe8WWW2egj8W8yfq8W"
"u-vl_3qwc7WeWYmW4anf8Wu-XmW4ija8WWWy-WqUqlp7WWWWWWCmzh7WWWWW_7uph6WWWWWWGeWr6WWWWW2abW7WWWWWWeVebs7WeWYmW4wrr8WWWWW_7uby"
"7WWWWWWGapZ8WWWWW2cyk8Wu-zlz3ioh7WWWWW2omy7WWWaW-pUe-z7WWWyVmcw7WWWWWWCegm7WWWWWW4oXy7WWWWW1mib8WWW4Ygm8WWWy-y3qes6WWWaW"
"X8k-t7WWWWWW4uqa8WWWy-_3mrY7WWWWW2mym7WWWWW_7ysd7WWWaW1if-7WWWyVmht7WWWWW1qhW8WWW4ceg8WWWWmzpUqma8WWWWGWiW8WWWyVquz7WWWW"
"WWC_ou7WWWam-3ipp8WWWyFqz-7WeWYGYbw8Wu-zFWgf8WWW4Yjq8WWWy-y3qZy6WeWYmW4imb8Wu--lW4Wsh8WWW2ysW8WWWWm-3swk8WWWWGWte8WWWWGy"
"Xq8WWW2ilv8W8wWX9Wu-vl_3Wnf7WWWWW2WXv7WeWYm_3WWk8WWWWW2csw8Wu-zlz3WYl7WWWaW1i-e8WWWyVWjW8WWWWW1meg8WWW4icr8WWWy-y3mWo7We"
"WYGiXo8Wu-1arp8WWWWGevi8WWWWGaxu8WWW2uw_8W8moc9Wu-vFu-Z8WeWYGkn-8Wu-zFudk8WWW4wrv8WWWyFqvp8WeW2moc9Wu-1e_-8WWW2aXd9W8gWl"
"9Wu-vlyZ_m7mWz3WeWYmWaWX8Wks5Wu----ZWX8anv6WWW2WZp6WWWWGiZq5WWWWWWy-_7i-v6WWWWm-3ynv6WWWWGmlp6WWWWWWyVqup6WWWWm-3mjq6WWW"
"WGabw5WWWWWWyVez_6WWWWm-3uz_6WWWWGezr6WWWWm-3ypa7WWWWGqxX7WWWWGuzd7WWW2qkh7W8aim7Wu-zl1qb-7WWWy-zZWX8qzi6WWWWW1ipm5WWWWW"
"----7_qo6WeWYmWaW1ldb8WWWWW1aki7Wu-z-zx-y7ojY7WWWWm1qfj6WWWWWWu-1gpj6WWWWW-7Yek6WWWWW1wqs5WWWWWWu-1znt6WWWWm_7kfe7WWWWm1"
"sWn6WWWWm_7qZn7WWWaW1cYW8WWWyFWhy6WWWWGkts7WWWWGWzX7WWW4WZf7WWWy-_l-w7etZ7WWWWWWeW1uzo6WWWam-xVisj7WWWWm1auW8WWWy-_3eiX7"
"WeWYmW4kfc8Wu-zFahy7WWWWW-3kin7WWWaW1YcX8WWWy-_lVsgp6WWWWWW8Wdw5WWWWWWuVsnf7WeWYmW4vrc8WWWWWW8uco7Wu-zl-3skk7WWWWW1mdu7W"
"WWWW-lVwbz6WWWam-3kmW8WWWyFjdn7WWWaW1plX8WWWy-_3yls6WWWWWX4ueu7WWWWmz3gjo7WWWWm1Z-X7WWWWW1umd7WWW4qtk7WWWy-_lVgcj7WWWam-"
"3epY8WWWyFwtt7WeWYGWrk8Wu-XGoye8WWWy-_3ygY7WeWYmW4cle8Wu-zFuf-7WWWWW-3xYp7WWWWW1ujw7WWW4wtZ8WWWWm_3dki8WWWyFubw7WeWYGaoo"
"8Wu-zFopY8WWW4lWj8WWWyFeoc8WeW2mpt8Wu-1knn8WWW2yYu8W8mf-8Wu-vlyZWX8sug5WeWYmWaWX8azb7Wu--lWaWX8Yry7WWW2XpY7WWWWm-Z-u7mig"
"7WWWWGeqd7WWW_--Rbmy7WWW2Wur7WWW_--Z-6bjy7WWW2lur7WWW_--RX-z7WWW2sde7WWWWm-ZVci_7WWWWG_dw7WWW_--Rlva8WWW2svw7WWWWm-3WYe8"
"WWWWGiiY8WWWWG-Yj8WWW2_Xo8W8qYv8Wu-vl_p-u7coX6WWWWWWWW4svm5WWWWWWWW4ife6WWWWWWGmxn6WWWWW2kdz6WeWYm_p-u7fqw7WWWWWWWW4urh7"
"WWWWWWWW4be-7WWWWWWGyid8WWWWW2zfp8Wu-zlzh-s7mcd6WWWWWYu-1uYY7WWWWW_7Wes6WWWaWX8kks7WWWy-W8-tk7WWWWW_l-1shq5WWWaWXeW2bhe7"
"WWWy-_7dZX7WWWWWYe-1gzk7WWWWW_7Xtj6WWWWWWGakt6WWWWW2gxY7WWWWWWe-1ofp7WWWWW_7_lu6WWWaWX8Wbx7WWWy-_7Wkb7WWWWW2eYq7WWWWW_7c"
"ah7WWWaW1ybZ8WWWyVXbx7WWWWW1gma8WWW4yrk8WWWy-yd_nlu1m_s2WWWWWWWWWW4WkY3WWWWWWWWGWol3WeWYmWaWndy1Wfv4WWWWWWWWWW4mwZ5WWWWW"
"WWWGyZp5Wu----ZWnlq1maj5WWW2mfg5WWWWGerz4WWWy-_t-je2cwq4WWWYmWeWol5azW6WWW2k-t5WWWWGWXt4WWW_l-----3myg6WWW2mzX6WWWWGmnX5"
"WWW_l---Fydv6WWW2s-l6WWWWGWum5WWWWWWy-kdq1uhj5WWWWm-3Wej5WWWWGepg5WWWWm--Vmwg5WWWWGuvW5WWWWmWaWXW1_qs6WWWWm1ewY7WWWWmz--"
"-Vchp6WWWWGoen6WWWWWWu-DymW7WWWWm-ZW1ta_6WWW_Frm-6WWW2qdk6WWWy-_t-z7mcx4WeWYmWaWX8ynp6Wu-XmWeWo7Wmy6WWWWWWu-Difg7WWWWWWa"
"W1Ylm6WWWWWWy-md1aee6WWWWm-3_ve6WWWWGepX6WWWWWWy-DgWn6WWWWm-ZW1nel6WWWWGyZY6WWW_----mt1xht6WWW2jXk6WWW_----EhgW7WWW2yfd6"
"WWWy-_t-zFury4WWWaWXeWnd1yzz5WWWWm-x-W8poY6WWWWGwtx5WWW_l-3mbY6WWW2ovy5WWWWGmtW5WWWWWWy-_7aYa6WWWWm-3qca6WWWWGmv_5WWWWWW"
"yVah-5WWWWm-3dqW6WWWWGusi5WWWWWWyVife6WWWWm-3qse6WWWWGWdX6WWWWm-3omj6WWWWGc_g6WWWWGsqm6WWW2m-p6W8uru6Wu-zl1Wdi7WWW_lzx-_"
"t3moi6WWW2Yqd6WWWWGavi5WWW_l---FmWy6WWW2gxu6WWWWGavX6WWWWWWy-k7eij6WWWWm-3mej6WWWWGurd6WWWWm--Vyef6WWWWGuho5WWWWWWyVmxn6"
"WWWWm-3obo6WWWWGaYg6WWWWm-3mgt6WWWWGmrq6WWWWGinw6WWW2W-z6W8WzY7Wu-zl1qir7WWWWW_t-Dahz6WWWWm-ZW1wox6WWWWGqog6WWWWWWyVio-6"
"WWWWm-3ax-6WWWWGqfr6WWWWm-3aWc7WWWWGuwY7WWWWGwgf7WWW2e-i7W8yao7Wu-zl1mtY8WWW_-zx-kt1Yyn6WWW2qjr5WWW_----Fkad7WWW2hll6WWW"
"y-_t-jFmbb4WWWWWWWWGexX5WWWWWXmWqtn1muz5WWWWW1arc5WWWWW----Fkww5WWWWWWWWW8w_b5WWWWW1ojw4WWWWW_l-hm4_dh4WWWWWXmWq-2oXo5WW"
"WWW1yrp4WWWWW-----3exx5WWWWW1Wb_4WWWWW---F_of6WWWWW1ibj5WWWWW_l-hVegx3WWWWWWWWGeXq4WWWWWXmWqto1opX6WWWWWWWWzNXob6WWWWWWW"
"W3Ywh5WWWWW1wsW5WWWWW----7ysY6WeWYmWaW1wdd7WWWWW1mbx6Wu-zl_x-Eapx6WWWWWWWWWW1mdb7WWWWWWWWWOkYz6WWWWW1yeh6WWWWW---m-1jbx6"
"WWWWWWWWFrrn6WWWWW1w_Y6WeWYm_p-yNbhg6Wu-zlWiWpt2zfy5WeWYmWaWX8ZZo7WWWWW1g_q6Wu-zl_l-_7jds6WWWWWWCaWY6WWWWW1zYi5WWWWW----"
"l3u-d6WWWWWWWWG_uv6WeWYmWaWn7anx7WWWWW1mY-6WWWWW---FqYf8WWWWW1aYk7Wu-zl_x-k7wrh6WWWWW1mxn5WWWWW---FkZ-6WWWWW1_yg6WeWYm_p"
"-iNqvt5WWWWWWWWGymo6Wu-zlXiWnlo1nzz5WWWWW---1mv_5WWWWW1Ywh5WWWWWWWW_Fd-x5WWWWW---1uXz5WWWWm---z7ilZ6WWWWm1odc5WWWWm_--1W"
"dz5WWWWGWmc5WWWWW1epz4WWWWm_--z7mWi6WWWWm1W-_5WWWWW---1qw-5WWWWW1aYi5WWWWWWu-1XWe6WWWWm_7afn6WWWWm1anY6WWWWm_7i_t6WWWaW1"
"ghZ7WWWyFqii6WWWWGgmy6WWWWGygn6WWW4__t6WWWy-zt-DWht6WWWWW1mcf6WWWam_t-zVbsb7WWWWGybm6WWWy--dW2pk-6WWWWm-dWoF_-d7WWWWm1uw"
"s6WWWWWWWWW8c_h6WWWWW-t-D__r6WWWWW1Zif6WWWWW---nt1mWm6WWWWW1fWf6WWWWW---Dqvu6WWWWWXu-n7t-X6WWWWm_7smu6WWWWm1hbz5WWWWm_--"
"Drkv6WWWWGize6WWWWW1qzz5WWWWW_l-xFYon4WWWaWXeWYGpgd6WWWy-WeWqFpff6WWWWWWWWEYoY6WWWWWWWWkl1uvt5WWWWWWWWW8nec6WWWWm_t-X8Yz"
"l6WWWWm1Zes5WWWWW-7zys5WWWWW1Whz4WWWWWWu--7oqb6WWWWW-7rrc6WWWWm---z7Yjp6WWWWm1nhv5WWWWWWu-1fwv5WWWWm_7--d6WWWWGdsw5WWWWW"
"1bff5WWWWWWu-1tYY6WWWWm_7WWv6WWWWm1XWz5WWWWm_7kdW7WWWaW1rlj7WWWyFrbc6WWWWGwwa7WWWWGqhh6WWW4YWo6WWWy-zt-zl3gqX6WWWWW1uhf5"
"WWWWW---Fywn6WWWWW1ctz5WWWWm_--jFyuw6WWWWm1w_X6WWWWm_--1Wjj6WWWWGefZ6WWWWW1e_k5WWWWWWu-1kdh6WWWWm_7kdW7WWWWm1cnb6WWWWm_7"
"mje7WWWaW1eqs7WWWyFeql6WWWWGimj7WWWWGWXr6WWW4mXy6WWWylzt-Dq_W7WWWWG_hq6WWWWW1gdc6WWWWWWu-1sbu6WWWWm_7kYg7WWWWm1som6WWWWm"
"_7ubq7WWWaW1iuZ8WWWyFYjz6WWWWGwYw7WWWWGybZ7WWW4ctg7WWWy-yd-fFukW4WWWWWWWWGYZx4WWWaWXeWoFanr5WWWWWWWWGyml6WWWy-WeWoFsWo5W"
"WWWWWWWGqug6WWWWWWWWktn1jjX6WWWWW---1iaY6WWWWW1qqk5WWWWWWWW_Flk-5WWWWW---1wu-5WWWWWXu-y7-cc6WWWWm_dW1Wpc6WWWWm1gWi5WWWWW"
"---1aYi5WWWWW1iuY5WWWWWWu-y7_si6WWWWWWeW1YrY6WWWam-xVgaw6WWWWm1_oZ7WWWy-_3uvj6WeWYmW4oxd7Wu-zFwt-6WWWam_3coZ7WWWyFmfu6WW"
"WaW1l-Z7WWWy-ztVWeZ6WWWWW1W_k5WWWWWWuVgYo6WWWWW-7n_n6WeWYmW4Y_d7WWWWW1mp_6Wu-zl-3ycs6WWWWW1rfz6WWWWW-lVenh6WWWWWW8sZc6WW"
"WWm_7epu6WWWaW1iXa7WWWyFazl6WWWWGqez6WWWWGyuq6WWW4eix6WWWy-zt-Depy6WWWWW1krj6WWWam_x-kVenv6WWWWGakt6WWWWWWu-Dgjf7WWWWm-Z"
"W1szc7WWW_Fgle7WWW2igr6WWWy--dW2xgc7WWWWWXeWlFxWf7WWWWm_--2_df7WWWWm1cXy6WWWWWWWWz7opc7WWWWWWWW2asa7WWWWWWWW1W_n6WWWWW-t"
"-Dta_6WWWWW1-am6WWWWWWeWl7xcg7WWWWWWWW2ind7WWWWm_-Vesg7WWWWm1opy6WWWWWWqVuWm7WWWWWWCezh7WWWam-3imZ8WWWyFWmo7WeWYGYlf8Wu-"
"zFicw7WWW4mZa8WWWWm_l-BjyW8WWWWm1ulj8WWWy-zZW1rld7WWWWW1ezr6WWWWW--Vfam7WeWYmW4kwp8WWWWW1W_c8Wu-zl-pVdXh7WWWWWW8vjW7WWWW"
"m_7epx7WWWaW1ssj8WWWyFibn7WWWWGgkZ8WWWWGavu7WWW4jjY8WWWy-_l-kVmm_6WWWWW-dWXGzrq6WWWWW1bsj6WWWWW---Dsrz6WWWWWXWWl7sfr6WWW"
"WWWu-1aZy6WWWWW-7vey6WWWWWXuVcpg6WWWWm_7-qy6WWWWm1ksb6WWWWW---Dzfo6WWWWW1_jc6WWWWWWWWl7iuu6WWWWWWu-1lp-6WWWWW-7yk-6WWWWW"
"XuVbgr6WWWWWW8chl6WWWWWWuVraZ7WWWam-3WYt7WWWyFqpi7WeWYGxlX8Wu-XGq-x7WWWy-_3g_v6WeWYmW4wny7Wu-zFdgp7WWWam_3pdy7WWWyFgje7W"
"WWWW1edl7WWW4d_t7WWWWm_p-Boit7WWWWm1mbY8WWWy-zZW1leW7WWWWW1irl6WWWWW--V-ne7WeWYmW4YZe8WWWWW1v_y7Wu-zl-pVyzZ7WWWWWW8-ew6W"
"WWWm_7_Xp7WWWaW1dxY8WWWyFYmf7WWWWGpnv7WWWWGegm7WWW4ryu7WWWy-yd-v7air4WeWYmWaWX8wkm6Wu--lWaWo7ex_6WWW2yhr6WWW_----Ek-e7WW"
"W2ifj6WWWWWWy-m7my_6WWWWm-3ey_6WWW_FWg-6WWW2yus6WWWWmWaW4r-W8WWWWm-t-9smj7WWWWm-ZW1btg7WWW_Fllh7WWW2Wzs6WWWWWWyV_fl7WWWW"
"m-3e_k7WWW_Fkll7WWW2kdY7WWWWm-3Wss7WWWWGmWp7WWWWGZpw7WWW2ia-7W8nob8Wu-vlWaWm7kwx6WWWWWWWW3eim6WWWWWWWWEefe6WWWWWWWWo7sXs"
"6WeWYmWaW1hZd8WWWWWWWWEchW8Wu-zl-xVgoW7WWWWWWWWj7cm-6WWWWWWu-1hxd7WWWWW-7jrd7WWWWWXuVYlt6WWWWWW8qwn6WWWWWWuVhWh7WWWWWW8W"
"iW7WWWWWW8yXn7WWWWW1ksu7WWW4ahY8WWWy-zt-CudY7WWWWW1cxn6WWWWW--Vpgm7WWWWWXuVkXc7WWWWWW8vwy6WWWWWW8jfi7WWWWW1_ap7WWW4Xey7W"
"WWy-_t-hVfn-5WWWWWWWWW8zxg6WWWam-xVgtv6WWWWm1--m7WWWy-_3qXu6WeWYmW4mnu7Wu-XW-3qYn7WWWWm1kpp7WWWy-zh-W8-zp6WWWWWX4au_5WWW"
"WW-7gx_5WWWWW1kmY5WWWWWWu--7vig6WWWWW-7tug6WeWYmXyVfqs7WWWWW-7n_s7WWWWW1eZ_6Wu-zl_3orb7WWWWW2rth7WWWWW-h-y7oft6WWWWm_Bqg"
"t6WWWWm1_-W6WWWWWWu-1-bY6WWWWW-7anY6WWWWW1r_k5WWWWWWq-1_zy6WWWWWW4zhg6WWWam-3kkp7WWWyFq_Y7WWWWGdYl7WWWaGgxn7WWWylz3myy6W"
"WWWm1_ma6WWWWWW4byW7WWWWW1Wkf7WWWWmz3ipa7WWWaW1bfo7WWWyFqvk6WWWWGjkf7WWWWGuXq6WWW4iyw6WWWy-_l-w7a_v6WWWWWWeW1xih6WWWam-x"
"Vdgb7WWWWm1c-q7WWWy-_3k-u6WeWYmW4z_v7Wu-zFcom7WWWam_3nwq7WWWyFhyc7WWWaW1qar7WWWy-_lVyvh6WWWWW-7zhi6WWWWW1cXr5WWWWWWuVnu-"
"6WeWYmW4xbw7Wu-zl_3Xt-6WeWYmW4nuw7WWWWW1mxf7Wu-zl-3vca7WWWWW1haj7WWWWW-lVWdr6WWWam-3mvq7WWWyFipc7WWWaW1zfr7WWWy-_3d_k6WW"
"WWWX4eWj7WWWWmz3_vd7WWWaW1-_r7WWWyFyxv6WWWWGsaj7WWWWGed-6WWW4shc7WWWy-_lVypZ7WWWam-3Yet7WWWyFiui7WeWYGqpX8Wu-XGlcy7WWWy-"
"_3_fw6WeWYmW4zpy7Wu-zFWop7WWWam_3qhy7WWWyFbye7WWWWW1upl7WWW4wYu7WWWWm_3-q-7WWWyFqal7WeWYGidb8Wu-zFurs7WWW4YWW8WWWyFyYw7W"
"eW2asf8Wu-1dXa8WWW2sWg8W8yqm8Wu-z-yl-xVyqa7WWWWGazX7WWWy-WWWZOzml7WWWWWW8v-i7WWWWWW4-hy6WWWam-p-yd1meb7WWWWm1qWx7WWWWm_-"
"-Fkkt7WWWWm1-uf8WWWy-zZWn7Yvg6WWWWW1yXl5WWWWW---Fcfz6WWWWW1_Xb6WWWWW---l7clm6WeWYmWaW1YfX8WWWWW1qvf7Wu-zl_x-EZib7WeWYmWa"
"W1mkm8WWWWW1mwy7Wu-z-zx-i7qe-6WWWWm1rbh6WWWWW---1qii6WWWWW1iZr5WWWWWWu-1pZr6WWWWm_7wwa7WWWWm1qvk6WWWWm_7imj7WWWaW1ify7WW"
"WyFeuv6WWWWGyxo7WWWWGWd-6WWW4sjc7WWWy-zt-DtXW7WWWWW1hfl6WWWWWWu-1tzZ7WWWWm_7iZl7WWWWm1tpw6WWWWm_7wYw7WWWaW1gzg8WWWyFyof7"
"WWWWGkoW8WWWWGihm7WWW4pxu7WWWy-_l-g7upW7WWWWWWeW1Wmm6WWWam-xVWyg7WWWWm1ixy7WWWy-_3il_6WeWYmW4eaY8Wu-zFifu7WWWam_3coy7WWW"
"yFqrj7WWWaW1YYz7WWWy-ztVygn6WWWWW1epu5WWWWWWuVYlc7WWWWW-7idc7WeWYmW4qWZ8WWWWW1mjl7Wu-zl-3qYh7WWWWW1wjq7WWWWW-lVcmw6WWWWW"
"W8uXq6WWWWm_7uWl7WWWaW1e-z7WWWyFWd-6WWWWGqoq7WWWWGWra7WWW4izh7WWWy-_lVaZg7WWWam-3qx_7WWWyFuZq7WeWYGueg8Wu-XGkla8WWWy-_3u"
"r-6WeWYmW4coa8Wu-zFqfx7WWWam_3mta8WWWyFynl7WWWWW1ius7WWW4ew-7WWWWm_3qee8WWWyFeqs7WeWYGWbk8Wu-zFet_7WWW4mqe8WWWyFufY8WeW2"
"exo8Wu-1iyi8WWW2ubp8W8icw8Wu-z-zl-BgZ-7WWWWm1efi8WWWy-zZW1yrc7WWWWW1Whq6WWWWW--Voom7WeWYmW4owo8WWWWW1swa8Wu-zl-pVung7WWW"
"WWW8WWW7WWWWm_7mxx7WWWaW1gbj8WWWyFihm7WWWWGewY8WWWWGmot7WWW4qoW8WWWy-_lVkpo7WWWam-3sye8WWWyFuh_7WeWYGmjs8Wu-XGsam8WWWy-_"
"3ucc7WeWYmW4oyk8Wu-zFwbc8WWWam_3emm8WWWyFsnu7WWWWW1qhW8WWW4kWg8WWWWm_3qrq8WWWyFieX8WeWYGWXx8Wu-zFyfg8WWW4yar8WWWyFydk8We"
"W2edW9Wu-1kwv8WWW2iqW9W8eee9Wu-vlyZ-e7itZ4WWWWWWWWGee-4WeWYmWaWn7qny5WWWWWWWWGmhv6Wu--lWaWn7qxu6WWW2Wdw5WWW_----Fqcn7WWW"
"2Ycs6WWWWWWy-k7ef-6WWWWm-3eg-6WWWWGqav6WWWWm--Venv6WWWWGuuz5WWWWWWyVypa7WWWWm-3yqa7WWWWGWmx6WWWWm-3mig7WWWWGepd7WWWWGisj"
"7WWW2edn7W8uas7Wu-zl-t-Davq7WWWWm-ZW1zko7WWWWGYrx6WWWWWWyVios7WWWWm-3Wss7WWWWGWXe7WWWWm-3ui_7WWWWGsdw7WWWWG_oY8WWW2ubd8W"
"8ssj8Wu-vlWaWn7Wts5WWWWWWWWGWcn6WeWYmWaWn7uco7WWWWWWWWGwje8Wu-zl-x-i7e-o6WWWWW---1chp6WWWWW1oew5WWWWWWu-1_cz6WWWWWW8wns6"
"WWWWWW8WXY7WWWWW1yqd7WWW4exk7WWWy-zt-Dxmf7WWWWW1nps6WWWWWWu-1ngj7WWWWWW8oqY7WWWWWW8rlp7WWWWW1yxw7WWW4ada8WWWy-ydWo-n1WvW"
"5WWWWWWWWWm1ycr4WWWWWWW-7_ko4WWWWWWWWWW3iab4WWWWWWWWm-1efX3WWWWWWWXeW2abk4WWWWWWW-t-1qpn3WWWWWWWWGoua4WWWWWWWWm-1WZu3WWW"
"WWWWX8mou4WWWWWWW-7qlk4WWWWWWWW8Wdw4WWWWWWW1yzc5WWWWWWWWmlp1Wad5WeWYmWaWX8mnW7WWWWWWWWWm1kgr6WWWWWWW-7emn6Wu-zl-xWt7qqd5"
"WWWWWWW-7cfX5WWWWWWWX8mWY6WWWWWWW---1mWm5WeWYmWaWvNk-a6WWWWWWWWm-1eZZ5WWWWWWWXeW2svk6WWWWWWW-t-1mcl5WWWWWWWWG_na6WWWWWWW"
"Wm-1Wxq5WWWWWWWX8euu6WWWWWWW-7Woj6WWWWWWWW8euu6WWWWWWW1iYd7Wu--lWa-elo1wdm5WWW2sWa5WWW_---WeW1ujo7WWW2iYz6WWW_-----VupW7"
"WWW2kco6WWW_---_7Y-Z7WWW2pbk6WWWy-_tWs7slx4WWWWWWW-7gXw4WWWaWXeXwFaco6WWWWWWW-7xkk6WWW_-----d1Xku6WWW2Wjd6WWW_-----t1-zW"
"7WWW2XbY6WWWy-_t-zF-nx4WWWWWWWW8gmg5WWWWWWW1gZx5WWWYWXe-fl1YhY6WWW2_wW5WWW_-----7yZe6WWW2kql5WWW_---Weu1wjg7WWW2m_h6WWWy"
"-_t-zFlic5WWWYWXe-vl1_bk6WWW2_zi5WWW_----FeeX7WWW2jyX6WWW_----l-1mqp6WWW2qoo5WWW_---W8mhp7WWW2uur6WWW_---_7k-e7WWW2_rg6W"
"WW_----7mhp7WWW2uur6WWW_--VkbW8WWW2wxZ7WWWy-_t_bFifa4WWWWWWWX8ybi5WWWWWWW-7WsW5WWWWWWWW8esm5WWWWWWW1WqY6WWWaWXa-etn1wap5"
"WWWWWW4Wlm5WWW_---Vmlm5WWW2oXc5WWWWmWaWXW1qxy6WWW_l-R-wm7WWW2i_h7WWW_----6Wsp7WWW2efY7WWWWm-Z-uVYzs6WWWWGkwq6WWW_--RpkW7"
"WWW2uxx6WWW_----6ceX7WWW2osr6WWWWWWy_6vXc7WWWWm-ZW1_zZ7WWW_FyZb7WWW2_xo6WWWy-_tWs7ye-4WWWWWWW-7yi_4WeWYmWaXv7Wmx6WWWWWWW"
"-7awu6Wu-XmWeWo7qwX7WWWWWWSrbi7WWWWWWWW7ucu6WWWWWWy_6ptn7WWWWWWaW1xnr6WWWWm-ZWn7iqa7WWWWGyfY7WWW_--Rosq7WWW2wwk7WWW_----"
"6ihr7WWW2wxY7WWWWm-ZVprs7WWWWGtYp7WWW_--Rwby7WWW2Zqp7WWWWm-3_l-7WWWWGatw7WWWWGYoa8WWW2mWf8W8Yyl8Wu-zl-t_5vxo7WWWWm-ZW1av"
"m7WWW_F-wm7WWW2Xdx6WWWWWWyVplq7WWWWm-3wkq7WWW_Fosq7WWW2iWc7WWWWm-3bjy7WWWWGnau7WWWWGesW8WWW2upb8W8hii8Wu-xl-xW7kjf8WWW2o"
"_u7WWWWWWy_eVcen6WWWWm-3qwn6WWW_F-vn6WWW2_lg6WWWWWWy-DgYx6WWWWm-ZW1zav6WWW_FYZv6WWW2X-g6WWWWm-ZWvVbmy7WWWWGpau7WWWWmWWW8"
"xyw7WWW_l-x-6mhw7WWW2wbc7WWW_----eNuay6WWW2axo6WWW_----EXjb7WWW2vwg6WWWWWWy-m7-hy6WWW_--3ity6WWW2ygq6WWWWm-ZW8cXp7WWWWGf"
"Xl7WWW_--Ryku7WWW2vll7WWWWWWy_5wcg7WWWWm-ZW1_rd7WWW_Fphe7WWW2rnq6WWWWWWyVmbi7WWWWm-3Wuh7WWW_Fhoi7WWW2tp-6WWWWm-3ofp7WWWW"
"Gbtl7WWWWGeWt7WWW2_jx7W8tmX8Wu-xl-x-6k_n7WWW2cu-6WWW_--Vza-7WWW2Wom7WWWy-_t_r7Yz-4WWWWWWWW8ugl5WWWWWWW1soW6WeWYmWa-u7mdw"
"6WWWWWWWW8ayb7WWWWWWW1sWu7Wu-XmWa-f7oax6WWWWWWWX8-wu7WWWWWWW-6rWt6WWWWWWWW1gZc7WWWWWWWW7anY7WWWWWWW1ZXq7WWWWWWW-cNuwb6WW"
"WWm-x-W8eih6WWW_FuWh6WWW2aqa6WWW_--3iza6WWW2iWc5WWWWWWy-_7pni6WWW_--3avi6WWW2koc6WWWWWWyVzYe6WWW_--3uqe6WWW2Wmo5WWWWWWyV"
"sWn6WWW_--3edn6WWW2_ze6WWWWm-3wns6WWWWGW_p6WWWWGivv6WWW2qbz6W8u_X7Wu-xl-Rs-i7WWW2tcd7WWWWmWa--Vu_d7WWW_l-Reuw7WWW2ceq7WW"
"W_--Z-cOerl7WWW2dqd7WWW_--Rabl7WWW2stq6WWWWm-Z-u7uYY7WWWWG-i-6WWW_--R-xm7WWW2btg7WWW_--Z-6a_m7WWW2axg7WWW_--RYro7WWW2uYW"
"7WWWWm-ZVrep7WWWWGnml7WWW_--Rxnu7WWW2fzl7WWWWm-3Zpx7WWWWGZos7WWWWGwbW8WWW2gua8W8kYh8Wu-vl_p-y7ssg5WeWYmWaWX8q_b7Wu-XmWe-"
"W8uiq7WWWWWWSmqY7WWW_l--_tVuws6WWW2wmm6WWW_Fa-m6WWW2epo5WWW_l---Fx-e7WWW2hza7WWW_Fzbb7WWW2yjf6WWWWWWy-k7qit6WWWWm-3zat6W"
"WWWGlen6WWWWm--VW_n6WWW_Fuoo6WWW2cru5WWWWWWyVWhy6WWWWm-3-hy6WWW_Fzky6WWW2jsp6WWWWm-3WXY7WWWWGeg-6WWWWGmib7WWW2uwe7W8ivj7"
"Wu-zl-t-Dacg7WWWWm-ZW1fzd7WWW_FWce7WWW2jXq6WWWWWWyVhfi7WWWWm-3jfi7WWW_Fypi7WWW2xw-6WWWWm-3rlp7WWWWGZwl7WWWWGYdt7WWW2Wnx7"
"W8_kX8Wu-xl-x-kt1oss6WWW2_su5WWW_---W8c_u7WWW2WYW7WWW_---_7qwj7WWW2jWq6WWW_----7c_u7WWW2WYW7WWW_--Vobd8WWW2lrm7WWWWWWy_c"
"7eqy6WWWWWW4mrs6WWW_---Vaot6WWW2mcy5WWWWWWyVWzX7WWW_--3W-X7WWW2iYv6WWWWm-3yqd7WWWWGa_a7WWWWGqWh7WWW2mkk7W8mjp7Wu-xl-Roju"
"7WWW2eWo7WWW_----6qnw7WWW2aob7WWWWm-ZVsqw7WWWWGkls7WWW_--RquW8WWW2_zs7WWWWm-3y-Z8WWWWGqj_7WWWWGque8WWW2mqj8W8ygq8Wu-zl-t"
"_5Yfn7WWWWm-ZW1y_k7WWW_Fqel7WWW2yev6WWWWWWyVkfp7WWWWm-3_ap7WWW_Fksp7WWW2ajb7WWWWm-3yxw7WWWWGoys7WWWWGmt_7WWW2ihZ8W8srf8W"
"u-xl-x-6qnw7WWW2aob7WWW_--Vief8WWW2qst7WWWWWWyUmZy7WWW_--3exy7WWW2y_h7WWWWm-3gma8WWWWGmt-7WWWWGque8WWW2mqj8W8ygq8Wu-xl-R"
"ufi8WWW2efW8WWWWm-3kYm8WWWWGwnf8WWWWGgar8WWW2elw8W8kuX9Wu-vl_p_a7ysd4WWWWWWWX8Wym5WWWWWWW-7Yeb5WWWWWWWW8uwr5WWWWWWW1wqe6"
"WeWYmWa-e7maW6WWWWWWWX8uqh7WWWWWWW-7e__6WWWWWWWW8uqh7WWWWWWW1md-7Wu-XmWa-e7yvz5WWWWWWWX8ufe7WWWWWWW-7jtx6WWWWWWWW8ufe7WW"
"WWWWW1Ydx7WWWy-We-fdn1uYj5WWWWW_Fqyw5WWWWWYm--NWvW5WWWWW_lW4w_b5WWWWWYm-x7egj5WWWWW_lW4maj5WWWWWWWW4wmZ6WWWWWYGqmt6WWWWW"
"WW-7evg6WWWWW_l-3iWo5WWWWWWW1Wnc6WWWWWWWWiNXon5WWWWWWWWW8yey5WWWWWWWW8mbY6WWWWWWGmoi6WWWWWWm-t7uq_4WWWWWWWW4Wlu4WWWWWWW-"
"7ybt4WWWWWWWXqFodq5WWWWWWWW4Wmc5WWWWWWWW4dsw5WWWWWWGefZ6WWWWW2clj6WWWWW_l_3YWW5WWWWWYmW4kbf6WWWWW_lW4dhW6WWWWWYm-x-1YyY6"
"WWWWW_l-3nmk5WWWWWWWWuFurk4WWWWWWWXyFgfW6WWWWWWWWWGiXr5WWWWWWW-3ayu4WWWWWYmW4_nz5WWWWW_l-3Wec5WWWWWWW1whs5WWWWWWW-dVavc3"
"WWWWWYmWaW1alz4WWWWWWWWWGyci5WWWWW_--ZGash5WWWWWWGwtt4WWWWWWm--FbYw5WWWWWWmWyFacl5WWWWWWWW4kqZ5WWWWWWWW4Wor5WWWWWWGydz5W"
"WWWW2qhd6WWWWW_l_pVWZu3WWWWWWWWGyZj4WWWWWYmWqVynf5WWWWWWWWGWrz5WWWWW_l-hVew_3WWWWWWWX8mtZ5WWWWWWW-7equ4WWWWWWWW8quc5WWWW"
"WWW1yks5WWWWWWW-dVWpY4WWWWWYmW4Wdl5WWWWW_Fuzs5WWWWWWWW4Wgf5WWWWWWWW4ydz5WWWWWWGW-b6WWWWW2Wzm6WWWWW_l_3mX_4WWWWWYmW4y-b6W"
"WWWW_l-3mzi5WWWWWWW1ee_5WWWWWWW-3maq5WWWWWYGWzm6WWWWW_Fytd6WWWWWWGmno6WWWWW2yl_6WWWWWWW-dlo1una5WWWWW_lW4mfg5WeWYmYq-y7c"
"iX7WWWWW_lW4ayb7Wu-zl-x-wNurt5WeWYmWaWX8pWn7WWWWWWWWWGeq-6WWWWWWWW4gxu6WWWWWWW-7igs6Wu-zl-xWp7khw5WWWWWWWW4mwg5WWWWWWWW4"
"dqW6WWWWWWGyef6WWWWW2ulp6WWWWW_l_3Yta5WWWWWYmW4uYm6WWWWW_lW4anc6WeWYmWaWj7Wtp7WWWWWWWW4mhc7WWWWWWWW4eZu7WWWWWWGiu-7WWWWW"
"2ovg8WWWWW_l_3wo_6WWWWWYmW4qpc8WWWWW_lW4mbz7Wu-zlXi-wt1Zwe6WWWWW_l-3cvp5WeWYmYqWz7ytW8WWWWW_l-3arf7WWWWWWWWuFa_j6Wu-zl-x"
"Wx7kZd6WeWYmWaWX8gdz7WWWWWWWWWGtrp7WWWWWWW-3mwt6WWWWWYmW4why7WWWWW_l-3gdZ7WWWWWWW1bkq7Wu-zl-x-o7_ve6WWWWWWW-3klb5WWWWWYm"
"W4Zwn6WWWWW_l-3e_r5WWWWWWW1e_e6WWWWWWW-3_ty5WWWWWYGcYz6WWWWW_FsWp6WWWWWWGax-6WWWWW2xsj7WeWYm_p_aNYhe5WWWWWYmWaW1ub_6Wu-z"
"l-x-_7_mm5WeWYmWaWX8ali7WWWWW_--ZGbyh7WWWWWWGmxt6Wu-zl-h-_7fyW6WeWYmWaWX8sdv7WWWWWWmWyFrcl7WWWWWWWW4slZ7WWWWWWWW4_Zq7WWW"
"WWWG_cx7WWWWW2Zvb8Wu-zlzh-s7kcY6WWWWWWWW4yum5WWWWWWWW4qse6WWWWWWGobo6WWWWW2nhz6WeWYm_p_qNm_q5WWWWWWWWG_ei6WWWWWYmWqVg_f7"
"WWWWWWWWGymy7Wu-zl-x-k7iss5WWWWWWWWGuin6WeWYm_p-iNgYx5WWWWWWWX8wiZ7WWWWWWW-7mbt6WWWWWWWW8wiZ7WWWWWWW1ekq7WWWWWWW-dVWp_5W"
"WWWWYmW4yol7WWWWW_Fyqs7WWWWWWWW4aXf7WWWWWWWW4Wfx7WWWWWWGueZ8WWWWW2qrk8WWWWW_l_3uny6WWWWWYmW4qfa8WWWWW_l-3aXf7WWWWWWW1etx"
"7WWWWWWW-3yol7WWWWWYGqrk8WWWWW_Fgua8WWWWWWGqrk8WWWWW2olx8Wu-zlzh_Y7mgg4WWWWWYmW4agw5WWWWW_Fiyc6WWWWWWWW4Wkq5WWWWWWWW4omj"
"6WWWWWWGmgt6WWWWW2ixY7WWWWW_l_3yve5WWWWWYmW4ans6WWWWW_l-3mwv5WWWWWWW1alj6WWWWWWW-3ecX6WWWWWYGixY7WWWWW_FYou6WWWWWWGaWc7W"
"WWWW2Yoq7WWWaW-t_bdn1uwd5WWWy-W8cba6WWWWWWWW2wdm5WWWWW_F_bW6WWWWWYm-zFgcY6WWWWWWWWW8aai5WWWWWWWW2WxY5WWWWW_lW4ewe5WWWWWY"
"m-v7ecb6WWWWWWWW2mlm5WWWWWWu-1ubk6WWWWWW8uqe6WWWWWW8uoo6WWWWW1aot6WWW4cc_6WWWy-_NyZb7WWWWW_l-1mnm5WWWaWXeW2oiY7WWWy-_7kd"
"w6WWWWWWm-1hre6WWWWWYGkty6WWWWW--_7rm-6WWWWW1nyl6WWWWW_l-3iyr5WWWWWWW1ygh6WWWWWWWWiNxcr5WWWWWWWWW8kpX6WWWaWXeW2nui7WWWWW"
"WWW4oiu6WWWy-_t-1afd6WWWWWWG_un6WWWaWXu_5nir6WWWy--dW2wYc7WWWWW-lWm7_ia5WWWWWWWW4epz4WWWWWWW-7czy4WWWWWYuWs7uay6WWWWW_7w"
"xj6WWWWWYGgsb7WWWWW_--3dpu6WWWWWWu_1_il6WWWWWWuWu7oYu5WWWWWYu-1_pl6WWWWW_7_ga6WWWaWX8eky6WWWy-W8dss6WWWWW_l-1yif5WWWaWXe"
"W2cvr6WWWy-_7mqi6WWWWWWm-1vg_5WWWWWWGezc6WWWWW2iXn6WWWWW_l_3YfZ5WWWaWXeW2kep6WWWy--dW2bgx6WWWWW1hwj6WWWWW_lW4ama6WWWWWWW"
"Wi7qvY6WWWWWYu-1ity6WWWWW_7e-m6WWWaWX8wsl7WWWy-W8cke7WWWWW_l-1yum5WWWaWXeW2k-Y7WWWy-_7_mx6WWWWWWm-1Xdf6WWWWWWGapo6WWWWW2"
"_pz6WWWWWWe-1hoi7WWWWW_7yZp6WWWaWX8Xbq7WWWy-_7en-6WWWWW2lij7WWWWW_7iXb7WWWaW1atx7WWWyVcYq7WWWWW1exy7WWW4Ykc8WWWy-yd_1yje"
"5WWWaWXeW2Yfx6WWWy--dW2ycd7WWWWW1svr6WWWWWWu-1ttg7WWWWWW8pkW7WWWWWW8a_m7WWWWW1oju7WWW4qZY8WWWy-ydW2kXi6WWWaWXeW2-zu7WWWy"
"-_t-1jas6WWWWWWGefZ7WWWWW2dXo7WWWaW-t_rVqmj6WWWy--dWqFxht6WWWWW1jdm6WWWWW---DcXX7WWWWWXu-n7iug6WWWWWW8kwb6WWWWW---Dzio6W"
"WWWW1Wlc6WWWWW_l-3sWo5WWWWWYeWk7fyt6WWWWWW8-vn6WWWWWWeW8-xm7WWWWW-t-5maZ7WWWWW1gzn6WWWWWWu-1etc7WWWWWW8czy6WWWWWW8ypi7WW"
"WWW1ksp7WWW4zry7WWWy-yd-1Yju5WWWaWXeW2ffc7WWWy-WeW2qqW7WWWWW_l-p7gvp4WWWWWWWXs7wkm6WWWWWWWWc8kza6WWWaWXe-5q_g6WWWy-_tWw7"
"cvi6WWWaWXeW2m-u7WWWWWWW-3s-s6WWWWWWWW8ulY7WWWWWWW1wZq7WWWy-_t_1yX-5WWWWWWW1oks6WWWWWYm-f7YZk6WWWWW_FYrg6WWWWWWWW6hbz5WW"
"WWWWW-3om_4WWWWWYmW4s-b6WWWWW_l-3_hj5WWWWWWW1yi_5WWWWWYm-j7mZs6WWWWW_Fvaq6WWWWWWWW8Wcs6WWWWWWGsdZ7WWWWW2ZXo7WWWWWWW-7mqW"
"7WWWWWWu-l7cer6WWWWWW8_pl6WWWWW_FsWk6WWWWWWWW6_rc6WWWWWYu-1qte7WWWWW_7ghm6WWWaWX8rYm7WWWy-_7m-x6WWWWW2pjf7WWWWW_l_1iYa5W"
"WWaWXeW2uvq6WWWy--dW2oh-6WWWWW1vpl6WWWWWWu-1ybZ7WWWWWW8Xmw6WWWWWW8wbf7WWWWW1Wxl7WWW4opu7WWWy-yd-1maq5WWWWWWW1iyc6WWWaWXe"
"-1kaW7WWWWWWW1ftm7WWWy-_t_1qWx5WWWWWYGYrw6WWWWW_Fnvm6WWWWWWGk-y6WWWWW2Ylg7WWWWW_l_ZFecg3WWWaWXeWYGsYc5WWWy-W8iu-5WWWaW-t"
"--7_Wq5WWWy-W8kej6WWWWWWu-X8wr_5WWWWWW8wpY5WWWWWWu--7uyi6WWWWWWeW_7waX6WWWWWWu-1aaY6WWWWWW8uYl5WWWWWWu-1mhg6WWWWWW8isa6W"
"WWWWW8kWl6WWWWW1uhq6WWW4obx6WWWy-_NiwW7WWWWWWW-x7osj6WWWWWWu-1ldk6WWWWWW8sps5WWWWWWu-1qst6WWWWWW8edn6WWWWWW8zky6WWWWW1W-"
"X7WWW4uYf7WWWy-_Ns-i7WWWWW_-_X8dip5WWWWWWGwxy4WWWWWWm--Fku_5WWWaWXeW2ide7WWWWWWGvzq6WWWy-_d-z7umc6WWWaWXeW2b_q7WWWWWWGtq"
"Y7WWWy-_t-v7qus5WWWWWWWW4vef5WWWWWWe-3qii6WWWWWYGymX7WWWWW_7XWz5WWWWWW8gzq6WWWWWW8cnb6WWWWW2p-l6WWWWW_t_-7air6WWWWWYGtlj"
"7WWWWW_Fpm-6WWWWWWu-t7waW6WWWWWYu-1sbw6WWWWW_7kmk6WWWaWX8-mh7WWWy-W8ija7WWWWW_l-1Yhl5WWWaWXeW2YjW7WWWy-_7sYu6WWWWWYe-1aq"
"a7WWWWW_7erc6WWWWWWGs-l6WWWWW2nYx6WWWWWWe-1wbf7WWWWW_7uXn6WWWaWX8mmm7WWWy-_7ily6WWWWW2eyf7WWWWW_7ypX7WWWaW1Wot7WWWyVwZm7"
"WWWWW1epu7WWW4rxX8WWWy-yd_nFi_x3WWWWWWWWGivn4WWWaWXeWoFaso5WWWWWWWWGyof6WWWWWWWWm7ecw5WWWWWWWWG_fs6WWWy--dWo7ang6WWWWW1o"
"cl5WWWWW---FtXz6WWWWW1lab6WWWWW---l7kro6WWWWWWWWGxje7WWWWWXWWk7ueh6WWWWW---1c_h6WWWWW1ier5WWWWWWu-1ker6WWWWWW8kWl6WWWWWW"
"8uYw6WWWWW1ys-6WWW4Wxc7WWWy-zt-Dvu-6WWWWW1igl6WWWWWWu-1wtZ7WWWWWW8qvw6WWWWWW8srf7WWWWW1mem7WWW4qyu7WWWy-yd-fFivY4WWWWWWW"
"X8qif5WWWWWWW-7o_z4WWWWWWWW8iti5WWWWWWW1Wiz5WWWaWXe-fFawu5WWWWWWWX8WgW7WWWWWWW-7sbq6WWWWWWWW8WgW7WWWWWWW1i_m7WWWy-_t_bFm"
"uc4WWWWWYmW4ogr5WWWWW_Fin-5WWWWWWWW4Wkl5WWWWWWWW4rbc6WWWWWWGeql6WWWWW2c-w6WWWWW_l_3gzZ5WWWWWYmW4sZl6WWWWW_l-3Yaq5WWWWWWW"
"1ssc6WWWWWWW-3umx5WWWWWYGc-w6WWWWW_FZbn6WWWWWWGYjz6WWWWW2qug7WWWWW_l_ZFWhf4WWWaWXeW2Why5WWWy-W8Wsm6WWWWWWWW2awu5WWWWW_Fi"
"va6WWWWWYe-1ivw6WWWWWW8uhq6WWWWWW8ys-6WWWWW1mhb7WWW4yli7WWWy-y7mqp6WWWaWX8uvo7WWWy-W8ahh7WWWWW_l-1W_o5WWWaWXeW2i_b7WWWy-"
"_7a-z6WWWWWWm-1qhh6WWWWWWGWXr6WWWWW2ikW7WWWWWWe-1Wxl7WWWWW_7eWs6WWWaWX8Ynt7WWWy-_7ieY7WWWWW2ynm7WWWWW_7m-d7WWWaW1ek-7WWW"
"yVqot7WWWWW1WpW8WWW4qmg8WWWy-yd_1mid5WWWaWXeW2anv6WWWy--dW2Ydc7WWWWW1kgq6WWWWWWu-1gbg7WWWWWW8weW7WWWWWW8mem7WWWWW1uet7WW"
"W4ekW8WWWy-yd-1uWu5WWWWWWW1qih6WWWaWXe-1i_b7WWWWWWW1k-t7WWWy-_t_1uk-5WWWWWYGikW7WWWWW_Fogs6WWWWWWGybZ7WWWWW2sin7WWWWW_l_"
"1myZ6WWWaWX8yli7WWWyVWho7WWWWWW8ivc7WWWWWW8epu7WWWWW1WpW8WWW4qmg8WWWy-y7Wey6WWWaWX8wtW8WWWy-_7y_f7WWWWW2ejv7WWWWW_7ium7W"
"WWaW1qmg8WWWyVsWY8WWWWW1ezh8WWW4oys8WWWWW_h_Ydn1mss5WWWWWW4q-p5WWWWWWWW1Wgf5WWWy-W8kmc6WWWWWWWW2qco5WWWWW_FiaZ6WWWWWYm-z"
"FYla6WWWWWWu-_7yth6WWWWWWeW1sol5WWWWWWWW2oXc5WWWWW_lW4mei5WWWWWYe-u7ado6WWWWWWeW1ipd6WWWam-xVab-6WWWWm1scf7WWWy-_3q_o6We"
"WYmW4anj7Wu-zFgkb7WWWWW-3suz6WWWaW1yqf7WWW_-zFciq7WWW2sil7WWWy-W8eyk7WWWWWWWVyko5WWWWWWuVojt6WeWYmWCoqZ7Wu-zl-3ipx6WWWWW"
"1WzY7WWWWW-lVkmm6WWWWWW8w-g6WWWWm_7ma_6WWWWm1kyq6WWWWW1ywv6WWW4ckW7WWWy-_Nbke7WWWWW_l-1mto5WeWYmWaW1mxe7Wu--lWaW1qgt7WWW"
"2wfb7WWWy-_7qcz6WWWWWWm-1uoh6WWWWWYGur-6WWWWW--_7rwY7WWWWW1uuo6WWWWW_l-3meu5WWWWWWW1ack6WWWWWWWWiNYXw5WWWamWi-_7sxx6WWWW"
"Gouv6WWW_--RiWc7WWW2WgX7WWWy-_tVmpa6WeWYmWaW1Zoq7Wu--lW4hzy7WWWYWWWW1rdm7WWW_----3qvc7WWW2mrw6WWWy-_t-1mbg6WWWWWWGetq6WW"
"WaWXq_4Wvi7WWWWm-ZW1mlg7WWW_Fi_h7WWW2xeu6WWWy--dW2k-f7WWWWW-lWm7yxd5WWWWWWWW4uvW5WWWWWWW-7eiW5WWWWWYuWp7yii7WeWYm_hW2eZb"
"7Wu-z--pVYzi7WWWWm1_X-6WWWWW_7Zrm6WWWWWYGkXf7WeWYm_p-2ivz6Wu-zl-hW1olx6WWWWWWu_1Wfo6WeWYmWy-4oux6Wu-XmWeWo7Wwa7WWWy-WCXy"
"f7WWWaW-Ffql7WWWy-_7kd_6WWWWW2sek7WWWWW_lVqwy5WWWWWYuVuzd7WWWWWWWW1ygq6WWWWW_7wcf6WWWaWX8urX7WWWy-W8pxx6WWWWW_l-1iwi5WWW"
"aWXeW2ynw6WWWy-_7srn6WWWWWWm-1ZWZ6WWWWWWGqqh6WWWWW2gwr6WWWWW_l_3szc5WWWaWXaW1qur7WWWWWWaW1gmu6WWWy--dW2shX7WWWWW1c_o6WWW"
"WW_lW4abf6WWWamWi-g7eqd7WWWWGufb7WWWy-WCuqj7WWWYW-Foju7WWW2zko7WWWy-_7ucY7WWWWW2Ypp7WWWWW_lVuwb6WWWWWYuVk_g7WeWYm_BWkt7W"
"u--lW4mpZ8WWW_l-lVmik7WWWWm1Yr-6WWWWW_7s_p6WWWaWX8ugp7WWWy-W8tzh7WWWWWWyUkkp7WWWWWWCYel7WWWam-3sbd8WWWyFqvr7WeWYGWdj8Wu-"
"zFqsz7WWW4Wxd8WWWy-y3_-v6WeWYmW4_qX8Wu--lW4YZc8WWW2yyy7WWWWm-3qqe8WWWWGmhZ8WWWWG-kj8WWW2muo8W8s-v8Wu-vlW4ydr7WeWYmW4_xp8"
"Wu-zl-3ncx7WWWWW1eca8WWW4iqk8WWWy-ydVW-o5WeWYmWaW1ihf7Wu--lWaW1eXv7WWW2czb7WWWy-_7yn_6WWWamWyU_ew7WWWWGips7WWW_--Ray-7WW"
"W2dbt7WWWWm-3aaZ8WWWWGWe_7WWWWGYde8WWW2qsi8W8mqp8Wu-vl_3oec7WeWYmW4cpe8Wu-XmW4lsZ8WWWy-_dVyai6WWWWWWGWor6WWWWW2yoW7WWWWW"
"WeV-xq7WeWYm_Bfsx7WWWWWWGyhZ8WWWWW2ymk8Wu-zlz3eih7WWWWW2uyx7WWWaW-pUoky7WWWyVwcv7WWWWWWCk_l7WWWWW_7qXs6WWWaWX8brt7WWWy-_"
"7_lY7WWWWW2Zvm7WWWWW_7ezd7WWWaW1yd-7WWWyVikt7WWWWW1WiW8WWW4cZg8WWWy-yd_1mug5WeWYmWaW1uxX7Wu-XGW-s7WWWWm-ZW1q_q7WWWWGsl_6"
"WWWWWWyVuku7WWWWm-3omu7WWWWGscf7WWWWm-3kmW8WWWWGqZy7WWWWGqWb8WWW2WWg8W8m-m8Wu-zl1iho8WWWy-zZW1sbh7WWWWW1g-u6WWWWW--Vg_p7"
"WeWYmW4exu8WWWWW1pah8Wu-zl-pVYpk7WWWWWW8coZ7WWWWm_7ot-7WWWaW1imo8WWWyFmvq7WWWWGxwd8WWWWGcoy7WWW4qlc8WWWy-ydW2ozk6WeWYmWa"
"W1icX8Wu--lWaW1aak8WWW2swy7WWWy-_t-1Yav6WWWWWWGqnc7WWWWW2msr7WWWaW-p_cV_as6WWWWm-3yus6WWWWGmhl6WWWy-WWW2tya7WWWaW-x-BalW"
"7WWWWm-ZW1go_6WWWWGWxl6WWWy--dWqFqfw6WWWWW1zZp6WWWWW---DZka7WWWWWXWWl7h-w6WWWWWWu-1cgY7WWWWW-7wxY7WWWWWXuVXll6WWWWm_7kiZ"
"7WWWWm1_lg6WWWWW---Dpnt6WWWWW1abh6WWWWW_l-3mYs5WWWWWYmWh7wp_6WWWWWWu-1z_b7WWWWW-7fXc7WWWWWXuVoww6WWWWWW8ttq6WWWWWWuVZjf7"
"WWWam-3jd_7WWWyFqmp7WeWYGtgf8Wu-XGxrZ8WWWy-_3an-6WeWYmW4_Ya8Wu-zFgpw7WWWam_3xxZ8WWWyFj-k7WWWWW1ybs7WWW4Xk-7WWWWmzp-3auW8"
"WWWWGmey7WWWy-WiW2XZw7WWWWWWqVeb-7WWWWWWCnwq7WWWam-p-4Zn_7WWWWm1krg8WWWy-zZW1prc7WWWWW1Yxq6WWWWW--Vael7WeWYmW4cvm8WWWWW1"
"hka8Wu-zl-pVsbg7WWWWWW8Xw-6WWWWm_7olw7WWWaW1zch8WWWyFoWm7WWWWG_jX8WWWWGoct7WWW4WgW8WWWy-yd-1gyw5WeWYmWaW1exi7Wu--lWaW1zh"
"_7WWW2Zjf7WWWy-WeW2yuZ7WWWWW_l-p7m-s4WWWWWWWXs7okp6WeWYmWa-Auvo6Wu--lWaWo7qwX7WWW2ggu6WWWy-_tW9k_f6WWWYWXe-5uli7WWW2arl6"
"WWWWWWy-m7iyX7WWW_--3yfY7WWW2ouv6WWWWmWaW4mfb8WWW_l-Rulj8WWW2XlY8WWWWm-Z-3yWw7WWWWGmur7WWW_--Ri_-7WWW2cjs7WWWy-_tVg_l6We"
"WYmWaW1hnX8Wu-XmWeVoWY8WWWWWWSraz7WWWWWWy_2oZn7WWWWm-ZW1shk7WWW_Febl7WWW2ezv6WWWWWWyVmwo7WWWWm-3iho7WWW_FtYp7WWW2xcb7WWW"
"Wm-3_dw7WWWWGmls7WWWWGXb_7WWW2ovY8W8_ff8Wu-xl-x-6uWv7WWW2whb7WWW_--VZgd8WWW2glt7WWWy-_t_1ilX6WWWWWWW1clv6WWWWWYm-c7a__6W"
"WWWWWWW3sgp6WWWWW_Fbvl6WWWWWWWW6epX6WWWWWWW-3a_X5WWWWWYmW4Wog6WWWWW_l-3agn5WWWWWWW1cvY6WWWWWYm-j7egv6WWWWW_Fzgt6WeWYmYqV"
"Wqh8WWWWW_Fufd8WWWWWWWW6Yrw7Wu-zl-xVWfv6WWWWWWGosc7WWWWW2rXs7WeWYm_p_2cdz6WWWWWYmW4vxZ8Wu-zl-xVfuZ7WeWYm_p-2mwe7WWWWWWW1"
"gkx7Wu-XmWa-f7mj_6WWWy-W8ewY7WWWWWWu-1oth7WWWWWWWW1_lw6WWWWWW8kwq6WWWWW_Fqgp6WWWWWYeVuvk7WWWWWW8_oZ7WWWWWW8c-q7WWWWW1ixy"
"7WWW4mwc8WWWy-y7acz6WWWaWX8YmY8WWWy-W8gmw7WWWaW-t-3xXz7WWWy-_7hng7WWWWWWmVgsh6WWWWWYuVyaw7WWWWWWWW1fXl7WWWWW_7elr6WWWaWX"
"8Zts7WWWy-_7awX7WWWWW2zyl7WWWWW_l_1ksd5WWWaWXeW2mWw6WWWWWWWW1Ygf7WWWy--dW1uob7WWWWW1zsq6WWWWW--Vvbq7WWWWWXuVuff7WWWWWW8u"
"v-6WWWWWW8nml7WWWWW1kls7WWW4ws-7WWWy-yd-1ufu5WWWWWWW1qqh6WWWaWXe-1wmb7WWWWWWW1_ht7WWWy-_t_1_Y-5WWWWWYGo_-6WWWWW_Fmwr6WWW"
"WWWGauY7WWWWW2_ym7WWWaW-p_c7e_d7WWWWWW4ab-6WWWy-W8mva7WWWWWWu-1_jj7WWWWWWWW1ilW7WWWWWW8gaw6WWWWW_FWgv6WWWWWYeVowm7WWWam-"
"3Wad8WWWyF_wx7WeWYGcep8Wu-XGwhj8WWWy-_3Wqb7WeWYmW4mgj8Wu-zFenZ8WWWWW-3Xys7WWWWW1up_7WWW4ole8WWWy-y7iv-6WeWYmW4arg8Wu--lW"
"4iZn8WWW2dsb8WWWy-W8glz7WWWam_x_3ntY8WWWWGjd_7WWW_--Rxef8WWW2Zy_7WWWy-_7ubj7WWWWWWmV_zm6WWWWWYuVbfz7WeWYm_BfjZ8Wu-XmWeVu"
"hb8WWWyVkkY8WWWWWWCWYt7WWWWW_7Wix6WWWaWX8nb-7WWWy-_7yse7WWWWW2f-t7WWWam_xUggi8WWWWGsbd8WWWyVmnb8WWWWWWCke-7WWWam-3wpz8WW"
"WyFmXe8WeWYGxoa9Wu-zFYho8WWW4ti_8WWWy-y3iwW7WeWYmW4Ymi8Wu--lW4ezq8WWW2mud8WWWWm-3xlu8WWWWGmfn8WWWWGva_8WWW2mYa9W8ldi9Wu-"
"vl_3ygl7WWWWW2u--7WeWYm_3ets8WWWWW2vdb9Wu-zlz3uWs7WWWaW1ktn8WWWyVfue8WWWWW1ipp8WWW4jl-8WWWy-ydUuch5WeWYmWaW1opY7Wu-XGybv"
"7WWWWm-ZW1krs7WWWWGWg-6WWWWWWyVmvw7WWWWm-3apw7WWWWGqfh7WWWWm-3epY8WWWWGik_7WWWWGXWd8WWW2mwh8W8Wso8Wu-zl1oZs8WWWy-zZW1hij"
"7WWWWW1i-v6WWWWW--Vdht7WeWYmW4mwy8WWWWW1XXj8Wu-zl-pVjXn7WWWWWW8iub7WWWWm_7mrZ8WWWaW1ims8WWWyFYet7WWWWGzmh8WWWWGqx_7WWW4w"
"oe8WWWy-_lVr_u7WWWam-3xWn8WWWyFyyb8WeWYGzbW9Wu-XGypv8WWWy-_3yph7WeWYmW4zjt8Wu-zFxnk8WWWam_3pqv8WWWyF_j-7WWWWW1yvd8WWW4ai"
"o8WWWWm_3kY_8WWWyFase8WeWYGbYb9Wu-zFoso8WWW4ew_8WWWyFult8WeW2idh9Wu-1tfa9WWW2wzh9W8siq9Wu-vlyZVmfy5WWWWWWW1mkm6WeWYmWaVq"
"yk7WWWWWWW1qlZ8Wu--lWaVmvX8WWW2ulh7WWW_--Vtco8WWW2wc-7WWWWWWyUYnZ8WWW_--3imZ8WWW2ein7WWWWm-3dki8WWWWGvhd8WWWWGgbn8WWW2ye"
"s8W8ynz8Wu-xl-R-Yr8WWW2bzd8WWWWm-3WZv8WWWWGwXo8WWWWGmw_8WWW2apa9W8Ywi9Wu-vl_pUehZ6WWWWWYGqzb7WWWWW_Fokx6WWWWWWGyZf7WWWWW"
"2mcu7WeWYm_pUgzq7WWWWWYGYot8WWWWW_Frri8WWWWWWGYot8WWWWW2dWc9Wu-zlzhUeid6WWWaWX8Wmn7WWWyVmZv7WWWWWW8wuh7WWWWWW8-q-7WWWWW1"
"qee8WWW4mto8WWWy-y7sWX7WWWaWX8cZe8WWWy-_7iyl7WWWWW2jiW8WWWWW_7uXt7WWWaW1mto8WWWyVvuf8WWWWW1qrq8WWW4jnW9WWWy-yd_X7mmi3WeW"
"YmWaWX8mph5Wu-XmW4meg6WWWWm-x-W8qZm6WWWWGmpf6WWWWWW4kff5WWWy-W8qYa6WWWaW-p-_7iln6WWWWWW4q_g6WWWWWWyVq-i6WWWWWW4_-r5WWWy-"
"W8sbm6WWWaW-pVezr6WWWWWW4efj6WWWWm-3Wmx6WWWWGcwu6WWWWGkt_6WWW2ybY7W8e-c7Wu-zl1vmu7WWWy-_3evz6WeWYmW4uYW8Wu-XmW4e-w7WWW_-"
"zFceq7WWW2gXk7WWWy-W8ovt7WWWWW-p_W8qnw6WWWWWX4cmZ6WWWWWW8mwb5WWWWWWu--7mxl6WeWYmWaW1kn_7WWWWWW8uZZ7Wu-zl_3Woi7WWWWW2ayo7"
"WWWWW-h-y7bxz6WWWWWWCWkb6WWWWWWu-1-xc6WWWWWW8amo5WWWWWWq-1miZ7WWWWWW4eYl6WWWam-3eyw7WWWyFsuf7WWWWGyms7WWWaGYsv7WWWy-_3_z"
"e6WWWWWW4imd7WWWWW1ppm7WWWWmz3kph7WWWWm1jsp6WWWWW1iYv6WWW4e_-6WWWy-_Ntcd7WWWWWWu_w7ukW7WWWWWWeW1gqm6WWWam-xVa_g7WWWWm1me"
"y7WWWy-_3iq_6WeWYmW4kiX8Wu-zFa_t7WWWWW-3vrj7WWWaW1ajy7WWW_-zFqb-7WWW2vmu7WWWy-W8yov7WWWWWWuUldn6WWWWWW8ivu5WWWWWWuVbcc7W"
"eWYmW4qXY8WWWWWW8mkl7Wu-zl-3-wg7WWWWW1wbq7WWWWW-lVarw6WWWam-3qZy7WWWyFwjj7WWWaW1fZz7WWWy-_3aZq6WWWWWX4zbq7WWWWmz3Wqk7WWW"
"Wm1oi-6WWWWW1eya7WWW4aWi7WWWy-_NqYn7WWWWWWuUgWg7WWWam-3ik_7WWWyFqwp7WeWYGolf8Wu-XGkWa8WWWy-_3mx-6WeWYmW4azZ8Wu-zFW-w7WWW"
"WW-3nql7WWWWW1iqs7WWW4yf-7WWWWm_3vhd8WWWyFWZs7WeWYGnbj8Wu-zFmX_7WWW4-wd8WWWyFitX8WeW2yzn8Wu-1_Zi8WWW2ugo8W8Wcv8Wu-z-zFoZ"
"s8WWWylW4mxx7WeWYmW4dXz8Wu-zl-3mrX8WWWWW1oih8WWW4hWt8WWWy-yt_W8yst5WWWWWWGaYW5WeWYmWq-W8yWp7WWWWWWGuty6Wu-zl-h-_7pvZ6WWW"
"YWXy-1h-s7WWW2Wsk7WWW_--7-xe8WWWYWW4fWl7WWW_--Fdms7WWW2Wrv6WWWWm-Z-u7eqd7WWWWGmya7WWW_--Rpau7WWW2onn7WWWy-_d-4ouf6WeWYmW"
"aW1_sz7Wu-XWW4lbh8WWW_lWqVnau7WWW2vxn7WWWWWWCeev7WWW_--Fgsv7WWW2cob7WWWWm-ZVXhw7WWWWGmls7WWWWm-Byok8WWWWGpsa8WWWWm-3r_m8"
"WWWWGkrg8WWWWGbls8WWW2gfy8W8qia9Wu-xl-BYYW8WWW2fxs7WWWWm-3maZ8WWWWGiwz7WWWWGnyd8WWW2ori8W8zep8Wu-zl-Brxg8WWWy-_d-u7kXx5W"
"WWWWWWW4csi5WWWWWWe-3uun6WWWWWW4mxX7WWWWW2qvo7WWWWWWCxae7WWWWW_7WdX6WWWWWW8exw6WWWWWW8aYg6WWWWW2crq6WeWYm_p-u7fgs7WWWWWW"
"WW4W_e7Wu-zl-Z-2Wru6WWWWWYGdqn7WWWWW_FtYZ7WeWYmWaVY_f8WWWWWYGeoz8WWWWW_7ibx7WWWWWW8nbm8WWWWWW8qpY8WWWWW2ftj8Wu-zlzh-s7Wb"
"b6WWWWWYi-1pop7WWWWWW8--m7WWWWWW4-i-6WWWWW_7axp6WWWWWW4_tc7WWWaWX4ffo7WWWy-W8bwg7WWWWW_l-1y_o5WWWaWXi-1itu7WWWWWWSerb7WW"
"Wy-_7aX_6WWWWWYy_1lXv7WWWWWWCkdh7WWWWW_7goh6WWWWWWGiZr6WWWWW2qfW7WWWWW_p_1Ws-6WWWaWX8ssa8WWWyVhiW8WWWWWW8sjy7WWWWWW4btl7"
"WWWWWW4mbY8WWWWW1efi8WWW4uzt8WWWy-y3ags6WWWWWW4ixh7WWWaWX4-ct7WWWWWW4kch8WWWy-_3WoY7WWWWW2-im7WWWWW_3cqm7WWWWW2jrY8WWWWW"
"_3cud7WWWaW1oo_7WWWyVmys7WWWWW1mt-7WWW4vhf8WWWWmzp_q7isj7WWWWGa_g7WWWy-WCcmr7WWWYW-Fr-W8WWW2tYw7WWWy-_7a_e7WWWWW2uXy7WWW"
"WW_lVwkg6WWWWWYuV_mo7WeWYm_Bfb-7Wu--lW4cjk8WWW_-WaVbhr7WWWWm_Bsps7WWWWm1dgb7WWWWW_7Wov6WWWaWX8Yww7WWWy-W8tyo7WWWWWWyUuzx"
"7WWWWWWCpat7WWWam-3xWn8WWWyFqe_7WeWYGYgt8Wu-zFY-c8WWW4Zsn8WWWy-y3inW7WeWYmW4akh8Wu--lW4ofn8WWW2Wic8WWWWm-3oXq8WWWWG-kj8W"
"WWWGcgv8WWW2_i-8W8aod9Wu-vlW4oyz7WeWYmW4ygW9Wu-zl-3dqa8WWWWW1Wtk8WWW4lkw8WWWy-ydVsrs5WeWYmWaW1q-k7Wu--lWeVjyW8WWW2waw7WW"
"W_--RvcY8WWW2uoh7WWWy-_7Wta7WWWamWyUXuY8WWWWGZn_7WWWWmWGYkv8WWW_l-Bugf8WWW2dZ-7WWWWm-3_oi8WWWWGquc8WWWWGjsn8WWW2Yts8W8Yz"
"z8Wu-vl_3Yrj7WeWYmW4e-o8Wu-XmW4hvj8WWWy-WqUYwx7WWWWWWCfZp7WWWWW_7aym6WWWWWWGqrw6WWWWW2mZc7WWWWWWeVyW_7WeWYmW4nnW9WWWWW_7"
"krZ8WWWWWWGyzh8WWWWW2lYu8Wu-zlz3oXp7WWWWW2zhb8WWWaW-pUwbc8WWWyVrtY8WWWWWWCoit7WWWWWW4cua8WWWWW1m_k8WWW4jtw8WWWy-y3gux6WW"
"WaWX8fj-7WWWWWW4pxj8WWWy-_3iXf7WWWWW2-bu7WWWWW_7csk7WWWaW1knd8WWWyVng-7WWWWW1sye8WWW4Wfp8WWWWmzpUsWj8WWWWGYde8WWWyVydc8W"
"WWWWWCncW8WWWam-3va_8WWWyFgpe8WeWYGcZb9Wu-zFmzo8WWW4rz_8WWWy-y3orX7WeWYmW4kmj8Wu--lW4Znr8WWW2ase8WWWWm-3--u8WWWWGkxn8WWW"
"WGsq_8WWW2moa9W8_ri9Wu-vl_3mam7WWWWW2mvW8WeWYm_3cft8WWWWW2wsb9Wu-zlz3gjs7WWWaW1sco8WWWyVscf8WWWWW1yXq8WWW4wy-8WWWy-y3myv"
"7WeWYGqay8Wu-1Wx_8WWWWGYus8WWWWGsla9WWW2aZh9W8alp9Wu-vFklj8WeWYGqqh9Wu-zFaxu8WWW4vfb9WWWyFWv_8WeW2alp9Wu-1Xei9WWW2edq9W8"
"fZz9Wu-vlyZ_m7mm_3WWWWWWWWGWvq4WeWYmWaWn7uju5WWWWWWWWGaqm6Wu----ZWn7Wmy6WWW2iYs6WWWWGmZs5WWW_l---Fusl7WWW2cth7WWWWGqwj6W"
"WWWWWy-k7u_y6WWWWm-3moy6WWWWGyjs6WWWWm--Vakt6WWWWGuhy5WWWWWWyVqxX7WWWWm-3azX7WWWWGcwu6WWWWm-3epd7WWWWGWwa7WWWWGazg7WWW2W"
"kk7W8mhp7Wu-zl1yqZ8WWWWW_t-Divm7WWWWm-ZW1qrk7WWWWGibv6WWWWWWyVevo7WWWWm-3mWp7WWWWGWhb7WWWWm-3sdw7WWWWGqes7WWWWGnf_7WWW2q"
"tY8W8eue8Wu-zl1q-p8WWWy-zZWn7yyl6WWWWW1aqo5WWWWW---FjiZ7WWWWW1gif6WWWWW---l7s_r6WeWYmWaW1Y_f8WWWWW1mjl7Wu-zl_x-Ejli7WeWY"
"mWaW1u_w8WWWWW1prZ8Wu-z-zx-i7Woc7WWWWm1afm6WWWWW---1oen6WWWWW1Yyu5WWWWWWu-1bnw6WWWWm_7Wdi7WWWWm1W_p6WWWWm_7qir7WWWaW1ssa"
"8WWWyFeg-6WWWWGqWx7WWWWGa_a7WWW4yZi7WWWy-zt-DvXc7WWWWW1beq6WWWWWWu-1Y_f7WWWWm_7lys7WWWWm1ZYW7WWWWm_7mtY8WWWaW1yyq8WWWyFZ"
"wl7WWWWG-uf8WWWWGoys7WWW4ms-7WWWy-_l-g7kyd7WWWWWWeW1Wds6WWWam-xVeWn7WWWWm1mfb8WWWy-_3kua7WeWYmW4f_g8Wu-zFiuW8WWWam_3qWb8"
"WWWyFshr7WWWaW1ztb8WWWy-ztV_qs6WWWWW1eoy5WWWWWWuVypj7WWWWW-7_mj7WeWYmW4akh8WWWWW1qmr7Wu-zl-3ymo7WWWWW1ymy7WWWWW-lVdlW7WW"
"WWWW8gtv6WWWWm_7Wus7WWWaW1wbc8WWWyFmeb7WWWWGWqy7WWWWGWyg7WWW4wYo7WWWy-_lVXan7WWWam-3XWd8WWWyFcXy7WeWYGcip8Wu-XGhlj8WWWy-"
"_3wrb7WeWYmW4ZWj8Wu-zFwsZ8WWWam_3znj8WWWyFoWt7WWWWW1ar_7WWW4-ce8WWWWm_3gbn8WWWyFal_7WeWYGYht8Wu-zFuad8WWW4itn8WWWyFiZh8W"
"eW2qky8Wu-1Ygs8WWW2W_y8W8ada9Wu-z-zl-BiWd8WWWWm1bls8WWWy-zZW1xpj7WWWWW1suv6WWWWW--Vvau7WeWYmW4chz8WWWWW1f-i8Wu-zl-pVahn7"
"WWWWWW8oyb7WWWWm_7cia8WWWaW1vat8WWWyFkkt7WWWWGfXi8WWWWGgZ-7WWW4Yqe8WWWy-_lVwyv7WWWam-3jsn8WWWyFevc8WeWYGjzW9Wu-XGzfw8WWW"
"y-_3adi7WeWYmW4l-t8Wu-zFail8WWWam_3jlw8WWWyFbfW8WWWWW1oqe8WWW4x_o8WWWWm_3mw_8WWWyFYpf8WeWYGrsb9Wu-zFiop8WWW4vl-8WWWyFYZu"
"8WeW2ssh9Wu-1cwa9WWW2qii9W8nuq9Wu-vlyZ-e7ijb4WWWWWWWX8mwi5WWWWWWW-7wdX5WWWWWWWW8egm5WWWWWWW1qiX6WeWYmWa-e7yt_5WWWWWWWX8m"
"xe7WWWWWWW-7key6WWWWWWWW8mxe7WWWWWWW1ayw7Wu--lWa-e7mby6WWW2qjy5WWW_---W8qeX8WWW2iob7WWW_---_7Wkr7WWW2lZv6WWW_----7qeX8WW"
"W2iob7WWW_--Vyym8WWW2gZt7WWWWWWy_c7qpY7WWWWWW4Wjy6WWW_---Vqxy6WWW2iZW6WWWWWWyVuzd7WWW_--3u_d7WWW2kt_6WWWWm-3isj7WWWWGazg"
"7WWWWGeWn7WWW2anq7W8qkv7Wu-xl-ResW8WWW2twv7WWW_----6gqY8WWW2gnh7WWWWm-ZVXpY8WWWWGXb_7WWW_--Rbjf8WWW2jt_7WWWWm-3sri8WWWWG"
"irc8WWWWGWsn8WWW2qws8W8Yzz8Wu-zl-t_5zzu7WWWWm-ZW1bns7WWW_FWus7WWW2ty_6WWWWWWyVZrw7WWWWm-3Zpw7WWW_Fxyw7WWW2ohh7WWWWm-3_oY"
"8WWWWGnf_7WWWWGavc8WWW2aqh8W8Zfo8Wu-xl-x-6gqY8WWW2gnh7WWW_--Vbzo8WWW2ib-7WWWWWWyUsXa8WWW_--3Yoa8WWW2__n7WWWWm-3-Yj8WWWWG"
"nyd8WWWWGWsn8WWW2qws8W8Yzz8Wu-xl-Rhzr8WWW2zke8WWWWm-3gwv8WWWWGjno8WWWWGyi-8WWW2ydb9W8vdj9Wu-vl_p_a7mlf4WWWWWYmW4e_u5WWWW"
"W_Fyda6WWWWWWWW4WYp5WWWWWWWW4c_g6WWWWWWGmrq6WWWWW2mbW7WWWWW_l_3akd5WWWWWYmW4s_p6WWWWW_l-3aau5WWWWWWW1yeh6WWWWWWW-3yo-5WW"
"WWWYGmbW7WWWWW_FmZs6WWWWWWGuwY7WWWWW2osm7WeWYm_p_a7ukY6WWWWWYmW4qmr7WWWWW_FWt_7WWWWWWWW4q_k7WWWWWWWW4bbZ8WWWWWWGmrh8WWWW"
"W2oyt8WWWWW_l_3sbY7WWWWWYmW4zpi8WWWWW_l-3q_k7WWWWWWW1afZ8WWWWWWW-3qmr7WWWWWYGoyt8WWWWW_FYZj8WWWWWWGoyt8WWWWW2hfc9Wu-zlzh"
"_Y7Wbi4WWWaWXeW2maW6WWWy-W8mds6WWWWWWWW2wpy5WWWWW_FsYg6WWWWWYe-1omW7WWWWWW8ivv6WWWWWW8mib7WWWWW1qWh7WWW4sco7WWWy-y7Wiv6W"
"WWaWX8okw7WWWy-W8-qo7WWWWW_l-1Wus5WWWaWXeW2_qh7WWWy-_7_ma7WWWWWWm-1sqm6WWWWWWGinw6WWWWW2eZc7WWWWWWe-1eWt7WWWWW_7gnx6WWWa"
"WX8nW-7WWWy-_7ove7WWWWW2nwt7WWWWW_7ytk7WWWaW1qid8WWWyVYd-7WWWWW1que8WWW4ybp8WWWy-yd_1_Zh5WWWaWXeW2W-_6WWWy--dW2mcj7WWWWW"
"1srv6WWWWWWu-1u-m7WWWWWW8tzb7WWWWWW8Ydt7WWWWW1mt_7WWW4kge8WWWy-yd-1egy5WWWWWWW1qhm6WWWaWXe-1_qh7WWWWWWW1ab-7WWWy-_t_1ssZ"
"6WWWWWYGeZc7WWWWW_Furx6WWWWWWGwgf7WWWWW2dfu7WWWWW_l_1WYe6WWWaWX8sco7WWWyVynv7WWWWWW8gli7WWWWWW8wbW8WWWWW1que8WWW4ybp8WWW"
"y-y7isX7WWWaWX8vpe8WWWy-_7mom7WWWWW2l_W8WWWWW_7ust7WWWaW1ybp8WWWyVeeg8WWWWW1gar8WWW4-zW9WWWy-yd_X7WXk4WeWYmWaW1Wya6Wu-XG"
"Wac7WWWWWW4iy-6WWWyVqgi7WWWaW--VWnY6WWWy-W8esv6WWWaW-pVqkh7WWWWWW4ybY7WWWWm-3edn7WWWWGWkk7WWWWGanq7WWW2WYu7W8m-y7Wu-zl1W"
"Wg8WWWy-_3Wje7WeWYmW4qam8Wu-zFWrb8WWWWW-3Yyv7WWWaW1exg8WWW_-zFupb8WWW2kp_7WWWy-_7Wzi7WWWWW2ypW8WWWWWWWVmW-5WWWWW_FWmj6WW"
"WWWYeVazn7WeWYmWCmXv7Wu-zl-3e-s7WWWWW1WfX8WeWYmzBWsZ8Wu--lW4qaq8WWW_-WWVq-Z7WWWWWW8qbz6WWWWm_7mfx7WWWWm1uwe7WWWWW1mkk7WW"
"W4arr7WWWy-y7qyy6WWWaWX8id-7WWWy-W8kct7WWWWWWuUugr7WWWam-3mwh8WWWyFypW8WeWYGiqu8Wu-XGwqo8WWWy-_3mdf7WeWYmW4WXo8Wu-zFqoe8"
"WWWWW-3ojx7WWWWW1WgZ8WWW4ecj8WWWWm_3yes8WWWyFWWZ8WeWYGWry8Wu-zFeWi8WWW4u_s8WWWyFubm8WeW2uyX9Wu-1erx8WWW2miY9W8uuf9Wu-vly"
"3qyZ7WeWYmW4qam8Wu--lW4m-s8WWW2YXh8WWWWm-3Wyv8WWWWGmuo8WWWWG_i-8WWW2mtb9W8qek9Wu-vlW4uhY8WeWYmW4Ytc9Wu-zl-3cuf8WWWWW1uhq"
"8WWW4crW9WWWy-ydVWbv5WeWYmWaW1mlo7Wu--lWaW1qed8WWW2iZl7WWWy-_7Wle7WWWamWyUqhd8WWWWGovY8WWW_--RWkk8WWW2_jZ8WWWWm-3Wtn8WWW"
"WGqmh8WWWWGqws8WWW2mXy8W8mgZ9Wu-vl_3Wnn7WeWYmW4ihu8Wu-XmW4gap8WWWy-_dVm-p6WWWWWWGW-z6WWWWW2Wof7WWWWWWeVimY8WeWYm_Bk-d8WW"
"WWWWGWsm8WWWWW2idz8Wu-zlz3mgt7WWWWW2ujg8WWWaW-pUexg8WWWyVird8WWWWWWC_jx7WWWWW_7W-_6WWWaWX8YrZ8WWWy-_7asi7WWWWW2yfy7WWWWW"
"_7mro7WWWaW1uci8WWWyVewZ8WWWWW1mqj8WWW4Wgu8WWWWmzpUa_n8WWWWGqsi8WWWyVyah8WWWWWWCeoa8WWWam-3mYa9WWWyFqoj8WeWYGYeh9Wu-zFyg"
"u8WWW4Wya9WWWy-y3W_a7WeWYmW4WXo8Wu--lW4ocx8WWW2_bj8WWWWm-3av_8WWWWG_Wt8WWWWGmoa9WWW2Wvg9W8Wdp9Wu-vl_3mzp7WWWWW2uZb8WeWYm"
"_3mmy8WWWWW2ixh9Wu-zlz3upw7WWWaW1Wjt8WWWyVqbk8WWWWW1ilv8WWW4_xb9WWWy-y3Wk_7WeWYGuyX9Wu-1Wfb9WWWWGmky8WWWWGaZh9WWW2WXo9W8"
"Wvw9Wu-vFW_o8WeWYGylo9Wu-zFuw_8WWW4mzh9WWWyFW-a9WeW2Wvw9Wu-1ydp9WWW2Wrx9W8aXbAWu-vlyZUWnj5WeWYmWaW1aqb7Wu-XGqlz7WWWWm-ZW"
"1sbx7WWWWGahY7WWWWWWyVeZ-7WWWWm-3ia-7WWWWGyyk7WWWWm-3ubd8WWWWGqtY8WWWWGaqh8WWW2Wnm8W8mit8Wu-zl1gfy8WWWy-zZW1wpn7WWWWW1WX"
"z6WWWWW--Vymy7WeWYmW4uhZ9WWWWW1arn8Wu-zl-pVyfr7WWWWWW8Yif7WWWWm_7qcf8WWWaW1kxy8WWWyFWnx7WWWWGmen8WWWWGihZ8WWW4Wcj8WWWy-_"
"lVgb_7WWWam-3Yts8WWWyFanh8WeWYGWzc9Wu-XGqYW9WWWy-_3uul7WeWYmW4aaz8Wu-zFYoq8WWWam_3gbW9WWWyFasa8WWWWW1egj8WWW4iWu8WWWWm_3"
"apa9WWWyFWfk8WeWYG_uh9Wu-zFyuu8WWW4Yhb9WWWyFeqz8WeW2qbo9Wu-1oWh9WWW2i_o9W8stx9Wu-vlyZVe__5WWWWWWW1ujp6WeWYmWaVmlo7WWWWWW"
"W1uud8Wu--lWaVqed8WWW2iZl7WWW_--Vwku8WWW2gmZ8WWWWWWyU_ve8WWW_--3mWf8WWW2Wnr7WWWWm-3_Xo8WWWWGori8WWWWGqws8WWW2mXy8W8mgZ9W"
"u-xl-Rikx8WWW2acj8WWWWm-3Yk-8WWWWGost8WWWWGydb9WWW2ufh9W8gtp9Wu-vl_pUmgc6WWWWWYGWof7WWWWW_Fm-_6WWWWWWGe-i7WWWWW2eiy7WeWY"
"m_pUmXv7WWWWWYGidz8WWWWW_Fg-n8WWWWWWGidz8WWWWW2Wmi9Wu-zlzhUWsg6WWWaWX8arr7WWWyVeZ_7WWWWWW8e_l7WWWWWW8gua8WWWWW1mqj8WWW4W"
"gu8WWWy-y7mYb7WWWaWX8cgj8WWWy-_7yiq7WWWWW2_ib8WWWWW_7uqx7WWWaW1Wgu8WWWyVyZl8WWWWW1elw8WWW4gwc9WWWy-ydUmnj6WeWYmW4m-y7Wu-"
"XGemk8WWWWWW4mmv7WWWyVqhZ8WWWam_3yYu8WWWWGugo8WWWWGW_y8WWW2miY9W8uuf9Wu-vFWln8WeWYGurk9Wu-XGcnd9WWWy-_3uvp7WeWYmW4ijZ9Wu"
"-zFuex8WWWWW-3sWg8WWWWW1ubp8WWW4ac_8WWWWm_3wzh9WWWyFyXq8WeWYGWkp9Wu-zFml-8WWW4eui9WWWyFW-a9WeW2Wvw9Wu-1ydp9WWW2Wrx9W8aXb"
"AWu-vly3mwe7WeWYmW4yrt8Wu--lW4amY9WWW2Wuo8WWWWm-3qjc9WWWWGuvz8WWWWGqii9WWW2i_o9W8mwx9Wu-vl_3Wsu7WWWWW2ilg8WeWYm_3ijZ9WWW"
"WW2a-p9Wu-zlz3iXW8WWWaW1ac_8WWWyVwqq8WWWWW1iqW9WWW4wtj9WWWy-y3Wka8WeWYGuuf9Wu-1uZk9WWWWGuba9WWWWGedq9WWW2Wrx9W8aXbAWu-vF"
"uew8WeWYGuXy9Wu-zFaXd9WWW4yYr9WWWyFWmj9WeW2aXbAWu-1q-y9WWW2eZcAW8WgmAWu-vlyZ_Wdm1Wid1WeWYmWaWXeW2eXk3Wu-XmW4ikx4WWWWWWWW"
"1mro4WWWWWWy-_dW2mcx4WWWWWW4all4WWWy-W8uYj5WWWaW-tVWfi3WWWy-WeW2mtk4WWWaW-t-yt-1Wcy4WWWWWWWW1WZp4WWWy-W8aso5WWWaW-p-_7ur"
"y4WWWWWW4air4WWWWWWWW1uou3WWWy-WeW2ojw4WWWaW-p-y7exX5WWWWWW4ee-4WWWWWWWW1Wvq4WWWWWWyVYeb5WWWWWW4wdX5WWWWm-3yve5WWWWGakd5"
"WWWWG_Zh5WWW2Wnj5W8mum5Wu-zl1ouf6WWWWWWCokp6WWW_-zFumc6WWW2pvZ6WWWy-WeVebe5WeWYmWaW1q-n6Wu-zl-3qig6WWWYW-FyZX7WWW_-WeVsr"
"y5WWWaWX8Ymk6WWWWW_Fqnw6WWWy-W8zow6WWWYW-t-3wkm6WWW2sld6WWWy-_dW2mvf6WWWWW2mzs6WWWaW-p_4_yW6WWWWm-ZW1fyW6WWWWGyst5WWWy-W"
"eW2Yze6WWWWWWu-idW2wqh5WWWWWWWW1cwq4WWWWWW8Yrh4WWWWWWWW2ewf3WWWWW_lW4mbe4WWWWWYe-v--1upW5WWWWWW8_hu4WWWWWWu--7iyt5WeWYmW"
"aW1got6WWWWWW8_bk6Wu-zlW4ylm6WeWYm-x-1sak5Wu-zl-pVkY-5WWWWW-Fgta6WWWWW1aoY6WWWWW1wye6WeWYmzhW3oWh6Wu--lWaW1Wbh7WWW_-WW-7"
"bsn6WWWWWWeWld-1ilk5WWWWWWWW1kfs4WWWWWWWW2all4WWWWWWu-yFlem5WWWWWWeW1Yon4WWWWWWWW2Was3WWWWW_lW4uzp4WWWWWYe-uFaiu5WWWWWW8"
"kjn5WWWWWWWW1YZx4WWWWWWqVXea6WWWam-7ack6WWWWm1aup6WWWy-_3_ls5WWWWWW4vcf6WWWWW1sql6WWWWW-3hw-5WWWaW1yvg6WWWy-_Njds6WWWWWW"
"WVivn4WWWWWWuVkWx5WWWWWW8snp5WWWWW-3kdf6WWWWW2Wrj6WWWWmz3Znf6WWWWm1r-_5WWWWW1yla6WWWWW-N-zp6WWWWm_pUalW6WWWWm1ily5WWWWWW"
"4WsW5WWWWWW8o_z4WWWWm_7uqX6WWWWm1gzZ5WWWWW1mid5WWW4ayh5WWWylzBWnw6WWWWmXCku_5WWWWW_l-1WyX5WWWWWWWW1qe-5WWWaWXeW1oae6WWWy"
"-WeW2WzY6WWWWm_-_7Yzl6WWWWGbYw5WWWWW1dip5WWWWW_lW4qYz5WWWWWYm-ft_1a-p5WWWWWWWWW8iaX5WWWWWWWW2sqw4WWWWWWWW_7mev5WWWam-xVs"
"rs5WWWWm1g_l6WWWy-_3q_X6WeWYmW4sev6Wu-XmW4cfr6WWW_-zF_qo6WWW2mxl6WWWy-W8qiz6WWWWWWWVmpe5WWWWWWuVawb6WeWYmWCiuo6Wu-zl-3ca"
"h6WWWWW1egn6WWWWW-tVyez5WWWWWW8yjb6WWWaW1mgl6WWWy-_Nvrx6WWWYW-t-3kwx6WWW2kno6WWWy-_t-1wvZ6WWWWWYGebu6WWWWW--_7sjq6WWWWW1"
"Wuf6WWWWWWu-i7eYr5WWWWWWeW1cix4WWWWWWWW2yey3WWWWW_lW4yvv4WWWWWYm-v7uXt5WeWYmWaW1wfq6Wu-zl-3l_g6WeWYmWy-1_tv5Wu-zl_3cah6W"
"WWWW2_jl6WWWWW-lVboW6WWWWWW8iov5WWWWm_7gZh6WWWWm1_da6WWWWW1crf6WWWWW-Nxtu6WeWYm_p-2WYs6Wu--lWaW1axi7WWW_--d-9ydq6WWWWWXu"
"-i7wW_5WWWWWWeW1mec5WWWam-xVozk6WWWWm1ujr6WWWy-_3_ry5WWWWWX4kjn6WWWWW-3y-b6WWWaW1oym6WWWy-_Nxdx6WWWWWWWVyvy4WWWWWWuVvaX6"
"WWWWWWGxXb6WWWWW1_og6WWWWW-hVvaY6WWWWWW4Wzh5WWWWWW8yZf5WWWWm_7mgd6WWWWm1mal5WWWWW1aqo5WWW4oft5WWWy-_Nvig6WWWWW_l-1qfe5WW"
"WaWXeW2cuo6WWWy-WeW2mjj6WWWWW--_7oqb6WWWWW1au_5WWWWW_lW4sba6WWWWWYe-e7yha6WWWWWWeW1cex5WWWam-xVmkm6WWWWm1clv6WWWy-_3eua6"
"WeWYmW4mpz6Wu-zF_rr6WWWWW-3xrk6WWWaW1ovv6WWWy-_NwhY7WWWWWWWVahf5WWWWWWuVWWf6WeWYmWCsiq6Wu-zl-3czi6WWWWW1ekp6WWWWW-lVuxY6"
"WWWWWW8cj_5WWWWm_7iWl6WWWWm1kwc6WWWWW1qdh6WWW4qan6WWWy-_Nlnz6WWWWWWuUsyh6WWWam-3okx6WWWyFqso6WeWYGmnY7Wu-XGnk_6WWWy-_3e_"
"b6WeWYmW4st-6Wu-zFYwt6WWWWW-3qfm6WWWWW1Whr6WWW4oXy6WWWWm_3sWX7WWWyFasq6WeWYGmgb7Wu-zFWcw6WWW4YgX7WWWyFexy6WeW2ane7Wu-1qe"
"a7WWW2mwe7W8irj7Wu-z-zFdht7WWWylW4kla7WeWYmW4rZz7Wu-zl-3hmd7WWWWW1Ysk7WWW4r-t7WWWy-ydVial5WeWYmWaW1yYZ7Wu--lWaW1oYl7WWW2"
"Wj-6WWW_---VY-q7WWW2sek7WWWWm-3Yot7WWWWGYpp7WWWWGuXy7WWW2ypW8W8WYd8Wu-vlWaW1imv6WWWWWWeVjcY7WeWYmWSuxX8Wu-zl-3exk7WWWWWW"
"qUfgb7WWWWWWCtw-6WWWWWWOrXd7WWWWWW8y-h7WWWWW1itp7WWW4i-y7WWWWm_p_4hij7WWWWm1vbq7WWWy-zZW1eWu6WWWWW1wzg6WWWWW--Vqsy6WeWYm"
"W4qpv7WWWWW1ewo7Wu-zl-pVyZw6WWWWWW8cYo6WWWWm_7mib7WWWaW1Xlq7WWWyFdf-6WWWWGizh7WWWWGiWc7WWW4xhk7WWWy-ydW2ueh6WeWYmWaW1sYx"
"7Wu--lWaW1_-Z8WWW2hms7WWWy-We-1Wot6WWWWWWW1auk7WWWWW_-_bdW2it_4WWWWWWmW2qfb4WWWWWWWW4aac3WWWWWWm-v--1wqh5WeWYmWaWX8er-6W"
"WWWWWmW2Zud6WWWWWWWW4udg5Wu-zl-x-wt-1mWo4WWWYWXi-_Fygh6WWW2kod6WWW_--7mdb7WWWYWW4pdx6WWW_--FWWn6WWW2Zla6WWW_----1oyb7WWW"
"_-_7-Yi6WWWaWXuVYua6WWW_----3qre6WWW2w-d5WWWy-_d-1tZq5WWWWWWW1Wpw5WWWamWy_sd_1shq5WWWWGy_o5WWW_--Rcvi6WWW2k_f6WWW_----1d"
"ic7WWWYWWWW1Zn-6WWW_----3sio6WWW2sdf6WWWy-_dW2Wwi6WWWaWXq_4Y_i6WWWWm-ZW1qzi6WWW_Fuyi6WWW2cmZ6WWWy-_tWod1_hu4WWWamWu-_7ci"
"c7WeW_--hW2Wzp6Wu-zl-hW1vsn6WWWYWXy_y7kXi6WWW2abf6WWWWWWCZz-6WWW_--FYpo6WWW2kng6WWW_----1wye7WWWYWWWW1nom6WWW_----3apk6W"
"WW2cip5WWWy-_d-1lzy5WWWWWWW1sca6WWWamWy_s7omj6WWWWGqqh6WWWWm-Bsle7WWWWGZka7WWW_--Foks6WWW2qho6WWW_----1wZl7WWWYWWWW1hwa7"
"WWWWm-ZVnpf7WWWWGprc7WWWWmWGYwx7WWW_l-Bpgm7WWW2Zjf7WWWWm-3fgp7WWWWGael7WWWWGvau7WWW2ymy7W8YZZ8Wu-zl-Bqxs7WWW_--l-2sXt6WW"
"W2sXi6WWWWm-ZVWhu6WWWWGmwr6WWWWm-BwYo7WWWWGsei7WWW_--FWlx6WWW2zZs6WWWWm-3uyz6WWWWGkuw6WWWWGisX7WWW2mYb7W8mxf7Wu-zl-Bqhl7"
"WWWy-_tU_Zd6WWWWWWW1qel6WeWYmWaVjuo7WWWWWWW1kmu7Wu-XmWuUzbf7WWWWWWCkdk7WWWWWWGlad7WWWWWWG_wp7WWWWm-p_4vff7WWWWGuob7WWW_-"
"-xW7asm7WWW2lbc7WWWy-_d-1avq6WWWWWWW1uiW7WWWWWWm-bd_1gkZ5WWWWWWWW6uqf4WWWWWWWWyV_dh4WWWWWWWW4yjo3WWWWWWe-uVmiv5WWWWWWuW1"
"fue5WWWWWYiVmlz6WWWWWWCWbv6WWWWW_7_-s5WWWWWWGyYW6WWWWW2ebh6WWWWW_lVeXq4WWWWWYuVcwq6WWWWW_Feyf6WWWWWYmVc-Y6WWWWW_7mXl5WWW"
"WWW8q-_5WWWWWY8Yz-5WWWWW_l-1yZj4WWWWWWeVnqX6WWWWWWW1k_e6WWWWWWuVbqi5WWWWWWGuos5WWWWWWu_1wnn5WWWWWWOequ4WWWWWWGmX_4WWWWW2"
"era5WWWWW_l-Bash5WWWWWWWWg-z1Wzj5WeWYmWaWX8kka7Wu-zlXq-2y_i6WeWYm_hW3oqi6Wu-zlXa-8uWx6WeWYm_xWpVuxj6WWWWWWWW4Wwr5Wu-zl-x"
"-uNqWp5WWWWWYuVir-6WWWWWWWW3y-i6WWWWW_7nzv5WWWWWW8Wve6WWWWWY8Znh6WWWWW_l-3dht5WWWWWWGtvX6WWWWWWu_1wly5WeWYmWyWt7fcf7WWWW"
"WWWW2gXs6Wu-zlXqVkgv6WWWWW_Fkzs6WeWYmYqVwnX8WWWWW_7gyj7WWWWWW8kwx7WWWWWY8yZ_7WWWWW_l-1adl6WWWWWWWW2-kh7WWWWWWG_bq7WWWWWW"
"u_1can7WWWWWWOprv6WWWWWWGmo_6WWWWW2YZc7Wu-zlzpUgrl6WWWWWYGzXd7WWWWW_FbZw6WWWWWWGag_6WWWWW2_vi7WWWWWWW-7-pk7WeWYm_hW3cdg7"
"Wu-zl-x-gdz1aje5WWWWWWWWaGikq4WWWWWWWWvFc-x5WWWWWYq-1j_p6WWWWWW4Zrh6WWWaW-Fhw-6WWWy-W8jbx6WWWWW-Z-1aYq6WWWWWX4tug6WWWWWW"
"Oqru6WWWWWWeVYhl5WWWWWWOkza6WWWWW_l-1WuY5WWWWWWWW1yxW6WWWWWWGolk6WWWaWXuVmuf6WWWy-_7wqW6WWWWWWm-1zfr5WWWWWYGuua6WWWWW--_"
"7prb6WWWWW1wr_5WWWWW_lW4ea-5WWWWWWWWiFqXr4WWWWWWWW4uou3WWWaWXi-wFeao6WWWWWWSXlm6WWWy-_tVf-j5WWWWWXqVcpX7WWWWW-Bvw-5WWWaW"
"XeW1-xg6WWWy-_d-2oab6WWWWWWW1nhj6WWWaWXuV_mp5WWWy-_x_1xib6WWWWWWSWjo5WWWWWWGqfy5WWWWWYe-sFapx6WWWWW_Nsff6WWWWW2dyq6WWWWW"
"_lV_x_4WWWWWYuVbdv6WWWWW_F_gk6WWWWWYmVama6WWWWW_7vyq5WWWWWYGX-b6WWWWW_l-1uvt4WWWWWWmW2Xpy5WWWWWWu_1e-s5WWWWWWOknZ5WWWWWW"
"GqXf5WWWWW2w_l5WWWWW_l-BZes5WWWWWWWWfFiW_5WWWaWXi-1uW-6WWWy-W8job7WWWWWW4hb-6WWWaW-Frqa7WWWy-_7cWq6WWWWW2zZY7WWWWW_lVYun"
"5WWWWWXqVeob7WWWWWX4srz6WWWWW_7vWe6WWWWWYGbd_6WWWWWWeViyc6WWWWW_7Yby5WWWaWX8o-o6WWWy-W8Xkj6WWWWWWyUdXg7WWWWWW8d_c7WWWWWW"
"4leW7WWWWWW4oWi7WWWWW1qlp7WWW4muy7WWWy-y3quh6WWWWWW4kxy6WWWaWX4Wxf7WWWWWW4yat7WWWy-W4mYZ7WWWWWW4vil7WWWWWW4-ne7WWWWW1oom"
"7WWW4mrv7WWWy-ydVW_Z5WWWWWWWW1YvY6WWWWWWGXYo6WWWaWXuVahi6WWWy-_7o-Z6WWWaWXyUZ-j7WWWWWWSokd7WWWWWW4Yyp7WWWy-_3gns6WWWWWW4"
"oqW7WWWaWX4qXm7WWWy-_hUWzf6WWWWWWScdt5WWWWWWGqu_5WWWWW2gsd6WWWWWWyUYzj7WWWWWWCyvY7WWWWW_7Xjf6WWWWWWGepq6WWWWW2WbX7WWWWW_"
"7WWx6WWWWW2qye7WWWWW_hUozk6WWWaWX8wki7WWWyVYjd7WWWWWW8teb7WWWWWW4nvm6WWWWW_7ed_5WWWWWW4k-t6WWWaWX4ers6WWWy-_7qad6WWWWW2z"
"gn6WWWWW_7qXh6WWWaW1Wpx6WWWyVsvr6WWWWW1Wey6WWW4uXZ7WWWWW_p_4__r7WWWy--dW2--s7WWWWWXaW1oh-6WWWWW_dW2YlX6WWWWWWWW1quj6WWWa"
"WXeW1fsc7WWWy-_t-1mre6WWWWWWG_np6WWWWW2chW7WWWWW_l-d-y1kmm5WWWamWi-_7Wdw5WWWWGivu5WWW_--RsXs6WWW2zZp6WWWy-W8_uY7WWWWW_lV"
"is_5WWWWWYuVyzq6WeWYm_Bycf7Wu--lW4uhh7WWW_-WmVc-k6WWWaW-Feca7WWWy-W8wmW7WWWYW-t-3gry6WWW2_dp6WWWy-_t-1kka6WWWWWWGmYk6WWW"
"WW2imv6WWWaW-p_4mZp6WWWWm-ZW1WZp6WWWWGmpf6WWWy--dW2eey6WWWWW1mam6WWWWW_lWq7iXw4WWWWWYu-w7lrq6WWWYW-Ftyh7WWW_--l-1szq6WWW"
"Wm--Vuyq6WWWWm1crj6WWWWWWOsaz6WeWYm_p-2qss6Wu--lWaW1auk7WWW_-_7wuo6WWWWWXW-9_iy6WWWWWXeWl7cXl6WWWaW-F-la7WWWy-W8mw-6WWWW"
"WWe-1nWk6WWWWm_-Vecm6WWWWm1cXr5WWWWWWObsj6WWWWW_l-1mpe5WWWaWXeW2ykp6WWWy-_7sof6WWWWWWm-1Wjz5WWWWWYGagk6WWWWW--_7zrh6WWWW"
"W1aqa6WWWWW_lW4_Wb6WWWWWYu-g7niu6WWWYW-Fwpj7WWW2kXf7WWWy-W8sdd7WWWWWWe-1cks6WWWWm_-Vuuu6WWWWm1_yl6WWWWWWOk-X7WWWWWWyUeqy"
"6WWWWWWCfXw6WWWam-3yph7WWWyFmr_6WeWYGqXm7Wu-zFema7WWW4g-h7WWWWm_Fbfz7WWWylW4qdf7WeWYmW4ZdZ8Wu-zl-3swi7WWWWW1oiq7WWW4ZY_7"
"WWWy-ydVWjl5WeWYmWaW1WuZ7Wu--lWaW1mom7WWW2kbW7WWWy-_7yyt6WWWamWyU-Wl7WWWWGtzh7WWW_--Ryos7WWW2vjl7WWWWm-3mgv7WWWWGydr7WWW"
"WGoyz7WWW2uhY8W8ave8Wu-vl_3qa_6WeWYmW4wlz7Wu-XmW4hpu7WWWy-_dVmqd6WWWWWYGunw6WWWWWWeV_gd7WeWYm_Brxp7WWWWWYGetZ8Wu-zl-3mum"
"7WWWWWWqUwtg7WWWWWWC-va7WWWWW_7Wjm6WWWaWX8rkl7WWWy-W8ule7WWWWWW8_wj7WWWWW1mur7WWW4w__7WWWWm_p_4krs7WWWWm1zh_7WWWy-zZW1jn"
"-6WWWWW1qzm6WWWWW--Vfya7WeWYmW4eZa8WWWWW1tqy7Wu-zl-pVtXY7WWWWWW8z_u6WWWWm_7ynk7WWWaW1ms_7WWWyFXud7WWWWGknr7WWWWGk_k7WWW4"
"pZu7WWWy-ydW2yXi6WeWYmWaW1ely7Wu--lWaW1slc8WWW2wWu7WWWy-_t-1qor6WWWWWYGmom7WWWWW_l-d7cfw4WWWWWWWW4yey3WeWYmWaWz7vZt6Wu-z"
"--pVmgZ7WWWWm-7ezZ6WeWYmWaW3mqx5Wu-zl-hVite6WWWWWWW1men6WWWYWXy_u7ezr6WWW2uuo6WWW_--Rvqy6WWW2krp6WWWy-_tVWur5WWWYWXeW1-p"
"k7WWWYWWWW1mwp6WWW_----3ont6WWW2gev5WWWy-_t-1lmw5WWWWWWGiXb6WWWamWy_s7mxs6WWWWGYxq6WWW_--RgoW7WWW2xby6WWWy-_tVmsW6WeWYmW"
"aW1uzj7Wu--lW4qsq7WWWYWWWW1zkf7WWWWmWqVglz7WWW_l-Bvcs7WWW2gwk7WWWWm-3Ybv7WWWWG-xq7WWWWGyW_7WWW2imY8W8qef8Wu-xl-x-2mgX7WW"
"W2kqr6WWWWm-ZVglY7WWWWGXw-6WWWWm-Bcqt7WWWWGvcn7WWW_--Fsxb7WWW2rcW7WWWWm-3sge7WWWWGgXb7WWWWGadi7WWW2uul7W8wsq7Wu-zl-ByWr7"
"WWWy-_dVsYc6WWWWWWGqdm6WeWYmWqV-ym7WWWWWWG_aw7Wu-zl-3YdY7WWWaWXqUuqk7WWWWWWSzki7WWWy-_7Whx6WWWaWX8yor7WWWWm-p_4rio7WWWWG"
"shk7WWW_--xW7nuw7WWW2cfl7WWWy-_t-1emo6WWWWWWGaWY7WWWWWYe-c7muW7WWWWW_Nimj6WWWWW2kgv6WWWWW_lVaka5WWWWWYuVyqz6WWWWW_Fmgo6W"
"WWWWYmVkrj6WWWWW_7Waz5WWWWWYGeuk6WWWWW_l-1ifz4WWWWWWmW2aXb6WWWWWWu_1ke-5WWWWWWOyaf5WWWWWWGmsk5WWWWW2esr5WWWWW_l-Bwtx5WWW"
"WWYu-g7boc7WeWYm_hW2w--6Wu-z--pVszc7WWWWm1aYw6WWWWW_7-rh6WWWWWYGkrY7WWWWWWeVvWe7WeWYmW4qbZ8WWWWW_7lkp7WWWWWYGuba8Wu-zl-3"
"u-m7WeWYm_h-1_vu6Wu-zl-hW1W-r6WeWYmWaW1s_v7Wu-zl-pUcaj6WeWYmWaW1ebs7WWWWWWOkwZ7WWWWWWGe_e7WWWWW2aum7Wu-zl-tUvil7WWWWWWCg"
"ce7WWWWW_7yjj6WWWWWWGWzu6WWWWW2Xdc7WWWWW_7qw-6WWWWW2Yjk7WWWWm_-_7rav7WWWWm1hYm7WeWYm_hW3gkp7Wu-XmWe-f7ur-6WWWy-WCn-Z7WWW"
"aW-Fkff7WWWy-_7iYu6WWWWW2zXd7WWWWW_lVYav5WWWWWYuVWaY7WWWWWWWW1irl6WWWWW_7aoa6WWWaWX8yny6WWWy-W8qus6WWWWWWyUZlh7WWWWWWCue"
"b7WWWWWW4enj7WWWWW1iWr7WWW4Wg_7WWWy-y3gWm6WWWaWX8-dl7WWWWWW4ktu7WWWy-W4gce7WWWWWW8cyj7WWWWW1ebs7WWW4Zp-7WWWy-ydVmlf5WWWa"
"WXeW2yor6WWWy-_7ovi6WWWaWXyUXXl7WWWWWWS-ti7WWWWWW4akr7WWWy-_3cWx6WWWaWX8crr7WWWy-_dVWW-5WWWWWWGibd6WWWWW2_vm6WWWWWWeVWXe"
"7WWWWW_Van-6WWWWW2wek7WWWWW_hUggo6WWWaWX8uin7WWWyVdni7WWWWWW8YWg7WWWWWW4-ew6WWWWW_7wsc6WWWWWW4cZy6WWWaWX4wjW7WWWy-_7kam6"
"WWWWW2lzw6WWWWW_7ieq6WWWaW1iob7WWWyV_n-6WWWWW1ucc7WWW4yfj7WWWWW_p_4qgt7WWWy-WiW3_rd7WWWWW_dW2qWd6WWWaWXeW2nml7WWWy-_t-1j"
"Yl6WWWWWWGYZx6WWWWW2cze7WWWam_x_c7ewY7WWWWGyoW7WWWy-WCvbe7WWWYW-Fufo7WWW2-wi7WWWy-_7Wpy6WWWWW2_vi7WWWWW_lVegY6WWWWWYuVar"
"b7WeWYm_Bgpn7Wu--lW4mux7WWW_l-lVeue7WWWWm1yWx6WWWWW_7wil6WWWaWX8Whj7WWWy-W8Xdc7WWWWWWyUumj7WWWWWWCxtf7WWWam-3u--7WWWyFit"
"l7WeWYGgpb8Wu-zFect7WWW4epW8WWWy-y3axq6WeWYmW4kpw7Wu--lW4gd_7WWW2dyr7WWWWm-3etW8WWWWGuyx7WWWWGzhb8WWW2ujg8W8egn8Wu-vlW4Y"
"jk7WeWYmW4lmh8Wu-zl-3bWq7WWWWW1omy7WWW4ijc8WWWy-ydVuvl5WeWYmWaW1era7Wu--lWaW1Wto7WWW2wbX7WWWy-_7Yov6WWWamWyUpZq7WWWWGZvm"
"7WWW_--RpXv7WWW2ogn7WWWWm-3sWy7WWWWGYtt7WWWWGmvW8WWW2uZb8W8ylh8Wu-vl_3kiW7WeWYmW4WWX8Wu-XmW4nby7WWWy-_dVqje6WWWWWWGWhn6W"
"WWWW2Wwx6WWWWWWeVwek7WeWYm_BYsr7WWWWWWGioy7WWWWW2Yqc8Wu-zlz3u-a7WWWWW2Woq7WWWaW-pUWsr7WWWyV_ao7WWWWWWCq-f7WWWWW_7onn6WWW"
"aWX8ukn7WWWy-_7mdz6WWWWW2ivg7WWWWW_7qZY7WWWaW1Wdu7WWWyVetm7WWWWW1WXv7WWW4yYY8WWWWmzpUoax7WWWWGikt7WWWyVarq7WWWWWWCvYm7WW"
"Wam-3fue8WWWyFcus7WeWYGxvk8Wu-zFsi-7WWW4klf8WWWy-y3kzr6WeWYmW4ujy7Wu--lW4hfX8WWW2uxt7WWWWm-3Yea8WWWWGzX-7WWWWGscf8WWW2qb"
"k8W8tXr8Wu-vl_3mfY7WWWWW2etm7WeWYm_3cZa8WWWWW2fil8Wu-zlz3wkd7WWWaW1eh-7WWWyVqgt7WWWWW1WjW8WWW4lgg8WWWy-y3mdg7WeWYGiwd8Wu"
"-1aoe8WWWWGawY8WWWWGklj8WWW2W_o8W8yyv8Wu-vFuow7WeWYGiqp8Wu-zFu-Z8WWW4_dk8WWWyFybf8WeW2yyv8Wu-1qyp8WWW2uew8W8YgX9Wu-z-yl_"
"3kpz7WWWWGeXv7WWWyl-hW3yyx7WWWWm1cwn7WWWWWWqVysz7WWWWWWCnau7WWWam-3ezq8WWWyFkiW8WeWYGYrx8Wu-zFyYg8WWW4_nr8WWWy-yZW1cXj6W"
"eWYmWaW1yc_7Wu--lWaW1i_f8WWW2fyv7WWWWm-ZVZqa8WWWWGay-7WWW_--Rcbi8WWW2qmW8WWWWm-3jyl8WWWWGWlf8WWWWGZnr8WWW2ocx8W8cYZ9Wu-v"
"l_pVeps6WWWWWWGiuZ7WWWWW2Wto7WeWYm_pV_bb8WWWWWWGoxk8WWWWW2tky8Wu-zl-ZVedu7WWWWW_7odx6WWWaWX8yoW8WWWy-_7kaf7WWWWW2pXv7WWW"
"WW_7_nl7WWWaW1qWg8WWWyVhfX8WWWWW1Wsh8WWW4b-s8WWWy-yd_fdW2uou3WWWWWWWW8e--2WeWYmWaWvdW2aYx5Wu-XmWWW1wxy6WeW_l---6ovZ5Wu--"
"--ZWodW2Wnc6WWW2iXb6WWWWGgYu5WWWWm---5mcw6WWW_lWWW1weu6WWW2tfu5WWW_l---7yZi6WWW2wiY6WWWWGYpX5WWWWWWy-mdy1svm5WWWWm-3yum5"
"WWWWGcsi5WWWWWWy-Dwfd6WWWWm-ZW1kZd6WWWWGkwz5WWWWWWy-ml3mcd6WWWWWWWW7-zz6WWWWm-ZWv7anc6WWWWG_Z_5WWWWm---5kYz6WWW_lWWW1luy"
"6WWW2_wZ6WWW_l---7qrj6WWW2Xge6WWWWG_yi5WWWWWWy-m7cpe6WWWWm-3e_e6WWWWGcvY6WWWWmWaW4xpj7WWWWm1lXv7WWWWmzx-1hbX7WWWWmWyVmy-"
"6WWW_--3cXX7WWW2Zkm6WWWWWWyVvlY7WWWWm-3udY7WWW_FmaZ7WWW2pnt6WWWWm-3xmf7WWWWGvXc7WWWWGmcj7WWW2wpn7W8ppt7Wu-zl-t-2idi7WWWW"
"WW4uXz6WWWWWW4usl7WWWWW2-xe8WWWWW_t-2ken6WWWWm-ZW1jtl6WWWWGazY6WWWWWWyVqWp6WWWWm-3sWp6WWWWGiug6WWWWm-3You6WWWWGmZs6WWWWG"
"urx6WWW2m-_6W8qqZ7Wu-zl1lys7WWW_-zx-6fvb7WWW2Xrt6WWWy-_t-jd-1qfb4WWWWWXmWxVq_o6WWWWW1wg-5WWWWW---1pwm6WWWWWWWW1ZW-5WWWWW"
"1fzp5WWWWW---3qum6WWWWWXWW2qyp5WWWWW---7auy5WWWWW1ah_4WWWWW---ndy1eWf6WeWYm-p-YW3k_c6Wu-zlWiWwNWbv6WWWWWWWW3rre6WWWWW1mW"
"-5WWWWW---3mcw6WWWWWWWWArie6WWWWWWWWo7dyq6WeWYmWaW1nl_7WWWWW1uYp7Wu-zl_x-2oyb7WeWYmWaW1gYl8WWWWWXWW2ano7Wu-zl_xVwye7WeWY"
"mWaW7xwy7WWWWW1Z--6Wu-zl_xVzZY7WWWWm---idy1Yok6WWWWm1aWY6WWWWWWu-1frc6WWWWW-7rrc6WWWWW1gx_5WWWWWWuV_Yi5WWWWm_7--d6WWWWm1"
"vef5WWWWm_--Dkjq6WWWWGgfW6WWWWW1qgv5WWWWW_l-pl2Yrh4WWWWWYeWzFWar6WWWam_--3qka7WWWWmWWW1cxZ6WWWy-WWW2uhp6WWWWWWeWtFrre6WW"
"WWW---1qxq6WWWWm--VWYr6WWWWGdhW6WWWWW1gvv5WWWWWWWW6o__5WWWWW---7XpY6WWWWW1ymf5WWWWm_--kFvq_6WWWWm1rrn6WWWWWWu-1hfu6WWWWW"
"-7qvu6WWWWW1jih6WWWWWWuVnoY6WWWWm_7rkv6WWWWm1yi_5WWWWWWuVnqw6WWWWm_7YqX7WWWWm1zfo6WWWWm_7oxg7WWWaW1onv7WWWyFtXW7WWWWGn_m"
"7WWWWGyrc7WWW4b-k7WWWylzt-3aqj7WWWaWX8pWf8WWWylWmVfat6WWWWWW8neh6WWWWWWuVWcZ7WWWWWW8_nt6WWWWm_7cvt7WWWWm1x-e7WWWWGka-7WW"
"WWm-lVttv6WWWWWW8zio6WWWWWW8vu-6WWWWW1Ydc7WWW4hxk7WWWylzt-5eXw6WWWWGbef6WWWWW1bp_5WWWWW--VYnz6WWWWW1Xmo6WWWWWWuVXei6WWWW"
"m_7ewW7WWWWm1pdc6WWWWm_7kYg7WWWaW1l-t7WWWyFZbn6WWWWGiZl7WWWWGogs6WWW4f-y6WWWy-_t-5eoo6WWWWWWWWddx1ugh6WWWWWWu-1wcl6WWWWW"
"-7mil6WWWWWXWW1eWc6WWWWW---Dkov6WWWWW1mjj6WWWWWWu-nF-zf6WWWWW-7wpf6WWWWW1pcY6WWWWW---Dqru6WWWWWXWWl7Wmb6WWWWWWu-1iZg6WWW"
"WW-7x-f6WWWWWXqVWzg6WWWWWW4kvn5WWWWm_7gZh6WWWWm1r_k5WWWWW---DfWf6WWWWW1q-X6WWWWWWWWl7myj6WWWWWWu-1jfo6WWWWW-7Who6WWWWWXu"
"Vwoh6WWWWWW8Xtc6WWWWWWuVbir6WWWam-3iub7WWWyFgty6WeWYG_cj7Wu-XGhWf7WWWy-_3eXl6WeWYmW4-dg7Wu-zFaYY7WWWam_3rWf7WWWyFoYw6WWW"
"WW1ij-6WWW4qmc7WWWy-_--5Xsg7WWWWWWqVmkk7WWWWWWCeZe7WWWam-p-4tyo7WWWWm1yaw7WWWy-zZW1wmy6WWWWW1agk6WWWWW--VvzX7WeWYmW4nu-7"
"WWWWW1jnu7Wu-zl-pVbb-6WWWWWW8hgs6WWWWm_7obh7WWWaW1vow7WWWyFzja7WWWWGfrn7WWWWGsfh7WWW4sXq7WWWy-_t-5gry6WWWWW_l-hd2all4WeW"
"YmWaWX8uXj6Wu-XmWWW1anc7WWWy-WaWx7XZw6WWWam_--3bsb7WWW_lWWW1qgb7WWW2mvf6WWWy-WWW2uex6WWWWWWWWv7yl-6WWWam-ZW2fZp7WWWWm1gm"
"w7WWWWmzx-1qlf7WWWWmWyVyYe7WWW_--3k-e7WWW2Yos6WWWWWWyVY-g7WWWWm-3btg7WWW_Fllh7WWW2go_6WWWWm-3zko7WWWWGqrk7WWWWGbns7WWW2s"
"bx7W8-vX8Wu-vlWyVuXd7WWWWWWWW1bwk7WeWYmW4ehn8Wu-XmWWW1Ych8WWWWm_--4oyb7WWWWm1sjy7WWW_-zx-6Ykk7WWW2wu_6WWWy-WeWf7y-i6WWWW"
"W---1bdv6WWWWWWWW1mcf6WWWWW1_cY6WWWWWWWW6qqa6WWWWW---7jih6WWWWW1qcl5WWWWW---n7dlr6WWWWW1euk6WWWWW--VgnY7WeWYmW4sx-7WWWWW"
"1gvu7WWWWWWWW6kky7Wu-zl_xVXYg7WWWWW1vqy6WWWWW-3ogv7WWWWW2kdX8WWWWW_x-5bd_6WeWYmWaW1imY8WWWWW1rig7Wu-zl_xVmYZ7WWWWW1qus6W"
"WWWWWWWj7qrr6WWWWWWu-1q-y6WWWWW-7-dz6WWWWWXuVbYh6WWWWm_7iqz6WWWWm1_jc6WWWWWWuViq-6WWWWWW8jls6WWWWm_7Wyh7WWWaW1mxw7WWWyFt"
"Xb7WWWWGlfo7WWWWGmzh7WWW4vnq7WWWWm_--3Ybh8WWWylWmVdv_6WWWWWW8Xbn6WWWWWWuVxxf7WWWWWWGoyl7WWWWWWmVgrX7WWWWWW8zav6WWWWWW8fz"
"d7WWWWW1y_k7WWW4Yfu7WWWy-zt-5Xmo6WWWWW1axc6WWWWW--VyvY7WWWWWXuVapr6WWWWm_7teb7WWWWm1gZl6WWWWm_7m-k7WWWaW1wnz7WWWyFtpw6WW"
"WWGgjq7WWWWGWWW7WWW4ZWd7WWWy-_t-5fiv6WWWWWWWWd7ytv6WWWWWWu-1hyW7WWWWW-7kvW7WWWWWXuVsgs6WWWWWW8fwm6WWWWWWuVhYa7WWWam-3f-t"
"7WWWyFgpj7WeWYGWXY8Wu-XGwuy7WWWy-_3qtw6WeWYmW4nnz7Wu-zFjfq7WWWam_3ezy7WWWyFZjf7WWWWW1shm7WWW4zZv7WWWWm_p-3vcY8WWWWWWCaak"
"8WWWylWmVppe7WWWWWW8ont6WWWWWWuVilm7WeWYmW4ynq8WWWWWW8tie8Wu-zl-3lus7WWWWWWmVWqh7WWWWWW4ipx7WWWaW1lkk8WWWy-_3uZX7WWWWWX4"
"nWa8WWWWW-3Ybo7WWWWW1stv7WWW4-qZ8WWWy-_lVYwn7WWWam-3xef8WWWyFqzz7WeWYGWZt8Wu-XGcwm8WWWy-_3otb7WeWYmW4hol8Wu-zFnfc8WWWam_"
"3_tm8WWWyFgeu7WWWWW1ogW8WWW4lng8WWWWm_3-Yr8WWWyFuuW8WeWYGlyx8Wu-zFueg8WWW4kvr8WWWyFezk8WeW2oxX9Wu-1aZx8WWW2amY9W8xsg9Wu-"
"z-zl-3-bu7WWWWm1jrY8WWWy-zZW1WbX7WWWWW1_vm6WWWWW--Vqye7WeWYmW4noe8WWWWW1uvz7Wu-zl-pVena7WWWWWW8lzw6WWWWm_7mip7WWWaW1weZ8"
"WWWyF_Yg7WWWWGa-v7WWWWGmym7WWW4pnv7WWWy-_lVljg7WWWam-3ng-7WWWyFigr7WeWYGheh8Wu-XGlmb8WWWy-_3_n-6WeWYmW4aYb8Wu-zFlky7WWWa"
"m_3jvb8WWWyF-Zm7WWWWW1mht7WWW4okW8WWWWm_3vuf8WWWyFicu7WeWYGpql8Wu-zFwiW8WWW4ydg8WWWyFeXa8WeW2ifq8Wu-1bkk8WWW2wqq8W8amx8W"
"u-z-zl-3ugf8WWWylWaW1mgX7WeWYmWaW1yql8Wu-zl-pVq-n7WWWWWW8sxb7WWWWWW8smu7WWWWW1WoW8WWW4wug8WWWy-yd-ndy1qt_3WWWWWWWWWW2Wfi"
"3WWWWWWWWq-1Wrp4WWWWWWWW2evZ5WWWWWWW1qms5WWWWWWWW6sni5WWWWWWW-3oua4WWWWWWWW4oa_4WWWWWWWW4qlk4WWWWWWW1eYv4WeWYmWa-udy1kbX"
"6WWWWWWWWWW2kfl5Wu-zl-x-qt1unh5WWWWWWW1coW6WeWYmWa-_7i_p6WWWWWWWW2mnW7WWWWWWW1qgq7WWWWWWWW6ltg7WWWWWWW-3wzb6WWWWWWWW4ybx"
"6WWWWWWWW4WXk6WWWWWWW1w-v6Wu--lWa-udy1yty6WWW2ue_5WWW_----m-1lfl6WWW2woZ6WWW_----Evek6WWW2rWj5WWWy-_t-nl1sww4WWWWWWWX8fu"
"s5WWWWWWW-7pxc5WWWYWXeWlFyZy6WWW2ilm6WWW_----1mbn7WWWYWWWW1qum6WWW_---Vujo7WWW2iYz6WWW_--Vtsa8WWW2ggm7WWW_----3uZs7WWW2h"
"zc7WWWWWWWW3lbd7WWW_---_3YqX7WWW2XYZ6WWW_---Vvsg7WWW2hut6WWWWWWWW3wXu6WWW_----3aif7WWW2mZh6WWW_--Vouq7WWW2oWt6WWWWWWy_ed"
"w1wqs5WWW_--3sps5WWW2amo5WWWWWWy-Dilm6WWWWm-ZW1eim6WWW_Fjdm6WWW2Wyc6WWWWm----l1cYZ7WWWWmWy-_7noY7WWW_--ZW1ghX7WWW2pYd6WW"
"WWm-ZWr7umo7WWWWGebl7WWW_--Rmhw7WWW2_ho7WWWWm-Z-3XnY7WWWWGuv-6WWW_--Rl-b7WWW2kcW7WWWWWWa-2y_n7WWWWWWSi_l7WWWWWWy_2-Xc7WW"
"WWm-ZW1zsa7WWW_Fgsb7WWW2zwp6WWWWWWyVrjd7WWWWm-3xsd7WWW_Fcke7WWW2pxx6WWWWm-3-tk7WWWWGbwg7WWWWG-qo7WWW2kct7W8_jz7Wu-z-_x-2"
"jhp7WWWWGegY7WWW_---W4pys7WWW2dnh7WWWWWWy_el1fqm6WWWWm-ZWW8-am6WWW_Fnyl6WWW2czc6WWW_l---E_nt6WWW2Xbn6WWW_Fkjn6WWW2lto5WW"
"WWWWy-m7inn6WWWWm-3cxn6WWW_Fgzn6WWW2abh6WWWWmWaW4Wus7WWWWW---3gzk7WWWWGkdh7WWWWWWWW3h-s7WWWWWWu-2wbx6WWWWm-ZW1fiv6WWW_Fr"
"lv6WWW2ynh6WWWWWWyVuzy6WWWWm-3vwy6WWW_Fczy6WWW2eYq6WWWWm-3oqY7WWWWGZYW7WWWWGtzb7WWW2Yif7W8vek7Wu-xl-x-6qgh7WWW2wXy6WWWy-"
"_t-fd1qy_4WWWWWWWX8uYy5WWWWWWW-7anh5WeWYmWaWn7yZw6WWWWWWWX8avp7WWWWWWW-7mgY7Wu--lWaWk7kty6WWW2uxp6WWW_----1ujo7WWWYWWWW1"
"avs6WWW_---VWsp7WWW2efY7WWW_--Vopc8WWW2wqt7WWW_----3lft7WWW2dZi7WWWWWWWW3cvl7WWW_---_3ycc7WWW2ijh6WWW_---Vush7WWW2nXy6WW"
"WWWWWW3s-_6WWW_----3ydk7WWW2abq6WWW_--Vvcw7WWW2ztW7WWWWWWy_e7Zfz6WWW_--3_pz6WWW2gwr6WWW_----1aZq7WWWYWWyVkto7WWWWWW4ucz6"
"WWWWWWyVYur7WWW_--3ihr7WWW2qvc7WWWWm-3X-z7WWWWGgsv7WWWWGgqY8WWW2qed8W8oek8Wu-xl-Rkjf8WWW2i__7WWWWm-Z-3typ7WWWWGzyl7WWW_-"
"-Rbev7WWW2ylm7WWWWWWa-2eo_7WWWWWWSnlw7WWWWm-ZVyta8WWWWGi_-7WWW_--Rgfi8WWW2nlW8WWWWm-3ydm8WWWWGmvf8WWWWGhzr8WWW2ikx8W8hiZ"
"9Wu-zl-t_1tah7WWWWm-ZW1cze7WWW_F-pf7WWW2q_r6WWWWWWyVpxi7WWWWm-3poi7WWW_Flij7WWW2wgW7WWWWm-3eYq7WWWWG-im7WWWWGnwt7WWW2yfy"
"7W8xkY8Wu-z-_x-2nuw7WWWWGoWd7WWWWWWyVwZy7WWWWm-3cYy7WWW_Fwby7WWW2_nh7WWWWm-3lva8WWWWGYYW8WWWWGbjf8WWW2Wkk8W8mnr8Wu-xl-x-"
"2cio7WWW2slW7WWW_--Vdn-7WWW2Zcn7WWWWWWyUtgp7WWW_--3cYq7WWW2ucb7WWWWm-3Xbx7WWWWGmys7WWWWGYd-7WWW2ewZ8W8obg8Wu-xl-RwxX8WWW"
"2xkt7WWWWm-3ilb8WWWWG__-7WWWWGeeg8WWW2yZl8W8-ur8Wu-zl-x_2Wrh7WWWWWWW1duW8WWWy-_t_ndx1Wme4WWWWWWWXpVazW6WWWWWWWW3imv5WWWW"
"WWWW4zys5WWWWWWWW2kqZ5WWWWWWW-3imt4WWWWWWWW2kjg5WWWWWYmW2unv5WWWWW_lW4iZn5WWWWWWW-tVyjo3WWWWWYmWpVqcg6WWWWWWWW3dw_5WWWWW"
"WWWEYqf5WWWWW_l-3cpY5WWWWWWWXkVZW-5WWWWWWWW6m_n5WWWWWWW-3urk4WWWWWWWW8quu4WWWWWWW1w-Z5WWWWWWW-fVwvX5WWWWWWWW1azo5WWWWWYG"
"mzs6WWWWW_FyZi6WWWWWYm-2woh6WWWWW_Fmhd6WWWWWYmVqmt6WWWWW_Fudm6WWWWWYGWnf7WWWWW_l-2XpY6WWWWWWWW1qrj6WWWWWWGmWy6WWWWWWmVwh"
"s5WWWWWWWW2ize6WWWWWWG_hq6WWWWW2kaX7WWWWW_l_1uwv4WWWWWWWW2mwl5WWWWWWWW1agu5WWWWWYmW1qi_5WWWWWWWW2vqo6WWWWW_l-1Wad5WWWWWW"
"W1mus5WWWWWWW-1svq5WWWWWWW1bef6WWWWWWW-1ahi5WWWWWYGehc6WWWWW_FWyz5WWWWWWGytd6WWWWW2aco6WeWYm_p_qdx1cfg6Wu-zl-xWrNjk-5WWW"
"WWWWW4ovy5WWWWWWW-7icl5WeWYmWaXr7p_s7WWWWWWWW4lgq7WWWWWWWW2tvZ7WWWWWWW-3aht6WWWWWWWW2ayb7WWWWWYmW2mau7WWWWW_lW4vol7WWWWW"
"WW-tViZr5Wu-zlXiWrNzsa6WeWYmWaWX8rty7WWWWWWWWEojg7WWWWW_l-3fo-6Wu-zl-xWjNiXb6WeWYmWaWX8q-x7WWWWWWWW6aXm7WWWWWWW-3mok6WWW"
"WWWWW8sjt6WWWWWWW1tZa7Wu-zl-x_eNwtb5WWWWWYmW4mpn6WWWWW_Fxpj6WWWWWWWW4Xge6WWWWWWWW4nel6WWWWWWGwox6WWWWW2hhf7WWWWW_l_3yjq5"
"WWWWWYmW4nkv6WWWWW_l-3kxv5WWWWWWW1jtl6WeWYmWa-e7yrW7WWWWWYmW4a-e8WWWWW_FruZ8WWWWWWWW4vW-7WWWWWWWW2woq7WWWWWWWW2tbb8WWWWW"
"WGmcl8WWWWW2cyy8WWWWW_l_1Ygv6WWWWWWWW2emg7WWWWWYmW2zdz7WWWWWWWW2Zrl8WWWWW_l-1m-Z7WWWWWWW1pbr7WWWWWWW-1ebl7WWWWWWW1bgb8WW"
"WWWWW-1mwe7WWWWWYGawa8WWWWW_FXtx7WWWWWWGawa8WWWWW2sam8Wu-zl-x_bdw1yZe6WWWWWWu-1_wi6WWWWWW8iza6WWWWWWuVm_n5WWWWWW8uYl5WWW"
"WW_lW3wwc6WWWWWWWW3zlz5WWWWWXm-7pff6WWWWW1gaY6WWWWW_l-3moj5WWWWWWW1WzY6WWWWWWW-tFssj4WWWWWWWXrFXWc6WWWWWWm-3svh6WWWWWWmW"
"3ugw5WWWaWXe-5fdd6WWWy--dW2rhu6WWWWW-lWoFhYz5WWWWWWe-5_f-5WWWWWWObff5WWWWWWW-3oXz4WWWWWYmW4aZY6WWWWW_lW4qgv5WWWWWWWWjFga"
"k6WWWWWWWW1ela6WWWWWYuVphe7WWWWW_7sho6WWWaWX8wvo7WWWy-W8ush7WWWWW_l-1ahe6WWWaWXeW2_Zm7WWWy-_7ZZ_6WWWWWWmVyy_5WWWWWYuVqgh"
"7WWWWW_7hrl6WWWWWWGmyx6WWWWW2-pf7WWWWWWeVXmw6WWWWW_7ipc6WWWaWX8jrW7WWWy-_7ocm6WWWWW2Xcx6WWWWW_l_1Y_Z5WWWWWWWW1cks5WWWaWX"
"eW1udq6WWWWWWWW1oiY7WWWy--dW1Ytx6WWWWW1xsk6WWWWW--Vbpf7WWWWW1jsy6WWWWWWuVyr_6WWWWWW8dss6WWWWWW8ija7WWWWW1ahh7WWW4cgq7WWW"
"y-ydW2uua6WWWWWWWW1sio6WWWaWXeW1c-h7WWWy-_t-1jti6WWWWWWGyau6WWWWW2qmb7WWWWW_l_pFWas3WWWaWXeWpFyqf6WWWy-WWW2YYz6WWWaW---C"
"qwo5WWWy-WeWnFlfl6WWWWW---1luy6WWWWWWWW1Zif6WWWWW1ybY6WWWWW---Dneh6WWWWW1Zgl5WWWWW_l-3Zmf5WWWWWYmWhFXku6WWWWWWu-1tz-6WWW"
"WW-7hgW7WWWWW1kjn6WWWWWWuV_Wh6WWWWWW8Wlc6WWWWWWuVwjY7WWWWWW8YZv6WWWWWW8Wce7WWWWW1qel7WWW4ghu7WWWy-_--5erl7WWWWWWWW1aqa7W"
"WWWW-t-5eoo6WWWWW1uWd6WWWWW--Vfvb7WWWWW1rlv6WWWWWWuV_rr6WWWWWW8kel6WWWWWW8qvw6WWWWW1weW7WWW4cgd7WWWy-yd-1spo5WWWWWWWW1qW"
"y5WWWaWXeW1ely6WWWy-WeW2x_s6WWWWW_lWgFc-Y6WWWWWWWW6gvv5WWWWWWW-3_wp4WWWWWWWW8uZ_4WWWWWWW1aof5WWWaWXe-gFkrs6WWWy-_tW2WWn6"
"WWWaWXeW2spt7WWWWWWWW4wsl7WWWy-_tVX-b6WWWWWWWW1Ypo6WWWaWXeW1tfi7WWWWWWW-3joh6WWWWWWWW1px_6WWWWWWWW7ghq6WWWWWWW1bWX7WWWy-"
"_t_1aZu5WWWWWWW1Xkj6WWWWWYm-cFyZy6WWWWWWWW3mXl6WWWWW_Fych6WWWWWYmVkty6WWWWW_Fwgr6WWWWWYGZjm7WWWWW_--3myX7WWWWWWmVqzz5WWW"
"WWWWW2h-i6WWWWWWGkqu6WWWWW2-Wc7WWWWW_l_1iW-4WWWWWYmW4mmc6WWWWWWWW2c_s6WWWWW_l-1Yvj5WWWWWWW1bp_5WWWWWWW-3wmp5WWWWWYGgal6W"
"WWWW_Fpdc6WWWWWWGsom6WWWWW2qqx6WWWWW_l_aFuvf5WWWaWXeW2kdz6WWWy-W8upW7WWWWWWu-1yqf7WWWWWW8eXu6WWWWW_Fkgr6WWWWWYeVWds6WWWW"
"WW8iXn6WWWWW_FmXl6WWWWWYeVgei7WWWWWW8ceX7WWWWWW8Yro7WWWWW1qnw7WWW4ufa8WWWy-y7ijw6WWWaWX8mZ-7WWWy-W8lft7WWWWW_l-1apk6WWWa"
"WXeW2irw7WWWy-_7Ywd7WWWWWWmVhYe6WWWWWYuVpys7WWWWW_7bWt6WWWWWWGiqa7WWWWW2zpp7WWWWWWeVpjf7WWWWW_7qZn6WWWaWX8uym7WWWy-_7ivy"
"6WWWWW2uhg7WWWWWWeVyku7WWWWW_7afx6WWWaWX8XuW8WWWy-_7_lf7WWWWW2bev7WWWWW_7ydm7WWWaW1ang8WWWyVwxX8WWWWW1ufi8WWW4Xqt8WWWy-y"
"dUg_a5WWWWWWWW1wjv5WWWaWXeW1Yes6WWWWWWWW1sWd7WWWy--dW1chW7WWWWW1-zm6WWWWW--Vasm7WWWWW1hjX7WWWWWWuVkxZ7WWWWWW8Xcx6WWWWWW8"
"eyf7WWWWW1ynm7WWW4Wkv7WWWy-_lVk_n7WWWWWW8l-b7WWWWWW8xnu7WWWWW1quW8WWW4n_g8WWWy-ydVuYr5WWWWWWW1gsd6WWWWWWWVqk-5WWWWWWW1sX"
"t6WWWaWXeVeyW7WWWWWWW1cln7WWWWWWWVyuh7WWWWWWW1xyW8WWWy-_tUqlx5WWWWWYGwhx6WWWWW_Fzgn6WWWWWWGinz6WWWWW2uXh7WWWWW_lUaxY6WWW"
"WWYGeac7WWWWW_FWlx6WWWWWWGYyf7WWWWW2Zpv7WWWWW_lUuy_5WWWaWX8gtb7WWWyVwXg7WWWWWW8yXW7WWWWWW8wZm7WWWWW1qot7WWW4YxW8WWWy-y7s"
"vr6WWWaWX8txt7WWWy-_7krY7WWWWW2m-m7WWWWW_7ycf7WWWaW1YxW8WWWyVozu7WWWWW1sWY8WWW4vzh8WWWWW_h_adv1abw5WWWWWW4_-r5WWWy-W8qpm"
"6WWWWWWu-1asq6WWWWWWeW1kxg6WWWWW_lW6idf6WWWaWXa-4gkr6WWWWm-ZW1yhr6WWWWGiwh6WWWy--dW2xs-6WWWWW1kno6WWWWWWu-nFiXl6WWWWWW8W"
"ad6WWWWW---DZn-6WWWWWXWWl7Wkg6WWWWWWu-1qZl6WWWWWWyVgem6WWWWWW4Wir5WWWWWW8Wmo5WWWWW_lW6vYY6WWWWWXm-7jXk6WWWWW1Wyc6WWWWW_l"
"-3egn5WWWWWWW1sld6WWWWWYm-g7y-o6WWWWWWu-1ypt6WWWWWWWW1kpm6WWWWWW8mkh6WWWWWWuVosw6WWWam-3qfh7WWWyFidY7WeWYGgyo7Wu-XG-rk7W"
"WWy-_3aZq6WeWYmW4yvl7Wu-zFusd7WWWWW-3Xl-6WWWWW1e_a7WWW4YZi7WWWy-_Nozm7WWWam_x_3Zzr7WWWWGzko7WWW_--R-k_7WWW2eis7WWWy-_7qj"
"a7WWWWWWmVogi6WWWWWYuVp_j7WeWYm_B-zw7Wu-zlXeV_vn7WWWWWWCsdh7WWWWW_7aor6WWWaWX8qns7WWWy-W8vjl7WWWam-x_4tYw7WWWWm1oWY8WWWy"
"-zZW1oqY7WWWWW1_dp6WWWWW--Vqee7WeWYmW4_vd8WWWWW1qaW8Wu-zl-pVifb7WWWWWW8bux6WWWWm_7wco7WWWaW1WjY8WWWyFs-g7WWWWGeYv7WWWWGe"
"eo7WWW4mpx7WWWy-yd-1mnu5WWWWWWW1Ymk6WeWYmWaVmxe7WWWWWWW1uYW8Wu--lWaViet7WWW2agb7WWW_--VYch8WWW2cqx7WWWy-We-1ur-6WWWWW_Fy"
"ju6WWWWWYGoZq7WWWWW_l_p7i_m4WWWWWWWXs7_we6WWWWWWm-3tkk6WeWYmWq-6sdl6Wu-XWWaW1lrf7WWWyl-tWw7YX-5WWWaWXa-4naf7WWW_--ZW1woe"
"7WWW2XWi6WWWy--dW2gf_6WWWYWWuWp7d-z7WWW2lwr7WWWWm-Z-3g-d7WWWWGxcb7WWWWm-Bfw-7WWWWGgXv7WWW_--F_nh7WWW2bqb7WWWy-_tVYrg6WeW"
"YmWaW1ust7Wu-XmWeVYjr7WWWWWWSzep7WWWy-_7dgX7WWWaWXq_2Yoi7WWWWm-ZW1sZh7WWW_Frbi7WWW2gwu6WWWWWWyVXzj7WWWWm-3ddk7WWW_Fwwk7W"
"WW2WgX7WWWWm-3Wur7WWWWGonn7WWWWGtwv7WWW2kp_7W8agb8Wu-vl-ZW1cig7WWWWWWWW1soo7WeWYmW4Yds8Wu-XWWaW1Yzl8WWW_l-lW4eo_7WWW2-lo"
"7WWWy-_t-1cfr6WWWWWWGWbb7WWWWWWm-f7quX6WWWWWWe-5oda6WWWWWWOusi5WWWWWWW-3akW5WWWWWYmW4otc6WWWWW_lW4kwz5WWWWWWWWk7sum6WWWW"
"WYuVgnk7WeWYm_Balw7Wu-zl-Z-4_so6WeWYmWaW1YY_7WWWWWWObdf7Wu-zlXeVqxs7WWWWWWCgwk7WWWWW_7lio6WWWWWWGqr_6WWWWW2-wi7WeWYm_p_2"
"ugy6WWWWWYmW4vs-7Wu-zl-pVcoj7WWWWWW8op-6WWWWm_7Wgz7WWWWm1kpp7WWWWGzlb8WeWYW_hW3ops7Wu-zl-x-i7wff6WWWWWYiVbmo7WWWWWWCknh7"
"WWWWW_7_dr6WWWaWX8sds7WWWy-W8XXl7WWWaW-x_3lwr7WWWWWWSYkp7WWWy-_7x-W7WWWWWWmVcjZ6WWWWWYuVuqk7WWWWW_hVsau6WWWaWX8czu7WWWyV"
"v_p7WWWWWW8vcn7WWWWWW4tp-6WWWWW_7gjh6WWWWWW4ynY7WWWaWX4kxb7WWWy-_7gdr6WWWWW2wgW7WWWWW_l_1oed5WWWaWXaW1__r7WWWWWWaW1qXv6W"
"WWWWWyVqgt7WWWWWW4wfb7WWWWWW4e-w7WWWWW2svl8WWWy-zZW1yoX7WWWWW1ojp6WWWWW--Vgij7WWWWWXuVjra7WWWWWW8uxx6WWWWWW8btg7WWWWW1eW"
"o7WWW4Ylx7WWWy-ydW2sdf6WWWaWXeW2uqo7WWWy-_t-1gsn6WWWWWWGw_z6WWWWW2vWi7WWWWW_l-f7mkq6WWWWWYiVweq7WWWWWWCY-l7WWWWW_7cYw6We"
"WYmW4yvX8Wu--lW4qfc8WWW2bYz7WWWy-W8akr7WWWam_x_3ixw7WWWWGdbt7WWW_--RqmW8WWW2oxt7WWWy-_7ckc7WWWWWWmVe_i6WWWWWYuVyWr7WeWYm"
"_Bofy7Wu-XmWeVmpy7WWWyVqiv7WWWWWWClem7WWWWW_7wjs6WWWaWX8zZu7WWWy-_7m_Y7WWWWW2ogn7WWWam_xUqiY8WWWWGWe_7WWWyVY-x7WWWWWWCnu"
"s7WWWam-3mfn8WWWyFme_7WeWYGppt8Wu-zFoid8WWW4eYo8WWWy-y3oWx6WeWYmW4ilZ8Wu--lW4Wlf8WWW2uz_7WWWWm-3cri8WWWWGuzc8WWWWGkxn8WW"
"W2_Wt8W8me_8Wu-vl_3qhe7WWWWW2Ytt7WeWYm_3qZi8WWWWW2lgu8Wu-zlz3wck7WWWaW1qhd8WWWyVzX-7WWWWW1Wte8WWW4Ycp8WWWy-ydUmgh5WeWYmW"
"aW1uyY7Wu-XGoht7WWWWm-ZW1dXs7WWWWGkl-6WWWWWWyVetu7WWWWm-3-ev7WWWWGyqf7WWWWm-3YcX8WWWWGajy7WWWWGztb8WWW2exg8W8mzn8Wu-zl1i"
"mo8WWWy-zZW1jth7WWWWW1yxv6WWWWW--VzYq7WeWYmW4lav8WWWWW1a_h8Wu-zl-pVwzk7WWWWWW8l-Z7WWWWm_7W_-7WWWaW1iyo8WWWyFqar7WWWWGZXe"
"8WWWWGYYz7WWW4rbd8WWWy-_lVflr7WWWam-3whj8WWWyFWxX8WeWYGxwx8Wu-XGkfr8WWWy-_3exe7WeWYmW4eup8Wu-zFikg8WWWam_3Wjr8WWWyFjxx7W"
"WWWW1uaa8WWW4tqk8WWWWm_3ypv8WWWyFuna8WeWYG_mW9Wu-zFWjk8WWW4dfw8WWWyFWep8WeW2Wyc9Wu-1tz-8WWW2cnd9W8eXm9Wu-vlyZW1mgl6WeWYm"
"WaW1knX8Wu--lWaW1lkk8WWW2jdz7WWWWm-ZVxte8WWWWGxrZ8WWW_--Rcwm8WWW2wfa8WWWWm-3zpq8WWWWGquj8WWWWGzfw8WWW2qYW9W8ece9Wu-vl_pV"
"_gv6WWWWWWGyuc7WWWWW2wWs7WeWYm_pVWWf8WWWWWWGycp8WWWWW2niX9Wu-zl-ZVq-x7WWWWW_7sb_6WWWaWX8uja8WWWy-_7eli7WWWWW2wuy7WWWWW_7"
"_cp7WWWaW1Wjk8WWWyVlmb8WWWWW1sam8WWW4nxx8WWWy-yd_n7uou3WWWaWXaWp7etr6WeW_l---Dcpu5Wu-XWWaWo7igr6WWWWGqwh6WWWy-WWW2dcW7WW"
"WYm_--CuXz6WWW2Yos6WWWWGies5WWWWWWy-m7sls6WWWWm-3Wzs6WWWWGWxl6WWWy-WWW2psb7WWWam-ZW2waw7WWWWm1XlY8WWWWmz--3lur7WWWWGvxn7"
"WWWWWWWW3eyw7WWWWWWu-2wmW7WWWWm-ZW1wu_6WWWWGufm6WWWWWWyVsdY7WWWWm-3kdY7WWWWGiZv6WWWWm-3WXe7WWWWGWhb7WWWWGohh7WWW2yyk7W8e"
"wp7Wu-zl1psa8WWW_-zx-6y_n7WWW2-mX7WWWy-_t-1mg_5WWWWWYmWd7eao6WWWWW---1Zz-6WWWWWWWW1qdk6WWWWW1czc6WWWWW---DZkm6WWWWW1auo5"
"WWWWW_l-3aij5WWWWWXmWk7iww6WWWWW1krp6WWWWW--Vuve7WeWYmW4pZe8WWWWW1ycW8Wu-zl_--6-gz7WWWWWWy-5hwa7WeWYmWaW1zyg8WWWWW1uxl7W"
"u-zl_xVZjf7WWWWW1xby6WeWYm_p-2iXb7Wu-zlXiWg7XYx6WWWWWWu-1h_Y7WWWWW-7cjZ7WWWWWXuVZvl6WWWWm_7vaa7WWWWm1X-g6WWWWWWuViqb7WWW"
"WWW8wux6WWWWm_7qvo7WWWaW1ctY8WWWyFmgh7WWWWGsqv7WWWWGYoo7WWW4_ux7WWWy-_--5kkp7WWWWWWWW1axg7WWWWW-t-5Xrt6WWWWW1ynh6WWWWW--"
"Vzbf7WWWWWXuVhuw6WWWWm_7sei7WWWWm1eYq6WWWWm_7wks7WWWaW1erb8WWWyFxw-6WWWWGuay7WWWWGajb7WWW4bni7WWWy-yd-1Yis5WWWaWXeW2ztX7"
"WWWy-WeW2pay6WWWWWWWWd7aZ-6WWWWWWu-1wxc7WWWWW-7pyc7WWWWWXuVxjx6WWWWWW8tpr6WWWWWWuViXg7WWWam-3Zy_7WWWyFedq7WeWYGzvf8Wu-XG"
"wfa8WWWy-_3m_-6WeWYmW4gva8Wu-zFygx7WWWam_3mha8WWWyFgql7WWWWW1m_s7WWW4ecW8WWWWmzp-3plX8WWWWGfZz7WWWy-WiW2gfw7WWWWWWqVzg-7"
"WWWWWWCzfr7WWWWWWqVgvX8WWWWWWCwxx7WWWam-3pqv8WWWyFgna8WeWYGeqW9Wu-zFeik8WWW4biw8WWWWm_l-3dZ-7WWWWm1rxg8WWWy-zZW1lad7WWWW"
"W1kqr6WWWWW--Vqhl7WeWYmW4-_m8WWWWW1zXb8Wu-zl-pVWmg7WWWWWW8rcW7WWWWm_7spw7WWWaW1nih8WWWyFshm7WWWWGqpX8WWWWGgot7WWW4jwW8WW"
"Wy-_lVyum7WWWam-3quc8WWWyFYmy7WeWYGksp8Wu-XGquj8WWWy-_3gXb7WeWYmW4myi8Wu-zFgaa8WWWam_3W_j8WWWyFxvs7WWWWW1wl_7WWW4tce8WWW"
"Wm_3wXo8WWWyFYj-7WeWYGtdu8Wu-zFsbe8WWW4vro8WWWyFeci8WeW2ygz8Wu-1tdt8WWW2uvz8W8sWb9Wu-vlyZVujx5WeWYmWaW1agj7Wu--lWaW1ms_7"
"WWW2vxf7WWWWWWyVvZW8WWWWm-3p_-7WWW_FyYW8WWW2-rk7WWWWm-3oye8WWWWGkWa8WWWWGhlj8WWW2wqo8W8szv8Wu-vlWaW1wca7WeWYmWaW1nyp8Wu-"
"zl-pVerr7WWWWWW8hWf7WWWWWW8lcy7WWWWW1kla8WWW4t-k8WWWy-ydWe7kod6WWWWWWWW6_Z_5WWWWWWW-3oXt4WWWWWWWW8qjX5WWWWWWW1w_i5WWWWWW"
"WWk7aup6WeWYmWaW1e_-7WWWWWWWW6W_s7Wu-zl-xVujr6WeWYmWa-2cfp6WWWWWWWW8eky6WWWWWWW1iif7Wu--lWa-f7efY7WWW2ayu6WWW_---W4Ybh8W"
"WW2ckx7WWW_----3i__7WWW2fwo7WWWy-_tVkng6WWWaWXeW2-wo7WWW_---_3Ybj7WWW2qZm6WWW_---V_ho7WWW2rmX7WWW_----6crr7WWW2qbv6WWW_-"
"-V-cY8WWW2YYc7WWWy-_t_1uXy5WWWWWWW1qho6WWWaWXa-c7WnY7WWW_--3wxY7WWW2mrw6WWWWmWaW4wbc8WWW_l-Rssj8WWW2ctY8WWWWm-Z-3Ypw7WWW"
"WGcjs7WWW_--RnlW8WWW2mYt7WWWy-_tVoym6WeWYmWaW1XkY8Wu-XmWeVWjY8WWWWWWSgwz7WWWWm-ZVhve8WWWWGxxZ8WWW_--R_tm8WWW2mha8WWWWm-3"
"qsq8WWWWGW_j8WWWWGjlw8WWW2gbW9W8qie9Wu-zl-t_1unn7WWWWm-ZW1cfl7WWW_Fi_l7WWW2ivw6WWWWWWyVubp7WWWWm-3q-o7WWW_FZqp7WWW2bqb7W"
"WWWm-3svw7WWWWGfxs7WWWWGjt_7WWW2_jZ8W8WWg8Wu-z----3znj8WWW_l-x-2obv7WWW2mvb7WWW_--Vmld8WWW2fxt7WWWWWWyUnaw7WWW_--3atw7WW"
"W2csg7WWWWm-3iiY8WWWWGiwz7WWWWGirc8WWW2qmh8W8ygo8Wu-xl-Rmvf8WWW2wn_7WWWWm-3kmj8WWWWGqpd8WWWWGjno8WWW2ost8W8bv_8Wu-vl_pUa"
"tX6WWWWWWW1ovv6WeWYmWaVaeo7WWWWWWW1zgf8Wu-XmWaVcvk7WWWWWWW1esa8WWWy-We-a7uW-6WWWWWWWW3uxp6WWWWW_FbZm6WWWWWYmVur-6WWWWW_F"
"qfu6WWWWWYGu-p7WWWWW_--3wYb7WWWWWWmVyZY6WWWWWWWW2exn6WWWWWWGsd_6WWWWW2hfi7WWWWW_l_1WeY5WWWWWYmW4a_g6WWWWWWWW2aay6WWWWW_l"
"-1Won5WWWWWWW1azY6WWWWWWW-3ilt5WWWWWYGywp6WWWWW_Fiug6WWWWWWGqfr6WWWWW2wpW7WWWWWWW-f7sfw6WWWWW_Fi-t6WeWYmYqV_oi8WWWWW_Fzr"
"d8WWWWWWWW6ogx7Wu-zl-xVeuv6WWWWWWGYjd7WWWWW2nws7WeWYm_pVtbf8WWWWWWGglp8WWWWW2hsX9WWWWW_l_1ma_6WWWWWYmW4bla8Wu-zl-xVWca7W"
"eWYmWaW1z_p8WWWWW_l-1ief7WWWWWWW1zwx7WWWWWWW-3yek7WWWWWYGkqi8WWWWW_FXzY8WWWWWWGkqi8WWWWW2puu8Wu-zlzhUWeb6WWWWWYGgbf7WWWW"
"W_Fnk_6WWWWWWGwYj7WWWWW2hgz7WWWaW-t_a7ak-6WWWy-W8ghZ7WWWWWWu-1uyi7WWWWWWWW1ybx6WWWWWW8osr6WWWWW_Fmzp6WWWWWYeVwrl7WWWWWW8"
"iXa7WWWWWW8-_r7WWWWW1e-z7WWW4wxd8WWWy-y7uhz6WWWaWX8qyY8WWWy-W8mxw7WWWaW-t-3sW_7WWWy-_7jyg7WWWWWWmVfni6WWWWWYuVvow7WWWWWW"
"WW1vll7WWWWW_7mzr6WWWaWX8set7WWWy-_7wgY7WWWWW2ylm7WWWWWWeVpdy7WWWWW_7qe_6WWWaWX8vpa8WWWy-_7wqi7WWWWW2ezy7WWWWW_7yjp7WWWa"
"W1krk8WWWyVjvb8WWWWW1emm8WWW4vdy8WWWy-ydUuce5WWWaWXeW2yyw6WWWWWWWW1quf7WWWy--dW1lbc7WWWWW1amr6WWWWW--VXlq7WWWWWXuVrsf7WW"
"WWWW8kcW7WWWWWW8fzl7WWWWW1_zs7WWW4ZeW8WWWy-_lVuvr7WWWWWW8rWf7WWWWWW8qhy7WWWWW1mta8WWW4wZl8WWWy-ydVuvu5WWWWWWW1sXi6WWWaWX"
"e-1u_b7WWWWWWW1tvt7WWWWWWWVkvk7WWWWWWW1gva8WWWy-_tUqg-5WWWWWYGuhW7WWWWW_FzZs6WWWWWWGuXZ7WWWWW2udn7WWWWW_l_1uwY6WWWaWX8__"
"g7WWWyVkem7WWWWWW8kdb7WWWWWW8Zos7WWWWW1qj_7WWW4Wce8WWWy-y7kuw6WWWaWX8uq_7WWWy-_7eme7WWWWW2tnt7WWWWW_7Wkl7WWWaW1Wce8WWWyV"
"__-7WWWWW1wnf8WWW4z_p8WWWWW_h_a7u_e7WWWWWW4ckW7WWWy-W8irb7WWWWWWu-1uxk7WWWWWWWW1mlX7WWWWWW8eix6WWWWW_Fodw6WWWWWYeVm-n7WW"
"Wam-3ole8WWWyFifz7WeWYGwkq8Wu-XGtqk8WWWy-_3ijc7WeWYmW4gvk8Wu-zFcXb8WWWWW-3xbu7WWWWW1yZW8WWW4y-f8WWWy-y7oeW7WeWYmW4mnh8Wu"
"--lW4_Wo8WWW2xmc8WWWy-W8Wg_7WWWam_x_3X_Z8WWWWGXk-7WWW_--Rlng8WWW2ecW8WWWy-_7szj7WWWWWWmVkZo6WWWWWYuVZY_7WeWYm_BWsa8Wu-Xm"
"WeVmdc8WWWyVzfZ8WWWWWWCd_t7WWWWW_7may6WWWaWX8deW8WWWy-_7usf7WWWWW2zZv7WWWam_xUm_i8WWWWGWxd8WWWyVubc8WWWWWWCmx-7WWWam-3ti"
"_8WWWyFete8WeWYGkjb9Wu-zFeZp8WWW4Yc-8WWWy-y3ucX7WeWYmW4Wcj8Wu--lW4_nr8WWW2qie8WWWWm-3wdv8WWWWGeYo8WWWWGrz_8WWW2Wya9W8eZj"
"9Wu-vl_3yyl7WWWWW2epW8WeWYm_3Yot8WWWWW2XZc9Wu-zlz3Wrs7WWWaW1ylo8WWWyVklf8WWWWW1Yjq8WWW4ihW9WWWy-ydUezh5WeWYmWaW1WzZ7Wu-X"
"GYaw7WWWWm-ZW1pZu7WWWWGeoW7WWWWWWyVWqx7WWWWm-3ntx7WWWWGYZi7WWWWm-3wtZ8WWWWGyf-7WWWWG-ce8WWW2ecj8W8abq8Wu-zl1hWt8WWWy-zZW"
"1xhk7WWWWW1Yax6WWWWW--Vr-t7WeWYmW4Yvz8WWWWW1jgk8Wu-zl-pVtwn7WWWWWW8qmc7WWWWm_7qka8WWWaW1Ylt8WWWyFwYu7WWWWGcji8WWWWGew-7W"
"WW4huf8WWWy-_lVlkv7WWWam-3Zsn8WWWyFcoc8WeWYGvyW9Wu-XGdfw8WWWy-_3g-h7WeWYmW4hau8Wu-zFxel8WWWam_3biw8WWWyFu--7WWWWW1mle8WW"
"W4iYp8WWWWm_3ew_8WWWyF_hf8WeWYGkwb9Wu-zFklp8WWW4co-8WWWyFWgu8WeW2WZi9Wu-1Xab9WWW2eui9W8uer9Wu-vlyZVaXz5WWWWWWW1qan6WeWYm"
"WaVqsl7WWWWWWW1oia8Wu--lWaV_oY8WWW2qfi7WWW_--VZap8WWW2XaW8WWWWWWyUdWa8WWW_--3mZa8WWW2_tn7WWWWm-3lWj8WWWWG-wd8WWWWGitn8WW"
"W2u_s8W8if_8Wu-xl-Rkvr8WWW2Wle8WWWWm-3uuv8WWWWGvro8WWWWGvl-8WWW2Yhb9W8qoj9Wu-vl_pUyvZ6WWWWWYGisc7WWWWW_FoXy6WWWWWWGuvf7W"
"WWWW2iWv7WeWYm_pU_er7WWWWWYGkbu8WWWWW_Fqbj8WWWWWWGkbu8WWWWW2hrc9Wu-zlzhUWpd6WWWaWX8kxn7WWWyVWlv7WWWWWW8yZi7WWWWWW8YWW8WW"
"WWW1mqe8WWW4wep8WWWy-y7YgX7WWWaWX8hne8WWWy-_7aem7WWWWW2axW8WWWWW_7ykt7WWWaW1wep8WWWyVydg8WWWWW1yar8WWW4gZX9WWWy-ydUezf6W"
"eWYmW4Whu7Wu-XGege8WWWWWW4exq7WWWyVklz7WWWam_3knn8WWWWG_Zi8WWWWGYgs8WWW2erx8W8mXZ9Wu-vFqXh8WeWYGutc9Wu-XGtz-8WWWy-_3aal7"
"WeWYmW4kvy8Wu-zFuhq8WWWWW-3dXa8WWWWW1iyi8WWW4yrt8WWWWm_3tfa9WWWyFqsj8WeWYGcnh9Wu-zFwmu8WWW4Xab9WWWyFWxz8WeW2qlo9Wu-1afh9"
"WWW2ydp9W8uZy9Wu-vly3qea7WeWYmW4cln8Wu--lW4aZx8WWW2xqi8WWWWm-3bW-8WWWWGtdt8WWWWGcwa9WWW2oWh9W8bnp9Wu-vl_3yop7WWWWW2usa8W"
"eWYm_3kvy8WWWWW2zbi9Wu-zlz3qxw7WWWaW1yrt8WWWyVbkk8WWWWW1kwv8WWW4gec9WWWy-y3md-7WeWYGmXZ9Wu-1mhc9WWWWGemz8WWWWGXei9WWW2yd"
"p9W8uZy9Wu-vFqyp8WeWYGeup9Wu-zFe_-8WWW4gaj9WWWyFkbc9WeW2uZy9Wu-1imq9WWW2q-y9W8zjcAWu-vlyZ_Wdu1mjv1WWWWWWWWWW8mrp2WeWYmWa"
"WXeu1Whw3Wu-XmW4Whd5WeW_l-x---7WXt4Wu-XmW4qYz5WWWWm-x-Weu1Wad5WWWWGWcy4WWWWWW4uou3WWWWm-x---7coW6WWWWGacs5WWWWWW4szq4WWW"
"WWWWW-tt1aod5WWWWWWyVuid5WWWWWW4uk_4WWWy-W8q-x5WWWam_p--7qqd5WWWWGye-4WWWWWW4qt_3WWWWWWy-_7yhj5WWWWWW4sug5WWWWWWyVssg5WW"
"WWWW4aYW5WWWWWWyVWym5WWWWWW4mwi5WWWWm-3Wkq5WWWWGWYp5WWWWGWus5WWW2Wbv5W8Wky5Wu-zl1s_r6WWWWWWCa__6WWW_-zFkro6WWW2yyl6WWWWW"
"WW-zl7ysz5WWWWm-x-W8mWY6WWWWGuYy5WWWWWW4aYW5WWWWWWy-_7eha6WWWWWW4mW-5WWWWWWyVsoW6WWWWWW4w_i5WWWWWWyVwqe6WWWWWW4qiX6WWWWm"
"-3alj6WWWWGyeh6WWWWGqhm6WWW2ujp6W8uqt6Wu-zl1jli7WWWWWWCqvo7WWW_-zFxje7WWW2jiZ7WWWy--x_Weu1eou5WWWWWW4WvW5WWWWW1_hu4WWWWW"
"W8Was3WWWWW-p---7mYj6WWWWWW4qms5WWWWW1tYn5WWWWWW8exn4WWWWW-t---t1arc5WWWWW1it_4WWWWW----7iqW6WeWYmWaW1yYZ7WWWWW1Ylw6WWWW"
"WW8ewv5Wu-zl_p-_t7wg-5WWWWW1_Wy5WWWWW----7ebh6WeWYmWaW1yrt7WWWWW1vzn7WWWWWW8Weq6Wu-zl-x-ydt1qfX5WWWWWWq-1Wtv5WWWWWW4WWX5"
"WWWWWW8oqw4WWWWW-p--Fkww5WWWWWX4slx4WWWWWW8yey3WWWWWWq-zFxqZ6WWWWWWCijc5WWWWWWq-1zfy5WWWWWW4lic5WWWWWW8wxy4WWWWm_p-1Whg6"
"WWWWm1u-d6WWWWWW4ybi5WWWam-3uW-6WWWyFwrh6WWWWGmuw6WWWaGYWt6WWWy-_3qif5WWWWm_3ifq6WWWWm1Yvg6WWWWGetu6WWWWGclm6WWWWmz3Wjj6"
"WWWWm1Wkl5WWWWW1W_o5WWW4Wnt5WWWylzBuxa7WWWWmXCang6WWWWWWW-x-6yut5WWWWW-p-XGpwm6WWWWWX4fus5WWWWWW8wuy4WWWWWWq-zFfmq6WWWWW"
"WCcxv5WWWWWWq-1rie6WWWWWW4gZx5WWWWWW8aof5WWWWm_p-1ayt6WWWWm1_uv6WWWWWW4WqY6WWWam-3exo7WWWyFkZ-6WWWWGovk7WWWaGilj7WWWy-_3"
"Wiz5WWWWm_3exb7WWWWm1cfz6WWWWGmhh7WWWWGZib7WWWWmz3q_W7WWWWm1ssc6WWWWW1qih6WWW4_in6WWWylzBWwo7WWWWmXCtXz6WWWWWWW-xts1yoy5"
"WWWWWWu-1i-y5WWWWWWeW_7qyc5WWWWWWu-1mvc5WWWWWW8kjW5WWWWWWWW_7_cX6WWWam-xVeoy5WWWWm1egv6WWWy-_3W_g6WeWYmW4WuZ7Wu-XmW4ur-6"
"WWW_-zFqxu6WWW2iYs6WWWy-W8uZc7WWWWWWuUxWY6WWWWWW8muk5WWWWWWuVull6WeWYmW4cqZ7WWWWWW8sgz6Wu-zl-3uzq6WWWWW1yox6WWWam_pVg-u6"
"WWWWm1op-6WWWy-_3mjb6WWWWWX4pnx6WWWWW-3Yyk6WWWaW1yxv6WWWy-_NoyZ7WWWWW-p_z7yjz5WWWWWX4wsW5WWWWWW8W--3WWWWWWWW_7wm-5WWWWWW"
"u-1bn-5WeWYmWaW1Yvz6WWWWWW8mq-5Wu-zl_3mzq6WWWWW2qkv6WWWWW-lVszf6WWWWWW4_xq6WWWWWW4qaY6WWWWW-3fXr6WWWWW2clv6WWWWW-3qyj6WW"
"WWW1Wnp6WWWWW-NibX7WWWWWWu_w7mrc6WWWWWWyViwc6WWWWWWCYai5WWWWWWu-1zYi5WWWWWW8kmY5WWWWWWq-1ceh6WWWWWW4mxn5WWWam-3ur-6WWWyF"
"cZl6WWWWGalx6WWWaGsfw6WWWy-_3yXl5WWWWWW4cck6WWWWW1Wwp6WWWWmz3yom6WWWWm1iZr5WWWWW1epu5WWW4aez5WWWy-_Nwmm6WWWWWWu_w7khj6WW"
"WWWWeW1iyY6WWWam-xVi-v6WWWWm1fuZ7WWWy-_3apj6WeWYmW4sZe7Wu-zFey-6WWWWW-3gku6WWWaW1wca7WWWy-_Niah7WWWWWWuUjhZ6WWWWWW8ual5W"
"WWWWWuViio6WeWYmW4mYe7WWWWWW8oh_6Wu-zl-3aks6WWWWW1mlz6WWWWW-lVqoh6WWWam-3yuZ7WWWyFwku6WWWaW1Wca7WWWy-_3_bc6WWWWWX4clz6WW"
"WWmz3_xu6WWWWm1qwl6WWWWW1uqq6WWW4Yax6WWWy-_Nuhb7WWWWWWuUWqr6WWWam-3qzb7WWWyFuyy6WeWYGWij7Wu-XGgbf7WWWy-_3mxk6WeWYmW4ekg7"
"Wu-zFWdY7WWWWW-3idw6WWWWW1mo-6WWW4isc7WWWWm_3wuh7WWWyFWz_6WeWYGscm7Wu-zFWra7WWW4yZi7WWWyFuid7WeW2elp7Wu-1aal7WWW2uvp7W8i"
"uu7Wu-z-zFmvX8WWWylW4ujj7WeWYmW4oyd8Wu-zl-3gxm7WWWWW1qpu7WWW4_oY8WWWy-_t_wt6iv-5WWWWWWWWW8Wsh6WWWam-xVsuv6WWWWm1dqn7WWWy"
"-_3epu6WeWYmW4myu7Wu-XmW4oZq7WWW_-zFqcn7WWW2cth7WWWy-W8ghq7WWWWW-p_W8cwq6WWWWWX4mW-5WWWWWW8mgY5WWWWWWu--7Znh6WeWYmWaW1ie"
"t7WWWWWW8yY_6Wu-zl_3wtc7WWWWW2aoi7WWWWW-h-y7xou6WWWWWWCymX6WWWWWWu-1w_Y6WWWWWW8qcl5WWWWWWq-1oY_6WWWWWW4_yg6WWWam-3u-p7WW"
"WyFexZ7WWWWGs_l7WWWaGato7WWWy-_3_Xb6WWWWWW4i_X7WWWWW1ehg7WWWWmz3mnb7WWWWm1hfl6WWWWW1Whq6WWW4gyw6WWWy-_Nhza7WWWWWWu_w7anx"
"6WWWWWWeW1eki6WWWam-xVmZc7WWWWm1rXs7WWWy-_3utv6WeWYmW4ksw7Wu-zFavn7WWWWW-3wce7WWWaW1wWs7WWWy-_Nios7WWWWWWuUWhj6WWWWWW8es"
"r5WWWWWWuVzcX7WeWYmW4rmx7WWWWWW8gqg7Wu-zl-3xob7WWWWW1mek7WWWWW-lVufs6WWWam-3msr7WWWyFnxd7WWWaW1nws7WWWy-_3e_l6WWWWWX4ojk"
"7WWWWmz3uYf7WWWWm1fyw6WWWWW1abW7WWW4_Zd7WWWy-_Nazk7WWWWWWuUWZb7WWWam-3mcu7WWWyFeYk7WeWYGulY8Wu-XGhgz7WWWy-_3ibx6WeWYmW4o"
"jz7Wu-zFmwq7WWWWW-3rfg7WWWWW1ivm7WWW4iWv7WWWWm_3jiW8WWWyFscm7WeWYGWxb8Wu-zFest7WWW4axW8WWWyFaZx7WeW2qZg8Wu-1usa8WWW2ilg8"
"W8wum8Wu-z-zFtco8WWWylW4wcv7WeWYmW4nYv8Wu-zl-3ph_7WWWWW1ssd8WWW4Zap8WWWy-yt_Weu1mWo4WWWWWWGyjo3WWWWWWm---7Whd5WWWWWWGkyi"
"4WeWYmWq-Weu1i_p6WWWWWWGazr5WWWWWWm---7wWe7WWWWWWGuvk6Wu-zl-h-_tt1_hu4WWWYWXy-XGyZy6WWW2ilm6WWW_--7mbn7WWWYWW4qum6WWW_--"
"Fevq6WWW2ypp5WWWy-_d-zl7tYn5WWWYWXy-XGjil7WWW2rzZ7WWW_--7yvY8WWWYWW4yia7WWW_--Fqog7WWW2eWi6WWWWm-Z-uds1oew5WWWWGYyu5WWW_"
"--RmZs6WWW2sgp6WWWWm-l-5tnl7WWW_lWqVsvr6WWW2c_o6WWWWWWCwoe7WWW_--Fjsy6WWW2ojp6WWWy-_d-zd1Wcy4WeWYmWaWX8yZw6Wu--lWu-W8kty"
"6WWW2uxp6WWW_--7ujo7WWWYWW4avs6WWW_--FeXu6WWW2wgv5WWWWm-Z-u7Yvs6WWWWGzsq6WWWWm-Bmdn7WWWWGuli7WWW_--FmqW7WWW2pay6WWWWm-l-"
"5vXv7WWW_lWqVqqW7WWW2aay6WWWWWWCYbj7WWW_--FhjX7WWW2amr6WWWWm-ZVyrY7WWWWGo_-6WWWWm-Bmdy7WWWWGcrr7WWWWm-3coz7WWWWGuWv7WWWW"
"GgqY8WWW2qed8W8oek8Wu-xl-Beac7WWW2uhW7WWWWm-3yoe7WWWWGkdb7WWWWGgli7WWW2e_l7W8kyq7Wu-zl-Bobv7WWWWm-p_t-5nps6WWWWGbeq6WWW_"
"--Rtlj7WWW2xae7WWWy-_d-ae1acs5WeWYmWaWX8wum7Wu--lWu-W8Zjm7WWW2xse7WWW_--7tsa8WWWYWW4ati7WWW_--Fssl7WWW2YWr6WWWWm-Z-u7gxY"
"7WWWWGqfW7WWWWm-BYry7WWWWGdms7WWW_--FZXo7WWW2vWi7WWWWm-l-5hmd8WWW_lWqVdXo7WWW2hfi7WWWWWWCXbt7WWW_--Fzpp7WWW2Y_W7WWWWm-ZV"
"wiq7WWWWG_ym7WWWWm-Bqfh8WWWWG-cY8WWWWm-3sdj8WWWWGZgd8WWWWGbzo8WWW2wku8W8ZlW9Wu-xl-BZpv7WWW2udn7WWWWm-3mjy7WWWWGtnt7WWWWG"
"l_W8WWW2_ib8W8eoh8Wu-zl-Bmld8WWWy-_l_yds1cyi5WWWWWWOWgq4WWWWWWm--Vycr4WWWWWWGuou3WWWWWWWWyVcy_4WWWWWWe-3oXo5WWWWWWOwtt4W"
"WWWWWe-3exx5WWWWWW4myg6WWWWW2mzs6WWWWWWCwoh6WWWWW_7mtZ5WWWWWW8gqX6WWWWWW8Wgf5WWWWW2mcm5WWWWW_-_x-6sni5WWWWWWGyit4WWWWWWW"
"WyVomm5WWWWWWe-3auy5WWWWWWOw-Z5WWWWWWe-3_of6WWWWWW4ydv6WWWWW2yne7WWWWWWCkX_6WWWWW_7yks5WWWWWW8ywn6WWWWWW8ee_5WWWWW2und6W"
"WWWW_t_x-r1YXp5WeWYmWaWX8yoj7WWWWWWOgxs6WWWWWWm--Vaht6WWWWWWGctx5Wu-zl-Z-_Nk-t5WWWWWWWW4mzX6WWWWWYGmpn6WWWWW_FYqd6WeWYmW"
"y-u7Y_-6WWWWWWe-3Wpn7WWWWWWOxqu6WWWWWWe-3ysw7WWWWWYGa-e8WWWWW_7k-Z7WWWWWW8ib_7WWWWWW8iaf7WWWWW2mWn7WWWWW_-_x-6iyi7WWWWWW"
"Gfau6Wu-zl-Z-_NwiY6WWWWWWWW4s-l6WWWWWYGe-b7WWWWW_Fgxu6WeWYmWy-u7yom7WWWWWWe-3mux7WWWWWWOsha7WWWWWWe-3ood8WWWWWYG-_v8WWWW"
"W_7ukr7WWWWWW8gwi8WWWWWW8may7WWWWW2mkc8Wu-zlzh-sdr1kgm5WWWWWWWWaGqYw4WWWWWYi-zFYyn6WWWWWW8a-m6WWWWWW4ier5WWWWWWOYZk6WWWW"
"W_p_1ujX6WWWWWWSoxe5WWWaWXi-1ese7WWWWWWSxvp6WWWy-_7suf6WWWWWYy_1Y-Z7WWWWWW8ghX7WWWWWW4hwj6WWWWW_7xbz5WWWWWW4oxr6WWWWWYCx"
"sk6WWWWW_-_xFojw4WWWWWWGyey3WWWWWWWWyFuwr5WWWWWWm-3air5WWWaWXy-1krs6WWWWWWCudq6WWWWWWGekv5WWWy-_x_1_uh6WWWWWWSwmw5WWWWWW"
"4Wwq6WWWWWWCxab6WWWWWWm-tFhna5WWWWWWWW4Whz4WWWWWWe-3qe-5WWWWWW4aYm6WWWWW2yZy6WWWWWWCmXl6WWWWW_7uhf5WWWWWW8ibb6WWWWWW8e_k"
"5WWWWW2_yr5WWWWW_l-tFowu5WWWWWYi-1Zcd7WWWWWW8Xjb7WWWWWW4vpl6WWWWW_7wja6WWWWWW4yex6WWWaWX4euy6WWWy-W8x_s6WWWWW_p_1iXZ6WWW"
"WWWSiof5WWWaWXi-1xxi7WWWWWWSqqr6WWWy-_7ywi6WWWWWWq_1qyl6WWWWWY8vsg7WWWWWW8ycc7WWWWWW4c_s6WWWWW_7gq_5WWWWWW4vWv6WWWWWWCuY"
"d6WWWWW2-zm6WWWWW_p_1mpr6WWWaWX8ewr7WWWyVatm7WWWWWW8ydk7WWWWWW4Yrw6WWWWWW4k_n7WWWWW1qnw7WWW4ufa8WWWy-y3msc6WWWWWW4yx-6WW"
"WaWX4mxW7WWWWWW4ayv7WWWy-_3qim6WWWWW2whx6WWWWW_3ueZ7WWWWW2cio7WWWWW_3moq6WWWaW1uXc7WWWyVyXW7WWWWW1ivc7WWW4syj7WWWy-_p_t-"
"5kad7WWWWWW8zbb7WWWWWW4igl6WWWWWWOymX7WWWWW_-_XGfzp5WWWWWWGwuy4WWWWWWm--FYz-5WWWaWXy-1hji7WWWWWWCpZf7WWWWWWGfcr6WWWy-_t-"
"vFmpt5WWWWWWWW4ymf5WWWWWWe-3cej6WWWWWW4aW-6WWWWW2jil7WWWWWWCaoY7WWWWW_7ctz5WWWWWW8nwr6WWWWWW8gdc6WWWWW2Zfm6WWWWW_l-tF_pX"
"6WWWWWYi-1ykn7WWWWWW8abl7WWWWWW4nYx6WWWWW_7kpl6WWWWWW4kka7WWWaWX4dwi7WWWy-W8qmb7WWWWW_p_1qre6WWWWWWSw_l5WWWaWXi-1kxs7WWW"
"WWWSffX7WWWy-_7vev6WWWWWWq_1kXt6WWWWWY8uZs7WWWWWW8ssl7WWWWWW4-Wc7WWWWW_7dyd6WWWWWW4hjX7WWWWWWCkcn6WWWWW2g-x6WWWWW_p_1e-z"
"6WWWaWX8mkY8WWWyV-sz7WWWWWW8vcw7WWWWWW4Ylg7WWWWWW4za-7WWWWW1ief8WWW4cnq8WWWy-y3qdo6WWWWWW4g_f7WWWaWX4qtn7WWWWWW4z_d8WWWy"
"-_3iuz6WWWWW2uXh7WWWWW_3wYk7WWWWW2dn-7WWWWW_3cmY7WWWaW1Wiu7WWWyVm-m7WWWWW1ejv7WWW4nmY8WWWy-yd-r-q1_dr5WWWamWi-_7uuz5WWWW"
"Guhy5WWW_--Roax6WWW2ggu6WWWy-W8yqf7WWWWW_lVcrZ6WWWWWYuVuhw6WeWYm_Bizm7Wu--lW4m-o7WWW_-WmV-cq6WWWaW-Fewh7WWWy-W8oWd7WWWYW"
"-x_3Xdx6WWW2xeu6WWW_--RegY7WWW2gwu6WWWy-Wa-1wgg7WWWWWWCnxd7WWWWW_7qnf6WWWWWWGWlp6WWWWW2Wj-6WWWWW_l-x7mnz4WWWWWXu-y7Ylw6W"
"WWWWXqView6WWWWW-7knw6WWWWWX4vbp6WWWWWWOeca7WeWYm_p-2oey6Wu--lWeVorp7WWWWWWShms7WWW_-_7YZv6WWWWWYe-1-la7WWWWW_Fpqu6WWWWW"
"Ya-v7saq6WWWWWW8ucp6WWWWm_3Wvr6WWWWm1cru5WWWWWWOaxo6WWWWW_l-1shi5WWWaWXi-1e-h7WWWWWWSj-u6WWWy-_7iuk6WWWWWYy_1bdd7WWWWWWC"
"_xo6WWWWW_7oWY6WWWWWYGzwp6WWWWWWe-s7czz6WWWYW-Fjmq7WWW2fql7WWWy-W8ugk7WWWWWWe-1nvx6WWWWWWqVlxz6WWWWm_Byh_6WWWWm1xWr6WWWW"
"WWOkhe7WWWWWWyUqgY7WWWWWWCwp-6WWWam-3ein7WWWyFyga7WeWYGYwr7Wu-zFydg7WWW4_tn7WWWWm_Fuhb8WWWylW4ilm7WeWYmW4mnh8Wu-zl-3gYq7"
"WWWWW1eXy7WWW4mdc8WWWy-ydVaZp5WeWYmWaW1shf7Wu--lWeVYbr7WWW2rdm7WWW_--RwWu7WWW2cvb7WWWy-_7huz6WWWamWyU_qs7WWWWGugp7WWWWmW"
"Gdsb8WWW_l-Bak_7WWW2qns7WWWWm-3hjX8WWWWGyyy7WWWWGWic8WWW2YXh8W8yzn8Wu-vl_3iua7WeWYmW4wrb8Wu-XmW4uqW8WWWy-WqUuyk7WWWWWWCg"
"af7WWWWW_7khi6WWWWWYGkbW7WWWWWWeVzxk7WeWYmW4-th8WWWWW_7ucx7WWWWWYGnqi8Wu-zl-3hpu7WWWWWWqUapo7WWWWWWCvbi7WWWWWW4ctq7WWWWW"
"1upy7WWW4xmc8WWWy-y3ywr6WWWaWX8evs7WWWWWW4WtW8WWWy-W4rkl7WWWWWW8ajr7WWWWW1wW_7WWW4-wd8WWWy-yt_v7erz4WWWWWWGqt_3WeWYmWq-W"
"8ugy6WWWWWWGyc-5Wu-zl-hVwgk6WWWWWWW1umt6WWWWWWm-v7rlw5WWWWWWm-3eaw5WWWYWXy-1efY7WWW2ayu6WWW_--7__r7WWWYWW4qXv6WWW_--Fucz"
"6WWW2yxy5WWWy-_t-1_g-5WWWWWWGwYg6WWWamWy_s7pWy6WWWWGezv6WWW_--RgZc7WWW2-mX7WWWy-_tVemb6WeWYmWaW1Zgr7Wu--lW4xxy7WWWYWWWW1"
"uwm7WWWy-_d-1gdb6WeWYmWaW1Xwq7Wu-XWW4Yoy7WWW_lWqVwbc7WWW2rmX7WWWWWWCjgm7WWW_--FoWd7WWW2ivw6WWWWm-ZVsae7WWWWGwhb7WWWWm-Bc"
"r-7WWWWGczu7WWWWm-3gZX8WWWWGoky7WWWWGwbc8WWW2exg8W8mzn8Wu-xl-BWrh7WWW2mvb7WWWWm-3cZk7WWWWGcsg7WWWWG__n7WWW2Wnr7W8alw7Wu-"
"zl-Bmpy7WWWy-_dVo-g6WWWWWWGair6WeWYmWqVgmu7WWWWWWGXYY8Wu-zl-3cXf7WWWaWXqUsds7WWWWWWSzXq7WWWWWW4bYz7WWWy-_3joX7WWWaWX8lmz"
"7WWWy-_d-r7W-d5WWWWWWWW4mtW5WWWWWWe-3eaa6WWWWWW4u_o6WWWWW2uW-6WWWWWWCuxp6WWWWW_7avi5WWWWWW8yzf6WWWWWW8uho5WWWWW2ahv5WWWW"
"WWe-s7dgj7WeWYm_hW2rgb7Wu-zlXeVqZj7WWWWm_Bluj7WWWWm1Yo-6WWWWW_7_Yn6WWWWWYGzkf7WeWYm_p-2nzz6Wu-zl-hW1xXy6WWWWWWu_1cjo6WWW"
"WWYGkff7WWWWW_Fhsx6WeWYmWaViX_7WWWWWYG_oi8WWWWW_7uif7WWWWWW8yrX8WWWWWW8uok7WWWWW2uls7Wu-zl-tUyat7WWWWWWC-dl7WWWWWW4ktu7W"
"WWWW_3_zo6WWWWWWGye-6WWWWW2Whj7WWWWW_7ehc7WWWWW2dyr7WWWaW-p_q7wfb7WWWy-WCYwg7WWWaW-Fjgm7WWWy-_7kh_6WWWWW2kdk7WWWWW_lVvhz"
"5WWWWWYuVzue7WWWWWWqVrfg7WWWWWW8zke7WWWWWW4rnq6WWWWW_7aif6WWWWWW4eY_6WWWaWX4czX7WWWy-W8wXy6WWWWW_l-1cWj5WWWaWXi-1mXm7WWW"
"WWWSdsw6WWWy-_7iwn6WWWWWYy_1Z-j7WWWWWWCnXy6WWWWW_7hiZ6WWWWWWGyzh6WWWWW2q_r6WWWWW_p_1uZu6WWWaWX8eZv7WWWyVi_p7WWWWWW8uin7W"
"WWWWW4cu-6WWWWWW4ydr7WWWWW1e-z7WWW4wxd8WWWy-y3qph6WWWWWW4qnY7WWWaWX4_Wc7WWWWWW4cgz7WWWy-_3eir6WWWWW2slW7WWWWW_3iYc7WWWWW"
"2Wsr7WWWWW_3upv6WWWaW1meh7WWWyVucb7WWWWW1y_h7WWW4iap7WWWWmzp_q7aee7WWWWGczb7WWWy-WCesk7WWWYW-Fdav7WWW2zep7WWWy-_7qoY7WWW"
"WW2_wp7WWWWW_lVuuc6WWWWWYuVozh7WeWYm_Byfu7Wu--lW4yxZ8WWW_-WaVvlk7WWWWm_Bcil7WWWWm1_eW7WWWWW_7aoq6WWWaWX8zXq7WWWy-W8zki7W"
"WWWWWyUijq7WWWWWWCZhm7WWWam-3mud8WWWyFaqs7WeWYGhsj8Wu-zFwl_7WWW4qie8WWWy-y3qmw6WeWYmW4giY8Wu--lW4umc8WWW2lmz7WWWWm-3w-e8"
"WWWWGlsZ8WWWWGhvj8WWW2gap8W8shw8Wu-vlW4yor7WeWYmW4ecq8Wu-zl-3pjx7WWWWW1ija8WWW4Yzk8WWWy-ydV_hp5WeWYmWaW1c-f7Wu--lWeVigv7"
"WWW2Ykp7WWW_--Rfyv7WWW2mmc7WWWy-_7vd-6WWWamWyU_cx7WWWWGbrt7WWWWmWGpxj8WWW_l-ByoW8WWW2zZu7WWWWm-3yrZ8WWWWGuz_7WWWWGase8WW"
"W2_bj8W8Y-p8Wu-vl_3qwc7WeWYmW4h_e8Wu-XmW4c-Z8WWWy-WqUYyp7WWWWWWC-ti7WWWWW_7kWj6WWWWWWGufs6WWWWW2wbX7WWWWWWeVcrr7WeWYmW4W"
"fq8WWWWW_7wry7WWWWWWGy-Z8WWWWW2zxk8Wu-zlz3mqh7WWWWW2nby7WWWaW-pUcgz7WWWyVouv7WWWWWWCZvm7WWWWWW4upx7WWWWW1uqa8WWW4lXl8WWW"
"y-y3yvs6WWWaWX8elu7WWWWWW4gYa8WWWy-_3oeZ7WWWWW2ukn7WWWWW_7eie7WWWaW1ks-7WWWyVuxt7WWWWW1ysW8WWW4phg8WWWWmzpUWdZ8WWWWGyd-7"
"WWWyViqy7WWWWWWCert7WWWam-3ktn8WWWyFqu_7WeWYGaXu8Wu-zFezd8WWW4ylo8WWWy-y3irx6WeWYmW4Wia8Wu--lW4qWg8WWW2ks-7WWWWm-3WYj8WW"
"WWGqhd8WWWWGsco8WWW2Wjt8W8qp_8Wu-vl_3mWf7WWWWW2Wdu7WeWYm_3eni8WWWWW2wqu8Wu-zlz3imk7WWWaW1esd8WWWyVeh-7WWWWW1i-e8WWW4wkp8"
"WWWy-y3mkn7WeWYGikm8Wu-1mrn8WWWWGugh8WWWWGYus8WWW2mky8W8atZ9Wu-vFawY8WeWYGoaz8Wu-zFevi8WWW4uot8WWWyFqco8WeW2atZ9Wu-1emz8"
"WWW2uba9W8qmh9Wu-z-yl_p-4Yrx6WWWWGibv6WWW_--Ruiq7WWW2Wsk7WWWy-W8yWu7WWWWW-d-XGrij7WWWWWXq-W8ucg7WWWWWW8gae7WWWWm_3oki7WW"
"WWm1jXq6WWWWWWOdqd7WWWWWWe-y7zpk7WWWYW-FcYW8WWW2Ysv7WWWy-W8u_v7WWWWWWe-1iuh7WWWWWWqVdck7WWWWm_Bsol7WWWWm1wXW7WWWWWWOgxn7"
"WWWWWWyUwrq7WWWWWWCppm7WWWam-3bzd8WWWyFews7WeWYGssj8Wu-zFyu_7WWW4Wle8WWWWm_Fims8WWWylW4qiy7WeWYmW4wnz8Wu-zl-3a_X8WWWWW1_"
"ph8WWW4Ylt8WWWy-yt_W8gYu5WWWWWWGaYW5WeWYmWq-W8csp7WWWWWWGqYz6Wu-zl-h-_7Zla6WWWYWXy-1wqt7WWW2cgl7WWW_--7pWf8WWWYWW4hnl7WW"
"W_--FXbt7WWW2u_v6WWWWm-Z-u7sde7WWWWGcob7WWW_--R-wu7WWW2-lo7WWWy-_d-4yvg6WeWYmWaW1m__7Wu-XWW4-nh8WWW_lWqVo_u7WWW2fwo7WWWW"
"WWCoew7WWW_--Fnlw7WWW2Ydc7WWWWm-ZVzbx7WWWWGglt7WWWWm-Brel8WWWWGerb8WWWWm-3hkn8WWWWGzch8WWWWGvat8WWW2kxy8W8aab9Wu-xl-BduW"
"8WWW2fxt7WWWWm-3lsZ8WWWWGwn_7WWWWGzke8WWW2acj8W8evp8Wu-zl-Bnih8WWWy-_d-u7mqx5WWWWWWWW4_yi5WWWWWWe-3geo6WWWWWW4WXY7WWWWW2"
"exo7WWWWWWCxse7WWWWW_7avX6WWWWWW8hhx6WWWWWW8qog6WWWWW2e_q6WeWYm_p-u7_ft7WWWWWWWW4Wqf7Wu-zl-Z-2sjv6WWWWWYGato7WWWWW_FfXa7"
"WeWYmWaVyYh8WWWWWYGqj_8WWWWW_7ncy7WWWWWW8ywm8WWWWWW8ohZ8WWWWW2Ygk8Wu-zlzh-s7rYc6WWWWWYi-1psq7WWWWWW8bfo7WWWWWW4uYW7WWWWW"
"_7ynq6WWWWWW4mgd7WWWaWX4zap7WWWy-W8dnh7WWWWW_l-1cip5WWWaWXi-1iWw7WWWWWWSngc7WWWy-_7ru_6WWWWWYy_1onv7WWWWWWCdZi7WWWWW_7xj"
"i6WWWWWWGszr6WWWWW2Y_W7WWWWW_p_1miW7WWWaWX8qzb8WWWyVqeX8WWWWWW8wnz7WWWWWW4Wom7WWWWWW4dxY8WWWWW1gbj8WWW4Yxu8WWWy-y3uZt6WW"
"WWWW4isi7WWWaWX4yYu7WWWWWW4zxh8WWWy-_3qhZ7WWWWW2Zcn7WWWWW_3sZn7WWWWW2weZ8WWWWW_3ige7WWWaW1ib-7WWWyVxkt7WWWWW1efW8WWW4ayf"
"8WWWWmzp_q7qtk7WWWWGaWi7WWWy-WCfct7WWWYW-FahY8WWW2mpx7WWWy-_7qyf7WWWWW2i-y7WWWWW_lVgth6WWWWWYuV-Zq7WeWYm_BpuW8Wu--lW4jjl"
"8WWW_-WaVdvs7WWWWm_Bqcu7WWWWm1shc7WWWWW_7cpw6WWWaWX8Wdy7WWWy-W8sXq7WWWWWWyUYoz7WWWWWWC-yu7WWWam-3aio8WWWyFsu-7WeWYGoqu8W"
"u-zFine8WWW4iYp8WWWy-y3WoX7WeWYmW4wYj8Wu--lW4boo8WWW2-wd8WWWWm-3wcr8WWWWGiqk8WWWWGlkw8WWW2crW9W8uze9Wu-vlW4w__7WeWYmW4kn"
"X9Wu-zl-3iob8WWWWW1yrl8WWW4Wox8WWWy-ydVoft5WeWYmWaW1WYm7Wu--lWeVjjY8WWW2_ux7WWW_--R-qZ8WWW2aqi7WWWy-_7w_b7WWWamWyUtha8WW"
"WWGWgW8WWWWmWGjtw8WWW_l-Bwug8WWW2jwW8WWWWm-3Yyj8WWWWGtce8WWWWGx_o8WWW2iWu8W8Wb-8Wu-vl_3cyk7WeWYmW4ddq8Wu-XmW4Yzk8WWWy-Wq"
"Umuy7WWWWWWCvnq7WWWWW_7_Yo6WWWWWWGaxx6WWWWW2_Zd7WWWWWWeVZp-7WeWYmW4h_X9WWWWW_7okb8WWWWWWGcij8WWWWW2Wgv8Wu-zlz3o_p7WWWWW2"
"ijc8WWWaW-pUwxd8WWWyVoYa8WWWWWWCryu7WWWWWW4szb8WWWWW1Ygm8WWW4qay8WWWy-y3Y-y6WWWaWX8v_W8WWWWWW4lXl8WWWy-_3ijg7WWWWW2pnv7W"
"WWWW_7Yvl7WWWaW1eue8WWWyVokW8WWWWW1kWg8WWW4viq8WWWWmzpUWrk8WWWWGcZg8WWWyVstd8WWWWWWCdzX8WWWam-3jl-8WWWyFezf8WeWYGomc9Wu-"
"zFahq8WWW4ihW9WWWy-y3YxY7WeWYmW4eil8Wu--lW4b-s8WWW2phg8WWWWm-3uew8WWWWGYcp8WWWWGwy-8WWW2_xb9W8iYk9Wu-vl_3uln7WWWWW2yYY8W"
"eWYm_3osu8WWWWW2sXd9Wu-zlz3ijt7WWWaW1wkp8WWWyVlgg8WWWWW1icr8WWW4saX9WWWy-y3eow7WeWYGyXz8Wu-1iq-8WWWWGuot8WWWWGvfb9WWW2mz"
"h9W8yhq9Wu-vF_dk8WeWYGWni9Wu-zFwrv8WWW4Ycc9WWWyFyr-8WeW2yhq9Wu-1gaj9WWW2yYr9W8o_z9Wu-vlyZ_mdq1m--1WWWWWWWWmW4Wfi3WWWWWWW"
"Wm-3e--2WWWWWWWWWW4Wol3WWWWWWWWGWeZ4WeWYmWaWndq1ylW4WWWWWWWWmW4ujl5WWWWWWWWm-3qhY5WWWWWWWWWW4ujl5WWWWWWWWGqla6Wu----ZWnd"
"q1uYj5WWW2knY5WWWWGqt_3WWW_l---lW4mzs6WWW2oek6WWWWGmaj5WWW_l---l-3qcg6WWW2-jX6WWWWGmZW5WWW_l-----3mzs6WWW2oek6WWWWGmaj5W"
"WW_l---Fyne7WWW2hfX7WWWWGcyX6WWWWWWWWltp1ygj5WWWWm--Vgfj5WWWWGqfa5WWW_l----7egj5WWW2una5WWWWGujY4WWWWWWy-_7adp5WWWWm-3qd"
"p5WWWWGipm5WWWWm--V_mm5WWWWGmwb5WWWWWWyVWts5WWWWm-3iss5WWWWGaqo5WWWWm-3agw5WWWWGe_u5WWWWGwpy5WWW2mW-5W8mfY6Wu-zl1mby6WWW"
"WW_t-Dwfm6WWWWm-ZW1uYm6WWWWGotc6WWW_l----t3qmt6WWW2mpn6WWWWGWxo5WWWWWWy-m7oen6WWWWm-3Zwn6WWWWGWog6WWWWWWy-Dcbx6WWWWm-ZW1"
"nkv6WWWWGa_g6WWWWWWyVaXz6WWWWm-3cYz6WWWWGywp6WWWWm-3ixY7WWWWGmbW7WWWWGeZc7WWW2Wof7W8ulk7Wu-zl1qeX8WWWWW_x-jl3kac6WWWWm-x"
"-W8yeh6WWWWGqqa6WWW_l-3evg6WWW2zsa6WWWWGuub5WWWWWWy-_7sui6WWWWm-3ozi6WWWWGkWd6WWWWWWyVefe6WWWWm-3Zwe6WWWWGauo5WWWWWWyVWc"
"n6WWWWm-3uin6WWWWGgif6WWWWm-3ans6WWWWGs_p6WWWWGsrv6WWW2WXz6W8atX7Wu-zl1Wkr7WWW_lzx-_t3qmt6WWW2mpn6WWWWGWxo5WWW_l---FWnf7"
"WWW2e-b7WWWWGcwf6WWWWWWy-k7qiu6WWWWm-3ebu6WWWWGceo6WWWWm--Vulp6WWWWGahv5WWWWWWyVkdz6WWWWm-3nhz6WWWWGcrq6WWWWm-3ixY7WWWWG"
"mbW7WWWWGeZc7WWW2Wof7W8ulk7Wu-zl1qeX8WWWWW_t-DcYh7WWWWm-ZW1hhf7WWWWGe_q6WWWWWWyVwdj7WWWWm-3xsj7WWWWGwpW7WWWWm-3Yoq7WWWWG"
"osm7WWWWGdfu7WWW2eiy7W8eaY8Wu-zl1yym8WWWy-zZWndq1it_4WWWWW1yey3WWWWW---lW4Wbe6WWWWW1atf5WWWWW---l-3klx5WWWWW1_ty4WWWWW--"
"---3Wbe6WWWWW1atf5WWWWW---Fwov6WWWWW1swz5WWWWW---l-p1knY5WeWYmWaWX8yrW7WWWWW1Ys-5Wu-zl_x-ku3oek6WeWYmWaWX8ood8WWWWW1Wqg7"
"Wu-zl_x-kt3-jX6WeWYmWaWX8wix7WWWWW1a-z6Wu-zl_x-_t3oek6WWWWWWWWGhfX7WeWYmWaWn7ood8WWWWW1Wqg7WWWWW---Fczt8WWWWW1mlz7Wu-zl-"
"x-idp1yzc5WWWWm_--1m_-5WWWWm1emW5WWWWW----FWvW5WWWWW1W--3WWWWm_--zFmvf6WWWWm1mei5WWWWm_--1YhY6WWWWGyci5WWWWW1wpY5WWWWWWu"
"-1sWo5WWWWm_7_bk6WWWWm1ocl5WWWWm_7mqp6WWWaW1kdz6WWWyFogr5WWWWGoss6WWWWGawu5WWW4ajz5WWWylzt-Dyty6WWWWGkbf6WWWWW1aZY6WWWWW"
"----l3woh6WWWWW1ajl5WWWWWWu-nFvyg6WWWWm_7-zW7WWWWm1s-b6WWWWm_--DYqX7WWWWGvqo6WWWWW1mmc6WWWWWWu-1mzr6WWWWm_7aif7WWWWm1gal"
"6WWWWm_7mhp7WWWaW1mkY8WWWyFc-w6WWWWGc_u7WWWWGikW7WWW4wmd7WWWy-_t-h-2XWW6WWWWm_t-XGweu6WWWWm1o__5WWWWW-7dw_5WWWWW1WiY5WWW"
"Wm_--zFlvx6WWWWm1loX6WWWWWWu-1YoY6WWWWm_7vek6WWWWGYyY6WWWWW1Zgl5WWWWWWu-1qug6WWWWm_7eeX7WWWWm1lab6WWWWm_7k-e7WWWaW1srs7W"
"WWyFsZl6WWWWGqwj7WWWWGkgq6WWW4x-w6WWWy-zt-zl3woh6WWWWW1ajl5WWWWW---FkX_6WWWWW1gob6WWWWm_--jFi_a7WWWWm1rgi6WWWWm_--1evq6W"
"WWWGclj6WWWWW1_yr5WWWWWWu-1jfs6WWWWm_7wjg7WWWWm1p-l6WWWWm_7mhp7WWWaW1mkY8WWWyFc-w6WWWWGc_u7WWWWGikW7WWW4wmd7WWWylzt-Dqog"
"7WWWWGkaX7WWWWW1Zfm6WWWWWWu-1pYb7WWWWm_7ouq7WWWWm1qqx6WWWWm_7kbW8WWWaW1lXo8WWWyFqug7WWWWGobd8WWWWGsin7WWW4uwv7WWWy-_t-ht"
"o1maY6WWWWW---1ibY6WWWWWXWW_7uig5WWWWWWWW2w_Z5WWWWWWWW_7qpc6WWWam-xViZW6WWWWm1mj_6WWWy-_3ylm6WeWYmW4shf7Wu-XW-3sl_6WWWWm"
"1agb7WWWy-ztVeWd6WWWWW1ajo5WWWWWWuVW_q6WeWYmWCe_Y7Wu-zl-3oow6WWWWW1geX7WWWWW-tVtqg6WWWam-7wfb7WWWyFyfq6WWWWGyaX7WWWaGkl-"
"6WWWy-zt-DrtW7WWWWW1cuo6WWWWW---l7sWa5WWWWW1ujY4WWWWWWWW_7aqa6WWWWW---1uma6WeWYmWaW1uyY7WWWWW1qbZ6Wu-zl_3_qw6WWWWW2mZ-6W"
"WWWW-lVffl6WWWWW-7jbl6WWWWW1wfd6WWWWWW8sip6WWWWW1iWv6WWWWW_t-Dhw-6WWWWWXu-i7m-h6WWWWm_dW1cWi6WWWWm1Ysl5WWWWW---1kql5WWWW"
"W1iWc5WWWWWWq-1kkm6WWWWWW4qjr5WWWWm_7mim6WWWWm1epo5WWWWm_7Wxr6WWWaW1ak-6WWWyF_su5WWWWGc_u6WWWWGmcy5WWW4qwW6WWWy-zt-Dpbk6"
"WWWWW1pYd6WWWWWWu-i7Yro6WWWWWWeW1wxd6WWWam-xVWg-6WWWWm1Ygf7WWWy-_3u-o6WeWYmW4guj7Wu-zFWnb7WWWam_3Zjf7WWWyFcY_6WWWaW1vxf7"
"WWWy-ztVgae6WWWWW1mso5WWWWWWuVkwt6WWWWW-7dut6WeWYmW4_qj7WWWWW1_uZ7Wu-zl-3eWy6WWWWW1aZZ7WWWWW-lVptm6WWWWWW8reh6WWWWm_7qj_"
"6WWWaW1quf7WWWyFYar6WWWWGeWZ7WWWWGm-v6WWW4eoW7WWWy-_lVaWx6WWWam-3ulh7WWWyFmlY7WeWYGy-o7Wu-XGcvk7WWWy-_3Wbq6WeWYmW4uWm7Wu"
"-zFyvd7WWWam_3kvk7WWWyFsu-6WWWWW1aab7WWW4qfi7WWWWm_3Wmn7WWWyFapa7WeWYG_zr7Wu-zFehg7WWW4kxn7WWWyFWZj7WeW2Wcv7Wu-1exq7WWW2"
"mmv7W8uk_7Wu-z-zl-BYww7WWWWm1YmY8WWWy-zZW1ojZ7WWWWW1ykp6WWWWW--Vxcf7WeWYmW4xce8WWWWW1ptW8Wu-zl-pVhec7WWWWWW8yay6WWWWm_7W"
"-o7WWWaW1qyY8WWWyFYwh7WWWWGWvv7WWWWGyZp7WWW4Wdy7WWWy-_l-k-2lWc7WWWam-ZWEgnh7WWWWm1ssa8WWWy-zZWX8ilm6WWWWW1Wxo5WWWWW---n7"
"ezw6WWWWW1mwp6WWWWW---Drqa7WeWYmWaW1yYh8WWWWW1aYm7Wu-zl_xVWxf7WWWWW1yny6WWWWWWWWj7egx6WWWWWWu-1wkZ7WWWWW-7ctZ7WWWWWXuVcv"
"l6WWWWm_7ozZ7WWWWm1vwg6WWWWW---Dhut6WWWWW1ijh6WWWWWWu-1YWx6WWWWm_7wki7WWWWm1abq6WWWWm_7eqs7WWWaW1qzb8WWWyFWYW7WWWWGify7W"
"WWWGaob7WWW4cti7WWWy-_t-i7gb-6WWWWWWu-1_cd7WWWWW-7-Wd7WWWWWXuV_nx6WWWWWW8qmr6WWWWWWuVhng7WWWam-3nb-7WWWyFulq7WeWYGnWg8Wu"
"-XGuja8WWWy-_3sbW7WeWYmW4xya8Wu-zFwmx7WWWam_3vpa8WWWyFw-l7WWWWW1gdt7WWW4deW8WWWWm_p-Bfj-7WWWWm1kch8WWWy-zZW1okd7WWWWW1yo"
"r6WWWWW--VqXm7WeWYmW4Xjn8WWWWW1acb8Wu-zl-pVxXh7WWWWWW8wjW7WWWWm_7wZx7WWWaW1zxh8WWWyFxum7WWWWGgYY8WWWWGk-t7WWW4v_W8WWWy-_"
"lV_sn7WWWam-3knd8WWWyFqdz7WeWYGejq8Wu-XGWjk8WWWy-_3iob7WeWYmW4slj8Wu-zFmxa8WWWam_3krk8WWWyFWpt7WWWWW1if-7WWW4eue8WWWWm_3"
"mto8WWWyFuZW8WeWYGgyu8Wu-zFaze8WWW4wep8WWWyFmti8WeW2Wvz8Wu-1yrt8WWW2ac_8W8mib9Wu-vl_p-gt2fka6WWWWWWWWW8jxm6WWWam-xVty_6W"
"WWWm1itu7WWWy-_3sg_6WeWYmW4-qW8Wu-XW-3eev7WWWWm1cqx7WWWy-zh-W8pdx6WWWWWX4_wZ6WWWWW-7woZ6WWWWW1uub5WWWWWWu--7nom6WWWWW-7X"
"lm6WeWYmXyVxZ-7WWWWW-7nu_7WWWWW1meZ7Wu-zl_3cij7WWWWW2Zpp7WWWWW-h-y7ez_6WWWWm_Bis_6WWWWm1lzb6WWWWWWu-1yfd6WWWWW-7Wjd6WWWW"
"W1lto5WWWWWWq-1kma7WWWWWW4hll6WWWam-3ckx7WWWyFjng7WWWWGadt7WWWaGoew7WWWylz3laa7WWWWm1yjf6WWWWWW4kme7WWWWW1ikn7WWWWmz3Wai"
"7WWWaW1iWw7WWWyFjWq6WWWWGqXn7WWWWGyev6WWW4gYW7WWWy-_l-w7rpX7WWWWWWeW1nin6WWWam-xVuoh7WWWWm1xXz7WWWy-_3se-6WeWYmW4zZY8Wu-"
"zFmvu7WWWam_3raz7WWWyFyqk7WWWaW1jdz7WWWy-_lVYWo6WWWWW-7tbo6WWWWW1gev5WWWWWWuVbjd7WeWYmW4ouY8Wu-zl_3hed7WeWYmW4ZzY8WWWWW1"
"qZm7Wu-zl-3W-h7WWWWW1tXr7WWWWW-lVWjx6WWWam-3swy7WWWyFdhk7WWWaW1gwz7WWWy-_3eyq6WWWWWX4abr7WWWWmz3mql7WWWaW1sW_7WWWyFvaW7W"
"WWWGXZr7WWWWGumb7WWW4aqi7WWWy-_lVoah7WWWam-3wc-7WWWyFeuq7WeWYGpbg8Wu-XGesa8WWWy-_3cnW7WeWYmW4asa8Wu-zFqwx7WWWam_3gva8WWW"
"yFwpm7WWWWW1Ymt7WWW4XaW8WWWWm_3cZe8WWWyFkXt7WeWYGmwj8Wu-zFm__7WWW4hne8WWWyFulY8WeW2aio8Wu-1xqi8WWW2Wuo8W8glv8Wu-z-zl-x-2"
"gnh7WWWWm1ssa8WWWWm_--Fib-7WWWWm1yyq8WWWy-zZWn7ilm6WWWWW1Wxo5WWWWW---FrzZ7WWWWW1cwf6WWWWW---l7YWt6WeWYmWaW1yYh8WWWWW1aYm"
"7Wu-zl_x-Eilj7WeWYmWaW1pZy8WWWWW1qoa8Wu-z-zx-i7qWe7WWWWm1fZn6WWWWW---1kco6WWWWW1wgv5WWWWWWu-1sfx6WWWWm_7rlj7WWWWm1stq6WW"
"WWm_7eqs7WWWaW1qzb8WWWyFWYW7WWWWGify7WWWWGaob7WWW4cti7WWWy-zt-Dhzc7WWWWW1YWr6WWWWWWu-1dxg7WWWWm_7l-t7WWWWm1ztW7WWWWm_7iu"
"Z8WWWaW1mas8WWWyFlrm7WWWWGgzg8WWWWGqst7WWW4ylW8WWWy-_l-g7qpf7WWWWWWeW1iht6WWWam-xVwYo7WWWWm1mwc8WWWy-_3_ub7WeWYmW4bhi8Wu"
"-zFgiY8WWWam_3qlc8WWWyFkys7WWWaW1rbd8WWWy-ztV__t6WWWWW1aez5WWWWWWuVgll7WWWWW-7wZl7WeWYmW4wYj8WWWWW1ups7Wu-zl-3keq7WWWWW1"
"ja_7WWWWW-lVrpX7WWWWWW8iyw6WWWWm_7iiu7WWWaW1wxd8WWWyFsjc7WWWWGYf_7WWWWGizh7WWW4eap7WWWy-_lVpyo7WWWam-3woe8WWWyFsqz7WeWYG"
"syq8Wu-XGt-k8WWWy-_3uvc7WeWYmW4unk8Wu-zFgjb8WWWam_3wZl8WWWyFequ7WWWWW1YhW8WWW4huf8WWWWm_3mto8WWWyFuZW8WeWYGgyu8Wu-zFaze8"
"WWW4wep8WWWyFmti8WeW2Wvz8Wu-1yrt8WWW2ac_8W8mib9Wu-z-zl-BYqe8WWWWm1uzt8WWWy-zZW1b-k7WWWWW1gyw6WWWWW--Vmrv7WeWYmW4o-_8WWWW"
"W1znk8Wu-zl-pVvwo7WWWWWW8ZWd7WWWWm_7swb8WWWaW1Yxu8WWWyFpxu7WWWWGWqj8WWWWGqoW8WWW4uXg8WWWy-_lVYpx7WWWam-3Wfp8WWWyFqge8WeW"
"YGmqY9Wu-XGnxx8WWWy-_3yfj7WeWYmW4jmv8Wu-zFgXn8WWWam_3vdy8WWWyFewX8WWWWW1ceg8WWW4viq8WWWWm_3jnW9WWWyFsbh8WeWYGXjd9Wu-zFog"
"r8WWW4gZX9WWWyFWqv8WeW2gbj9Wu-1gec9WWW2wtj9W8aZs9Wu-vlyZ-edo1mzZ2WWWWWWWXeW2uou3WWWWWWW-7iud4WWWWWWWWWW2yjo3WWWWWWWWWW2a"
"bk4WWWWWWWW8mou4WWWWWWW1WYa5WWWWWWW-d-1aac3WWWWWWWXeW2ybt4WWWWWWW-t-1iht3WWWWWWWWGkyi4WWWWWWWWm-1qt_3WWWWWWWX8WYa5WWWWWW"
"W-7eYv4WWWWWWWW8yzc5WWWWWWW1qms5WeWYmWa-edo1Wca4WWWWWWWXeW2ivx5WWWWWWW-7eYg6WWWWWWWWWW2idr5WWWWWWWWWW2yzj6WWWWWWWW8ect6W"
"WWWWWW1qda7WWWWWWW-d-1Wae5WWWWWWWXeW2yvt6WWWWWWW-t-1idr5WWWWWWWWGusi6WWWWWWWWm-1ivx5WWWWWWWX8qda7WWWWWWW-7eau6WWWWWWWW8q"
"da7WWWWWWW1qer7Wu--lWa-edo1mhc5WWW2ujY4WWW_---WeW2uWx6WWW2kmv5WWW_---_7ejb7WWW2WYd6WWW_------1ukq6WWW2k_o5WWW_------1csf"
"7WWW2aWh6WWW_----7eno7WWW2Wcq6WWW_--Vi-_7WWW2cbX7WWW_---_d-1ald6WWW2mxb5WWW_---WeW2ump7WWW2fzq6WWW_---_t-1ukq6WWW2k_o5WW"
"W_----Fmmf7WWW2jWg6WWW_----l-1uWx6WWW2kmv5WWW_---W8i-_7WWW2cbX7WWW_---_7ump7WWW2rar6WWW_----7i-_7WWW2cbX7WWW_--Vk_j8WWW2"
"twn7WWWWWWW-ctn1eym5WWW_---Viwm5WWW2qvd5WWW_-----7uwd5WWW2mya4WWWWWWy-_7ius5WWWWWW4iZq5WWW_---V_Wq5WWW2kff5WWWWWWyVWdw5W"
"WW_--3ecw5WWW2mZs5WWWWm-3yvz5WWWWGqjy5WWWWGmaW6WWW2WnY6W8Wwb6Wu-xl-RYfx6WWW2gmu6WWW_----6oiY7WWW2qXv6WWWWWWy_6vqr6WWWWm-"
"ZW1xnr6WWW_Fnir6WWW2XWi6WWWWm----l1kYg7WWW_lWWXu7kdz6WWW2uzy5WWW_---_7ese7WWW2uai6WWWWm-ZWn7yYy6WWWWGmWw6WWW_--Rffc7WWW2"
"ztX7WWW_----6sWd7WWW2yyw6WWWWm-ZVgee7WWWWGwmb7WWW_--Ryuh7WWW2u_b7WWWWm-3ogk7WWWWG__g7WWWWGsco7WWW2arr7W8ipw7Wu-zl-t_5mej"
"7WWWWm-ZW1nmh7WWW_Fnui7WWW2j-u6WWWWWWyVxsk7WWW_--3wsl7WWW2urX7WWWWm-3kks7WWWWGffo7WWWWGokw7WWW2id-7W8kub8Wu-xl-xW7mZ-7WW"
"W2zap7WWW_l--_tt1iYz6WWW2avs6WWW_Fkrs6WWW2uhs5WWWWWWy-m7xjs6WWWWm-3rWt6WWW_Fs-s6WWW2arl6WWWWWWy-DkrW7WWWWm-ZW1s-_6WWW_Fp"
"x_6WWW2qZm6WWWWWWyVukY7WWWWm-3anY7WWW_FulY7WWW2qbv6WWWWm-3ufe7WWWWGiob7WWWWG_qh7WWW2iZl7W8mXq7Wu-xl-x-6wvo7WWW2czX7WWW_-"
"---et1oiY7WWW2qXv6WWW_----Exxi7WWW2g_l6WWW_----7ewr7WWW2uev6WWW_--VmkY8WWW2agc7WWWWWWy_e7dqY7WWW_--3k-Y7WWW2ynw6WWWWm-ZW"
"8h_w7WWWWGZts7WWW_--RXuW8WWW2set7WWWWWWy_5awn7WWWWm-ZW1nml7WWW_F_Zm7WWW2dsw6WWWWWWyVlpp7WWWWm-3mhp7WWW_FXbq7WWW2kxb7WWWW"
"m-3Wbx7WWWWG-ct7WWWWGnW-7WWW2YrZ8W8YWg8Wu-xl-x-6ayv7WWW2_Wc7WWW_--Vz_d8WWW2yYu7WWWWWWyUs_w7WWW_--3atx7WWW2meh7WWWWm-3ybZ"
"8WWWWGoo_7WWWWGqid8WWW2uci8W8awo8Wu-xl-Rang8WWW2ib-7WWWWm-3kdk8WWWWGWce8WWWWGybp8WWW2Wgu8W8eg-8Wu-zl-x_bl1Wug6WWWWm-x-W8"
"Ylm6WWW_Fybm6WWW2mvf6WWW_--3yqf6WWW2ief5WWWWWWy-_7etn6WWW_--3iyn6WWW2_lh6WWWWWWyVifj6WWW_--3qmj6WWW2ies5WWWWWWyVYcs6WWW_"
"--3_fs6WWW2qwj6WWWWm-3jtx6WWWWGlZv6WWWWGW-_6WWW2ahY7W8Wad7Wu-xl-Rb_q7WWW2fWl7WWW_--Z-cu1spt7WWW2hnl7WWW_--Rkxs7WWW2hzv6W"
"WWWm-Z-u7bhe7WWWWGerb7WWW_--Rm-u7WWW2uqo7WWW_--Z-6-zu7WWW2-wo7WWW_--Rirw7WWW2ngc7WWWWm-ZVdcx7WWWWG_ht7WWW_--RxyW8WWW2tvt"
"7WWWWm-3yzZ8WWWWGuq_7WWWWGvpe8WWW2cgj8W8_vp8Wu-x-_x_st1iYz6WWW2avs6WWW_Fkrs6WWW2uhs5WWW_l---Fggm7WWW2ati7WWW_Fhji7WWW2cg"
"k6WWWWWWy-k7kqz6WWWWm-3rgz6WWWWGhet6WWWWm--Vucu6WWW_Foiu6WWW2yxy5WWWWWWyVXpY7WWWWm-3mqY7WWW_FtqY7WWW2Wrv6WWWWm-3ufe7WWWW"
"Giob7WWWWG_qh7WWW2iZl7W8mXq7Wu-zl-t-Dhnn7WWWWm-ZW1cvl7WWW_Fwsl7WWW2u_v6WWWWWWyVyop7WWWWm-3ZXq7WWW_FwZq7WWW2YYc7WWWWm-3Yd"
"x7WWWWGgZt7WWWWGab-7WWW2gmZ8W8qnf8Wu-xl-x-kt1kdz6WWW2uzy5WWW_---W8mkY8WWW2agc7WWW_---_7srs7WWW2hzv6WWW_----7mkY8WWW2agc7"
"WWW_--VlXo8WWW2W_t7WWWWWWy_c7utZ7WWWWWW4apz6WWW_---Vcc_6WWW2qwW6WWWWWWyVWZf7WWW_--3uYf7WWW2e_-6WWWWm-3exk7WWWWGyZi7WWWWG"
"sco7WWW2arr7W8ipw7Wu-xl-RqZY8WWW2Ylx7WWW_----6ufa8WWW2cti7WWWWm-ZVtaa8WWWWGws-7WWW_--Rn_g8WWW2ZeW8WWWWm-3kdk8WWWWGWce8WW"
"WWGybp8WWW2Wgu8W8eg-8Wu-zl-t_5vcw7WWWWm-ZW1Yfu7WWW_Fghu7WWW2gYW7WWWWWWyVwXy7WWWWm-3Xey7WWW_Fzry7WWW2bni7WWWWm-3ada8WWWWG"
"ms-7WWWWGkge8WWW2Wcj8W8gvp8Wu-xl-x-6ufa8WWW2cti7WWW_--Vcnq8WWW2ylW8WWWWWWyUtpb8WWW_--3Ykc8WWW2iap7WWWWm-3yrk8WWWWGvhf8WW"
"WWGybp8WWW2Wgu8W8eg-8Wu-xl-RXqt8WWW2ayf8WWWWm-3nmx8WWWWGz_p8WWWWG-zW9WWW2gwc9W8wtk9Wu-vl_p_adn1mnc2WWWWWYmWaW1W--3WWWWW_"
"lW4Wdw4WWWWWWWWWW1yey3WWWWWWW-7amj4WWWWWWWXqVWta5WWWWWWWW4alz4WWWWWWWW4ynf5WWWWWWGWdl5WWWWW2mZs5WWWWW_l_3mbz4WWWWWYmW4ma"
"Y6WWWWW_lW4unv5WWWWWWW-tVWas3WWWWWYmWaW1mnl5WWWWW_l-3yZf5WWWWWWWWuVyrp4WWWWWWWW8Wb_4WWWWWWW1atf5WWWWWWWWqV_nz5WWWWWWW-3u"
"x_4WWWWWYmW4ycc6WWWWW_l-3ecj5WWWWWWW1qi_5WWWWWWW-3Wbp5WWWWWYGmel6WWWWW_Fehc6WWWWWWGWzm6WWWWW2uZy6WWWWW_l_ZVewf3WWWWWYmWa"
"W1elY5WWWWW_--ZW1qyp5WWWWWWG_ty4WWWWWWWWyV_jt5WWWWWWWW4Yqf5WWWWWWWW4Wrz5WWWWWWGy-b6WWWWW2Wem6WWWWW_l_pVenx3WWWWWWWWGexn4"
"WWWWWYmWqVmnl5WWWWWWWWGWub6WWWWW_l-hVqrY4WWWWWWWX8atf5WWWWWWW-7ah_4WWWWWWWW8ibj5WWWWWWW1swz5WWWWWWW-dVmxc4WWWWWYmW4mZs5W"
"WWWW_FuuW6WWWWWWWW4mcm5WWWWWWWW4qhd6WWWWWWGWzm6WWWWW2uZy6WWWWW_l_3era5WWWWWYmW4Wem6WWWWW_l-3ysq5WWWWWWW1und6WWWWWWW-3mWy"
"5WWWWWYGuZy6WWWWW_Faco6WWWWWWGyl_6WWWWW2i_h7WeWYm_p_adn1uqc4WWWWWYmWaW1ucZ6WWWWW_lW4kmy6WWWWWWWWWW1ue-5WWWWWWW-7Wjl6WWWW"
"WWWXqVcob7WWWWWWWW4YX_6WWWWWWWW4aof7WWWWWWGWyk7WWWWW2Wus7WWWWW_l_3kmy6WWWWWYmW4acW8WWWWW_lW4het7WWWWWWW-tVusu5WWWWWYmWaW"
"1acm7WWWWW_l-3ckb7WWWWWWWWuVZZp6WWWWWWWW8Wny6WWWWWWW1mqf7WWWWWWWWqVsmx7WWWWWWW-3YX_6WWWWWYmW4xoa8WWWWW_l-3amf7WWWWWWW1sY"
"y7WWWWWWW-3Wyk7WWWWWYGicj8WWWWW_FmnZ8WWWWWWGicj8WWWWW2ghv8WWWWW_l_ZV_oh5WWWWWYmWaW1YhZ7WWWWW_--ZW1Wzp7WWWWWWGuWz6WWWWWWW"
"WyVggt7WWWWWWWW4ktf7WWWWWWWW4tYy7WWWWWWGWjZ8WWWWW2Yik8WWWWW_l_pVusu5WWWWWWWWGmbn6WWWWWYmWqVacm7WWWWWWWWGdoa8WWWWW_l-hVue"
"-5WWWWWWWX8mqf7WWWWWWW-7uZz6WWWWWWWW8mqf7WWWWWWW1jux7WWWWWWW-dVucZ6WWWWWYmW4Wus7WWWWW_FogW8WWWWWWWW4acm7WWWWWWWW4hsa8WWW"
"WWWGicj8WWWWW2ghv8WWWWW_l_3YjZ7WWWWWYmW4Xak8WWWWW_l-3acm7WWWWWWW1sra8WWWWWWW-3Wus7WWWWWYGghv8WWWWW_Fwnk8WWWWWWGghv8WWWWW"
"2xud9Wu-zlzh_Ytm1mje2WWWaWXeWYGmya4WWWy-W8mmg5WWWWWWWW2sWa5WWWWW_Fwlr5WWWWWYm--FujY4WWWWW_lW4erz4WWWWWYm-vF_ul5WWWWWWWW2"
"sYc5WWWWWWu-1anr5WWWWWW8aso5WWWWWW8awu5WWWWW1Why5WWW4W_W6WWWy-_Nkep6WWWWW_l-1aoi5WWWaWXeW2ajv6WWWy-_7ebl6WWWWWWm-1nbY6WW"
"WWWYGudq6WWWWW--_7xkk6WWWWW1fdd6WWWWW_l-3urn5WWWWWWW1oae6WWWWWWWWmFqt_3WWWWWWW-7i_m4WWWWWWWXqFgjw5WWWaWXeW6WWz5WWWy-_t-1"
"ii-5WWWWWWGYig6WWWaWXu_5egi6WWWy--dW2Wa-6WWWWW-lWmF_Ze5WWWWWWWW4_wW5WWWWWWe-3yka6WWWWWWO_zi5WWWWWWGqoo5WWWWW2kmv5WWWWW_l"
"_3YrW5WWWWWYmW4WYd6WWWWW_lW4ue_5WWWWWWWWiFagz5WWWWWYu-1uvq6WWWWW_7qnf6WWWaWX8ugY7WWWy-W8ely6WWWWW_l-1uaj5WWWaWXeW2W-w6WW"
"Wy-_7obo6WWWWWWm-1jkZ6WWWWWWGiai6WWWWW2Yes6WWWWWWe-1kaW7WWWWW_7qsh6WWWaWX8oic7WWWy-_7urr6WWWWW2eyW7WWWWW_7eXw6WWWaW1euh7"
"WWWyVgtb7WWWWW1yli7WWW4eqp7WWWy-yd_1_kd5WWWaWXeW2ajv6WWWy--dW2xeY7WWWWW1xvp6WWWWWWu-1_jb7WWWWWW8eky6WWWWWW8-mh7WWWWW1uvo"
"7WWW4udy7WWWy-ydW2muf6WWWaWXeW2clp7WWWy-_t-1eio6WWWWWWG_q_6WWWWW2dwi7WWWWW_l_pFuou3WWWaWXeWYGWks5WWWy--dWYGqum6WWWWW1k_o"
"5WWWWW_l-3ajj5WWWWWYeWkFY_l6WWWWWW8q_g6WWWWW---DwXu6WWWWW1joh6WWWWWWu-1sdx6WWWWWW8ghq6WWWWWW8WgW7WWWWW1i_b7WWW4mYj7WWWy-"
"yd-1kls5WWWaWXeW2ugY7WWWy-WeW2euy6WWWWW_l-pFWXt4WWWWWWWW8mnX5WWWWWWW1maj5WWWWWWWWqF-xg6WWWaWXe-5wYm6WWWWWWWW8ekv6WWWWWWW"
"1enc7WWWy-_t_1egy5WWWWWWW1o-o6WWWWWYm-fFudq6WWWWW_Fqnm6WWWWWWWW6XbY6WWWWWWW-3keY5WWWWWYmW4aWh6WWWWW_l-3skn5WWWWWWW1XYZ6W"
"WWWWWW-3amt5WWWWWYGWcq6WWWWW_FmZh6WWWWWWGuur6WWWWW2cbX7WWWWWWu_fFklx6WWWWWW8cvr6WWWWW_FYfq6WWWWWWWW6wri6WWWWWYu-1rYm7WWW"
"WW_7qis6WWWaWX8kut7WWWy-_7osY7WWWWW2uym7WWWWW_l_1eee5WWWaWXeW2W-w6WWWy--dW2fsc7WWWWW1qqr6WWWWWWu-1vhg7WWWWWW8jrW7WWWWWW8"
"mmm7WWWWW1Ynt7WWW4zsW8WWWy-yd-1qvu5WWWWWWW1ahi6WWWaWXe-1oic7WWWWWWW1yfu7WWWy-_t_1Wn-5WWWWWYGmxW7WWWWW_Fers6WWWWWWGimZ7WW"
"WWW2qtn7WWWWW_l_1mdZ6WWWaWX8euh7WWWyVqgn7WWWWWW8uXc7WWWWWW8Wot7WWWWW1ek-7WWW4Waf8WWWy-y7Wpx6WWWaWX8qo-7WWWy-_7edf7WWWWW2"
"Wiu7WWWWW_7uWm7WWWaW1Waf8WWWyVYxW8WWWWW1qmg8WWW4qWr8WWWy-yd_XFWfi3WWWaWXeWYGigf5WWWy-W8yra6WWWWWWu-XGcxZ6WWWWWW8mxb5WWWW"
"WWWW_FuYc6WWWWWWu-1pgd6WWWWWW8qwo5WWWWWWu-1yml6WWWWWW8yof6WWWWWW8sbq6WWWWW1anv6WWW4_gW7WWWy-_Nide7WWWWW_-_XGtfu5WWWWWWGm"
"ZW5WWWWWWm--FYua6WWWaWXeW2mYm7WWWWWWGXZw6WWWy-_t-vFdtx5WWWWWWWW4rWj5WWWWWWe-3yro6WWWWWYGpZf7WWWWW_7jyX6WWWWWW8zqx6WWWWWW"
"8_rg6WWWWW2rar6WWWWW_l-tFyac6WWWWWYu-1YjW7WWWWW_7awq6WWWaWX8clp7WWWy-W8c-h7WWWWW_l-1_mp5WWWaWXeW2kqc7WWWy-_7y__6WWWWWYe-"
"1tfi7WWWWW_7ini6WWWWWWGsbs6WWWWW2ffX7WWWWWWe-1ftm7WWWWW_7Wet6WWWaWX8yfu7WWWy-_7qjZ7WWWWW2cln7WWWWW_7ane7WWWaW1qo-7WWWyVt"
"xt7WWWWW1wtW8WWW4lhg8WWWy-yd_nFyd_3WWWWWWWWGszq4WWWaWXeWoFWks5WWWWWWWWGilk6WWWy--dWoFqum6WWWWW1k_o5WWWWW---Fyia7WWWWW1jW"
"g6WWWWWWWWkFien6WWWWW---1aco6WWWWW1ekv5WWWWWWu-1wlx6WWWWWW8vzq6WWWWWW8WgW7WWWWW1i_b7WWW4mYj7WWWy-zt-Dlbd7WWWWW1fcr6WWWWW"
"Wu-1oXh7WWWWWW8bWX7WWWWWW8i_m7WWWWW1k-t7WWW4lxW8WWWy-yd-fFqfb4WWWWWWWX8maj5WWWWWWW-7YpX5WWWWWWWW8Wum5WWWWWWW1cyX6WWWaWXe"
"-fFWWz5WWWWWWWX8enc7WWWWWWW-7XZw6WWWWWWWW8enc7WWWWWWW1keu7WWWy-_t_bFmlf4WWWWWYmW4kmv5WWWWW_Fafb6WWWWWWWW4ypp5WWWWWWWW4m_"
"h6WWWWWWGuur6WWWWW2cbX7WWWWW_l_3w-d5WWWWWYmW4fzq6WWWWW_l-3gru5WWWWWWW1eWi6WWWWWWW-3kYW6WWWWWYGcbX7WWWWW_FoWt6WWWWWWGwxZ7"
"WWWWW2twn7WWWWW_l_ZFuei4WWWaWXeW2W_W6WWWy-W8mot6WWWWWWWW2ajz5WWWWW_FWkh6WWWWWYe-1mzX7WWWWWW8obx6WWWWWW8Wxc7WWWWW1yli7WWW"
"4eqp7WWWy-y7yuw6WWWaWX8udy7WWWy-W8cgq7WWWWW_l-1Wnt5WWWaWXeW2mYj7WWWy-_7ezb7WWWWWWm-1YWo6WWWWWWGmXy6WWWWW2wmd7WWWWWWe-1op"
"u7WWWWW_7ozy6WWWaWX8zsW8WWWy-_7yag7WWWWW2Wkv7WWWWW_7uWm7WWWaW1Waf8WWWyVYxW8WWWWW1qmg8WWW4qWr8WWWy-yd_1ayh5WWWaWXeW2_gW7W"
"WWy--dW2hxk7WWWWW1x-w6WWWWWWu-1vqo7WWWWWW8cgd7WWWWWW8qyu7WWWWW1ekW8WWW4oZg8WWWy-yd-1qYz5WWWWWWW1_in6WWWaWXe-1mYj7WWWWWWW"
"1lxW8WWWy-_t_1yka6WWWWWYGwmd7WWWWW_Ff-y6WWWWWWGctg7WWWWW2uwv7WWWWW_l_1Wwe6WWWaWX8eqp7WWWyVYgx7WWWWWW8syj7WWWWWW8rxX8WWWW"
"W1qmg8WWW4qWr8WWWy-y7uXZ7WWWaWX8lhg8WWWy-_7Wyn7WWWWW2nmY8WWWWW_7ozu7WWWaW1qWr8WWWyVvzh8WWWWW1oys8WWW4azY9WWWy-yd_Xlm1mwf"
"2WeWYmWaWX8Wje4Wu-XmW4qdp5WWWWWWWW1eag5WWWy-W8qpb6WWWaW-t--7uqc4WWWy-W8Wwi5WWWWWWWW2cgc5WWWWW_Fcsu5WWWaWXa-y7uZv5WWWWWW4"
"Wks5WWWWWWWW1mph5WWWy-W8q-f6WWWaW-pVqny5WWWWWW4uju5WWWWm-3maW6WWWWGyt_5WWWWGukY6WWW2Wya6W8Wbe6Wu-zl1uxX7WWWy-_3W-p6WeWYm"
"W4Wzi7Wu-XmW4mxe7WWW_-zFwo_6WWW2oux6WWWy-W8uuk7WWWWWWWVyvq5WWWWW_Fybd6WWWWWYeVeiu6WeWYmWCWhc7Wu-zl-3uzz6WWWWW1Wua7WeWYmz"
"BWZs7Wu--lW4iYu7WWW_-WeVYyj6WWWWWW8qpt6WWWaW1uyY7WWWWW_Fizm7WWWy-W8uWi7WWWYW-t-3ayb7WWW2ugy6WWWy-_t-1Wvi6WWWWWWGmXt6WWWW"
"W2yYZ7WWWaW-p_4oyu6WWWWm-ZW1awu6WWWWGsdl6WWWy--dW2kra7WWWWW1WYs6WWWWWWWWm7Wca4WWWWW_lW4u_-4WWWWWYm-v7szd6WeWYmWaW3Wnb6Wu"
"-zl_3wZ_6WWWWW2erY7WWWWW-lVkoo6WWWWWW8ang6WWWWWW8mrs6WWWWW1Wjy6WWWWW-Nycf7WeWYm_p-2Wv-6Wu--lWaW1sYx7WWW_-_7azy6WWWWWXW-9"
"kka7WWWWWXu-i7qkl6WWWWWWeW1wXo5WWWWWWWW2Yhe5WWWWWWq-1Yxp6WWWWWW4qvt5WWWWWW8m_q5WWWWm_7qfv6WWWWm1gYx5WWWWW1Wp_5WWW4ucZ6WW"
"Wy-_Nigs6WWWWW_l-1uxk5WWWaWXeW2kmy6WWWy-_7mdo6WWWWWWm-1Wcb6WWWWWYGaht6WWWWW--_7emn6WWWWW1cfg6WWWWW_l-3Wbq5WWWWWWW1oWh6WW"
"WWWYe-e7ias6WWWWWWeW1_Yh6WWWam-xVopY7WWWWm1exi7WWWy-_3qgs6WeWYmW4Wcn7Wu-zFqXf7WWWWW-3_jX7WWWaW1agj7WWW_-zF-lv7WWW2Zoq7WW"
"Wy-W8Wmp7WWWWWWWVaYr5WWWWWWuVscx6WeWYmWCWZd7Wu-zl-3ig-6WWWWW1_nc7WWWWW-lVq-p6WWWWWW8Ykk6WWWWm_7qyX7WWWWm1ohu6WWWWW1yfz6W"
"WW4WzZ7WWWy-_Ncfj7WWWWWWuUii_6WWWam-3qyk7WWWyFuxb7WeWYGWks7Wu-XGaeo7WWWy-_3ekt6WeWYmW4Wjp7Wu-zFifh7WWWWW-3aZZ7WWWWW1une7"
"WWW4qsl7WWWWm_3gzq7WWWyFW_d7WeWYGmgv7Wu-zFmvj7WWW4_er7WWWyFmpm7WeW2Wry7Wu-1Whu7WWW2m-y7W8WzX8Wu-z-zFarg8WWWylW4mpr7WeWYm"
"W4mxm8Wu-zl-3_dv7WWWWW1qgX8WWW4mnh8WWWy-ydVqor5WeWYmWaW1Wzi7Wu--lWaW1ely7WWW2shf7WWWy-_7yqX7WWWamWyUozw7WWWWGWkt7WWW_--R"
"WeZ8WWW2-zw7WWWWm-3qhc8WWWWG_qX8WWWWGakh8WWW2qam8W8mdt8Wu-vl_3ute7WeWYmW4Wtg8Wu-XmW4wrb8WWWy-_dVwnl6WWWWWYGWuZ7WWWWWWeVk"
"Wp7WeWYm_BWp-7WWWWWYGWyn8Wu-zl-3wlz7WWWWWWqUrWt7WWWWWWCtcm7WWWWW_7wdv6WWWaWX8ucx7WWWy-W8rxp7WWWWWW8gaw7WWWWW1qWZ8WWW4wYj"
"8WWWWm_p_4fb-7WWWWm1ufd8WWWy-zZW1ijd7WWWWW1qss6WWWWW--VXcj7WeWYmW4mZj8WWWWW1mfb8Wu-zl-pVkZg7WWWWWW8xn-6WWWWm_7oft7WWWaW1"
"zrd8WWWyFtul7WWWWGxg_7WWWWGeht7WWW4puW8WWWy-yd-1ahx5WWWWWWW1q-n6WeWYmWaVWzi7WWWWWWW1Wcb8Wu--lWaVely7WWW2shf7WWW_--Vehn8W"
"WW2-qW8WWWy-We-1WuZ7WWWWW_Fsgy6WWWWWYGmyu7WWWWW_l-h7ylW4WWWWWWW-7ydp4WeWYmWaXv7WpX6Wu-zl-hVogo6WWWWWWW1Wux6WeWYmWq_6Wro6"
"Wu-XWWaW1YZk7WWWyl-tWo7emz5WWWYWXeW6yrW7WWW2ue-5WWWy-_t-1kjY6WWWWWWGWkj6WWWYWXu_5yoj7WWW2Wjl6WWWy--dW2opY7WWWam-x-k7ag-6"
"WWWWGcdz6WWW_--Rarf7WWW2iXb7WWWy-_tVire6WeWYmWaW1Wwv7Wu--lW4_vX8WWWYWWWW1Zgr7WWW_----3emg7WWW2ma_6WWWWm-ZVuoh7WWWWGmwe7W"
"WWWm-Boya8WWWWGYY_7WWW_--Febl7WWW2ief7WWWWm-3krn7WWWWGyek7WWWWGqmr7WWW2mXv7W8W-z7Wu-zl-ByvX8WWWy-_dVsZk6WWWWWWGawu6WeWYm"
"WqVWuy7WWWWWWGWzc8Wu-zl-3ofj7WWWaWXqUalw7WWWWWWSyfu7WWWy-_7vib7WWWaWX8giY8WWWWWWi_2dgn7WWWWm-ZW1zkl7WWW_FpWn7WWW2oey6WWW"
"WWWyVYso7WWW_--3Wtp7WWW2eZb7WWWWm-3fqw7WWWWGfgs7WWWWGWt_7WWW2WsZ8W8Wlg8Wu-vl-ZW1mbl7WWWWWWWW1szt7WeWYmW4Wwy8Wu-XWWaW1Yds"
"8WWW_l-lW4ruZ8WWW2_ft7WWWy-_t-1sev6WWWWWWGkkf7WWWWWWm-d7yig5WWWWWWWW4eZZ5WWWWWWe-3Wqd6WWWWWWOmcl5WWWWWWGWxq5WWWWW2ivx5WW"
"WWW_l_3m-Y5WWWWWYmW4eYg6WWWWW_lW4kbX6WWWWWYu-g7smn7WeWYm_hW2Wxe7Wu-z--pViYo7WWWWm1aaZ7WWWWW_7snq6WWWWWYGuzj7WeWYm_p-2WeX"
"7Wu-zl-hW1Xy-6WWWWWWu_1mhs6WeWYmWaW1WdZ8WWWWWWOWxi7WWWWWWGWbo7WWWWW2WXw7Wu-zl-tUkwx7WWWWWWClkp7WWWWW_7ybs6WWWWWWGe-Y7WWW"
"WW2gpn7WWWWW_7alg7WWWWW2kpw7WeWYm_h_2Wv-6WWWWWYmW4mqa8Wu-zl-pVkko7WWWWWW8cqZ7WWWWm_7YzY8WWWWm1mnu7WWWWGojh8WeWYW_hW3mjx7"
"Wu-XmWe-f7mxe7WWWy-WCmzk7WWWaW-FXwq7WWWy-_7ihY7WWWWW2juo7WWWWW_lVugW6WWWWWYuVWXj7WWWWWWWW1mwt6WWWWW_7uqi6WWWaWX8ckb7WWWy"
"-W8fo-6WWWWW_l-1qjl5WWWaWXeW2YX_6WWWy-_7cer6WWWWWWm-1xjc6WWWWWWGabl6WWWWW2Ygv6WWWWW_p_1yYy6WWWaWX8iX_7WWWyVavu7WWWWWW8eb"
"s7WWWWWW4gdZ7WWWWW_7Wvk6WWWWWW4mvc7WWWaWX4amf7WWWy-_7muu6WWWWW2m-Z7WWWWW_7eaz6WWWaW1Wyk7WWWyVmwe7WWWWW1yol7WWW4Wus7WWWy-"
"yd_1wuf5WWWaWXaW1sYx7WWWWWWaW1kmy6WWWWWWaW1uYW8WWWy--ZW1nvb7WWWWW1gxs6WWWWWWu-1q-e7WWWWWW8eq-6WWWWWW8rcl7WWWWW1yqs7WWW4o"
"gW8WWWy-ydW2oqi6WWWaWXeW2ggt7WWWy-_t-1-jr6WWWWWWGkZY7WWWWW2yom7WWWam_x_c7urh7WWWWGihf7WWWy-WCjvo7WWWYW-Fpqz7WWW2ust7WWWy"
"-_7Wqc7WWWWW2kmu7WWWWW_lVWzf6WWWWWYuVaam7WeWYm_BWuy7Wu--lW4s_e8WWW_l-lVuop7WWWWm1itZ7WWWWW_7uXu6WWWaWX8gmu7WWWy-W8-ym7WW"
"WWWWyUasu7WWWWWWCugq7WWWam-3Ymi8WWWyFeWx7WeWYGWoo8Wu-zFWXZ8WWW4Wcj8WWWy-y3y_z6WeWYmW4Wzc8Wu--lW4bmh8WWW2XYY8WWWWm-3aZk8W"
"WWWGcpe8WWWWGe-o8WWW2ihu8W8mt-8Wu-vlW4_aw7WeWYmW4emv8Wu-zl-3kfW8WWWWW1anf8WWW4ddq8WWWy-ydVawr5WeWYmWaW1Wjj7Wu--lWaW1yc_7"
"WWW2c-f7WWWy-_7iYZ7WWWamWyUfj-7WWWWGfsx7WWW_--R_bb8WWW2ofy7WWWWm-3mje8WWWWGilZ8WWWWGkmj8WWW2WXo8W8m-u8Wu-vl_3Wtg7WeWYmW4"
"Wzj8Wu-XmW4h_e8WWWy-_dVYam6WWWWWWGWrv6WWWWW2era7WWWWWWeVs_v7WeWYm_BWxW8WWWWWWGWqe8WWWWW2Wxp8Wu-zlz3ywl7WWWWW2WWX8WWWaW-p"
"UyrX8WWWyVah_7WWWWWWCrvq7WWWWW_7uXw6WWWaWX8wry7WWWy-_7a-c7WWWWW2Ysr7WWWWW_7yii7WWWaW1Wia8WWWyVujy7WWWWW1imb8WWW4eil8WWWW"
"mzpUund8WWWWGyhZ8WWWyVaZX8WWWWWWCmux7WWWam-3ets8WWWyFygZ8WeWYGmaz8Wu-zFasi8WWW4Yot8WWWy-y3qz_6WeWYmW4Wqe8Wu--lW4oxk8WWW2"
"y-Z8WWWWm-3_Xo8WWWWGqZi8WWWWGcft8WWW2mmy8W8WyZ9Wu-vl_3uui7WWWWW2ioy7WeWYm_3Whn8WWWWW2mxz8Wu-zlz3Wqo7WWWaW1eni8WWWyVcZa8W"
"WWWW1WWk8WWW4osu8WWWy-y3Wwr7WeWYGWpr8Wu-1mXt8WWWWGikm8WWWWGqay8WWW2uyX9W8Wff9Wu-vFiwd8WeWYGWqY9Wu-zFiXo8WWW4yXz8WWWyFWot"
"8WeW2Wff9Wu-1mXZ9WWW2uuf9W8Wbn9Wu-vlyZUuwj5WeWYmWaW1Whc7Wu-XGihy7WWWWm-ZW1Zyw7WWWWGe_Y7WWWWWWyV_tz7WWWWm-3vc_7WWWWGanj7W"
"WWWm-3kfc8WWWWGkiX8WWWWGf_g8WWW2qam8W8mdt8Wu-zl1exu8WWWy-zZW1akm7WWWWW1sgz6WWWWW--Vghv7WeWYmW4Wr-8WWWWW1uan8Wu-zl-pVktp7"
"WWWWWW8oxd7WWWWm_7slb8WWWaW1lav8WWWyFz_v7WWWWGuzj8WWWWGeaY8WWW4bhi8WWWy-_lVovw7WWWam-3cep8WWWyFkmd8WeWYGWoY9Wu-XGxwx8WWW"
"y-_3aXj7WeWYmW4mrv8Wu-zFcmm8WWWWW-3WeX8WWWWW1ewf8WWW4wkq8WWWWm_3zbW9WWWyFocg8WeWYGehd9Wu-zFomq8WWW4vyW9WWWyFqmv8WeW2W_j9"
"Wu-1utc9WWW2urk9W8Wnt9Wu-vlyZW1iuo6WeWYmWaW1mmc8Wu--lWaW1ynq8WWW2zZY8WWWWm-ZVmnk8WWWWGtgf8WWW_--RWZt8WWW2zvf8WWWWm-3gXx8"
"WWWWGksp8WWWWGjzW9WWW2Wzc9W8ehl9Wu-vl_pV_bz6WWWWWWGy-g7WWWWW2ksw7WeWYm_pVerk8WWWWWWGWfv8WWWWW2eee9Wu-zl-ZVxlX8WWWWW_7kgY"
"7WWWaWX8nWg8WWWy-_7gbn7WWWWW2WXY8WWWWW_7mWu7WWWaW1ejq8WWWyVheh8WWWWW1mjs8WWW4mqY9WWWy-yd_n7Whw3WeWYmWaWX8WXx5Wu----ZWX8m"
"nW7WWW2yZw6WWWWGusu5WWWWWWy-m7ipv6WWWWm-3mdw6WWWWGuvo6WWWy-WWW2z_f7WWWaW-x-BuWa7WWWWm-ZW1mgY7WWWWGcfp6WWWWWWyVqub7WWWWm-"
"3ayb7WWWWGeky6WWWWm-3uqh7WWWWGmxe7WWWWGq_k7WWW2mlo7W8Wjt7Wu-zl1Y_f8WWW_-zx-6p_s7WWW2rgb7WWWy-_t-1mfX6WWWWWXmWu7i_p6WWWWW"
"1idr5WWWWW_l-3aYm5WWWWWXmWk7nh_6WWWWW1vZt6WWWWW---Dfcf7WeWYmWaW1Whm8WWWWW1Wlp7Wu-zl_xVgyj7WWWWW1w--6WeWYm_p-2Wxe7Wu-zlXi"
"Wg7xw_6WWWWWWu-1Xgd7WWWWW-7gxd7WWWWWXuVe_o6WWWWm_7-ie7WWWWm1a_j6WWWWW---Dybx6WWWWW1mok6WWWWWWu-1Wh_6WWWWm_7can7WWWWm1sjt"
"6WWWWm_7anx7WWWaW1yYh8WWWyFwiZ7WWWWGYfX8WWWWGaXf7WWW4acm7WWWy-yd-1cYv5WWWaWXeW2cob7WWWy-WeW2Y_-6WWWWWWWWd7yrY7WWWWWWu-1z"
"Xh7WWWWW-7vZh7WWWWWXuVpy_6WWWWWW8buu6WWWWWWuVghk7WWWam-3fjZ8WWWyFgqu7WeWYGerk8Wu-XGWWf8WWWy-_3onZ7WeWYmW4ugf8Wu-zFyy-7WW"
"Wam_3tbf8WWWyFayp7WWWWW1Yix7WWW4Wsa8WWWWmzp-3vrc8WWWWGqXY8WWWy-WiW2mp-7WWWWWWqVaya8WWWWWWCxbw7WWWam-p-4krZ8WWWWm1nbm8WWW"
"y-zZW1-kh7WWWWW1_vu6WWWWW--V_bq7WeWYmW4eks8WWWWW1mqf8Wu-zl-pVpyk7WWWWWW8kwZ7WWWWm_7wq-7WWWaW1ywm8WWWyFssq7WWWWGZwc8WWWWG"
"uby7WWW4okb8WWWy-_lVgqr7WWWam-3yzh8WWWyFqoX8WeWYGWfv8Wu-XGycp8WWWy-_3e_e7WeWYmW4mYo8Wu-zFukf8WWWam_3glp8WWWyFgpx7WWWWW1a"
"pZ8WWW4cij8WWWWm_3Yot8WWWyFWka8WeWYGWvz8Wu-zFunj8WWW4kbu8WWWyFuon8WeW2W_Y9Wu-1kvy8WWW2ijZ9W8msg9Wu-vlyZVoa_5WeWYmWaW1Wcn"
"7Wu--lWaW1eZa8WWW2guj7WWWWWWyViob8WWWWm-3nnb8WWWWGgyo7WWWWm-3Wrk8WWWWGolf8WWWWGcip8WWW2iqu8W8m_-8Wu-vlWaW1sZe7WeWYmWaW1e"
"wv8Wu-zl-pVZWx7WWWWWW8_cj7WWWWWW8qpX8WWWWW1ueg8WWW4syq8WWWy-yd-n7Wfv4WWWWWWWW8mwZ5WWWWWWW1ujl5WWWWWWWWk7got6WeWYmWa-AWes"
"6WWWWWWWW8Wv-6WWWWWWW1Wzi7Wu--lWa-f7ayb7WWW2ugy6WWWy-_tW9uxj6WWWYWXe-5Wpn7WWW2ZZp6WWW_----7ysw7WWW2Wny6WWW_--Vood8WWW2mq"
"f7WWWy-_t_1mz_5WWWWWWW1gXs6WWWaWXa-c7yzb7WWW_--3mhc7WWW2ivz6WWWWmWaW4akh8WWW_l-Rkwp8WWW2pZe8WWWWm-Z-3WX-7WWWWGYrw7WWW_--"
"Rtbb8WWW2ogx7WWWy-_tVwfq6WeWYmWaW1uid8Wu-XmWeV_vd8WWWWWWSouY8WWWWWWy_2nxr7WWWWm-ZW1gkp7WWW_Flgq7WWW2nzz6WWWWWWyVtmt7WWWW"
"m-3wet7WWW_FeZu7WWW2bdf7WWWWm-3be-7WWWWGibx7WWWWGbbZ8WWW2k-d8W8unk8Wu-xl-x-6ib_7WWW2uif7WWW_--Vgwi8WWW2ncy7WWWWWWyUW-_7W"
"WW_--3iu-7WWW2uok7WWWWm-3yid8WWWWGqpY8WWWWGmrh8WWW2Wsm8W8Wnt8Wu-xl-Rmcl8WWW2ohZ8WWWWm-3eyo8WWWWGkqi8WWWWGoyt8WWW2idz8W8W"
"ha9Wu-vl_pUupa6WWWWWWW1mpz6WeWYmWaVWks7WWWWWWW1mwk8Wu-XmWaVy-o7WWWWWWW1pbg8WWWy-We-a7yYZ7WWWWWWWW3aht6WWWWW_Fuqp6WWWWWWW"
"W6k-a6WWWWWWW-3ina5WWWWWYmW4yzj6WWWWW_l-3eZq5WWWWWWW1wzb6WWWWWWW-3Wcw5WWWWWYGect6WWWWW_FWXk6WWWWWWGeuu6WWWWW2qda7WWWWWWW"
"-f7Yvz6WWWWW_Fstx6WeWYmYqVWyn8WWWWW_FmZj8WWWWWWWW6mo-7Wu-zl-xVhnz6WWWWWWGooh7WWWWW2rmx7WeWYm_p_2WeX7WWWWWYmW4Wze8Wu-zl-x"
"VmYe7WeWYm_p-2Wxi7WWWWWWW1WbW8WWWWWWW-3Wbo7WWWWWYGWrn8WWWWW_Fmsd8WWWWWWGWrn8WWWWW2Wa_8Wu-zlzhUyfe6WWWWWYGWij7WWWWW_FmnY7"
"WWWWWWGyqn7WWWWW2ulY8WWWaW-t_a7uyY7WWWy-W8wdd7WWWWWWu-1ion7WWWWWWWW1eo_6WWWWWW8gxu6WWWWW_Fqit6WWWWWYeVakq7WWWWWW8Y_d7WWW"
"WWW8nuw7WWWWW1qWZ8WWW4wYj8WWWy-y7WjX7WWWaWX8xce8WWWy-W8sx-7WWWaW-t-3ZzY8WWWy-_7rfl7WWWWWWmVkql6WWWWWYuVnu-7WWWWWWWW1trp7"
"WWWWW_7qjv6WWWaWX8smx7WWWy-_7eZc7WWWWW2woq7WWWWW_l_1ong5WWWaWXeW2YX_6WWWWWWWW1_qj7WWWy--dW1cdg7WWWWW1xqu6WWWWW--Vqpv7WWW"
"WWXuVxxj7WWWWWW8tvZ7WWWWWW8_Zq7WWWWW1Wfx7WWW4hsa8WWWy-yd-1mix5WWWWWWW1adl6WWWaWXe-1aof7WWWWWWW1tYy7WWWy-_t_1gZY6WWWWWYGk"
"-Z7WWWWW_Fprv6WWWWWWGgzc7WWWWW2ukr7WWWWW_l_1mub6WWWaWX8Wyk7WWWyVWyq7WWWWWW8iaf7WWWWWW8_cx7WWWWW1ueZ8WWW4icj8WWWy-y7mo_6W"
"WWaWX8WjZ8WWWy-_7ari7WWWWW2may7WWWWW_7urp7WWWaW1icj8WWWyVawa8WWWWW1qrk8WWW4ghv8WWWWW_h_a7qki7WWWWWW4oqZ7WWWy-W8iif7WWWWW"
"Wu-1ogp7WWWWWWWW1iWb7WWWWWW8mp_6WWWWW_Fcyz6WWWWWYeVsns7WWWam-3mgj8WWWyFe-X8WeWYGmrv8Wu-XGeup8WWWy-_3qag7WeWYmW4Wqp8Wu-zF"
"_yf8WWWWW-3qty7WWWWW1uwa8WWW4gvk8WWWy-y7sda7WeWYmW4mxm8Wu--lW4kxt8WWW2-th8WWWy-W8qbZ8WWWam_x_3pte8WWWWG_Ya8WWW_--Rhol8WW"
"W2gva8WWWy-_7kdo7WWWWWWmVegr6WWWWWYuVZdZ8WeWYm_Bugf8Wu-XmWeVmnh8WWWyVuoe8WWWWWWCwny7WWWWW_7Ww-6WWWaWX8xya8WWWy-_7Ytj7WWW"
"WW2nnz7WWWam_xUqmo8WWWWGWdj8WWWyV_rh8WWWWWWCYZb8WWWam-3xoa9WWWyFuak8WeWYGWvh9Wu-zF_zu8WWW4kjb9WWWy-y3kcb7WeWYmW4Woo8Wu--"
"lW4Yrx8WWW2hsj8WWWWm-3-f-8WWWWGppt8WWWWGcZb9WWW2Yeh9W8Wsp9Wu-vl_3ugq7WWWWW2gpb8WeWYm_3maz8WWWWW2uii9Wu-zlz3sZx7WWWaW1aXu"
"8WWWyVxvk8WWWWW1Ybw8WWW4omc9WWWy-ydUWfk5WeWYmWaW1WZd7Wu-XGqt_7WWWWm-ZW1tqy7WWWWG_uZ7WWWWWWyVqeW8WWWWm-3fiW8WWWWGyvl7WWWW"
"m-3cle8WWWWGazZ8WWWWGZWj8WWW2WXo8W8m-u8Wu-zl1dXz8WWWy-zZW1ewo7WWWWW1oh_6WWWWW--VrZz7WeWYmW4mXa9WWWWW1eZp8Wu-zl-pVdis7WWW"
"WWW8-dg7WWWWm_7ixf8WWWaW1wnz8WWWyFzpy7WWWWGdYo8WWWWGcoa8WWW4unk8WWWy-_lVeq_7WWWam-3Ygt8WWWyFuXi8WeWYGehd9Wu-XG_mW9WWWy-_"
"3qXm7WeWYmW4euz8Wu-zFkZr8WWWam_3eqW9WWWyFkbb8WWWWW1W_j8WWW4oqu8WWWWm_3bYb9WWWyFavk8WeWYGmdi9Wu-zFWhv8WWW4kwb9WWWyFae_8We"
"W2mro9Wu-1cnh9WWW2Wkp9W8ecy9Wu-vlyZVar-5WWWWWWW1siq6WeWYmWaVWjp7WWWWWWW1m-e8Wu--lWaVoyd8WWW2uWm7WWW_--VnYv8WWW2asa8WWWWW"
"WyUpgf8WWW_--3Ylf8WWW2Ywr7WWWWm-3aoo8WWWWGnbj8WWWWGYht8WWW2Wry8W8m-Z9Wu-xl-Rlyx8WWW2ssj8WWWWm-3ay-8WWWWGtdu8WWWWGrsb9WWW"
"2_uh9W8ucq9Wu-vl_pUeqc6WWWWWYGekg7WWWWW_Fst-6WWWWWWGawj7WWWWW2ojz7WeWYm_pUmgv7WWWWWYGWvz8WWWWW_FWmo8WWWWWWGWvz8WWWWW2eWj"
"9Wu-zlzhUWpg6WWWaWX8_zr7WWWyVwp_7WWWWWW8scm7WWWWWW8idb8WWWWW1Wbk8WWW4gyu8WWWy-y7mgb7WWWaWX8mwj8WWWy-_7ksq7WWWWW2Wxb8WWWW"
"W_7k-x7WWWaW1gyu8WWWyVpql8WWWWW1WXx8WWW4Xjd9WWWy-ydUmYj6WeWYmW4Wry7Wu-XGuZk8WWWWWW4Wcv7WWWyViYZ8WWWam_3mpt8WWWWGyzn8WWWW"
"Gqky8WWW2uyX9W8Wff9Wu-vFmYn8WeWYGW_j9Wu-XGWyc9WWWy-_3elp7WeWYmW4W_Y9Wu-zFaww8WWWWW-3asf8WWWWW1exo8WWW4Wvz8WWWWm_3idh9WWW"
"yFWrp8WeWYGmro9Wu-zFmW-8WWW4WZi9WWWyFela9WeW2Wzv9Wu-1qlo9WWW2Wvw9W8W-ZAWu-vly3ane7WeWYmW4Wft8Wu--lW4oxX9WWW2aio8WWWWm-3k"
"ub9WWWWGygz8WWWWGssh9WWW2qbo9W8m_w9Wu-vl_3mhu7WWWWW2qZg8WeWYm_3W_Y9WWWWW2mdp9Wu-zlz3ys-7WWWaW1Wvz8WWWyVifq8WWWWW1edW9WWW"
"4gbj9WWWy-y3mZa8WeWYGWff9Wu-1ejj9WWWWGatZ9WWWWGalp9WWW2Wvw9W8W-ZAWu-vFyyv8WeWYGWcx9Wu-zFmoc9WWW4yhq9WWWyFeWj9WeW2W-ZAWu-"
"1uZy9WWW2aXbAW8WzkAWu-vlyZ_W7eXk3WeWYmWaWX8Wzj5Wu-XmW4upj6WWWWm-x-W8ynp6WWWWGuXj6WWWWWW4_oh5WWWy-W8yjd6WWWaW-p-_7W_q6WWW"
"WWW4Ygk6WWWWWWyVwkm6WWWWWW4cpu5WWWy-W8caq6WWWaW-pVmhv6WWWWWW4aqm6WWWWm-3e__6WWWWGkey6WWWWGsbY7WWW2aqb7W8mjg7Wu-zl1_sz7WW"
"Wy-_3ixX7WeWYmW4Wcb8Wu-XmW4uYW8WWW_-zFsdv7WWW2yWp7WWWy-W8iez7WWWWW-p_W8er-6WWWWWX4k_c6WWWWWW8Wae5WWWWWWu--7Wzp6WeWYmWaW1"
"ewZ8WWWWWW8Woc7Wu-zl_3hnn7WWWWW2m_t7WWWWW-h-y7-WZ7WWWWWWCqve6WWWWWWu-1bhg6WWWWWW8iZr5WWWWWWq-1mke7WWWWWW4ymo6WWWam-3e_-7"
"WWWyFjqk7WWWWGYvx7WWWaGm__7WWWy-_3_ei6WWWWWW4Yli7WWWWW1ivr7WWWWmz3ivm7WWWWm1mbt6WWWWW1uny6WWW4YjZ7WWWy-_Nbyh7WWWWWWu_w7o"
"sb7WWWWWWeW1_oq6WWWam-xVq-k7WWWWm1hnX8WWWy-_3qsY7WeWYmW4mmc8Wu-zFedz7WWWWW-3wro7WWWaW1knX8WWW_-zFldb8WWW2kn_7WWWy-W8kb-7"
"WWWWWWuUhfr6WWWWWW8mqx5WWWWWWuVXgh7WeWYmW4uid8WWWWWW8Wmp7Wu-zl-3Xyl7WWWWW1_ev7WWWWW-lVws_6WWWam-3icX8WWWyFuio7WWWaW1XkY8"
"WWWy-_3kWu6WWWWWX4ikv7WWWWmz3ayp7WWWWm1pkZ7WWWWW1m_e7WWW4WYm7WWWy-_Nfqs7WWWWWWuUYXl7WWWam-3qlZ8WWWyFg-u7WeWYGmwk8Wu-XGzg"
"f8WWWy-_3yyZ7WeWYmW4m-e8Wu-zFWfW8WWWWW-3lpq7WWWWW1asx7WWW4oia8WWWWm_3rri8WWWyFobx7WeWYGWmo8Wu-zFqhZ8WWW4qbj8WWWyFuYd8WeW"
"2Wft8Wu-1cln8WWW2yrt8W8Wn_8Wu-z-zFmwy8WWWylW4enX8WeWYmW4mXa9Wu-zl-3hjd8WWWWW1eon8WWW4Yvz8WWWy-yt_W8aYx5WWWWWWGqhY5WeWYmW"
"q-W8WYu7WWWWWWGWcW7Wu-zl-h-_7Zud6WWWYWXy-1q-x7WWW2csp7WWW_--7gYl8WWWYWW4Wzp7WWW_--Fmux7WWW2uZz6WWWWm-Z-u7urh7WWWWGW_e7WW"
"W_--Rgdz7WWW2ops7WWWy-_d-4_bk6WeWYmWaW1ewZ8Wu-XWW4enn8WWW_lWqVmbz7WWW2W_s7WWWWWWCxZ-7WWW_--FvW-7WWW2Wqf7WWWWm-ZVug-7WWWW"
"Ggkx7WWWWm-Bedr8WWWWGzyg8WWWWm-3knt8WWWWGcvm8WWWWGchz8WWW2uhZ9W8exh9Wu-xl-Bbgb8WWW2zwx7WWWWm-3bhe8WWWWGXzY8WWWWGYZj8WWW2"
"g-n8W8epu8Wu-zl-B-_m8WWWy-_d-u7qj_5WWWWWWWW4kfl5WWWWWWe-3_xr6WWWWWW4mdc7WWWWW2yrt7WWWWWWCiyi7WWWWW_7_na6WWWWWW8Wa-6WWWWW"
"W8Woj6WWWWW2eau6WeWYm_p-u7mjx7WWWWWWWW4m-i7Wu-zl-Z-2idz6WWWWWYGiet7WWWWW_FkYe7WeWYmWaVWhm8WWWWWYGuta9WWWWW_7WbW8WWWWWW8e"
"ks8WWWWWW8msd8WWWWW2e_o8Wu-zlzh-s7yZf6WWWWWYi-1Xlv7WWWWWW8n_s7WWWWWW4slZ7WWWWW_7s_t6WWWWWW4snh7WWWaWX4het7WWWy-W8vol7WWW"
"WW_l-1Wwr5WWWaWXi-1nu_7WWWWWWSktf7WWWy-_7yiY7WWWWWYy_1nl_7WWWWWWCaXm7WWWWW_7wkl6WWWWWWGWcv6WWWWW2sha7WWWWW_p_1kea7WWWaWX"
"8yYh8WWWyV_jc8WWWWWW8imY8WWWWWW4bkq7WWWWWW4YZe8WWWWW1owo8WWW4o-_8WWWy-y3khw6WWWWWW4gym7WWWaWX4sYy7WWWWWW4Xjn8WWWy-_3k_c7"
"WWWWW2pbr7WWWWW_3inr7WWWWW2noe8WWWWW_3sZi7WWWaW1mnZ8WWWyVXtx7WWWWW1gua8WWW4wnk8WWWWmzp_q7uco7WWWWGmkl7WWWy-WCelx7WWWYW-F"
"hZd8WWW2qaW8WWWy-_7e-j7WWWWW2uxX8WWWWW_lViyk6WWWWWYuVumu7WeWYm_Bmfb8Wu--lW4zYr8WWW_-WaVkfx7WWWWm_Bcty7WWWWm1mxf7WWWWW_7o"
"a_6WWWaWX8ptW8WWWy-W8jnu7WWWWWWyUsYY8WWWWWWCsXz7WWWam-3zjt8WWWyFyha8WeWYGeuz8Wu-zFeij8WWW4hau8WWWy-y3Wab7WeWYmW4Wyn8Wu--"
"lW4Yau8WWW2nqi8WWWWm-3xzw8WWWWG_xp8WWWWGygW9WWW2Ytc9W8Wdl9Wu-vlW4etZ8WeWYmW4Wqd9Wu-zl-3wtg8WWWWW1Yfr8WWW4knX9WWWy-ydV_tv"
"5WeWYmWaW1Wmp7Wu--lWeVW_c8WWW2ycW8WWW_--Rtie8WWW2qZm7WWWy-_7svf7WWWamWyU_se8WWWWGhka8WWWWmWGnnW9WWW_l-Byql8WWW2zXb8WWWWm"
"-3Wyo8WWWWGmyi8WWWWGl-t8WWW2aaz8W8eha9Wu-vl_3ywo7WeWYmW4emv8Wu-XmW4ecq8WWWy-WqUwnX8WWWWWWCgvu7WWWWW_7qcr6WWWWWWGyc-6WWWW"
"W2gqg7WWWWWWeVuba8WeWYmW4Wzd9WWWWW_7mqf8WWWWWWGmYo8WWWWW2mi_8Wu-zlz3scu7WWWWW2lmh8WWWaW-pU_oi8WWWyVb-e8WWWWWWCv_y7WWWWWW"
"4Yzg8WWWWW1wrr8WWW4h_X9WWWy-y3_dW7WWWaWX8acb8WWWWWW4Wfq8WWWy-_3aak7WWWWW2uvz7WWWWW_7_up7WWWaW1slj8WWWyVaYb8WWWWW1oyk8WWW"
"4jmv8WWWWmzpUYip8WWWWGymk8WWWyVuoi8WWWWWWC_ec8WWWam-3vdb9WWWyFixk8WeWYGuii9Wu-zFmrv8WWW4XZc9WWWy-y3gcc7WeWYmW4Wxp8Wu--lW"
"4tky8WWW2zxk8WWWWm-3l_-8WWWWGlgu8WWWWGwsb9WWW2ixh9W8Weq9Wu-vl_3qgr7WWWWW2Yqc8WeWYm_3mxz8WWWWW2mWj9Wu-zlz3epx7WWWaW1wqu8W"
"WWyVfil8WWWWW1csw8WWW4sXd9WWWy-y3WW-7WeWYGWqY9Wu-1ixb9WWWWGoaz8WWWWGqqh9WWW2ylo9W8Wcx9Wu-vFiqp8WeWYGWXp9Wu-zFkn-8WWW4Wni"
"9WWWyFesb9WeW2Wcx9Wu-1eup9WWW2uXy9W8WebAWu-vlyZ_m7WbW4WWWWWWWWGWXt4WeWYmWaWn7WXx5WWWWWWWWGW-p6Wu----ZWn7mnW7WWW2yZw6WWWW"
"Gusu5WWW_l---Fqgq7WWW2wum7WWWWGmbn6WWWWWWy-k7iWX7WWWWm-3WqW7WWWWGiiw6WWWWm--VWmx6WWWWGyc-5WWWWWWyVazb7WWWWm-3q_b7WWWWGut"
"y6WWWWm-3uqh7WWWWGmxe7WWWWGq_k7WWW2mlo7W8Wjt7Wu-zl1Y_f8WWWWW_t-Dujr7WWWWm-ZW1avp7WWWWGqYz6WWWWWWyVWjt7WWWWm-3sWu7WWWWGii"
"f7WWWWm-3md-7WWWWGayw7WWWWGafZ8WWW2uud8W8mwj8Wu-zl1u_w8WWWy-zZWn7i_p6WWWWW1idr5WWWWW---FwWe7WWWWW1usi6WWWWW---l7Ylw6WeWY"
"mWaW1Whm8WWWWW1Wlp7Wu-zl_x-Evzn7WeWYmWaW1WfY9WWWWW1Wse8Wu-z-zx-i7ipi7WWWWm1qdq6WWWWW---1kgr6WWWWW1ctx5WWWWWWu-1ep_6WWWWm"
"_7ZZo7WWWWm1mxt6WWWWm_7anx7WWWaW1yYh8WWWyFwiZ7WWWWGYfX8WWWWGaXf7WWW4acm7WWWy-zt-Dltg7WWWWW1fau6WWWWWWu-1gok7WWWWm_7xwy7W"
"WWWm1tZa7WWWWm_7qYf8WWWaW1pZy8WWWyFekq7WWWWGmkm8WWWWGetx7WWW4sra8WWWy-_l-g7s_j7WWWWWWeW1iqw6WWWam-xVqmr7WWWWm1Wqh8WWWy-_"
"3igf7WeWYmW4uan8Wu-zFkZd8WWWam_3pah8WWWyFxax7WWWaW1a_h8WWWy-ztVmbx6WWWWW1mq-5WWWWWWuVinp7WWWWW-7yjp7WeWYmW4Wyn8WWWWW1WXw"
"7Wu-zl-3qhu7WWWWW1tqY8WWWWW-lVWWb7WWWWWW8eZ_6WWWWm_7izy7WWWaW1_oi8WWWyFqvf7WWWWGuzY8WWWWGmjl7WWW4ups7WWWy-_lVuys7WWWam-3"
"XXj8WWWyFcYY8WeWYGewv8Wu-XGnyp8WWWy-_3acg7WeWYmW4eZp8Wu-zFWZg8WWWam_3z_p8WWWyFmty7WWWWW1ssa8WWW4jgk8WWWWm_3Yot8WWWyFWka8"
"WeWYGWvz8Wu-zFunj8WWW4kbu8WWWyFuon8WeW2W_Y9Wu-1kvy8WWW2ijZ9W8msg9Wu-z-zl-Bf-i8WWWWm1eoz8WWWy-zZW1uYp7WWWWW1yY_6WWWWW--Vy"
"Z_7WeWYmW4uta9WWWWW1WWp8Wu-zl-pVqts7WWWWWW8rig7WWWWm_7cug8WWWaW1qj_8WWWyFmwy7WWWWGowo8WWWWGswa8WWW4znk8WWWy-_lVpv-7WWWam"
"-3lYu8WWWyFqYj8WeWYGeee9Wu-XGniX9WWWy-_3aum7WeWYmW4mi_8Wu-zFXbs8WWWam_3hsX9WWWyFsZc8WWWWW1cyk8WWW4Wgv8WWWWm_3dWc9WWWyFwv"
"l8WeWYGeWj9Wu-zFgkw8WWW4hrc9WWWyFYX-8WeW2mdp9Wu-1zbi9WWW2a-p9W8uoy9Wu-vlyZ-e7qbd4WWWWWWWX8ujl5WWWWWWW-7ovZ5WWWWWWWW8yZp5"
"WWWWWWW1qla6WeWYmWa-e7WpX6WWWWWWWX8Wzi7WWWWWWW-7WcW7WWWWWWWW8Wzi7WWWWWWW1Wm-7Wu--lWa-e7yrW7WWW2ue-5WWW_---W8ood8WWW2mqf7"
"WWW_---_7wix7WWW2uWz6WWW_----7ood8WWW2mqf7WWW_--Vczt8WWW2jux7WWWWWWy_c7Wad7WWWWWW4iwW7WWW_---VciX7WWW2qbZ6WWWWWWyVaki7WW"
"W_--3ali7WWW2uZZ7WWWWm-3uco7WWWWGmjl7WWWWGqmr7WWW2mXv7W8W-z7Wu-xl-Rqpc8WWW2vs-7WWW_----6a-e8WWW2aYm7WWWWm-ZVwje8WWWWGvxZ"
"8WWW_--RZrl8WWW2bla8WWWWm-3eyo8WWWWGkqi8WWWWGoyt8WWW2idz8W8Wha9Wu-zl-t_5Yi_7WWWWm-ZW1kky7WWW_Frty7WWW2meZ7WWWWWWyVmXW8WW"
"WWm-3chW8WWW_FytW8WWW2uxl7WWWWm-3wje8WWWWGprZ8WWWWGzpi8WWW2arn8W8eiu8Wu-xl-x-6a-e8WWW2aYm7WWW_--V-_v8WWW2qoa8WWWWWWyUa_f"
"8WWW_--3ovg8WWW2uls7WWWWm-3zfp8WWWWGftj8WWWWGoyt8WWW2idz8W8Wha9Wu-xl-Rcyy8WWW2Ygk8WWWWm-3gtW9WWWWGpuu8WWWWGhfc9WWW2Wmi9W"
"8Wqq9Wu-vl_p_a7mhh4WWWWWYmW4ivx5WWWWW_FiZe6WWWWWWWW4azr5WWWWWWWW4svk6WWWWWWGeuu6WWWWW2qda7WWWWW_l_3udg5WWWWWYmW4yvt6WWWW"
"W_l-3ecx5WWWWWWW1uvk6WWWWWWW-3arY6WWWWWYGqda7WWWWW_Fw-v6WWWWWWGiYd7WWWWW2qer7WeWYm_p_a7Wnb6WWWWWYmW4WXw7WWWWW_Fmqa8WWWWW"
"WWW4Wlp7WWWWWWWW4Wze8WWWWWWGWrn8WWWWW2Wa_8WWWWW_l_3Woc7WWWWWYmW4Wmo8WWWWW_l-3Wlp7WWWWWWW1Wse8WWWWWWW-3WXw7WWWWWYGWa_8WWW"
"WW_Fe_o8WWWWWWGWa_8WWWWW2Wdj9Wu-zlzh_Y7uak4WWWaWXeW2ucZ6WWWy-W8yqw6WWWWWWWW2Ys-5WWWWW_FYjk6WWWWWYe-1uXb7WWWWWW8ub_6WWWWW"
"W8g_f7WWWWW1yol7WWW4Wus7WWWy-y7yzz6WWWaWX8acW8WWWy-W8mau7WWWWW_l-1ewv5WWWaWXeW2acm7WWWy-_7kkf7WWWWWWm-1g_q6WWWWWWGmY-6WW"
"WWW2Wqg7WWWWWWe-1why7WWWWW_7o--6WWWaWX8xoa8WWWy-_7Ysj7WWWWW2zdz7WWWWW_7urp7WWWaW1icj8WWWyVawa8WWWWW1qrk8WWW4ghv8WWWy-yd_"
"1sak5WWWaWXeW2YhZ7WWWy--dW2ano7WWWWW1a-z6WWWWWWu-1Xes7WWWWWW8ojg7WWWWWW8ymy7WWWWW1qfa8WWW4Xak8WWWy-yd-1mq-5WWWWWWW1Weq6W"
"WWaWXe-1acm7WWWWWWW1doa8WWWy-_t_1kWd6WWWWWYGWqg7WWWWW_FZ--6WWWWWWGaYk7WWWWW2mlz7WWWWW_l_1Whh6WWWaWX8Wus7WWWyV_Y-7WWWWWW8"
"mWn7WWWWWW8Zvb8WWWWW1qrk8WWW4ghv8WWWy-y7YZc7WWWaWX8Yik8WWWy-_7ikr7WWWWW2mkc8WWWWW_7iry7WWWaW1ghv8WWWyVsam8WWWWW1olx8WWW4"
"xud9WWWy-yd_X7mam4WeWYmWaW1Wbe6Wu-XGmXh7WWWWWW4ysa7WWWyVyXp7WWWaW--VWwb6WWWy-W8um_6WWWaW-pVaim7WWWWWW4e-c7WWWWm-3uas7WWW"
"WGmhp7WWWWGqkv7WWW2m-y7W8WzX8Wu-zl1m-m8WWWy-_3Wjj7WeWYmW4mdt8Wu-zFqxi8WWWWW-3elW8WWWaW1mzn8WWW_-zFhii8WWW2agb8WWWy-_7Wko"
"7WWWWW2WYd8WWWWWWWVmfY6WWWWW_Fmdo6WWWWWYeVuku7WeWYmWCW-z7Wu-zl-3upz7WWWWW1Wee8WeWYmzBWlg8Wu--lW4qvx8WWW_-WWVuze7WWWWWW8u"
"_X7WWWWm_7aaY8WWWWm1ivj7WWWWW1mjp7WWW4ipw7WWWy-y7_xX7WWWaWX8kub8WWWy-W8_jz7WWWWWWuUysx7WWWam-3Wso8WWWyFgld8WeWYGm_-8Wu-X"
"Gszv8WWWy-_3ebk7WeWYmW4m-u8Wu-zFiwl8WWWWW-3Y_X8WWWWW1ecg8WWW4abq8WWWWm_3ynz8WWWyFuvf8WeWYGm-Z9Wu-zFmfp8WWW4if_8WWWyFWot8"
"WeW2Wff9Wu-1mXZ9WWW2uuf9W8Wbn9Wu-vly3exe7WeWYmW4mdt8Wu--lW4iu_8WWW2yzn8WWWWm-3auX9WWWWGs-v8WWWWGaod9WWW2qek9W8Wet9Wu-vlW"
"4ave8WeWYmW4Wdl9Wu-zl-3kqm8WWWWW1e-x8WWW4uze9WWWy-ydVWky5WeWYmWaW1Wjt7Wu--lWaW1oek8WWW2mXq7WWWy-_7yWk7WWWamWyUpWk8WWWWG_"
"ff8WWW_--Rmnr8WWW2WWg8WWWWm-3kvu8WWWWGygo8WWWWGYzz8WWW2mgZ9W8Wrg9Wu-vl_3kbt7WeWYmW4mt-8Wu-XmW4shw8WWWy-_dVuru6WWWWWWGWzY"
"7WWWWW2ulk7WWWWWWeVqef8WeWYm_Bunk8WWWWWWGWnt8WWWWW2Wha9Wu-zlz3uWz7WWWWW2egn8WWWaW-pUmzn8WWWyVypk8WWWWWWCtmX8WWWWW_7awZ7W"
"WWaWX8YWg8WWWy-_7uco7WWWWW2xkY8WWWWW_7Weu7WWWaW1awo8WWWyVobg8WWWWW1ygq8WWW4eg-8WWWWmzpUaXv8WWWWGmqp8WWWyVmco8WWWWWWCjdh8"
"WWWam-3ldi9WWWyFqnq8WeWYGWsp9Wu-zFoWW9WWW4eZj9WWWy-y3iwf7WeWYmW4m-u8Wu--lW4cYZ9WWW2Y-p8WWWWm-3jsc9WWWWGme_8WWWWG_ri9WWW2"
"Wdp9W8WXy9Wu-vl_3qnv7WWWWW2ylh8WeWYm_3WyZ9WWWWW2Weq9Wu-zlz3wfW8WWWaW1qp_8WWWyVtXr8WWWWW1wWX9WWW4iYk9WWWy-y3mZa8WeWYGWff9"
"Wu-1ejj9WWWWGatZ9WWWWGalp9WWW2Wvw9W8W-ZAWu-vFyyv8WeWYGWcx9Wu-zFmoc9WWW4yhq9WWWyFeWj9WeW2W-ZAWu-1uZy9WWW2aXbAW8WzkAWu-vly"
"ZUmum5WeWYmWaW1mjg7Wu-XGepZ8WWWWm-ZW1-vX8WWWWGWad7WWWWWWyVeab8WWWWm-3nob8WWWWGewp7WWWWm-3ssj8WWWWGeue8WWWWGZfo8WWW2mit8W"
"8Wh_8Wu-zl1qia9WWWy-zZW1ppt7WWWWW1atX7WWWWW--VYZZ8WeWYmW4exh9WWWWW1eiu8Wu-zl-pVocx7WWWWWW8vek7WWWWm_7_fm8WWWaW1aab9WWWyF"
"_kX8WWWWGnyu8WWWWGsrf8WWW4gvp8WWWy-_lVrqa8WWWam-3Yzz8WWWyFkpo8WeWYGehl9Wu-XGece9WWWy-_3wsq7WeWYmW4eha9Wu-zFfdy8WWWam_3qi"
"e9WWWyFfdh8WWWWW1yfq8WWW4Wb-8WWWWm_3Ywi9WWWyFwer8WeWYGucq9Wu-zFwnW9WWW4qoj9WWWyFonb9WeW2m_w9Wu-1bnp9WWW2mwx9W8WWbAWu-vly"
"ZVqmY6WWWWWWW1uqt6WeWYmWaVWjt7WWWWWWW1mwj8Wu--lWaVoek8WWW2mXq7WWW_--VZlW9WWW2qnf8WWWWWWyUdjl8WWW_--3Yyl8WWW2alw7WWWWm-3q"
"Yv8WWWWGzep8WWWWGYzz8WWW2mgZ9W8Wrg9Wu-xl-RhiZ9WWW2evp8WWWWm-3Xhd9WWWWGbv_8WWWWGvdj9WWW2gtp9W8Wjy9Wu-vl_pUuxf6WWWWWYGulk7"
"WWWWW_FqqZ7WWWWWWGyao7WWWWW2eaY8WeWYm_pUW-z7WWWWWYGWha9WWWWW_Fepu8WWWWWWGWha9WWWWW2Wqq9Wu-zlzhUmck6WWWaWX8ipw7WWWyVcga8W"
"WWWWW8kyq7WWWWWW8kYh8WWWWW1ygq8WWW4eg-8WWWy-y7mxf7WWWaWX8_vp8WWWy-_7Wwv7WWWWW2eoh8WWWWW_7ibX8WWWaW1eg-8WWWyV-ur8WWWWW1ku"
"X9WWW4wtk9WWWy-ydUWYn6WeWYmW4WzX8Wu-XGihr8WWWWWW4uk_7WWWyVYzf8WWWam_3mf-8WWWWGWcv8WWWWGada9WWW2uuf9W8Wbn9Wu-vFipu8WeWYGW"
"nt9Wu-XGeXm9WWWy-_3iuu7WeWYmW4msg9Wu-zFgYZ9WWWWW-3yqm8WWWWW1icw8WWW4mib9WWWWm_3siq9WWWyFgYx8WeWYGecy9Wu-zFkgd9WWW4uer9WW"
"WyFeWj9WeW2W-ZAWu-1uZy9WWW2aXbAW8WzkAWu-vly3irj7WeWYmW4Wn_8Wu--lW4xsg9WWW2glv8WWWWm-3npk9WWWWGsWb9WWWWGnuq9WWW2stx9W8WWb"
"AWu-vl_3mb_7WWWWW2wum8WeWYm_3msg9WWWWW2uoy9Wu-zlz3_ob8WWWaW1mib9WWWyVamx8WWWWW1eee9WWW4aZs9WWWy-y3u-f8WeWYGWbn9Wu-1kss9W"
"WWWGqmh9WWWWGfZz9WWW2aXbAW8WzkAWu-vFYgX9WeWYGWebAWu-zFgWl9WWW4o_z9WWWyFcur9WeW2WzkAWu-1zjcAWWW2WgmAW8mexA";

// Each packed entry is the difference of sorted canonical relations followed by
// the sum of exact legal distances for that relation and its transpose. The table
// contains every eight-element partial order, independently of the input targets.
struct Poset8Costs {
    static constexpr unsigned CS=1u<<20;
    std::vector<u64> keys,relations;
    std::vector<int> values,both;
    long long misses=0;
    static unsigned hash(u64 r){r^=r>>27;r*=0x3c79ac492ba7b653ULL;r^=r>>33;return unsigned(r)&(CS-1);}
    Poset8Costs():keys(CS,~0ULL),values(CS){
        const char* p=kPoset8Packed;
        auto read=[&](){
            u64 value=0;unsigned shift=0;
            for(;;){
                unsigned char c=*p++;
                unsigned digit=c>='0'&&c<='9'?c-'0':c>='A'&&c<='Z'?c-'A'+10:c>='a'&&c<='z'?c-'a'+36:c=='_'?62:63;
                value|=u64(digit&31)<<shift;
                if(!(digit&32))return value;
                shift+=5;
            }
        };
        u64 relation=0;
        for(int i=0;i<16999;++i){relation+=read();relations.push_back(relation);both.push_back(int(read()));}
        assert(!*p);
    }
    int cost(u64 raw){
        unsigned h=hash(raw);if(keys[h]==raw)return values[h];
        int value=0;
        if(!(raw&transpose8(raw))){
            u64 closed=closure8(raw,8);
            if(!(closed&kDiagonal)){
                ++misses;u64 canonical=canonical8(closed);
                auto it=std::lower_bound(relations.begin(),relations.end(),canonical);
                assert(it!=relations.end()&&*it==canonical);
                value=1+both[it-relations.begin()];
            }
        }
        keys[h]=raw;values[h]=value;return value;
    }
    static Poset8Costs&get(){static Poset8Costs table;return table;}
};
struct WindowStats{int iterations=0;double score=0,gobj_before=0,gobj_after=0;int climb_steps=0;};
WindowStats assign_windows(std::vector<u64>& A,int m,int g,
    std::vector<std::pair<int,int>>& edges,std::vector<int>& polarity,
    std::vector<int>& permutation,double seconds,int fixed_iters,int climb_steps,double climb_seconds) {
    assert(m==8&&g>=28&&g<64);
    auto& costs=Poset8Costs::get();
    const double start=elapsed_sec();
    constexpr int need=73;
    constexpr bool sparse = false;
    XorShift rng{0x71eb2566be932e31ULL};
    std::vector<std::pair<int,int>> ep;
    int index[8][8];std::memset(index,-1,sizeof(index));
    for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)index[a][b]=index[b][a]=ep.size(),ep.push_back({a,b});
    std::array<u64,28> masks{},forward{},reverse{};
    std::array<int,64> which{},order{};which.fill(-1);std::iota(order.begin(),order.end(),0);
    std::array<int,28> counts{};
    u64 pol=0,hm=kActiveWindows & ~low_bits(g);
    for(int e=0;e<28;e++)forward[e]=1ULL<<(8*ep[e].first+ep[e].second),reverse[e]=1ULL<<(8*ep[e].second+ep[e].first);
    for(int j=0;j<g;j++) {
        auto[a,b]=edges[j];int e=index[a][b];masks[e]|=1ULL<<j;counts[e]++;which[j]=e;
        if(polarity[j]^(a>b))pol|=1ULL<<j;
    }
    struct Pair {u64 a,d,r;int u,v,dist,rel;};
    std::vector<Pair> pairs;
    auto relation=[&](u64 a,u64 d) {
        u64 z=a^pol,r=0;
        for(int e=0;e<28;e++){u64 x=d&masks[e];if(x&~z)r|=forward[e];if(x&z)r|=reverse[e];}
        return r;
    };
    for(int u=0;u<256;u++)for(int v=u+1;v<256;v++) {
        u64 d=A[u]^A[v];int hd=__builtin_popcountll(d);
        if(hd>26)continue;
        u64 r=relation(A[u],d);pairs.push_back({A[u],d,r,u,v,hd,costs.cost(r)});
    }
    const int np=pairs.size();
    std::vector<u64> nr(np);std::vector<int> nc(np),selected,newselected;
    std::vector<std::pair<int,int>> sorted;sorted.reserve(np);
    auto matching=[&](u64 handles,bool next,std::vector<int>& matching)->double {
        sorted.clear();
        for(int p=0;p<np;p++) {
            int c=next?nc[p]:pairs[p].rel;if(!c)continue;
            const auto& x=pairs[p];
            // 403200 times (0.65 handle differences + both legal means + 0.04 all differences).
            int key=201600*__builtin_popcountll(x.d&handles)+10*(c-1)+16128*x.dist;
            sorted.emplace_back(key,p);
        }
        std::sort(sorted.begin(),sorted.end());
        std::array<unsigned char,256> used{};matching.clear();long long sum=0;
        for(auto[key,p]:sorted) {
            const auto& x=pairs[p];if(used[x.u]||used[x.v])continue;
            used[x.u]=used[x.v]=1;matching.push_back(p);sum+=key;
            if(int(matching.size())==need)break;
        }
        return double(sum)/(403200*need)+10.0*(need-int(matching.size()));
    };
    double current=matching(hm,false,selected),best=current;
    auto best_masks=masks;auto best_order=order;u64 best_pol=pol;
    WindowStats stats;stats.gobj_before=current;
    long long full=0,escapes=0;unsigned generation=1;
    std::vector<unsigned> seen(1<<20);
    int no_accept=0;
    double escape_score=1e100;auto escape_masks=masks;auto escape_order=order;u64 escape_pol=pol;
    auto restore_state=[&](const auto& mm,const auto& oo,u64 pp) {
        masks=mm;order=oo;pol=pp;hm=0;which.fill(-1);
        for(int j=g;j<63;j++)hm|=1ULL<<order[j];
        for(int e=0;e<28;e++) {
            counts[e]=__builtin_popcountll(masks[e]);
            for(u64 s=masks[e];s;s&=s-1)which[__builtin_ctzll(s)]=e;
        }
        for(auto& p:pairs)p.r=relation(p.a,p.d),p.rel=costs.cost(p.r);
        current=matching(hm,false,selected);generation++;no_accept=0;escape_score=1e100;
    };
    struct Option {int ib,edge,color,loss;};
    struct Options {unsigned epoch=0;std::vector<Option>rows;};
    std::array<std::array<Options,3>,64>options;
    auto stage=[&](double duration,int iterations,bool climb) {
        const double st=elapsed_sec();double now=st;
        for(int it=0;;it++) {
            if((it&31)==0) {
                now=elapsed_sec();
                if(iterations>0?it>=iterations:now-st>=duration)break;
            }
            if(climb)stats.climb_steps++;else stats.iterations++;
            no_accept++;
            if(no_accept>=(climb?512:256)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                escapes++;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
            int ia=rng.mod(g),ib=rng.mod(g),a=order[ia],b=order[ib];
            bool swap_window=rng.real()<0.6;
            if(swap_window)ib=g+rng.mod(63-g),b=order[ib];
            int kind=rng.mod(10),ea=which[a],eb=swap_window?ea:which[b],transfer=-1;
            bool cross=swap_window && rng.mod(16)==0;
            int newcolor=int(pol>>a&1), memo=0;
            auto can_remove=[&](int e){return counts[e]>1 || (sparse && ep[e].second==6);};
            auto same_kind=[&](int x,int y){return !sparse || ((ep[x].second==6)==(ep[y].second==6));};
            if(swap_window || kind>=8) {
                int typ=swap_window?(cross?2:0):1;
                auto& cache=options[a][typ];
                if(cache.epoch!=generation) {
                    cache.epoch=generation;cache.rows.clear();
                    if(typ==0 || can_remove(ea)) {
                        for(int jj=(swap_window?g:ia);jj<(swap_window?63:ia+1);jj++) {
                            int w=order[jj];
                            for(int ee=0;ee<28;ee++) {
                                if((typ==0&&ee!=ea)||(typ!=0&&(ee==ea||!same_kind(ea,ee))))continue;
                                for(int color=0;color<2;color++) {
                                    u64 ma=masks[ea]&~(1ULL<<a), mb=masks[ee];
                                    if(ee==ea)ma|=1ULL<<w,mb=ma;else mb|=1ULL<<w;
                                    u64 pp=(pol&~(1ULL<<w))|(u64(color)<<w);
                                    u64 erase=forward[ea]|reverse[ea]|forward[ee]|reverse[ee];
                                    int lost=0;
                                    for(int z:selected) {
                                        const auto& x=pairs[z];u64 rr=x.r&~erase,zz=x.a^pp;
                                        u64 da=x.d&ma,db=x.d&mb;
                                        if(da&~zz)rr|=forward[ea];if(da&zz)rr|=reverse[ea];
                                        if(db&~zz)rr|=forward[ee];if(db&zz)rr|=reverse[ee];
                                        if((closure8(rr,8)&kDiagonal)&&++lost>=3)break;
                                    }
                                    if(lost<3)cache.rows.push_back({jj,ee,color,lost});
                                }
                            }
                        }
                    }
                }
                if(cache.rows.empty())continue;
                int total=0;for(auto&o:cache.rows)total+=1<<(2-o.loss);
                int pick=rng.mod(total),ix=0;
                while(pick>=(1<<(2-cache.rows[ix].loss)))pick-=1<<(2-cache.rows[ix++].loss);
                auto opt=cache.rows[ix];cache.rows[ix]=cache.rows.back();cache.rows.pop_back();
                ib=opt.ib;b=order[ib];eb=opt.edge;newcolor=opt.color;
                if(!swap_window)transfer=eb;
                memo=16384+2*(28*(a*64+b)+eb)+newcolor;
            } else if(kind<3)memo=8192+a;
            else {if(ea==eb)continue;memo=8256+std::min(a,b)*64+std::max(a,b);}
            if(seen[memo]==generation)continue;seen[memo]=generation;
            const u64 olda=masks[ea],oldb=masks[eb],oldpol=pol;
            if(swap_window) {
                masks[ea]&=~(1ULL<<a);masks[eb]|=1ULL<<b;
                pol=(pol&~(1ULL<<b))|(u64(newcolor)<<b);
            } else if(kind<3)pol^=1ULL<<a;
            else if(kind<8)masks[ea]^=(1ULL<<a)|(1ULL<<b),masks[eb]^=(1ULL<<a)|(1ULL<<b);
            else {masks[ea]^=1ULL<<a;masks[eb]|=1ULL<<a;pol=(pol&~(1ULL<<a))|(u64(newcolor)<<a);}
            u64 erase=forward[ea]|reverse[ea]|forward[eb]|reverse[eb];
            auto changed_relation=[&](const Pair& x) {
                u64 r=x.r&~erase,z=x.a^pol,da=x.d&masks[ea],db=x.d&masks[eb];
                if(da&~z)r|=forward[ea];if(da&z)r|=reverse[ea];
                if(db&~z)r|=forward[eb];if(db&z)r|=reverse[eb];return r;
            };
            int lost=0;
            for(int p:selected) {
                u64 r=changed_relation(pairs[p]);
                if(r!=pairs[p].r&&(closure8(r,8)&kDiagonal)) {
                    if(++lost>=3)break;
                }
            }
            if(lost>=3) {masks[ea]=olda;masks[eb]=oldb;pol=oldpol;continue;}
            full++;
            for(int p=0;p<np;p++) {
                nr[p]=changed_relation(pairs[p]);
                nc[p]=nr[p]==pairs[p].r?pairs[p].rel:costs.cost(nr[p]);
            }
            u64 nhm=swap_window?hm^((1ULL<<a)|(1ULL<<b)):hm;
            double next=matching(nhm,true,newselected);
            double progress=iterations>0?double(it)/iterations:(now-st)/duration;
            double temp=climb?0.0:0.05*std::pow(0.025,progress);
            bool accept=next<=current||(!climb&&rng.real()<std::exp((current-next)/temp));
            if(next<escape_score) {
                escape_score=next;escape_masks=masks;escape_pol=pol;escape_order=order;
                if(swap_window)std::swap(escape_order[ia],escape_order[ib]);
            }
            if(accept) {
                for(int p=0;p<np;p++)pairs[p].r=nr[p],pairs[p].rel=nc[p];
                hm=nhm;selected.swap(newselected);current=next;
                if(swap_window){which[a]=-1;which[b]=eb;std::swap(order[ia],order[ib]);if(ea!=eb){counts[ea]--;counts[eb]++;}}
                else if(kind>=3&&kind<8)std::swap(which[a],which[b]);
                else if(transfer>=0)counts[ea]--,counts[eb]++,which[a]=eb;
                generation++;no_accept=0;escape_score=1e100;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            } else {
                masks[ea]=olda;masks[eb]=oldb;pol=oldpol;
            }
        }
    };
    stage(std::max(0.0,seconds-(elapsed_sec()-start)),fixed_iters,false);
    restore_state(best_masks,best_order,best_pol);
    if(climb_steps>0||climb_seconds>0)stage(climb_seconds,climb_steps,true);
    masks=best_masks;order=best_order;pol=best_pol;
    for(int j=0;j<g;j++) {
        int x=order[j],e=0;while(e<28&&!(masks[e]>>x&1))e++;
        assert(e<28);edges[j]=ep[e];polarity[j]=(pol>>x)&1;
    }
    auto oldperm=permutation;
    for(int j=0;j<64;j++)permutation[j]=oldperm[order[j]];
    for(u64& a:A){u64 b=0;for(int j=0;j<64;j++)b|=((a>>order[j])&1)<<j;a=b;}
    stats.score=best;stats.gobj_after=best;
    std::cerr<<"map_escapes = "<<escapes<<"\nmap_full_evaluations = "<<full<<"\nposet8_cache_misses = "<<costs.misses<<'\n';
    return stats;
}

// kBitLanes[v][i]: bit i of v as 0.0f / 1.0f (8 float lanes of a byte of a bit mask; Design::Annealer)
alignas(32) const std::array<std::array<float, 8>, 256> kBitLanes = [] {
    std::array<std::array<float, 8>, 256> a{};
    for (int v = 0; v < 256; v++)
        for (int i = 0; i < 8; i++) a[v][i] = float(v >> i & 1);
    return a;
}();

// The dedicated papers: units (a pair of targets a, b or a single target a, b = -1) in columns c, and
// the handle order (handle[j]: window of h_j; hb[t]: colors of target t at h_0..h_{H-1}).
// Model of the moves per request, summed over the targets (cur):
//   - column c (colcost; from solutions/gpt6pro-10-01-filler-chain): (1 - kRankPriority) times the
//     digs nt (nc - 1) / 2 of a cyclic column (nt targets on nc papers) plus kRankPriority times the
//     least weighted depth W of the column with the pairs (asked twice as often) first, under the
//     condition that the top two papers have both handle colors; 1e5 without both colors (as6-imb0:
//     no balance term: a column holds mostly the minority color of the demand at its handle);
//   - handle hole h_j (hcost): kHoleWeight 4 n0 n1 / (n0 + n1) for n0 / n1 holes of color 0 / 1 (the
//     top of column j keeps the color of the last request with a hole there: persistence);
//   - generic layer of a pair (gc): the mean number of moves of the generic layer from a uniform
//     order of the sheets for each of its two targets, summed (2 gcost; PosetSums).
struct Design {
    struct Unit {
        int a = -1, b = -1, c = -1;
    };
    static constexpr double kHoleWeight = 0.40, kRankPriority = 0.85;
    XorShift rng{0x6176abcd1349ULL};
    int M, G, H, U, need;
    std::vector<u64> A, hb;
    std::vector<int> handle, owner;  // owner[t]: unit of target t
    std::vector<Unit> unit;
    std::vector<std::vector<int>> partners;  // compatible targets
    std::array<std::array<uint8_t, 256>, 256> ok{};
    std::array<std::array<float, 256>, 256> gcost{};
    std::vector<int> nc, nt, n1, pairOne;  // per column: units, targets, units / pairs of color 1
    std::vector<std::array<int, 2>> hn;    // per handle: holes of color 0 and 1
    std::vector<double> cval;              // colcost of the current counts
    double cur = 0;
    int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
    int colswap_tried = 0, colswap_accepted = 0, replace_tried = 0, replace_accepted = 0;  // (anneal)
    double proxy_before = 0, proxy_after = 0;

    static int pc(u64 x) { return __builtin_popcountll(x); }
    Design(const std::vector<u64>& a, int m, int g) : M(m), G(g), H(63 - g), U(191 - m), need(256 - U), A(a) {
        handle.resize(H);
        std::iota(handle.begin(), handle.end(), G);
        hb.resize(256);
        for (int i = 0; i < 256; i++) hb[i] = A[i] >> G;
        owner.assign(256, -1);
        partners.resize(256);
        nc.resize(H);
        nt.resize(H);
        n1.resize(H);
        pairOne.resize(H);
        hn.resize(H);
    }
    bool valid(const Unit& u, int c) const { return u.b < 0 || (((hb[u.a] ^ hb[u.b]) >> c) & 1) == 0; }
    // valid without branches: the pair differences of u (0 for a single) at column c
    int invalid_bit(const Unit& u, int c) const {
        return int(((hb[u.a] ^ hb[u.b & 255]) & (u64(0) - u64(u.b >= 0))) >> c & 1);
    }
    int color(const Unit& u, int c) const { return hb[u.a] >> c & 1; }
    int weight(const Unit& u) const { return u.b < 0 ? 1 : 2; }
    u64 holes(const Unit& u) const {
        u64 d = u.b < 0 ? 0 : hb[u.a] ^ hb[u.b];
        return (low_bits(H) & ~low_bits(u.c + 1)) | d;
    }
    // colcost of a column with nc units, nt targets, n1 units and p1 pairs of color 1 at its handle.
    // W (doubled: minimum2) is the least sum of the depths weighted by the targets (a pair counts
    // twice) with the np pairs on top: nc (nc - 1) / 2 + np (np - 1) / 2, plus np - 1 when the pairs
    // all have one handle color (a single of the other color must then be second, below the first
    // pair). No balance term (as6-imb0): the design gathers the targets of the minority color at
    // h_c in column c, and the top two papers already carry both colors.
    // Written without branches (the annealing evaluates it twice per move, on random counts).
    // always_inline: Annealer (AVX2) must not call SSE code.
    __attribute__((always_inline)) static double colcost_of(int nc, int nt, int n1, int p1) {
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        const int base2 = nt * (nc - 1);
        const int minimum2 = nc * (nc - 1) + np * (np - 1) + 2 * correction;
        const double retrieval = (1.0 - kRankPriority) * base2 * 0.5 + kRankPriority * minimum2 * 0.5;
        return retrieval + 100000.0 * int((n1 == 0) | (n1 == nc));
    }
    double colcost(int c) const { return colcost_of(nc[c], nt[c], n1[c], pairOne[c]); }
    // 40 colcost_of in integers (exact; kRankPriority = 17 / 20): 0.15 / 2 * 40 = 3,
    // 0.85 / 2 * 40 = 17, for the annealing
    static_assert(kRankPriority == 0.85);
    __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        const int base2 = nt * (nc - 1);
        const int minimum2 = nc * (nc - 1) + np * (np - 1) + 2 * correction;
        return 3 * base2 + 17 * minimum2 + 4000000 * int((n1 == 0) | (n1 == nc));
    }
    // hcost of x holes of color 0 and y of color 1: hole_table()[x * 257 + y] = kHoleWeight 4 x y / (x + y)
    static const std::array<double, 257 * 257>& hole_table() {
        static const std::array<double, 257 * 257> table = [] {
            std::array<double, 257 * 257> t{};
            for (int x = 0; x <= 256; x++)
                for (int y = 0; y <= 256; y++)
                    if (x + y) t[x * 257 + y] = kHoleWeight * (4.0 * x * y / (x + y));
            return t;
        }();
        return table;
    }
    double hcost(int j) const { return hole_table()[hn[j][0] * 257 + hn[j][1]]; }
    double gc(const Unit& u) const { return u.b < 0 ? 0 : gcost[u.a][u.b] * 2; }
    void update(const Unit& u, int sgn) {
        cur -= cval[u.c];
        nc[u.c] += sgn;
        nt[u.c] += sgn * weight(u);
        n1[u.c] += sgn * color(u, u.c);
        if (u.b >= 0) pairOne[u.c] += sgn * color(u, u.c);
        cur += cval[u.c] = colcost(u.c);
        u64 hs = holes(u);
        for (u64 s = hs; s; s &= s - 1) {
            int j = __builtin_ctzll(s);
            cur -= hcost(j);
            hn[j][hb[u.a] >> j & 1] += sgn;
            if (u.b >= 0) hn[j][hb[u.b] >> j & 1] += sgn;
            cur += hcost(j);
        }
        cur += sgn * gc(u);
    }
    void rebuild() {
        std::fill(nc.begin(), nc.end(), 0);
        std::fill(nt.begin(), nt.end(), 0);
        std::fill(n1.begin(), n1.end(), 0);
        std::fill(pairOne.begin(), pairOne.end(), 0);
        std::fill(hn.begin(), hn.end(), std::array<int, 2>{0, 0});
        cur = 0;
        cval.assign(H, 0.0);
        for (int j = 0; j < H; j++) cur += cval[j] = colcost(j);
        for (const auto& u : unit) update(u, 1);
        for (int x = 0; x < U; x++) {
            owner[unit[x].a] = x;
            if (unit[x].b >= 0) owner[unit[x].b] = x;
        }
    }
    // Units and columns. Pairs: a greedy matching of the compatible pairs by 0.65 handle differences +
    // 2 gcost + 0.04 differences, completed by augmenting paths of length 3 (one pair replaced by
    // two); the rest are singles. Columns: both colors in every column (singles first), then sizes
    // about proportional to c + 1.5 (even), filled from the deepest column, pairs first; leftovers
    // where cheapest. false if impossible (or expired).
    template <class Compatible, class Estimate, class Expired>
    bool initialize(Compatible compatible, Estimate estimate, Expired expired) {
        struct E {
            double w;
            int a, b;
        };
        std::vector<E> edges;
        for (int a = 0; a < 256; a++)
            for (int b = a + 1; b < 256; b++) {
                if ((b & 31) == 0 && expired()) return false;
                if (!compatible(A[a], A[b])) continue;
                ok[a][b] = ok[b][a] = 1;
                partners[a].push_back(b);
                partners[b].push_back(a);
                u64 d = A[a] ^ A[b];
                gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]);
                edges.push_back({0.65 * pc(d >> G) + 2 * gcost[a][b] + 0.04 * pc(d), a, b});
            }
        std::sort(edges.begin(), edges.end(), [](const E& a, const E& b) { return a.w < b.w; });
        std::vector<char> used(256, 0);
        for (const auto& e : edges) {
            if (int(unit.size()) == need) break;
            if (used[e.a] || used[e.b]) continue;
            used[e.a] = used[e.b] = 1;
            unit.push_back({e.a, e.b, -1});
        }
        // Greedy matching can get stuck despite an adequate compatibility
        // graph.  A length-three augmenting path replaces one pair by two.
        auto edgeCost = [&](int a, int b) {
            u64 d = A[a] ^ A[b];
            return 0.65 * pc(d >> G) + 2 * gcost[a][b] + 0.04 * pc(d);
        };
        while (int(unit.size()) < need) {
            double best = 1e100;
            int bx = -1, bu = -1, bv = -1, flip = 0;
            for (int x = 0; x < int(unit.size()); x++)
                for (int f = 0; f < 2; f++) {
                    if (expired()) return false;
                    int a = f ? unit[x].b : unit[x].a, b = f ? unit[x].a : unit[x].b;
                    for (int u : partners[a])
                        if (!used[u])
                            for (int v : partners[b])
                                if (!used[v] && u != v) {
                                    double c = edgeCost(a, u) + edgeCost(b, v) - edgeCost(a, b);
                                    if (c < best) {
                                        best = c;
                                        bx = x;
                                        bu = u;
                                        bv = v;
                                        flip = f;
                                    }
                                }
                }
            if (bx < 0) break;
            int a = flip ? unit[bx].b : unit[bx].a, b = flip ? unit[bx].a : unit[bx].b;
            unit[bx] = {a, bu, -1};
            unit.push_back({b, bv, -1});
            used[bu] = used[bv] = 1;
        }
        if (int(unit.size()) < need) return false;
        for (int a = 0; a < 256; a++)
            if (!used[a]) unit.push_back({a, -1, -1});
        // Reserve both colors of every column using single-target papers first.
        std::vector<int> perm(U);
        std::iota(perm.begin(), perm.end(), 0);
        for (int i = U - 1; i > 0; i--) std::swap(perm[i], perm[rng.below(i + 1)]);
        auto take = [&](int c, int colorWanted, bool pairFirst) {
            for (int pass = 0; pass < 2; pass++)
                for (int x : perm) {
                    auto& u = unit[x];
                    if (u.c >= 0 || (u.b >= 0) != (pairFirst ^ (pass != 0)) || !valid(u, c) ||
                        color(u, c) != colorWanted)
                        continue;
                    u.c = c;
                    nc[c]++;
                    n1[c] += colorWanted;
                    return true;
                }
            return false;
        };
        for (int c = 0; c < H; c++)
            for (int v = 0; v < 2; v++)
                if (!take(c, v, false)) return false;
        std::vector<int> cap(H, 2);
        int tot = H * 2;
        while (tot + 2 <= U) {
            int best = 0;
            double val = 1e100;
            for (int c = 0; c < H; c++) {
                double q = (cap[c] + 1.0) / (c + 1.5);
                if (q < val) val = q, best = c;
            }
            cap[best] += 2;
            tot += 2;
        }
        for (int c = H - 1; c >= 0; c--)
            while (nc[c] < cap[c]) {
                int v = 2 * n1[c] < nc[c] ? 1 : 0;
                if (!take(c, v, true) && !take(c, v ^ 1, true)) break;
            }
        for (auto& u : unit)
            if (u.c < 0) {
                int best = -1;
                double cost = 1e100;
                for (int c = 0; c < H; c++)
                    if (valid(u, c)) {
                        double q = weight(u) * (nc[c] * 0.5 + 0.5 * (H - 1 - c)) + nc[c] * 0.5 +
                                   3 * std::abs(nc[c] + 1 - 2 * (n1[c] + color(u, c)));
                        if (q < cost) cost = q, best = c;
                    }
                if (best < 0) return false;
                u.c = best;
                nc[best]++;
                n1[best] += color(u, best);
            }
        rebuild();
        return true;
    }
    // Annealing of the pairing (exchange a target between two units, mostly towards a compatible
    // partner; pair replaces), the columns (exchange, move one unit, move two units of opposite
    // colors) and the handle order (exchange two handles, 15% of the moves; column swaps with their
    // handle windows), until `seconds` (or fixedIterations);
    // keeps the best state. The moves, the model and the acceptance are those of cmp-speed; the state
    // is kept in a form that evaluates a move quickly (Annealer).
    // The schedule in kAnnealSegments segments, each a new Annealer from the best state so far (run
    // keeps the best state on return), with the temperatures of its slice of the whole schedule.
    static constexpr int kAnnealSegments = 4;
    void anneal(double seconds, int fixedIterations = 0) {
        const auto t0 = std::chrono::steady_clock::now();
        int total = 0;
        for (int s = 0; s < kAnnealSegments; s++) {
            const double used = CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            const double sec = fixedIterations ? 1e9 : std::max(0.0, seconds * (s + 1) / kAnnealSegments - used);
            const int fi = fixedIterations ? fixedIterations / kAnnealSegments : 0;
            const double p0 = double(s) / kAnnealSegments, p1 = double(s + 1) / kAnnealSegments;
            if (H <= 32)
                Annealer<4>(*this).run(sec, fi, p0, p1);
            else
                Annealer<5>(*this).run(sec, fi, p0, p1);
            total += anneal_iters;
        }
        anneal_iters = total;
    }
    static const std::array<double, 16384>& anneal_logs() {  // -log of a uniform (0, 1), quantized
        static const std::array<double, 16384> logs = []() {
            std::array<double, 16384> a{};
            for (int i = 0; i < 16384; i++) a[i] = -std::log((i + 0.5) / 16384);
            return a;
        }();
        return logs;
    }
    // The state of the annealing, NR registers of 8 float lanes covering the handles (H <= 8 NR):
    //   - a move is evaluated without changing the state and applied only if accepted (a rejection
    //     restores nothing);
    //   - per handle j, the hole counts n0[j], n1[j] and q[j] = n0 n1 / max(n0 + n1, 1) as float lanes
    //     (hcost = kHoleWeight 4 q). A move adds per lane its sign times its weight to n0 or n1 (from
    //     the bit masks of the handles, kBitLanes), and its cost change is the sum of the new q minus
    //     the old q, computed for all the handles at once (AVX2, no branches);
    //   - per column c and handle j, the targets / units / pairs of color 1 there and the pairs that
    //     differ there (rows[c].t1 / u1 / p1 / pd, float lanes, updated on acceptance), so that a
    //     handle exchange a <-> b is counted by sums over the columns a..b-1 instead of their units;
    //   - key[x] = column * 2 + color at its handle of unit x (the partner of the two-unit move).
#define ANNEAL_TARGET __attribute__((target("avx2,fma,bmi,bmi2,popcnt")))
    template <int NR>
    struct Annealer {
        static constexpr int L = 8 * NR;
        static constexpr double kHoleScale = 4 * kHoleWeight;
        struct ColRow {
            alignas(32) float t1[L], u1[L], p1[L], pd[L];
        };
        Design& D;
        const int H, U;
        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {};
        std::vector<ColRow> rows;
        std::array<int, 64> cnc{}, cnt{}, cn1{}, cp1{};
        std::array<int, 64> cv{};  // colcost40
        std::vector<int> key;
        double cur = 0, temp = 2.0;
        const double* const logs = anneal_logs().data();

        // Four independent integer lanes use exactly the scalar colcost40 formula. Callers
        // use two lanes; unused lanes cannot affect the result. All possible counts fit int32.
        ANNEAL_TARGET static __m128i colcost_pair(__m128i nc, __m128i nt, __m128i n1, __m128i p1) {
            const __m128i z = _mm_setzero_si128(), one = _mm_set1_epi32(1);
            const __m128i np = _mm_sub_epi32(nt, nc), p0 = _mm_sub_epi32(np, p1);
            const __m128i same = _mm_or_si128(_mm_cmpeq_epi32(p0, z), _mm_cmpeq_epi32(p1, z));
            const __m128i correction = _mm_and_si128(_mm_max_epi32(z, _mm_sub_epi32(np, one)), same);
            const __m128i nm = _mm_sub_epi32(nc, one);
            const __m128i base2 = _mm_mullo_epi32(nt, nm);
            const __m128i minimum2 = _mm_add_epi32(
                _mm_add_epi32(_mm_mullo_epi32(nc, nm), _mm_mullo_epi32(np, _mm_sub_epi32(np, one))),
                _mm_slli_epi32(correction, 1));
            const __m128i retrieval = _mm_add_epi32(
                _mm_add_epi32(base2, _mm_slli_epi32(base2, 1)),
                _mm_add_epi32(minimum2, _mm_slli_epi32(minimum2, 4)));
            const __m128i penalty = _mm_and_si128(_mm_set1_epi32(4000000),
                _mm_or_si128(_mm_cmpeq_epi32(n1, z), _mm_cmpeq_epi32(n1, nc)));
            return _mm_add_epi32(retrieval, penalty);
        }
        static const float* bit_lanes(unsigned v) { return kBitLanes[v].data(); }
        ANNEAL_TARGET static float qf(float a, float b) {  // the same operations as eval_holes per lane
            const float s = a + b;
            return a * b / (s > 1.0f ? s : 1.0f);
        }
        ANNEAL_TARGET static float hsum(__m256 v) {
            __m128 x = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
            x = _mm_add_ps(x, _mm_movehl_ps(x, x));
            x = _mm_add_ss(x, _mm_shuffle_ps(x, x, 1));
            return _mm_cvtss_f32(x);
        }
        // Explicitly unroll these fixed-size loops: GCC -O2 otherwise spills the temporary
        // vector arrays to the stack. Arithmetic order within each lane and hsum stays intact.
        // acc[lane j] += k for every bit j of m
        ANNEAL_TARGET static void add_bits(__m256* acc, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++)
                acc[r] = _mm256_fmadd_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv, acc[r]);
        }
        ANNEAL_TARGET static void add_bits(float* row, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++)
                _mm256_store_ps(row + 8 * r, _mm256_add_ps(_mm256_load_ps(row + 8 * r),
                                                           _mm256_mul_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv)));
        }
        // New counts N0 = n0 + d0, N1 = n1 + d1 and their q; returns the sum of the changes of q.
        ANNEAL_TARGET float eval_holes(const __m256* d0, const __m256* d1, __m256* N0, __m256* N1, __m256* Q) const {
            const __m256 one = _mm256_set1_ps(1.0f);
            __m256 dif[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                N0[r] = _mm256_add_ps(_mm256_load_ps(n0 + 8 * r), d0[r]);
                N1[r] = _mm256_add_ps(_mm256_load_ps(n1 + 8 * r), d1[r]);
                const __m256 s = _mm256_max_ps(_mm256_add_ps(N0[r], N1[r]), one);
                Q[r] = _mm256_div_ps(_mm256_mul_ps(N0[r], N1[r]), s);
                dif[r] = _mm256_sub_ps(Q[r], _mm256_load_ps(hq + 8 * r));
            }
            __m256 acc = _mm256_add_ps(_mm256_add_ps(dif[0], dif[1]), _mm256_add_ps(dif[2], dif[3]));
            if constexpr (NR == 5) acc = _mm256_add_ps(acc, dif[4]);
            static_assert(NR == 4 || NR == 5);
            return hsum(acc);
        }
        ANNEAL_TARGET void commit_holes(const __m256* N0, const __m256* N1, const __m256* Q) {
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                _mm256_store_ps(n0 + 8 * r, N0[r]);
                _mm256_store_ps(n1 + 8 * r, N1[r]);
                _mm256_store_ps(hq + 8 * r, Q[r]);
            }
        }
        // The rows of column u.c: the unit u added (sgn 1) or removed (-1).
        ANNEAL_TARGET void unit_rows(const Unit& u, float sgn) {
            auto& row = rows[u.c];
            const u64 ha = D.hb[u.a];
            add_bits(row.t1, ha, sgn);
            add_bits(row.u1, ha, sgn);
            if (u.b >= 0) {
                add_bits(row.t1, D.hb[u.b], sgn);
                add_bits(row.p1, ha, sgn);
                add_bits(row.pd, ha ^ D.hb[u.b], sgn);
            }
        }
        int unit_key(const Unit& u) const { return u.c * 2 + D.color(u, u.c); }
        bool accept(double d) {
            return d <= 0 || d < temp * logs[D.rng.next() & 16383];
        }

        explicit Annealer(Design& d) : D(d), H(d.H), U(d.U), rows(d.H), key(d.U) {
            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            for (int j = 0; j < H; j++) n0[j] = float(D.hn[j][0]), n1[j] = float(D.hn[j][1]), hq[j] = qf(n0[j], n1[j]);
            for (int c = 0; c < H; c++)
                cnc[c] = D.nc[c], cnt[c] = D.nt[c], cn1[c] = D.n1[c], cp1[c] = D.pairOne[c];
            for (int c = 0; c < H; c++) cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c]);
            for (const auto& u : D.unit) unit_rows(u, 1.0f);
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
            cur = D.cur;
        }

        // Units x, y moved between the columns P = ox.c and Q = nx.c (!= P): x to Q, y to the other
        // column (ny.c != oy.c) or not (ny.c == oy.c; its terms then cancel). Applied if accepted.
        ANNEAL_TARGET void column_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            const int P = ox.c, Q = nx.c;
            // x always moves P -> Q. y either stays, follows x, or moves Q -> P.
            const int sy = ny.c == oy.c ? 0 : (oy.c == P ? -1 : 1);
            const int px = ox.b >= 0, py = oy.b >= 0, wx = 1 + px, wy = 1 + py;
            const int cxP = D.color(ox, P), cxQ = D.color(ox, Q);
            const int cyP = D.color(oy, P), cyQ = D.color(oy, Q);
            const int dn = -1 + sy, dt = -wx + sy * wy;
            int dnc[2] = {dn, -dn}, dnt[2] = {dt, -dt};
            int dn1[2] = {-cxP + sy * cyP, cxQ - sy * cyQ};
            int dp1[2] = {-px * cxP + sy * py * cyP, px * cxQ - sy * py * cyQ};
            const __m128i costs = colcost_pair(
                _mm_setr_epi32(cnc[P]+dnc[0],cnc[Q]+dnc[1],0,0),
                _mm_setr_epi32(cnt[P]+dnt[0],cnt[Q]+dnt[1],0,0),
                _mm_setr_epi32(cn1[P]+dn1[0],cn1[Q]+dn1[1],0,0),
                _mm_setr_epi32(cp1[P]+dp1[0],cp1[Q]+dp1[1],0,0));
            const int cvP = _mm_cvtsi128_si32(costs), cvQ = _mm_extract_epi32(costs,1);
            // The handles between the two columns stop (moving deeper) or start being holes of the
            // unit, except its pair differences (always holes); a pair's targets agree there.
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            const u64 interval = low_bits(P + 1) ^ low_bits(Q + 1);
            const int sign = Q > P ? -1 : 1;
            const u64 hx = D.hb[ox.a], dx = px ? hx ^ D.hb[ox.b] : 0;
            const u64 mx = interval & ~dx;
            add_bits(d1, mx & hx, float(sign * wx));
            add_bits(d0, mx & ~hx, float(sign * wx));
            if (sy) {
                const u64 hy = D.hb[oy.a], dy = py ? hy ^ D.hb[oy.b] : 0;
                const u64 my = interval & ~dy;
                add_bits(d1, my & hy, float(-sy * sign * wy));
                add_bits(d0, my & ~hy, float(-sy * sign * wy));
            }
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = ((cvP - cv[P]) + (cvQ - cv[Q])) * (1.0 / 40) + kHoleScale * dq;
            if (!accept(delta)) return;
            cur += delta;
            commit_holes(N0, N1, Qv);
            cnc[P] += dnc[0], cnt[P] += dnt[0], cn1[P] += dn1[0], cp1[P] += dp1[0], cv[P] = cvP;
            cnc[Q] += dnc[1], cnt[Q] += dnt[1], cn1[Q] += dn1[1], cp1[Q] += dp1[1], cv[Q] = cvQ;
            unit_rows(ox, -1.0f);
            unit_rows(nx, 1.0f);
            D.unit[x] = nx;
            key[x] = unit_key(nx);
            if (ny.c != oy.c) {
                unit_rows(oy, -1.0f);
                unit_rows(ny, 1.0f);
                D.unit[y] = ny;
                key[y] = unit_key(ny);
            }
        }
        // An exchange of targets between units x and y (both keep their columns). Applied if accepted.
        ANNEAL_TARGET void target_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            const int cx = ox.c, cy = oy.c, iy = cx == cy ? 0 : 1;
            int dnt[2] = {0, 0}, dn1[2] = {0, 0}, dp1[2] = {0, 0};  // [0]: column of x, [1]: of y (if other)
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 4")
            for (const auto& [u, i, sgn] : {std::tuple<const Unit&, int, int>{ox, 0, -1}, std::tuple<const Unit&, int, int>{nx, 0, 1},
                                            std::tuple<const Unit&, int, int>{oy, iy, -1}, std::tuple<const Unit&, int, int>{ny, iy, 1}}) {
                const int cl = D.color(u, u.c);
                dnt[i] += sgn * D.weight(u), dn1[i] += sgn * cl, dp1[i] += sgn * (u.b >= 0) * cl;
                const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2")
                for (int t : {u.a, u.b}) {
                    if (t < 0) continue;
                    add_bits(d1, hs & D.hb[t], float(sgn));
                    add_bits(d0, hs & ~D.hb[t], float(sgn));
                }
            }
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[cx],cnc[cy],0,0),
                _mm_setr_epi32(cnt[cx]+dnt[0],cnt[cy]+dnt[1],0,0),
                _mm_setr_epi32(cn1[cx]+dn1[0],cn1[cy]+dn1[1],0,0),
                _mm_setr_epi32(cp1[cx]+dp1[0],cp1[cy]+dp1[1],0,0));
            const int cvx = _mm_cvtsi128_si32(costs), cvy = iy ? _mm_extract_epi32(costs,1) : 0;
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double dcol = ((cvx - cv[cx]) + (iy ? cvy - cv[cy] : 0)) * (1.0 / 40);
            const double delta = dcol + kHoleScale * dq + ((D.gc(nx) + D.gc(ny)) - (D.gc(ox) + D.gc(oy)));
            if (!accept(delta)) return;
            cur += delta;
            commit_holes(N0, N1, Qv);
            cnt[cx] += dnt[0], cn1[cx] += dn1[0], cp1[cx] += dp1[0], cv[cx] = cvx;
            if (iy) cnt[cy] += dnt[1], cn1[cy] += dn1[1], cp1[cy] += dp1[1], cv[cy] = cvy;
            unit_rows(ox, -1.0f);
            unit_rows(oy, -1.0f);
            unit_rows(nx, 1.0f);
            unit_rows(ny, 1.0f);
            D.unit[x] = nx;
            D.unit[y] = ny;
            key[x] = unit_key(nx);
            key[y] = unit_key(ny);
            D.owner[nx.a] = x;
            if (nx.b >= 0) D.owner[nx.b] = x;
            D.owner[ny.a] = y;
            if (ny.b >= 0) D.owner[ny.b] = y;
        }
        ANNEAL_TARGET void mutate(int x, int y, const Unit& nx, const Unit& ny) {
            if (D.invalid_bit(nx, nx.c) | D.invalid_bit(ny, ny.c)) return;  // (one branch for both)
            const Unit ox = D.unit[x], oy = D.unit[y];
            if (nx.a == ox.a && nx.b == ox.b && ny.a == oy.a && ny.b == oy.b) {  // only the columns change
                column_move(x, y, ox, oy, nx, ny);  // (the pairs are compatible)
            } else {
                if ((nx.b >= 0 && !D.ok[nx.a][nx.b]) || (ny.b >= 0 && !D.ok[ny.a][ny.b])) return;
                target_move(x, y, ox, oy, nx, ny);
            }
        }
        // Exchange the handles at positions a < b. The units of the columns < a and >= b see h_a and
        // h_b exchanged, so the new hole counts are the old ones of the other handle, corrected for
        // the targets of the columns a..b-1 (b deeper, a only a pair difference: one hole of each
        // color); the colors at the handles of the columns a and b change. Applied if accepted.
        ANNEAL_TARGET void handle_swap(int a, int b) {
            if (rows[a].pd[b] != 0 || rows[b].pd[a] != 0) return;  // a pair must agree at the new handle of its column
            const int n1a = int(rows[a].u1[b]), n1b = int(rows[b].u1[a]), pa = int(rows[a].p1[b]), pb = int(rows[b].p1[a]);
            int tot = 0;
            float mb_old1 = 0, mb_new1 = 0, ma_old = 0, ma_new = 0;  // (small integers: exact)
            for (int c = a; c < b; c++) {
                tot += cnt[c];
                mb_old1 += rows[c].t1[b];
                mb_new1 += rows[c].t1[a];
                ma_old += rows[c].pd[a];
                ma_new += rows[c].pd[b];
            }
            const float na0 = n0[b] - (float(tot) - mb_old1) + ma_new, na1 = n1[b] - mb_old1 + ma_new;
            const float nb0 = n0[a] - ma_old + (float(tot) - mb_new1), nb1 = n1[a] - ma_old + mb_new1;
            const float qa = qf(na0, na1), qb = qf(nb0, nb1);
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[a],cnc[b],0,0),
                _mm_setr_epi32(cnt[a],cnt[b],0,0),_mm_setr_epi32(n1a,n1b,0,0),_mm_setr_epi32(pa,pb,0,0));
            const int cva = _mm_cvtsi128_si32(costs), cvb = _mm_extract_epi32(costs,1);
            const double delta = kHoleScale * ((qa - hq[a]) + (qb - hq[b])) + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);
            if (!accept(delta)) return;
            cur += delta;
            std::swap(D.handle[a], D.handle[b]);
            for (auto& h : D.hb) {
                const u64 t = ((h >> a) ^ (h >> b)) & 1;
                h ^= (t << a) | (t << b);
            }
            for (auto& row : rows) {
                std::swap(row.t1[a], row.t1[b]);
                std::swap(row.u1[a], row.u1[b]);
                std::swap(row.p1[a], row.p1[b]);
                std::swap(row.pd[a], row.pd[b]);
            }
            n0[a] = na0, n1[a] = na1, hq[a] = qa, n0[b] = nb0, n1[b] = nb1, hq[b] = qb;
            cn1[a] = n1a, cn1[b] = n1b, cp1[a] = pa, cp1[b] = pb, cv[a] = cva, cv[b] = cvb;
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
        }
        // Exchange the columns at positions a < b together with their handle windows (the column
        // swap of solutions/gpt6pro-08-01-colswap and gpt6pro-06-02-regroup). Every unit keeps its
        // own handle window, so the validity and every column cost stay; only hole counts change.
        // With the new positions (h_a's window moves to position b, h_b's to a):
        //   - position a (window of old h_b): the old counts of h_b, less the holes there of the
        //     columns a..b-1 (old column a is now deeper, the columns a+1..b-1 are above it);
        //   - position b (window of old h_a): the old counts of h_a, plus the holes there of the
        //     columns a+1..b (old column b is now at position a, the columns a+1..b-1 are above it);
        //   - positions a < j < b: old column a stops being a hole there, old column b starts;
        // always except the pair differences (holes anyway). Without its pair differences, a column c
        // has t1 - pd holes of color 1 and nt - t1 - pd of color 0 at a handle (a differing pair counts
        // one target of each color in t1). Applied if accepted.
        ANNEAL_TARGET void column_swap(int a, int b) {
            ++D.colswap_tried;
            float T = 0, X1 = 0, Xd = 0;  // columns a..b-1 at h_b (small integers: exact)
            for (int c = a; c < b; c++) T += float(cnt[c]), X1 += rows[c].t1[b], Xd += rows[c].pd[b];
            float T2 = 0, Y1 = 0, Yd = 0;  // columns a+1..b at h_a
            for (int c = a + 1; c <= b; c++) T2 += float(cnt[c]), Y1 += rows[c].t1[a], Yd += rows[c].pd[a];
            __m256 d0[NR], d1[NR];
            if (b - a > 1) {
                const u64 mid = low_bits(b) & ~low_bits(a + 1);
                const __m256 ta = _mm256_set1_ps(float(cnt[a])), tb = _mm256_set1_ps(float(cnt[b]));
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                    const __m256 m = _mm256_load_ps(bit_lanes((mid >> (8 * r)) & 255));
                    const __m256 a1 = _mm256_sub_ps(_mm256_load_ps(rows[a].t1 + 8 * r), _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b1 = _mm256_sub_ps(_mm256_load_ps(rows[b].t1 + 8 * r), _mm256_load_ps(rows[b].pd + 8 * r));
                    const __m256 a0 = _mm256_sub_ps(_mm256_sub_ps(ta, _mm256_load_ps(rows[a].t1 + 8 * r)), _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b0 = _mm256_sub_ps(_mm256_sub_ps(tb, _mm256_load_ps(rows[b].t1 + 8 * r)), _mm256_load_ps(rows[b].pd + 8 * r));
                    d1[r] = _mm256_mul_ps(m, _mm256_sub_ps(b1, a1));
                    d0[r] = _mm256_mul_ps(m, _mm256_sub_ps(b0, a0));
                }
            } else {
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            }
            const u64 ba = u64(1) << a, bb = u64(1) << b;
            add_bits(d0, ba, (n0[b] - n0[a]) - (T - X1 - Xd));
            add_bits(d1, ba, (n1[b] - n1[a]) - (X1 - Xd));
            add_bits(d0, bb, (n0[a] - n0[b]) + (T2 - Y1 - Yd));
            add_bits(d1, bb, (n1[a] - n1[b]) + (Y1 - Yd));
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = kHoleScale * dq;
            if (!accept(delta)) return;
            ++D.colswap_accepted;
            cur += delta;
            commit_holes(N0, N1, Qv);
            std::swap(cnc[a], cnc[b]), std::swap(cnt[a], cnt[b]), std::swap(cn1[a], cn1[b]);
            std::swap(cp1[a], cp1[b]), std::swap(cv[a], cv[b]);
            std::swap(D.handle[a], D.handle[b]);
            // bits a and b of every target exchanged, without branches (vectorized; a branch per
            // target would be mispredicted half of the time)
            for (auto& h : D.hb) {
                const u64 t = ((h >> a) ^ (h >> b)) & 1;
                h ^= (t << a) | (t << b);
            }
            for (auto& row : rows) {
                std::swap(row.t1[a], row.t1[b]);
                std::swap(row.u1[a], row.u1[b]);
                std::swap(row.p1[a], row.p1[b]);
                std::swap(row.pd[a], row.pd[b]);
            }
            std::swap(rows[a], rows[b]);
            for (int x = 0; x < U; x++) {
                auto& u = D.unit[x];
                if (u.c == a || u.c == b) {
                    u.c ^= a ^ b;
                    key[x] = unit_key(u);
                }
            }
        }
        // Pair replace (solutions/gpt6pro-07-02-replace; the pair shift of gpt6pro-06-02-regroup is
        // one of its outcomes): units xs[0..k-1] become nu[0..k-1] (any targets and columns). The
        // column counts are summed per distinct column, the hole counts per target as in
        // target_move. Applied if accepted.
        ANNEAL_TARGET void multi_move(int k, const int* xs, const Unit* nu) {
            int cols[6], dnc[6], dnt[6], dn1[6], dp1[6], ncols = 0;
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 3")
            for (int i = 0; i < k; i++)
                _Pragma("GCC unroll 2")
                for (int sgn = -1; sgn <= 1; sgn += 2) {
                    const Unit& u = sgn < 0 ? D.unit[xs[i]] : nu[i];
                    int ci = 0;
                    while (ci < ncols && cols[ci] != u.c) ci++;
                    if (ci == ncols) cols[ncols] = u.c, dnc[ncols] = dnt[ncols] = dn1[ncols] = dp1[ncols] = 0, ncols++;
                    const int cl = D.color(u, u.c);
                    dnc[ci] += sgn, dnt[ci] += sgn * D.weight(u), dn1[ci] += sgn * cl, dp1[ci] += sgn * (u.b >= 0) * cl;
                    const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2")
                for (int t : {u.a, u.b}) {
                        if (t < 0) continue;
                        add_bits(d1, hs & D.hb[t], float(sgn));
                        add_bits(d0, hs & ~D.hb[t], float(sgn));
                    }
                }
            int ncv[6], dcol = 0;
            for (int i = 0; i < ncols; i++) {
                const int c = cols[i];
                ncv[i] = colcost40(cnc[c] + dnc[i], cnt[c] + dnt[i], cn1[c] + dn1[i], cp1[c] + dp1[i]);
                dcol += ncv[i] - cv[c];
            }
            double dg = 0;
            for (int i = 0; i < k; i++) dg += D.gc(nu[i]) - D.gc(D.unit[xs[i]]);
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = dcol * (1.0 / 40) + kHoleScale * dq + dg;
            if (!accept(delta)) return;
            ++D.replace_accepted;
            cur += delta;
            commit_holes(N0, N1, Qv);
            for (int i = 0; i < ncols; i++) {
                const int c = cols[i];
                cnc[c] += dnc[i], cnt[c] += dnt[i], cn1[c] += dn1[i], cp1[c] += dp1[i], cv[c] = ncv[i];
            }
            for (int i = 0; i < k; i++) unit_rows(D.unit[xs[i]], -1.0f);
            for (int i = 0; i < k; i++) {
                unit_rows(nu[i], 1.0f);
                D.unit[xs[i]] = nu[i];
                key[xs[i]] = unit_key(nu[i]);
                D.owner[nu[i].a] = xs[i];
                if (nu[i].b >= 0) D.owner[nu[i].b] = xs[i];
            }
        }

        // p0, p1: the slice of the whole schedule (progress) that this run covers
        ANNEAL_TARGET void run(double seconds, int fixedIterations, double p0 = 0, double p1 = 1) {
            auto start = std::chrono::steady_clock::now();
            double progress = 0;
            // Handle exchanges, column swaps (distances 1..kColSwapDist) and pair replaces, per mille
            // of the moves (then target exchanges until 430, column exchanges until 750, unit moves
            // until 900, two-unit moves).
            constexpr int kHandleSwapRate = 150, kColSwapRate = 20, kColSwapDist = 4, kReplaceRate = 100;
            constexpr int kColSwapEnd = kHandleSwapRate + kColSwapRate, kReplaceEnd = kColSwapEnd + kReplaceRate;
            auto& rng = D.rng;
            auto& unit = D.unit;
            // The units that are pairs / singles: no move changes it (a pair replace keeps the pair
            // in the unit that was a pair; the units exchange columns instead).
            std::vector<int> pairUnits, singleUnits;
            for (int x = 0; x < U; x++) (unit[x].b >= 0 ? pairUnits : singleUnits).push_back(x);
            std::vector<Unit> best = unit;
            std::vector<int> bestHandle = D.handle;
            double bestCost = cur;
            for (int it = 0;; it++) {
                D.anneal_iters = it;
                if ((it & 255) == 0) {
                    double elapsed =
                        CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                    progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                    if (progress >= 1 || elapsed >= seconds) break;
                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);
                }
                int type = rng.below(1000);
                if (type < kHandleSwapRate) {
                    int a = rng.below(H), b = rng.below(H);
                    if (a == b) continue;
                    if (a > b) std::swap(a, b);
                    handle_swap(a, b);
                } else if (type < kColSwapEnd) {
                    const int d = 1 + rng.below(std::min(kColSwapDist, H - 1));
                    const int a = rng.below(H - d);
                    column_swap(a, a + d);
                } else if (type < kReplaceEnd) {
                    // The pair x = (a, b), a single y = c and a single z = d compatible with c become
                    // the pair (c, d) in x and the singles a, b in y, z (in random order); the pair
                    // takes a random one of the three columns where it is valid (the other two units
                    // take the other two columns).
                    if (pairUnits.empty() || singleUnits.size() < 2) continue;
                    const int x = pairUnits[rng.below(pairUnits.size())];
                    const int y = singleUnits[rng.below(singleUnits.size())];
                    const auto& ps = D.partners[unit[y].a];
                    if (ps.empty()) continue;
                    int z = -1;
                    for (int t = 0; t < 4; t++) {
                        const int cand = D.owner[ps[rng.below(ps.size())]];
                        if (cand != y && unit[cand].b < 0) {
                            z = cand;
                            break;
                        }
                    }
                    if (z < 0) continue;
                    const Unit ox = unit[x], oy = unit[y], oz = unit[z];
                    Unit nu[3] = {{oy.a, oz.a, ox.c}, {ox.a, -1, oy.c}, {ox.b, -1, oz.c}};
                    if (rng.below(2)) std::swap(nu[1].a, nu[2].a);
                    int choice[3], nch = 0;
                    for (int i = 0; i < 3; i++)
                        if (!D.invalid_bit(nu[0], nu[i].c)) choice[nch++] = i;
                    if (!nch) continue;
                    const int ch = choice[rng.below(nch)];
                    if (ch) std::swap(nu[0].c, nu[ch].c);
                    ++D.replace_tried;
                    const int xs[3] = {x, y, z};
                    multi_move(3, xs, nu);
                } else {
                    int x = rng.below(U), y = rng.below(U);
                    if (x == y) continue;
                    Unit nx = unit[x], ny = unit[y];
                    if (type < 430) {
                        if (nx.b < 0) {
                            std::swap(x, y);
                            nx = unit[x];
                            ny = unit[y];
                            if (nx.b < 0) continue;
                        }
                        int ix = rng.below(2), iy = ny.b < 0 ? 0 : rng.below(2);
                        if (type < 380) {
                            int fixed = ix == 0 ? nx.b : nx.a;
                            const auto& p = D.partners[fixed];
                            if (p.empty()) continue;
                            int newTarget = p[rng.below(p.size())];
                            y = D.owner[newTarget];
                            if (x == y) continue;
                            ny = unit[y];
                            iy = ny.a == newTarget ? 0 : 1;
                        }
                        int& a = ix == 0 ? nx.a : nx.b;
                        int& b = iy == 0 ? ny.a : ny.b;
                        std::swap(a, b);
                    } else if (type < 750) {
                        if (nx.c == ny.c) continue;
                        std::swap(nx.c, ny.c);
                    } else if (type < 900) {
                        if (nx.c == ny.c || cnc[nx.c] <= 2) continue;
                        nx.c = ny.c;
                    } else {
                        int c = nx.c, d = ny.c;
                        if (c == d || cnc[c] <= 2) continue;
                        // a unit of column c with the other color at h_c (x itself never matches)
                        const int want = 2 * c + 1 - D.color(nx, c);
                        int z = -1;
                        for (int t = 0; t < 16; t++) {
                            int j = rng.below(U);
                            if (key[j] == want) {
                                z = j;
                                break;
                            }
                        }
                        if (z < 0) continue;
                        y = z;
                        ny = unit[y];
                        nx.c = ny.c = d;
                    }
                    mutate(x, y, nx, ny);
                }
                if (cur < bestCost - 1e-7) {
                    bestCost = cur;
                    best = unit;
                    bestHandle = D.handle;
                }
            }
            unit = best;
            D.handle = bestHandle;
            for (int i = 0; i < 256; i++) {
                D.hb[i] = 0;
                for (int j = 0; j < H; j++) D.hb[i] |= ((D.A[i] >> D.handle[j]) & 1) << j;
            }
            D.rebuild();
        }
    };
#undef ANNEAL_TARGET
    // Persistence-weighted handle holes of a target (colors tb at the handles, column l) that the
    // paper of a unit (colors yb, pair differences dy) of column c > l would cover as a filler, at
    // the level just past its deepest mismatch with the target (h_c excluded), minus kT, at least 0.
    // q[j] = sum over the handles m < j of 2 (1 - p_m(color of the target at h_m)): the fixes a
    // covered hole saves relative to an unbiased handle. (solutions/clean-base)
    static double filler_gain(u64 tb, int l, u64 yb, u64 dy, int c, const double* q) {
        constexpr int kT = 3;
        u64 range = low_bits(c + 1) & ~dy & ~low_bits(l + 1);
        u64 mis = (yb ^ tb) & range;
        if (mis >> c & 1) return 0.0;
        int lvl = mis ? 64 - __builtin_clzll(mis) : 0;
        u64 cov = range & low_bits(c) & ~low_bits(lvl);
        if (!cov) return 0.0;
        int lo = __builtin_ctzll(cov);
        double g = q[c] - q[lo];
        for (u64 d = dy & low_bits(c) & ~low_bits(lo); d; d &= d - 1) {
            int m = __builtin_ctzll(d);
            g -= q[m + 1] - q[m];
        }
        return std::max(0.0, g - kT);
    }
    // Hill climbing after the annealing (solutions/clean-base filler_climb, pool-climb): exchanges
    // two units of the same kind between two columns, with the same colors at both handles (the
    // column costs and the generic costs do not change), when the model cost minus kW times the
    // filler proxy decreases:
    //   proxy(t) = sum over the columns c deeper than t's of the mean over the units y of c of
    //              filler_gain(t, paper of y).
    // Incremental: a target outside x and y only sees the sums of the columns a and b change.
    void filler_climb(double seconds, int fixedIterations = 0) {
        constexpr double kW = 0.3;
        auto start = std::chrono::steady_clock::now();
        std::vector<u64> diffb(U, 0);
        for (int x = 0; x < U; x++)
            if (unit[x].b >= 0) diffb[x] = hb[unit[x].a] ^ hb[unit[x].b];
        std::vector<std::vector<double>> pq(256, std::vector<double>(H + 1, 0.0));
        for (int t = 0; t < 256; t++)
            for (int m = 0; m < H; m++) {
                int n = hn[m][0] + hn[m][1];
                double p1 = n ? double(hn[m][1]) / n : 0.5, pc = (hb[t] >> m & 1) ? p1 : 1 - p1;
                pq[t][m + 1] = pq[t][m] + 2 * (1 - pc);
            }
        std::vector<std::vector<int>> colm(H);
        for (int x = 0; x < U; x++) colm[unit[x].c].push_back(x);
        auto tcol = [&](int t) { return unit[owner[t]].c; };
        auto gval = [&](int t, int l, int y, int c) {
            return filler_gain(hb[t], l, hb[unit[y].a], diffb[y], c, pq[t].data());
        };
        std::vector<std::vector<double>> colsum(256, std::vector<double>(H, 0.0));
        auto recompute = [&](int t) {
            int l = tcol(t);
            for (int c = 0; c < H; c++) {
                colsum[t][c] = 0;
                if (c <= l) continue;
                for (int y : colm[c]) colsum[t][c] += gval(t, l, y, c);
            }
        };
        for (int t = 0; t < 256; t++) recompute(t);
        auto proxy = [&](int t) {
            int l = tcol(t);
            double s = 0;
            for (int c = l + 1; c < H; c++)
                if (!colm[c].empty()) s += colsum[t][c] / colm[c].size();
            return s;
        };
        proxy_before = 0;
        for (int t = 0; t < 256; t++) proxy_before += proxy(t);
        std::vector<int> others, moved;
        std::vector<std::array<double, 2>> dlt;
        std::vector<std::vector<double>> saved;
        for (int it = 0;; it++) {
            if (fixedIterations > 0
                    ? it >= fixedIterations
                    : ((it & 63) == 0 &&
                       CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() >=
                           seconds))
                break;
            climb_iters = it + 1;
            int x = rng.below(U), y = rng.below(U);
            int a = unit[x].c, b = unit[y].c;
            if (a == b || (unit[x].b >= 0) != (unit[y].b >= 0)) continue;
            Unit nx = unit[x], ny = unit[y];
            nx.c = b;
            ny.c = a;
            if (!valid(nx, b) || !valid(ny, a)) continue;
            if (color(nx, b) != color(unit[y], b) || color(ny, a) != color(unit[x], a)) continue;
            double old = cur;
            Unit ox = unit[x], oy = unit[y];
            update(ox, -1);
            update(oy, -1);
            update(nx, 1);
            update(ny, 1);
            double dmodel = cur - old;
            const double na = colm[a].size(), nb = colm[b].size();
            const int hi = std::max(a, b);
            double dproxy = 0;
            others.clear();
            dlt.clear();
            for (int t = 0; t < 256; t++) {
                int o = owner[t];
                if (o == x || o == y) continue;
                int l = tcol(t);
                if (l >= hi) continue;
                double da = 0, db = 0;
                if (a > l) da = gval(t, l, y, a) - gval(t, l, x, a);
                if (b > l) db = gval(t, l, x, b) - gval(t, l, y, b);
                if (da || db) {
                    others.push_back(t);
                    dlt.push_back({da, db});
                    dproxy += da / na + db / nb;
                }
            }
            moved.clear();
            for (int t : {ox.a, ox.b, oy.a, oy.b})
                if (t >= 0) moved.push_back(t);
            saved.resize(moved.size());
            for (size_t i = 0; i < moved.size(); i++) {
                dproxy -= proxy(moved[i]);
                saved[i] = colsum[moved[i]];
            }
            auto apply = [&](int cx, int cy) {
                auto& ma = colm[unit[x].c];
                ma.erase(std::find(ma.begin(), ma.end(), x));
                auto& mb = colm[unit[y].c];
                mb.erase(std::find(mb.begin(), mb.end(), y));
                unit[x].c = cx;
                unit[y].c = cy;
                colm[cx].push_back(x);
                colm[cy].push_back(y);
            };
            apply(b, a);
            for (int t : moved) {
                recompute(t);
                dproxy += proxy(t);
            }
            if (dmodel - kW * dproxy < -1e-9) {
                climb_accepted++;
                for (size_t i = 0; i < others.size(); i++) {
                    colsum[others[i]][a] += dlt[i][0];
                    colsum[others[i]][b] += dlt[i][1];
                }
            } else {
                apply(a, b);
                for (size_t i = 0; i < moved.size(); i++) colsum[moved[i]] = saved[i];
                update(nx, -1);
                update(ny, -1);
                update(ox, 1);
                update(oy, 1);
                cur = old;
            }
        }
        proxy_after = 0;
        for (int t = 0; t < 256; t++) proxy_after += proxy(t);
        rebuild();
    }
};

struct Paper {
    u64 opaque = 0, black = 0;
};

// Helpers inside the generic layer (from solutions/gpt6pro-08-01-colswap): a dedicated paper x of
// another column placed between the generic sheets shows its colors on the generic windows that the
// sheets above it leave as holes, hides the sheets below it there, and also shows on the handle holes
// of the requested paper D. The 720 orders s of the 6 generic sheets (states) and their distances are
// those of the Comparator (the bottom sheet of the layer never moves). For a target u, helpers[u]
// lists the papers x (not of D's column, the
// same colors as A_u on their opaque handle holes of D, opaque on some generic hole of D) with the
// goals (s, t) such that order s with x inserted under the t upper sheets shows A_u on D's generic
// holes (the deepest t per s).
struct Interleave {
    static constexpr int GM = 6;
    struct Goal {
        uint16_t state;
        uint8_t depth;
    };
    struct Helper {
        int paper;
        std::vector<Goal> goals;
    };
    struct Pick {
        int paper, goal, depth, distance;
    };
    const Comparator* comp = nullptr;  // the orders of the generic sheets and their distances
    std::vector<std::vector<Helper>> helpers;
    std::vector<u64> display;                     // generic display of order s
    std::vector<std::array<u64, GM + 1>> prefix;  // windows covered by the t upper sheets of s
    bool ready = false;
    long long helper_papers = 0;
    // Builds the tables (comparator c with its tables built); stops (ready stays false) after the
    // scaled time `limit`.
    void init(const Comparator& c, const std::vector<Paper>& paper, const std::vector<u64>& A,
              const std::vector<int>& ded, const std::vector<int>& col_of, u64 gmask, u64 hmask, double limit) {
        comp = &c;
        const int NS = c.perms.size();
        display.assign(NS, 0);
        prefix.assign(NS, {});
        for (int s = 0; s < NS; s++) {
            u64 cov = 0, b = 0;
            for (int j = 0; j < GM; j++) {
                const int k = c.perms[s][j];
                b |= paper[k].black & gmask & ~cov;
                cov |= paper[k].opaque & gmask;
                prefix[s][j + 1] = cov;
            }
            display[s] = b;
        }
        helpers.assign(A.size(), {});
        for (int u = 0; u < (int)A.size(); u++) {
            if (ded[u] < 0) continue;
            const u64 holes = ~paper[ded[u]].opaque, gh = holes & gmask, hh = holes & hmask;
            if (!gh) continue;
            for (int x = GM; x < (int)paper.size(); x++) {
                if ((x & 15) == 0 && elapsed_sec() > limit) return;
                if (x == ded[u] || col_of[x] == col_of[ded[u]]) continue;
                const auto& pp = paper[x];
                if ((pp.black ^ A[u]) & pp.opaque & hh) continue;
                if (!(pp.opaque & gh)) continue;
                Helper h{x, {}};
                for (int s = 0; s < NS; s++)
                    for (int t = GM; t >= 0; t--) {
                        const u64 y = (display[s] & (prefix[s][t] | ~pp.opaque)) | (pp.black & ~prefix[s][t]);
                        if (!((y ^ A[u]) & gh)) {
                            h.goals.push_back({(uint16_t)s, (uint8_t)t});
                            break;
                        }
                    }
                if (!h.goals.empty()) helper_papers++, helpers[u].push_back(std::move(h));
            }
        }
        ready = true;
    }
    int state(const std::vector<int>& order) const {  // the order of the generic sheets in the stack
        std::vector<int> p;
        for (int k : order)
            if (k < GM) p.push_back(k);
        return comp->order_index(p);
    }
    Pick best(int s, const Helper& h) const {  // the nearest goal (deeper on ties)
        Pick b{h.paper, -1, 0, 255};
        for (auto g : h.goals) {
            const int d = comp->distance(s, g.state);
            if (d < b.distance || (d == b.distance && g.depth > b.depth)) b = {h.paper, g.state, g.depth, d};
        }
        return b;
    }
};

// The papers and the request processing (clean-base's plan search with the generic layer replaced by
// the comparator and the cyclic columns replaced by adaptive_insert). The generic sheets are papers
// 0..M-1.
struct Solver {
    int M = 8, G = 40, H = 23;
    Comparator comparator;
    std::vector<u64> A;
    std::vector<int> handle, hidx;  // window of h_j; handle index of each window (-1: generic)
    u64 gmask = 0, hmask = 0;       // generic windows, handle windows
    std::vector<Paper> paper;
    std::vector<u64> h_opq, h_blk;  // per paper: opaque / black handles, by handle index
    std::vector<int> col_of, ded;   // column of each dedicated paper (-1: generic); paper of each target
    // as6-imb0gb: the index of the deepest generic sheet. Papers above it are in or above the generic
    // layer (gen_harm, move_to_level). clean-base used its base paper F (generic sheet 0) for this, but
    // in the comparator sheet 0 may lie anywhere in the layer, and set_generic needs the six sheets
    // together: a paper left between them makes every plan ordering the sheets invalid.
    int generic_bottom() const {
        int b = -1;
        for (int i = 0; i < int(order.size()); i++)
            if (order[i] < M) b = i;
        return b;
    }

    // State of the stack.
    std::vector<int> order;  // top first
    int top_d = -1;          // dedicated paper lifted to the top, -1 if none
    // Fillers: column papers out of their column, showing on the handles h_lvl..h_hi (hi = their
    // column).
    struct Filler {
        int paper;
        int lvl = 0, hi = 0;
    };
    std::vector<Filler> fillers;
    std::vector<std::pair<int, int>> ops;  // moves (paper, depth) of the plan being simulated
    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    u64 handle_bits(u64 windows) const {  // the window set by handle index (bit j = window h_j)
        u64 r = 0;
        for (int j = 0; j < H; j++) r |= (windows >> handle[j] & 1) << j;
        return r;
    }

    // Orders the generic sheets (contiguous in the stack) so that the generic holes `holes` of the
    // paper of u show A_u (Comparator::plan).
    void set_generic(int u, u64 holes) {
        holes &= gmask;
        if (!holes) return;
        int offset = -1;
        for (int i = 0; i < K; i++)
            if (order[i] < M) {
                offset = i;
                break;
            }
        if (offset < 0 || offset + M > K) {
            invalid = true;
            return;
        }
        std::vector<int> local;
        for (int i = 0; i < M; i++) {
            int k = order[offset + i];
            if (k < 0 || k >= M) {
                invalid = true;
                return;
            }
            local.push_back(k);
        }
        std::vector<std::pair<int, int>> path;
        if (!future.empty() && holes == (gmask & ~paper[ded[u]].opaque) && !sat[u].empty()) {
            // the satisfying order of least moves, ties broken by the expected moves of the next request
            const int s0 = comparator.order_index(local);
            int best = -1, bd = 1 << 30;
            double bv = 1e18;
            for (int t : sat[u]) {
                const int dd = comparator.distance(s0, t);
                if (dd < bd || (dd == bd && future[t] < bv)) bd = dd, bv = future[t], best = t;
            }
            path = comparator.path(s0, best);
        } else
            path = comparator.plan(local, A[u], holes);
        for (auto [k, d] : path) {
            if (k < 0 || k >= M || d < 0 || d >= M) {
                invalid = true;
                return;
            }
            move(k, offset + d);
            if (invalid) return;
        }
    }

    // Generic look-ahead (from the [ChatGPT] report of hitonanode/ahc074 PR 49): sat[u] lists the
    // orders of the generic sheets that show A_u on the generic holes of its paper, and future[s] is
    // the mean over the targets with generic holes of the least moves from order s to one of theirs
    // (the generic moves of the next such request; the requests in between leave the layer as it is).
    // set_generic goes to a satisfying order of least moves, ties broken by future (init_lookahead;
    // without it, Comparator::plan).
    std::vector<std::vector<int>> sat;
    std::vector<double> future;
    void init_lookahead() {
        const int n = comparator.perms.size();
        sat.assign(P, {});
        future.assign(n, 0.0);
        int cnt = 0;
        for (int u = 0; u < P; u++) {
            const u64 gh = gmask & ~paper[ded[u]].opaque;
            if (!gh) continue;
            sat[u] = comparator.satisfying(A[u], gh);
            if (sat[u].empty()) continue;
            cnt++;
            for (int s = 0; s < n; s++) {
                int m = 255;
                for (int t : sat[u])
                    if ((m = std::min(m, comparator.distance(s, t))) == 0) break;
                future[s] += m;
            }
        }
        if (cnt)
            for (auto& f : future) f /= cnt;
    }

    // Adaptive columns: a paper moved out of the way (dig) or back into its column (return_paper)
    // goes to the depth of least expected future cost: weighted depths (a pair's paper is asked twice
    // as often) / P + for each handle color the depth of the first paper of that color times the
    // share of the requests with a hole of that color at the handle (adaptive_holes); a dig never
    // inserts above its barrier (the paper being dug for), so the current dig is not lengthened.
    int adaptive_request = -1;
    bool adaptive_initialized = false;
    std::vector<double> adaptive_weights;
    std::vector<std::array<double, 2>> adaptive_holes;
    static constexpr double kTopPenalty = 0.35, kEndWeight = 1.0;
    bool fast_mode = false;
    long long fast_requests = 0, plan_failures = 0;
    void init_adaptive() {  // (once)
        if (adaptive_initialized) return;
        adaptive_initialized = true;
        adaptive_weights.assign(K, 0.0);
        adaptive_holes.assign(H, {0.0, 0.0});
        for (int u = 0; u < P; u++) {
            int d = ded[u];
            if (d < 0) continue;
            adaptive_weights[d] += 1.0;
            for (int c = 0; c < H; c++)
                if (!(paper[d].opaque >> handle[c] & 1)) adaptive_holes[c][A[u] >> handle[c] & 1] += 1.0 / P;
        }
    }
    // Expected cost of the next request from the stack left (weighted depths and handle colors).
    double adaptive_next_cost() const {
        std::vector<int> rank(H, 0);
        std::vector<std::array<int, 2>> first(H);
        std::vector<std::array<bool, 2>> available(H, {false, false});
        for (auto& f : first) f = {-1, -1};
        double cost = 0;
        for (int k : order) {
            int c = col_of[k];
            if (c < 0) continue;
            int color = paper[k].black >> handle[c] & 1;
            if (k == top_d || is_filler(k)) {
                available[c][color] = true;
                continue;
            }
            if (first[c][color] < 0) first[c][color] = rank[c];
            cost += adaptive_weights[k] * rank[c] / P;
            rank[c]++;
        }
        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[c][color] ? 0 : first[c][color];
                if (fixes < 0) fixes = rank[c];
                cost += adaptive_holes[c][color] * fixes;
            }
        return cost;
    }
    // Puts paper x into its column at the best depth below `barrier`; mode 1 adds kTopPenalty for the
    // very top. With u, a handle of x's column that the paper of u leaves as a hole adds the digs to
    // set it for u (when not digging).
    void adaptive_insert(int x, int u, int barrier = -1, int mode = 2) {
        const int c = col_of[x], cx = paper[x].black >> handle[c] & 1;
        std::vector<int> v;
        for (int k : order)
            if (k != x && in_column(k, c)) v.push_back(k);
        const int n = v.size();
        int lo = 0;
        if (barrier >= 0) {
            auto it = std::find(v.begin(), v.end(), barrier);
            if (it == v.end()) {
                invalid = true;
                return;
            }
            lo = int(it - v.begin()) + 1;
        }
        std::vector<double> suffix(n + 1, 0.0);
        std::array<int, 2> first = {n, n};
        for (int i = n - 1; i >= 0; i--) {
            suffix[i] = suffix[i + 1] + adaptive_weights[v[i]];
            first[paper[v[i]].black >> handle[c] & 1] = i;
        }
        int requested = u >= 0 ? ded[u] : -1;
        bool need = requested >= 0 && c != col_of[requested] && !(paper[requested].opaque >> handle[c] & 1);
        int desired = u >= 0 ? (A[u] >> handle[c] & 1) : 0;
        double best = 1e100;
        int gap = n;
        for (int i = lo; i <= n; i++) {
            std::array<int, 2> fc;
            for (int color = 0; color < 2; color++) {
                fc[color] = first[color] + (first[color] >= i);
                if (color == cx) fc[color] = std::min(fc[color], i);
            }
            double rank = adaptive_weights[x] * i + suffix[i];
            double value = rank / P + adaptive_holes[c][0] * fc[0] + adaptive_holes[c][1] * fc[1];
            if (need && barrier < 0) value += fc[desired];
            if (mode == 1 && i == 0 && n) value += kTopPenalty;
            value += 1e-7 * (n - i);
            if (value < best) {
                best = value;
                gap = i;
            }
        }
        if (x == top_d) top_d = -1;
        drop_filler(x);
        if (!n) {
            int anchor = -1;
            for (int k : order) {
                if (k == x || k == top_d || is_filler(k)) continue;
                if (k < M || (col_of[k] >= 0 && col_of[k] < c)) anchor = k;
            }
            if (anchor < 0)
                move(x, 0);
            else
                move_after(x, anchor);
        } else if (gap < n) {
            int from = index_of(x), to = index_of(v[gap]);
            move(x, from < to ? to - 1 : to);
        } else
            move_after(x, v.back());
    }
    // ------------------------------------------------------------------------------------------
    // The stack

    int index_of(int k) const {
        for (int i = 0; i < K; i++)
            if (order[i] == k) return i;
        return -1;
    }
    bool visible(int k) const {
        u64 e = paper[k].opaque;
        for (int x : order) {
            if (x == k) return e != 0;
            e &= ~paper[x].opaque;
        }
        return false;
    }
    u64 display() const {
        u64 covered = 0, black = 0;
        for (int k : order) {
            black |= paper[k].black & ~covered;
            covered |= paper[k].opaque;
        }
        return black;
    }
    bool check_vis = false, invalid = false;
    // Moves paper k so that d papers are above it (no move if it is there already). While plans are
    // simulated (check_vis), a move of an invisible paper marks the plan invalid.
    void move(int k, int d) {
        int i = index_of(k);
        if (i == d) return;
        if (check_vis && !visible(k)) invalid = true;
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    // Moves paper k just below paper x.
    void move_after(int k, int x) {
        int i = index_of(k);
        if (index_of(x) + 1 == i) return;
        if (check_vis && !visible(k)) invalid = true;
        order.erase(order.begin() + i);
        int j = 0;
        while (order[j] != x) j++;
        order.insert(order.begin() + j + 1, k);
        ops.push_back({k, j + 1});
    }
    bool is_filler(int k) const {
        for (auto& f : fillers)
            if (f.paper == k) return true;
        return false;
    }
    void drop_filler(int k) {
        std::erase_if(fillers, [&](const Filler& f) { return f.paper == k; });
    }
    // Papers of column l that are in place (not lifted to the top, not out as a filler).
    bool in_column(int k, int l) const { return col_of[k] == l && k != top_d && !is_filler(k); }
    // Up to n papers in place at the top of column l, top first, into `top`.
    void column_tops(int l, int n, std::vector<int>& top) const {
        top.clear();
        for (int k : order)
            if (in_column(k, l)) {
                top.push_back(k);
                if ((int)top.size() >= n) break;
            }
    }
    int column_top(int l) const {
        for (int k : order)
            if (in_column(k, l)) return k;
        return -1;
    }
    // One dig of column l: its top paper goes back into the column below `barrier` (the paper dug
    // for; -1: below the column bottom), at the best depth (adaptive_insert).
    void dig(int l, int barrier = -1) {
        int t = column_top(l);
        if (t < 0) {
            invalid = true;
            return;
        }
        if (barrier < 0) {
            for (int k : order)
                if (in_column(k, l)) barrier = k;
        }
        if (t != barrier) adaptive_insert(t, adaptive_request, barrier, 2);
    }
    // The cap stays above the generic layer. A dedicated sheet printed white
    // at the cap window requests black by stopping immediately below the cap;
    // otherwise the usual top insertion shows its own (correct) printed color.
    void move_to_target_top(int d) {
        const bool needs_cap = (A[adaptive_request] & kCapBit) && !(paper[d].black & kCapBit);
        if (!needs_cap) move(d, 0);
        else {
            const int cp = index_of(kCapPaper), dp = index_of(d);
            move(d, cp + int(dp > cp));
        }
    }
    // Digs the column of d until d is its top, and performs its cap-aware lift.
    void lift(int d) {
        int c = col_of[d];
        for (int it = 0; column_top(c) != d; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(c, d);
        }
        move_to_target_top(d);
        top_d = d;
    }
    // Digs column l until its handle shows `color` (until the first paper of that color is on top).
    void set_handle(int l, int color) {
        int barrier = -1;
        for (int k : order)
            if (in_column(k, l) && int(paper[k].black >> handle[l] & 1) == color) {
                barrier = k;
                break;
            }
        if (barrier < 0) {
            invalid = true;
            return;
        }
        for (int it = 0; column_top(l) != barrier; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(l, barrier);
        }
    }
    void fix_handles(int u, u64 hh) {
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) set_handle(j, A[u] >> handle[j] & 1);
    }
    // Digs set_handle(l, c) would spend (without moving anything).
    int handle_fix_cost(int l, int c) const {
        int i = 0;
        for (int k : order) {
            if (!in_column(k, l)) continue;
            if ((int)(paper[k].black >> handle[l] & 1) == c) return i;
            i++;
        }
        return 0;
    }
    std::vector<int> fix_costs(int u, u64 hh) const {
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        return fix;
    }
    // The level just past the deepest handle of the windows `wrong`.
    int level_past(u64 wrong) const {
        int lvl = 0;
        for (u64 x = wrong; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
        return lvl;
    }
    // The handle windows a filler shows on.
    u64 shown_by(const Filler& f) const {
        u64 m = 0;
        for (int j = f.lvl; j <= f.hi; j++)
            if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
        return m;
    }
    // A filler [lvl, c] placed now would sit above a filler of a deeper level that it reaches.
    static bool reaches_deeper(int lvl, int c, const std::vector<Filler>& placed) {
        for (auto& f : placed)
            if (f.lvl > lvl && c >= f.lvl) return true;
        return false;
    }
    // Paper x to level lvl: just above the first paper in place of a column >= lvl, i.e. below the
    // generic layer, the columns 0..lvl-1 and the fillers of lower levels. lazy: no move if x is
    // already between the last paper in place of a column < lvl (or the generic layer, below_generic) and
    // that position.
    void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
        int q = K, last_above = -1;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (below_generic && k < M) last_above = i;  // the deepest sheet
            if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
            if (col_of[k] < lvl)
                last_above = i;
            else if (q == K)
                q = i;
        }
        int xi = index_of(x);
        if (lazy && xi < q && xi > last_above) return;
        move(x, xi < q ? q - 1 : q);
    }
    // The paper at depth `depth` of column c (the papers above it dug out first) placed as a filler
    // at level lvl; the handles it shows leave hh.
    void place_filler(int c, int depth, int lvl, u64& hh) {
        std::vector<int> top;
        column_tops(c, depth + 1, top);
        if (depth < 0 || depth >= int(top.size())) {
            invalid = true;
            return;
        }
        int x = top[depth];
        for (int it = 0; column_top(c) != x; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(c, x);
        }
        move_to_level(x, lvl);
        fillers.push_back({x, lvl, c});
        hh &= ~shown_by(fillers.back());
    }
    // An out-of-place paper x (the lifted paper or a filler) goes back to its column at the best
    // depth (adaptive_insert; mode 1 adds the top penalty); below u's paper if that paper is still in
    // place in the same column (the column is dug for it in this request).
    void return_paper(int x, int u, int mode) {
        const int d = u >= 0 ? ded[u] : -1;
        adaptive_insert(x, u, d >= 0 && d != x && col_of[d] == col_of[x] && in_column(d, col_of[x]) ? d : -1, mode);
    }
    // Returns the fillers olds to their columns (return_paper), each time the last one in the list
    // that is visible (from solutions/gpt6pro-10-01-filler-chain): fillers may hide each other
    // (fillers_reachable), and an invisible paper cannot move. The order is the reverse list order
    // when nothing is hidden. Invalid if at some point none of the fillers left is visible.
    void return_visible_fillers(const std::vector<Filler>& olds, int u, int mode) {
        std::vector<char> done(olds.size(), 0);
        for (int left = olds.size(); left > 0; left--) {
            int chosen = -1;
            for (int i = (int)olds.size() - 1; i >= 0; i--)
                if (!done[i] && visible(olds[i].paper)) {
                    chosen = i;
                    break;
                }
            if (chosen < 0) {
                invalid = true;
                return;
            }
            done[chosen] = 1;
            return_paper(olds[chosen].paper, u, mode);
            if (invalid) return;
        }
    }

    // ------------------------------------------------------------------------------------------
    // Plans of a request

    // Options of a plan (process tries the combinations):
    //   ret_mode   the previous lifted paper: 1 / 2 back to its column (with / without the top
    //              penalty), 3 re-used as a filler, 4 left in place under the new paper (a filler of
    //              level 0);
    //   fret_mode  the old fillers: 0 / 1 all back (without / with the top penalty), 4 moved to a new
    //              level if they save at least 2 digs, else left in place if harmless, else back
    //              (refill_or_return), 5 everything chosen by one interval DP (run_joint);
    //   use_filler new fillers from the column tops (choose_fillers_prelift).
    struct PlanOpt {
        int ret_mode = 0;
        int fret_mode = 0;
        bool use_filler = false;
    };
    struct FillerPick {
        int c = -1, depth = 0, lvl = 0;
        bool post = false;
        int chain_id = -1, chain_rank = -1;  // a paper of chain placement_chains[chain_id] at rank (0: top)
    };
    // A candidate interval [lvl, c] of handles for the interval DPs.
    struct Cand {
        int lvl;
        double gain;
        int c, depth;
        int kind = 0;
        int idx = -1;
        bool post = false;
    };
    // Weighted interval scheduling over the handle indices (cand[c]: the candidates ending at c): the
    // best set of disjoint intervals, deepest first. Disjoint intervals never cover each other's
    // column handles, so their gains add up.
    std::vector<Cand> best_intervals(const std::vector<std::vector<Cand>>& cand) const {
        std::vector<double> best(H + 1, 0);
        std::vector<int> pick(H + 1, -1);
        for (int c = 0; c < H; c++) {
            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand[c].size(); i++)
                if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9) {
                    best[c + 1] = best[cand[c][i].lvl] + cand[c][i].gain;
                    pick[c + 1] = i;
                }
        }
        std::vector<Cand> res;
        for (int j = H; j > 0;) {
            if (pick[j] < 0) {
                j--;
                continue;
            }
            res.push_back(cand[j - 1][pick[j]]);
            j = res.back().lvl;
        }
        return res;
    }
    // A filler from a column costs 1 move (+ depth) now and is charged at most 1 more for its return,
    // but papers left out are often re-used or left in place: one that saves 2 + depth digs is worth
    // taking.
    static constexpr int kFillerDepth = 3, kFillerCost = 1, kMaxFillers = 8;
    // Fillers when D (column l) is already on top (kept plans): the papers at depth <= kFillerDepth of
    // the columns whose handle is a hole of D, at the level just past their deepest wrong handle.
    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {
        auto fix = fix_costs(u, hh);
        std::vector<std::vector<Cand>> cand(H);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (!(hh >> handle[c] & 1)) continue;
            column_tops(c, kFillerDepth + 1, top);
            if (top.empty() || top[0] == d) continue;
            for (int depth = 0; depth < (int)top.size(); depth++) {
                u64 shown = paper[top[depth]].opaque & hh;
                int lvl = level_past((paper[top[depth]].black ^ A[u]) & shown);
                if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                int save = 0;
                for (int j = lvl; j <= c; j++)
                    if ((j != c || depth) && (shown >> handle[j] & 1)) save += fix[j];
                int gain = save - kFillerCost - depth;
                if (gain > 0) cand[c].push_back({lvl, (double)gain, c, depth});
            }
        }
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) res.push_back({cd.c, cd.depth, cd.lvl, false});
        std::reverse(res.begin(), res.end());
        return res;
    }

    // Level for an out-of-place paper x (the previous lifted paper or an old filler) to serve as a
    // filler for D (column l, handle holes hh): just past its deepest wrong handle, and below D's
    // column when x would cover h_l (it must not hide D's column top). -1 if it covers nothing there.
    // cov receives the covered holes.
    int level_for(int x, int d, u64 hh, int u, u64& cov) const {
        int cx = col_of[x], l = col_of[d];
        u64 shown = paper[x].opaque & hh;
        int lvl = level_past((paper[x].black ^ A[u]) & shown);
        if (cx >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
        cov = 0;
        for (int j = lvl; j <= cx; j++)
            if (shown >> handle[j] & 1) cov |= 1ULL << handle[j];
        return cov ? lvl : -1;
    }
    // An old filler above the bottom of the generic layer (the previous lifted paper left under the new one by the stay
    // plan) may show its colors on the generic holes of the next paper D; where they differ from A_u
    // it cannot stay there: re-leveling moves it below the generic layer, and it is not harmless in
    // place.
    bool gen_harm(int x, int d, int u) const {
        if (d < 0 || index_of(x) > generic_bottom()) return false;
        return (paper[x].opaque & gmask & ~paper[d].opaque & (paper[x].black ^ A[u])) != 0;
    }
    // Old fillers (olds) that can cover holes of D = ded[u] not yet covered (pre_cov) move straight to
    // their new level if that saves at least 2 digs (no move if they already sit at that level); the
    // others stay where they are when they do not hide D's column top and show A_u on the holes they
    // cover; the rest go back to their columns (with the top penalty). `placed` holds the fillers of
    // this request so far.
    // The old fillers are taken from the top of the stack down (fillers may hide each other); one
    // left in place need not be visible (fillers_reachable checks at the end that all the fillers can
    // still be removed one by one).
    void refill_or_return(int u, std::vector<Filler> olds, u64& pre_cov, std::vector<Filler>& placed) {
        int d = ded[u];
        std::sort(olds.begin(), olds.end(),
                  [&](const Filler& a, const Filler& b) { return index_of(a.paper) > index_of(b.paper); });
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            int x = olds[i].paper, cf = col_of[x];
            bool use = false;
            int lvl = 0;
            u64 cov = 0;
            if (d >= 0 && x != d && visible(x)) {
                lvl = level_for(x, d, hmask & ~paper[d].opaque & ~pre_cov, u, cov);
                if (lvl >= 0 && !reaches_deeper(lvl, cf, placed)) {
                    int save = 0;
                    for (int j = lvl; j <= cf; j++)
                        if (cov >> handle[j] & 1) save += handle_fix_cost(j, A[u] >> handle[j] & 1);
                    use = save >= 2;
                }
            }
            if (!use && d >= 0 && x != d) {
                int L = olds[i].lvl, l = col_of[d];
                bool harm = (L <= l && l <= cf && (paper[x].opaque >> handle[l] & 1)) || reaches_deeper(L, cf, placed);
                u64 hcov = 0;
                for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
                hcov &= paper[x].opaque & hmask & ~paper[d].opaque & ~pre_cov;
                if ((paper[x].black ^ A[u]) & hcov || gen_harm(x, d, u)) harm = true;
                if (!harm) {
                    drop_filler(x);
                    placed.push_back(olds[i]);
                    pre_cov |= hcov;
                    continue;
                }
            }
            if (!use) {
                return_paper(x, u, 1);
                continue;
            }
            drop_filler(x);
            move_to_level(x, lvl, true, gen_harm(x, d, u));
            placed.push_back({x, lvl, cf});
            pre_cov |= cov;
        }
    }
    static constexpr double kRelevel = 0.5, kStay = 0.8;
    int depth_in_column(int x) const {
        int i = 0;
        for (int k : order) {
            if (k == x) return i;
            if (in_column(k, col_of[x])) i++;
        }
        return -1;
    }
    // Joint choice (fret_mode 5) of the papers out of their columns (the previous lifted paper x0 and
    // the old fillers) and of the new fillers from the column tops: one weighted interval scheduling
    // over the handles, every candidate an interval [lvl, c] that a paper of column c shows on
    // (matching A_u on all the holes of D it covers):
    //   - a new filler, the paper at depth p <= kFillerDepth of column c: gain = saved digs - 1 - p
    //     (taken only if at least kFillerCost);
    //   - an old paper moved to a new level: gain = saved digs - kRelevel;
    //   - an old filler left where it is: gain = saved digs + 1 - kStay;
    // all also at narrower levels. Old papers not chosen go back to their columns. Saved digs are the
    // handle_fix_cost of the covered holes before any move. The requested paper D, when it is an old
    // filler, is lifted straight from there (no dig).
    void run_joint(int u, const PlanOpt& opt) {
        int d = ded[u];
        if (d < 0 || d == top_d) {
            invalid = true;
            return;
        }
        const int l = col_of[d];
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        auto fix = fix_costs(u, hh);
        const bool d_out = is_filler(d);
        std::vector<Filler> olds;
        for (auto& f : fillers)
            if (f.paper != d) olds.push_back(f);
        const int x0 = top_d;
        std::vector<std::vector<Cand>> cand(H);
        auto mism_level = [&](int x) { return level_past((paper[x].black ^ A[u]) & paper[x].opaque & hh); };
        auto saved = [&](int x, int lvl, int c, bool skip_c) {
            int sv = 0;
            for (int j = lvl; j <= c; j++)
                if ((hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1) && !(skip_c && j == c)) sv += fix[j];
            return sv;
        };
        auto covers = [&](int x, int j) { return (hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1); };
        auto add_old = [&](int x, int idx, int L, bool is_x0) {
            int c = col_of[x];
            int lvl = mism_level(x);
            if (!is_x0 && gen_harm(x, d, u)) L = -2;
            if (!d_out && c >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);
                double g = sv - kRelevel;
                if (!is_x0 && lvl == L) g = sv + 1 - kStay;
                if (g > 0) cand[c].push_back({lvl, g, c, 0, is_x0 ? 3 : (lvl == L ? 2 : 1), idx});
            }
            if (!is_x0 && L > lvl && L <= c) {
                bool harm = !d_out && L <= l && l <= c && (paper[x].opaque >> handle[l] & 1);
                double g = saved(x, L, c, false) + 1 - kStay;
                if (!harm && g > 0) cand[c].push_back({L, g, c, 0, 2, idx});
            }
            for (int lv = lvl + 1; lv <= c; lv++) {
                if (!covers(x, lv) || (!is_x0 && lv == L)) continue;
                double g = saved(x, lv, c, false) - kRelevel;
                if (g > 0) cand[c].push_back({lv, g, c, 0, is_x0 ? 3 : 1, idx});
            }
        };
        for (int i = 0; i < (int)olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
        if (x0 >= 0) add_old(x0, -1, -1, true);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            bool hole_c = hh >> handle[c] & 1;
            if (c == l || (d_out && !hole_c)) continue;
            column_tops(c, kFillerDepth + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                int lvl = mism_level(f);
                for (int lv = lvl; lv <= c; lv++) {
                    if (lv > lvl && !covers(f, lv)) continue;
                    bool post = d_out || (c > l && lv <= l && (paper[f].opaque >> handle[l] & 1));
                    int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    if (g >= kFillerCost) cand[c].push_back({lv, (double)g, c, 0, 0, f, post});
                }
            }
        }
        const auto picks = best_intervals(cand);
        std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);
        int x0_lvl = -1;
        for (auto& cd : picks) {
            if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
            if (cd.kind == 3) x0_lvl = cd.lvl;
        }
        Filler fd{d};
        for (auto& f : fillers)
            if (f.paper == d) fd = f;
        fillers = olds;
        if (d_out) fillers.push_back(fd);
        std::vector<char> done(olds.size(), 0);
        // the visible ones first, each time the last visible one in the list (a filler may be hidden
        // by another one, visible once that one is back)
        for (;;) {
            int chosen = -1;
            for (int i = (int)olds.size() - 1; i >= 0; i--)
                if (old_dec[i] == 0 && !done[i] && visible(olds[i].paper)) {
                    chosen = i;
                    break;
                }
            if (chosen < 0) break;
            return_paper(olds[chosen].paper, u, 1);
            done[chosen] = 1;
            if (invalid) return;
        }
        if (x0 >= 0) {
            if (x0_lvl >= 0) {
                top_d = -1;
                move_to_level(x0, x0_lvl, true, gen_harm(x0, d, u));
                fillers.push_back({x0, x0_lvl, col_of[x0]});
            } else {
                return_paper(x0, u, opt.ret_mode);
            }
        }
        for (int i = (int)olds.size() - 1; i >= 0; i--)
            if (old_dec[i] == 0 && !done[i]) return_paper(olds[i].paper, u, 1);
        for (int i = 0; i < (int)olds.size(); i++) {
            if (old_dec[i] == 0) continue;
            int x = olds[i].paper;
            for (auto& f : fillers)
                if (f.paper == x) f.lvl = old_lvl[i], f.hi = col_of[x];
            if (old_dec[i] == 1) move_to_level(x, old_lvl[i], true, gen_harm(x, d, u));
        }
        for (auto& f : fillers)
            if (f.paper != d) hh &= ~shown_by(f);
        set_generic(u, hole_all);
        for (auto& cd : picks)
            if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        if (d_out) {
            drop_filler(d);
            move_to_target_top(d);
            top_d = d;
        } else {
            lift(d);
        }
        for (auto& cd : picks)
            if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        fix_handles(u, hh);
    }
    // One plan: the previous lifted paper and the old fillers (PlanOpt), the generic layer, new
    // fillers (chosen with every column top visible: those that do not reach D's handle go in before
    // the dig and the lift, the others after), the lift of D and the digs of the remaining handle
    // holes.
    void run_plan(int u, const PlanOpt& opt) {
        if (opt.fret_mode == 5) {
            run_joint(u, opt);
            return;
        }
        u64 pre_cov = 0;
        int stay = -1;
        if (opt.ret_mode == 4) {
            int d = ded[u];
            if (top_d < 0 || d == top_d || (gmask & ~paper[d].opaque & paper[top_d].opaque)) {
                invalid = true;
                return;
            }
            stay = top_d;
            top_d = -1;
        }
        if (top_d >= 0 && opt.ret_mode == 3) {
            int x = top_d, lp = col_of[x], d = ded[u];
            if (d < 0 || d == x) {
                invalid = true;
                return;
            }
            u64 cov0 = 0;
            int lvl = level_for(x, d, hmask & ~paper[d].opaque, u, cov0);
            if (lvl < 0) {
                invalid = true;
                return;
            }
            std::vector<Filler> vis_old, def_old;
            for (auto& f : fillers) (visible(f.paper) ? vis_old : def_old).push_back(f);
            std::vector<Filler> placed = {{x, lvl, lp}};
            pre_cov |= cov0;
            auto put_back = [&](const std::vector<Filler>& olds) {
                if (opt.fret_mode == 4)
                    refill_or_return(u, olds, pre_cov, placed);
                else
                    return_visible_fillers(olds, u, opt.fret_mode);
            };
            put_back(vis_old);
            move_to_level(x, lvl);
            top_d = -1;
            put_back(def_old);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0) return_paper(top_d, u, opt.ret_mode);
            if (opt.fret_mode == 4) {
                std::vector<Filler> olds = fillers, placed;
                refill_or_return(u, olds, pre_cov, placed);
                for (auto& f : placed) fillers.push_back(f);
            } else {
                const auto olds = fillers;
                return_visible_fillers(olds, u, opt.fret_mode);
            }
        }
        if (stay >= 0) {
            fillers.push_back({stay, 0, col_of[stay]});
            pre_cov |= shown_by(fillers.back());
        }
        if (!tail_cache_on || invalid) {
            run_plan_tail(u, opt, pre_cov);
            return;
        }
        // the rest of the plan depends only on the state reached and on (pre_cov, use_filler)
        u64 h = 1469598103934665603ULL ^ pre_cov ^ (u64(opt.use_filler) << 2) ^ (u64(top_d + 1) << 3);
        for (int k : order) h = (h ^ u64(k)) * 1099511628211ULL;
        for (const auto& f : fillers) h = (h ^ u64(f.paper * 4096 + f.lvl * 64 + f.hi)) * 1099511628211ULL;
        for (const auto& e : tail_cache)
            if (e.hash == h && e.pre_cov == pre_cov && e.use_filler == opt.use_filler &&
                e.top_d == top_d && e.order == order && same_fillers(e.fillers, fillers)) {
                tail_hits++;
                order = e.out_order;
                top_d = e.out_top;
                fillers = e.out_fillers;
                ops.insert(ops.end(), e.out_ops.begin(), e.out_ops.end());
                invalid = e.out_invalid;
                return;
            }
        TailEntry e{h, order, top_d, fillers, pre_cov, opt.use_filler, {}, -1, {}, {}, false};
        const size_t prefix = ops.size();
        run_plan_tail(u, opt, pre_cov);
        e.out_order = order;
        e.out_top = top_d;
        e.out_fillers = fillers;
        e.out_ops.assign(ops.begin() + prefix, ops.end());
        e.out_invalid = invalid;
        tail_cache.push_back(std::move(e));
    }
    // Plans that reach the same state after their first part (the previous lifted paper and the old
    // fillers handled) share the rest (from solutions/gpt6pro-06-02-regroup): while process tries
    // the plan options (tail_cache_on), the result of run_plan_tail is kept per request and re-used
    // (the same moves appended, the same state). The output is unchanged.
    struct TailEntry {
        u64 hash;
        std::vector<int> order;
        int top_d;
        std::vector<Filler> fillers;
        u64 pre_cov;
        bool use_filler;
        std::vector<int> out_order;
        int out_top;
        std::vector<Filler> out_fillers;
        std::vector<std::pair<int, int>> out_ops;
        bool out_invalid;
    };
    std::vector<TailEntry> tail_cache;
    bool tail_cache_on = false;
    long long tail_hits = 0;
    static bool same_fillers(const std::vector<Filler>& a, const std::vector<Filler>& b) {
        if (a.size() != b.size()) return false;
        for (size_t i = 0; i < a.size(); i++)
            if (a[i].paper != b[i].paper || a[i].lvl != b[i].lvl || a[i].hi != b[i].hi) return false;
        return true;
    }
    // The second part of run_plan: the generic layer, the new fillers, the lift of D and the digs of
    // the handle holes left.
    void run_plan_tail(int u, const PlanOpt& opt, u64 pre_cov) {
        const int d = ded[u];
        const u64 holes = (gmask | hmask) & ~paper[d].opaque;
        set_generic(u, holes);
        u64 hh = holes & ~gmask & ~pre_cov;
        if (opt.use_filler) {
            auto picks = choose_fillers_prelift(u, d, hh);
            // the chain search picked no chain: the same plan as without it (process has it already)
            if (beam_enabled && placement_chains.empty()) {
                invalid = true;
                return;
            }
            for (auto& pk : picks)
                if (!pk.post) place_picked_filler(pk, hh);
            lift(d);
            for (auto& pk : picks)
                if (pk.post) place_picked_filler(pk, hh);
        } else
            lift(d);
        fix_handles(u, hh);
    }
    // Fillers chosen before D (column l, in place) is lifted: candidates are the top papers of every
    // column c != l whose handle is not covered by a filler already placed, at the level just past
    // their deepest wrong handle and at the narrower levels lv whose handle h_lv is a hole they cover.
    // A candidate of a column c > l whose interval reaches h_l would hide D's column top: it is placed
    // after the lift (post). A candidate of a column c < l whose handle D covers can only be placed
    // before the lift.
    // Stacks: two papers at one level a, U (column cU) placed first and L (column cL > cU) next,
    // which inserts L just below U. U shows on its opaque handles in [a, cU], L on the holes of U
    // there and on (cU, cL]; L may be wrong where U masks it.
    // With beam_enabled, chains of up to 4 papers (append_wide_chains) are candidates too.
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) {
        placement_chains.clear();
        const int l = col_of[d];
        const u64 hole_all = hmask & ~paper[d].opaque;
        u64 covered = 0;
        for (auto& f : fillers) covered |= shown_by(f);
        auto fix = fix_costs(u, hh);
        std::vector<std::vector<Cand>> cand(H);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            bool hole_c = hole_all >> handle[c] & 1;
            column_tops(c, kFillerDepth + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                int lvl = level_past((paper[f].black ^ A[u]) & shown);
                if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                for (int lv = lvl; lv <= c; lv++) {
                    if (lv > lvl && (!(shown >> handle[lv] & 1) || reaches_deeper(lv, c, fillers))) continue;
                    bool post = c > l && lv <= l && (paper[f].opaque >> handle[l] & 1);
                    int save = 0;
                    for (int j = lv; j <= c; j++)
                        if ((shown >> handle[j] & 1) && (j != c || depth || !hole_c)) save += fix[j];
                    int gain = save - kFillerCost - depth;
                    if (gain > 0) cand[c].push_back({lv, (double)gain, c, depth, 0, -1, post});
                }
            }
        }
        struct PC {
            int c, depth;
            u64 opq, shown, bad;
            bool hole_c;
            int fsum;
        };
        struct Stack {
            int cU, dU, cL, dL;
            bool postU, postL;
        };
        std::vector<Stack> stacks;
        auto hib = [](u64 x) { return x ? 63 - __builtin_clzll(x) : -1; };
        auto upto = [](int b) -> u64 { return b < 0 ? 0 : b >= 63 ? ~0ULL : (1ULL << (b + 1)) - 1; };
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
        std::vector<std::array<int, kFillerDepth + 1>> tops(H);
        std::vector<int> ntop(H, 0);
        for (int k : order) {
            int c = col_of[k];
            if (c < 0 || ntop[c] > kFillerDepth || !in_column(k, c)) continue;
            tops[c][ntop[c]++] = k;
        }
        std::vector<PC> pcs;
        std::vector<int> first_of(H + 1, 0);
        for (int c = 0; c < H; c++) {
            first_of[c] = pcs.size();
            if (c == l || (covered >> handle[c] & 1)) continue;
            for (int dpt = 0; dpt < ntop[c]; dpt++) {
                int k = tops[c][dpt];
                PC pc{c, dpt, h_opq[k] & upto(c), 0, 0, (bool)(hole_all >> handle[c] & 1), 0};
                pc.shown = pc.opq & hh_i;
                pc.bad = pc.shown & (h_blk[k] ^ au_i);
                for (u64 x = pc.shown; x; x &= x - 1) pc.fsum += fix[__builtin_ctzll(x)];
                pcs.push_back(pc);
            }
        }
        first_of[H] = pcs.size();
        for (auto& L : pcs) {
            if (!L.bad) continue;
            for (int ui = first_of[std::max(hib(L.bad), 0)]; ui < first_of[L.c]; ui++) {
                const PC& U = pcs[ui];
                if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 2) continue;
                int aU = hib(U.bad) + 1;
                if (aU > U.c) continue;
                int a = std::max(aU, hib(L.bad & ~U.opq & upto(U.c)) + 1);
                if (a > U.c) continue;
                bool postU = U.c > l && a <= l && (U.opq >> l & 1);
                bool postL = postU || (L.c > l && a <= l && (L.opq >> l & 1));
                if ((postU && !U.hole_c) || (postL && !L.hole_c) || reaches_deeper(a, L.c, fillers)) continue;
                u64 from_a = ~upto(a - 1);
                u64 covU = U.shown & from_a & upto(U.c), covL = L.shown & ~U.opq & from_a & upto(L.c);
                if (U.depth == 0 && U.hole_c) covU &= ~(1ULL << U.c);
                if (L.depth == 0 && L.hole_c) covL &= ~(1ULL << L.c);
                int save = 0;
                for (u64 x = covU | covL; x; x &= x - 1) save += fix[__builtin_ctzll(x)];
                int gain = save - 2 * kFillerCost - U.depth - L.depth;
                if (gain < 2) continue;
                stacks.push_back({U.c, U.depth, L.c, L.depth, postU, postL});
                cand[L.c].push_back({a, (double)gain, L.c, -(int)stacks.size()});
            }
        }
        std::vector<std::vector<FillerPick>> wide_chains;
        if (beam_enabled) append_wide_chains(u, d, hh, fix, cand, wide_chains);
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) {
            if (cd.kind == 7) {
                // a chain: its papers taken in increasing column order (res is reversed below), each
                // placed at its rank among those of the chain already placed (place_picked_filler)
                auto chain = wide_chains[cd.idx];
                const int chain_id = placement_chains.size();
                placement_chains.emplace_back(chain.size(), -1);
                for (int i = 0; i < (int)chain.size(); i++) chain[i].chain_id = chain_id, chain[i].chain_rank = i;
                std::sort(chain.begin(), chain.end(), [](const FillerPick& a, const FillerPick& b) { return a.c > b.c; });
                for (const auto& pick : chain) res.push_back(pick);
            } else if (cd.depth < 0) {
                const Stack& st = stacks[-1 - cd.depth];
                res.push_back({st.cL, st.dL, cd.lvl, st.postL});
                res.push_back({st.cU, st.dU, cd.lvl, st.postU});
            } else {
                res.push_back({cd.c, cd.depth, cd.lvl, cd.post});
            }
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    // Chains of fillers (from solutions/gpt6pro-10-01-filler-chain): up to kChainLength papers of
    // distinct columns (at most kChainDepth deep in their column) stacked at one level, the first of
    // the path on top. Walking down the path, the opaque handles O of the papers so far and the
    // wrong ones B (shown with a color other than A_u on a hole of D, not masked by a paper above)
    // are updated; the level is just past the deepest wrong handle and must not exceed the least
    // column. The gain is the digs (fix) of the holes of D covered from the level on, less 1 + depth
    // per paper; a beam of kBeamWidth paths per length, pruned when the cost reaches the digs left
    // from the level on (suffixFix: an upper bound of the saving). A chain is an interval candidate
    // [level, deepest column] (kind 7, idx: its index in chains). Papers of columns deeper than D's
    // are placed after the lift (D must not cover their handle, or their column top is hidden).
    static constexpr int kChainDepth = 2, kChainLength = 4, kBeamWidth = 24;
    long long chain_trials = 0, chain_selected = 0, chain_papers = 0;
    bool beam_enabled = false;                       // choose_fillers_prelift searches chains
    std::vector<std::vector<int>> placement_chains;  // per chain of the plan: the paper placed at each rank
    void append_wide_chains(int u, int d, u64 hh, const std::vector<int>& fix, std::vector<std::vector<Cand>>& cand,
                            std::vector<std::vector<FillerPick>>& chains) const {
        const int totalFix = std::accumulate(fix.begin(), fix.end(), 0);
        if (totalFix < 3) return;
        std::vector<int> suffixFix(H + 1, 0);
        for (int j = H - 1; j >= 0; j--) suffixFix[j] = suffixFix[j + 1] + fix[j];
        struct PC {
            int c, depth;
            u64 opaque, bad;  // by handle index
        };
        const int l = col_of[d];
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
        u64 covered = 0;
        for (const auto& f : fillers) covered |= shown_by(f);
        std::vector<PC> pool;
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            column_tops(c, std::min(kFillerDepth, kChainDepth) + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                const int k = top[depth];
                pool.push_back({c, depth, h_opq[k], h_opq[k] & hh_i & (h_blk[k] ^ au_i)});
            }
        }
        struct BeamState {
            std::array<int, kChainLength> path{};
            int length = 0, minc = 0, maxc = 0, cost = 0, level = 0, gain = 0;
            u64 opaque = 0, bad = 0;
        };
        auto evaluate = [&](BeamState& b) {
            if (b.cost >= totalFix) return false;
            b.level = b.bad ? 64 - __builtin_clzll(b.bad) : 0;
            if (b.level > b.minc || reaches_deeper(b.level, b.maxc, fillers)) return false;
            if (b.cost >= suffixFix[b.level]) return false;
            int saved = 0;
            for (u64 x = b.opaque & hh_i & ~low_bits(b.level); x; x &= x - 1) saved += fix[__builtin_ctzll(x)];
            b.gain = saved - b.cost;
            return true;
        };
        auto add = [&](const BeamState& b) {
            if (b.gain <= 0) return;
            std::vector<FillerPick> chain;
            for (int j = 0; j < b.length; j++) {
                const auto& p = pool[b.path[j]];
                const bool post = p.c > l;
                if (post && (paper[d].opaque >> handle[p.c] & 1)) return;
                chain.push_back({p.c, p.depth, b.level, post});
            }
            const int index = chains.size();
            chains.push_back(std::move(chain));
            cand[b.maxc].push_back({b.level, double(b.gain), b.maxc, 0, 7, index});
        };
        std::vector<BeamState> current;
        for (int i = 0; i < (int)pool.size(); i++) {
            const auto& p = pool[i];
            BeamState b;
            b.path[0] = i;
            b.length = 1;
            b.minc = b.maxc = p.c;
            b.cost = kFillerCost + p.depth;
            b.opaque = p.opaque;
            b.bad = p.bad;
            if (evaluate(b)) current.push_back(b);
        }
        for (int length = 2; length <= std::min(kChainLength, totalFix - 1); length++) {
            std::vector<BeamState> next;
            for (const auto& b : current) {
                for (int i = 0; i < (int)pool.size(); i++) {
                    const auto& p = pool[i];
                    if (b.cost + kFillerCost + p.depth >= suffixFix[b.level]) continue;
                    bool duplicate_column = false;
                    for (int j = 0; j < b.length; j++)
                        if (pool[b.path[j]].c == p.c) duplicate_column = true;
                    if (duplicate_column) continue;
                    BeamState nb = b;
                    nb.path[nb.length++] = i;
                    nb.minc = std::min(nb.minc, p.c);
                    nb.maxc = std::max(nb.maxc, p.c);
                    nb.cost += kFillerCost + p.depth;
                    nb.bad |= p.bad & ~b.opaque;
                    nb.opaque |= p.opaque;
                    if (!evaluate(nb)) continue;
                    add(nb);
                    next.push_back(nb);
                }
            }
            std::sort(next.begin(), next.end(), [](const BeamState& a, const BeamState& b) { return a.gain > b.gain; });
            if ((int)next.size() > kBeamWidth) next.resize(kBeamWidth);
            current = std::move(next);
        }
    }
    // place_filler, and for a paper of a chain: just above the nearest paper of the chain below it
    // that is placed already, else just below the nearest one above it, else at the level.
    void place_picked_filler(const FillerPick& pick, u64& hh) {
        if (pick.chain_id < 0) {
            place_filler(pick.c, pick.depth, pick.lvl, hh);
            return;
        }
        std::vector<int> top;
        column_tops(pick.c, pick.depth + 1, top);
        if (pick.depth < 0 || pick.depth >= (int)top.size()) {
            invalid = true;
            return;
        }
        const int x = top[pick.depth];
        for (int it = 0; column_top(pick.c) != x; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(pick.c, x);
        }
        auto& placed = placement_chains[pick.chain_id];
        int successor = -1, predecessor = -1;
        for (int i = pick.chain_rank + 1; i < (int)placed.size(); i++)
            if (placed[i] >= 0) {
                successor = placed[i];
                break;
            }
        for (int i = pick.chain_rank - 1; i >= 0; i--)
            if (placed[i] >= 0) {
                predecessor = placed[i];
                break;
            }
        if (successor >= 0) {
            const int from = index_of(x), to = index_of(successor);
            move(x, from < to ? to - 1 : to);
        } else if (predecessor >= 0) {
            move_after(x, predecessor);
        } else {
            move_to_level(x, pick.lvl);
        }
        placed[pick.chain_rank] = x;
        fillers.push_back({x, pick.lvl, pick.c});
        hh &= ~shown_by(fillers.back());
    }

    // The fillers can be removed one by one with the lifted paper set aside (it goes back first at
    // the next request): each time one of those left is visible once the removed ones are gone
    // (from solutions/gpt6pro-10-01-filler-chain; fillers may hide each other). Removing a paper
    // never hides another, so taking any visible one (here the topmost) decides it.
    bool fillers_reachable() const {
        std::array<bool, K> removed{}, pending{};
        if (top_d >= 0) removed[top_d] = true;
        for (const auto& f : fillers) {
            if (pending[f.paper]) return false;
            pending[f.paper] = true;
        }
        for (int left = fillers.size(); left > 0; left--) {
            int chosen = -1;
            u64 covered = 0;
            for (int k : order) {
                if (removed[k]) continue;
                if (pending[k] && (paper[k].opaque & ~covered)) {
                    chosen = k;
                    break;
                }
                covered |= paper[k].opaque;
            }
            if (chosen < 0) return false;
            removed[chosen] = true;
            pending[chosen] = false;
        }
        return true;
    }

    // The records of the papers out of their columns rebuilt from the order after every request.
    // Walking up from the bottom, a paper of column c <= cur (cur = column of the nearest paper in
    // place below) is in place, one of a column > cur is out (a filler of level cur), and a column
    // paper above a generic sheet is out (level 0); the paper on the very top is the lifted one.
    void canonicalize() {
        std::vector<char> inpl(K, 0);
        std::vector<int> lv(K, -1);
        int cur = H;
        bool gen_seen = false;
        for (int i = K - 1; i >= 0; i--) {
            int k = order[i], c = col_of[k];
            if (c < 0) {
                if (k < M) gen_seen = true;
                continue;
            }
            if (!gen_seen && c <= cur) {
                cur = c;
                inpl[k] = 1;
            } else
                lv[k] = gen_seen ? 0 : std::min(cur, c);
        }
        // as6-canon: a filler of level L shows on h_L.. only if column L - 1 has a paper in place; the
        // columns just above it with no paper in place (shallow columns have about two papers, one of
        // which is often lifted or out as a filler) leave their handles to it as well
        std::vector<char> nonempty(H, 0);
        for (int k = 0; k < K; k++)
            if (inpl[k]) nonempty[col_of[k]] = 1;
        int ntop = -1;
        std::vector<Filler> nf;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (col_of[k] < 0 || inpl[k]) continue;
            int l = lv[k];
            while (l > 0 && !nonempty[l - 1]) l--;
            if (i == 0 || (i == 1 && order[0] == kCapPaper))
                ntop = k;
            else
                nf.push_back({k, l, col_of[k]});
        }
        std::vector<Filler> res;
        for (auto& f : fillers)
            for (auto& g : nf)
                if (g.paper == f.paper) res.push_back(g);
        for (auto& g : nf)
            if (!is_filler(g.paper)) res.push_back(g);
        top_d = ntop;
        fillers = res;
    }
    struct State {
        std::vector<int> order;
        int top_d;
        std::vector<Filler> fillers;
    };
    State save() const { return {order, top_d, fillers}; }
    void restore(const State& st) {
        order = st.order;
        top_d = st.top_d;
        fillers = st.fillers;
    }
    // A paper left out costs its return later but is often re-used instead (kFillerCharge), and the
    // state left is valued by kEndWeight times adaptive_next_cost.
    static constexpr double kFillerCharge = 0.6;
    // Helper plans (Interleave; from solutions/gpt6pro-08-01-colswap), tried after the plan options
    // from the state with the lifted paper and the old fillers back in their columns (the generic
    // layer then on top): the generic sheets go to a goal order (Interleave::path), the helper is dug
    // out of its column and inserted at the goal depth of the layer (a filler of level 0), D is
    // lifted, and the remaining handle holes are covered as in run_plan (fillers of the interval DP,
    // digs). A pair of helpers x (upper) and y (lower, of a deeper column) inserted at depths tu <= tl
    // of the same goal order: best_interleave_pair (goals of distance < limit, the nearest first).
    std::shared_ptr<Interleave> interleave;
    long long interleave_trials = 0, interleave_selected = 0;
    struct PairHelperPick {
        int upper, lower, goal, tu, tl, distance;
    };
    PairHelperPick best_interleave_pair(int source, int u, int x, int y, int limit) const {
        const u64 gh = gmask & ~paper[ded[u]].opaque;
        for (int distance = 0; distance < limit; distance++)
            for (int state = 0; state < (int)comparator.perms.size(); state++) {
                if (comparator.distance(source, state) != distance) continue;
                for (int tl = M; tl >= 0; tl--) {
                    const u64 py = interleave->prefix[state][tl];
                    const u64 b = (interleave->display[state] & (py | ~paper[y].opaque)) | (paper[y].black & ~py);
                    for (int tu = tl; tu >= 0; tu--) {
                        const u64 px = interleave->prefix[state][tu];
                        const u64 z = (b & (px | ~paper[x].opaque)) | (paper[x].black & ~px);
                        if (!((z ^ A[u]) & gh)) return {x, y, state, tu, tl, distance};
                    }
                }
            }
        return {x, y, -1, 0, 0, limit};
    }
    // The remaining handle holes hh (not shown by the helpers): fillers of the interval DP and digs.
    void finish_handles(int u, int d, u64 hh) {
        for (auto& pk : choose_fillers_dp(u, d, hh)) {
            if ((int)fillers.size() >= kMaxFillers) break;
            place_filler(pk.c, pk.depth, pk.lvl, hh);
        }
        fix_handles(u, hh);
    }
    void run_interleave(int u, const Interleave::Pick& pk) {
        const int d = ded[u], c = col_of[pk.paper], l = col_of[d];
        const int s = interleave->state(order);
        for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth + 1);
        auto get_helper = [&](bool after_target) {
            for (int it = 0; column_top(c) != pk.paper; it++) {
                if (it >= K || invalid) {
                    invalid = true;
                    return;
                }
                dig(c, pk.paper);
            }
            move(pk.paper, 1 + pk.depth + (after_target ? 1 : 0));
            fillers.push_back({pk.paper, 0, c});
        };
        if (c < l) get_helper(false);  // digging a shallower column first does not hide D's column
        lift(d);
        if (c > l) get_helper(true);
        if (invalid) return;
        finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.paper].opaque);
    }
    void run_interleave_pair(int u, const PairHelperPick& pk) {
        const int d = ded[u], l = col_of[d];
        const int s = interleave->state(order);
        for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth + 1);
        int placed = 0;
        bool lifted = false;
        auto get = [&](int x, int depth) {
            const int c = col_of[x];
            if (c > l && !lifted) lift(d), lifted = true;
            for (int it = 0; column_top(c) != x; it++) {
                if (it >= K || invalid) {
                    invalid = true;
                    return;
                }
                dig(c, x);
            }
            move(x, 1 + depth + placed + (lifted ? 1 : 0));
            fillers.push_back({x, 0, c});
            placed++;
        };
        get(pk.upper, pk.tu);
        get(pk.lower, pk.tl);
        if (!lifted) lift(d);
        if (invalid) return;
        finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.upper].opaque & ~paper[pk.lower].opaque);
    }
    // The helper plans of request u from st0 (cost as in process); updates best / best_ops / best_state.
    template <class Keep>
    void try_helpers(int u, const State& st0, Keep keep) {
        const int d = ded[u];
        restore(st0);
        ops.clear();
        invalid = false;
        if (top_d >= 0) return_paper(top_d, u, 1);
        const auto olds = fillers;
        return_visible_fillers(olds, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;
        for (int i = 0; i < M; i++)
            if (order[i + 1] >= M) return;
        const State clean = save();
        const auto clean_ops = ops;
        const int s = interleave->state(order);
        std::vector<int> current(order.begin() + 1, order.begin() + 1 + M);
        const int base_generic = comparator.plan(current, A[u], ~paper[d].opaque & gmask).size();
        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        // single helpers: at most 5 deep in their column, fewer generic moves than without; the 4 of
        // least distance + depth + 1.8 + digs of the handle holes they do not cover
        std::vector<std::pair<double, Interleave::Pick>> picks;
        for (const auto& h : interleave->helpers[u]) {
            const int dep = depth_in_column(h.paper);
            if (dep < 0 || dep > 5) continue;
            auto pk = interleave->best(s, h);
            if (pk.distance >= base_generic) continue;
            double score = pk.distance + dep + 1.8;
            for (int c = 0; c < H; c++)
                if (!(paper[h.paper].opaque >> handle[c] & 1)) score += fixes[c];
            picks.push_back({score, pk});
        }
        std::sort(picks.begin(), picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (picks.size() > 4) picks.resize(4);
        // pairs: a helper x at most 3 deep and a paper y of a deeper column (not D's) at most 3 deep
        // that is right on the handle holes of D that x leaves; the 12 of least estimate, then the 4
        // of least estimate + distance
        struct PP {
            double estimate;
            int x, y;
        };
        std::vector<PP> pairs;
        std::vector<int> available, depths(K, -1), ranks(H, 0);
        for (int k : order)
            if (col_of[k] >= 0 && in_column(k, col_of[k])) {
                const int c = col_of[k];
                depths[k] = ranks[c]++;
                if (k != d && c != col_of[d] && depths[k] <= 3) available.push_back(k);
            }
        const u64 hh = ~paper[d].opaque & hmask;
        for (const auto& h : interleave->helpers[u]) {
            const int x = h.paper;
            if (depths[x] < 0 || depths[x] > 3) continue;
            for (int y : available) {
                if (col_of[y] <= col_of[x]) continue;
                if ((paper[y].black ^ A[u]) & paper[y].opaque & hh & ~paper[x].opaque) continue;
                double estimate = depths[x] + depths[y] + 3.6;
                for (int c = 0; c < H; c++)
                    if (!((paper[x].opaque | paper[y].opaque) >> handle[c] & 1)) estimate += fixes[c];
                pairs.push_back({estimate, x, y});
            }
        }
        std::sort(pairs.begin(), pairs.end(), [](const PP& a, const PP& b) { return a.estimate < b.estimate; });
        if (pairs.size() > 12) pairs.resize(12);
        std::vector<std::pair<double, PairHelperPick>> pair_picks;
        for (auto pp : pairs) {
            auto pk = best_interleave_pair(s, u, pp.x, pp.y, base_generic);
            if (pk.goal >= 0) pair_picks.push_back({pp.estimate + pk.distance, pk});
        }
        std::sort(pair_picks.begin(), pair_picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (pair_picks.size() > 4) pair_picks.resize(4);
        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            keep(ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost());
        };
        for (const auto& item : pair_picks) {
            restore(clean);
            ops = clean_ops;
            invalid = false;
            interleave_trials++;
            run_interleave_pair(u, item.second);
            finish();
        }
        for (const auto& item : picks) {
            restore(clean);
            ops = clean_ops;
            invalid = false;
            interleave_trials++;
            run_interleave(u, item.second);
            finish();
        }
    }

    // Post-processing of the chosen plan (from solutions/gpt6pro-07-02-replace): the plan is a list
    // of edits "paper k goes just below paper anchor" (anchor -1: the top), replayed from the start
    // with the depths recomputed. A request only needs the display A_u, not one final order, so an
    // edited list is kept when every move is legal (the paper is visible), the display is A_u, the
    // fillers are reachable (after canonicalize; the generic sheets may be split by column papers,
    // fillers of level 0 that the next request returns before it orders the generic sheets) and the
    // cost of process (moves + kFillerCharge fillers + kEndWeight adaptive_next_cost) decreases.
    // Edits tried: delete one edit (repeated), and move the anchor of an old filler / the old lifted
    // paper / a paper moved twice.
    long long post_saved = 0;
    std::vector<std::pair<int, int>> post_optimize(const State& initial, std::vector<std::pair<int, int>> input_ops,
                                                   int u) {
        if (input_ops.empty()) return input_ops;
        struct Edit {
            int paper, anchor;
        };
        auto anchorize = [&](const std::vector<std::pair<int, int>>& path) {
            std::vector<int> ord = initial.order;
            std::vector<Edit> edits;
            edits.reserve(path.size());
            for (auto [k, d] : path) {
                ord.erase(std::find(ord.begin(), ord.end(), k));
                edits.push_back({k, d ? ord[d - 1] : -1});
                ord.insert(ord.begin() + d, k);
            }
            return edits;
        };
        auto edits = anchorize(input_ops);
        std::array<bool, K> initial_extra{};  // the old lifted paper and old fillers
        if (initial.top_d >= 0) initial_extra[initial.top_d] = true;
        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;
        // Every candidate rebuilds its records from the same saved state (canonicalize keeps the
        // priority of the fillers listed there).
        const State seed = save();
        State best_state = seed;
        auto best_ops = input_ops;
        auto score = [&](size_t count) {
            return count + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();
        };
        double best_score = score(best_ops.size());
        // Keeps the trial if valid and better (best_ops / best_state / best_score). No-op edits are
        // dropped.
        auto evaluate = [&](const std::vector<Edit>& trial) {
            std::vector<int> ord = initial.order;
            std::vector<std::pair<int, int>> path;
            for (auto [k, a] : trial) {
                if (a == k) return false;
                const int p = int(std::find(ord.begin(), ord.end(), k) - ord.begin());
                int dest = a < 0 ? 0 : int(std::find(ord.begin(), ord.end(), a) - ord.begin()) + 1;
                if (p < dest) dest--;
                if (p == dest) continue;
                u64 covered = 0;
                for (int i = 0; i < p; i++) covered |= paper[ord[i]].opaque;
                if (!(paper[k].opaque & ~covered)) return false;
                ord.erase(ord.begin() + p);
                ord.insert(ord.begin() + dest, k);
                path.push_back({k, dest});
            }
            // Preserve the invariant needed by contiguous generic planning
            // and the +1 offset of helper insertion. The cap itself is never
            // an edit, so this also prevents a generic edit crossing the cap.
            const auto cap_it = std::find(ord.begin(), ord.end(), kCapPaper);
            for (auto it = ord.begin(); it != cap_it; ++it) if (*it < M) return false;
            u64 covered = 0, shown = 0;
            for (int k : ord) {
                shown |= paper[k].black & ~covered;
                covered |= paper[k].opaque;
            }
            if (shown != A[u]) return false;
            restore(seed);
            order = std::move(ord);
            canonicalize();
            if (!fillers_reachable()) return false;
            const double value = score(path.size());
            if (value + 1e-8 >= best_score) return false;
            best_score = value;
            best_ops = std::move(path);
            best_state = save();
            return true;
        };
        auto delete_singles = [&]() {
            bool any = false;
            for (int i = int(edits.size()) - 1; i >= 0; i--) {
                auto trial = edits;
                trial.erase(trial.begin() + i);
                if (evaluate(trial)) {
                    edits = anchorize(best_ops);
                    any = true;
                    i = std::min(i, int(edits.size()));  // other edits may have become no-ops
                }
            }
            return any;
        };
        for (int pass = 0; pass < 3; pass++)
            if (!delete_singles()) break;
        // Other anchors for an old lifted paper / old filler / a paper moved twice: the top, around
        // the papers of its column and the column boundaries (column papers), or around the other
        // papers out of the columns (a generic sheet).
        for (int i = int(edits.size()) - 1; i >= 0; i--) {
            const int k = edits[i].paper;
            if (!initial_extra[k]) {
                int repeats = 0;
                for (const auto& e : edits) repeats += e.paper == k;
                if (repeats < 2) continue;
            }
            std::vector<int> ord = initial.order;
            for (int t = 0; t < i; t++) {
                auto [x, a] = edits[t];
                ord.erase(std::find(ord.begin(), ord.end(), x));
                const int d = a < 0 ? 0 : int(std::find(ord.begin(), ord.end(), a) - ord.begin()) + 1;
                ord.insert(ord.begin() + d, x);
            }
            std::vector<int> anchors{-1};
            auto add = [&](int a) {
                if (a != k && std::find(anchors.begin(), anchors.end(), a) == anchors.end()) anchors.push_back(a);
            };
            int last = -1;
            std::array<bool, 64> seen{};
            for (int x : ord)
                if (x != k) {
                    if (col_of[k] < 0) {
                        if (col_of[x] < 0) add(last), add(x);
                    } else {
                        if (col_of[x] >= 0 && !seen[col_of[x]]) {
                            seen[col_of[x]] = true;
                            if (col_of[x] <= col_of[k]) add(last);
                        }
                        if (col_of[x] == col_of[k]) add(last), add(x);
                        if (col_of[x] < 0) add(x);
                    }
                    last = x;
                }
            for (int t = i + 1; t < int(edits.size()); t++)
                if (edits[t].paper == k) add(edits[t].anchor);
            auto chosen = edits;
            for (int a : anchors) {
                if (a == edits[i].anchor) continue;
                auto trial = edits;
                trial[i].anchor = a;
                if (evaluate(trial)) chosen = anchorize(best_ops);
            }
            edits = std::move(chosen);
            i = std::min(i, int(edits.size()));
        }
        delete_singles();
        post_saved += int(input_ops.size()) - int(best_ops.size());
        restore(best_state);
        return best_ops;
    }
    // The moves for request u: every combination of the plan options simulated on a copy of the
    // state, the cheapest valid one kept (display A_u, at most 2K moves, fillers reachable), and the
    // best plan without the joint choice again with the chain search (append_wide_chains). In
    // fast_mode, or when no plan is valid, the plain plan; if it is not legal either (it would move
    // an invisible paper, or more than 2K moves: fillers may hide each other), the full search, and
    // as the last resort no move at all (a wrong display, never an illegal output).
    long long unsafe_plans = 0;
    std::vector<std::pair<int, int>> process(int u) {
        init_adaptive();
        adaptive_request = u;
        const State st0 = save();
        if (fast_mode) {
            fast_requests++;
            ops.clear();
            invalid = false;
            check_vis = true;
            run_plan(u, PlanOpt{});
            check_vis = false;
            if (!invalid && ops.size() <= 2 * K) {
                canonicalize();
                return ops;
            }
            unsafe_plans++;
            restore(st0);
        }
        const int top0 = top_d, d = ded[u];
        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
        // without old fillers, their options are all the same
        const bool any_out = !fillers.empty();
        const std::vector<int> fms = any_out ? std::vector<int>{1, 4} : std::vector<int>{1};
        std::vector<PlanOpt> opts;
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : fms) opts.push_back({rm, fm, true});
        if (d != top0)
            for (int rm = 1; rm <= 2; rm++) opts.push_back({rm, 5, true});
        if (prev_ok)
            for (int fm : fms) opts.push_back({4, fm, true});
        double best = 1e18, best_normal = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        PlanOpt best_normal_opt;
        check_vis = true;
        tail_cache.clear();
        tail_cache_on = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double future = kEndWeight * adaptive_next_cost();
            double cost = ops.size() + kFillerCharge * fillers.size() + future;
            if (cost < best) best = cost, best_ops = ops, best_state = save();
            if (o.fret_mode != 5 && cost < best_normal) best_normal = cost, best_normal_opt = o;
        }
        tail_cache_on = false;
        int source = 0, chain_count = 0;  // the plan kept: 0 the options, 1 the chain search, 2 helpers
        if (best_normal < 1e17) {
            restore(st0);
            ops.clear();
            invalid = false;
            beam_enabled = true;
            run_plan(u, best_normal_opt);
            beam_enabled = false;
            if (!placement_chains.empty()) chain_trials++;
            for (const auto& ch : placement_chains) chain_count += ch.size();
            placement_chains.clear();
            if (!invalid && ops.size() <= 2 * K && display() == A[u] && fillers_reachable()) {
                double cost = ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();
                if (cost < best) best = cost, best_ops = ops, best_state = save(), source = 1;
            }
        }
        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {
            bool used = false;
            try_helpers(u, st0, [&](double cost) {
                if (cost < best) best = cost, best_ops = ops, best_state = save(), used = true;
            });
            interleave_selected += used;
            if (used) source = 2;
        }
        if (source == 1) chain_selected++, chain_papers += chain_count;
        if (best > 1e17) {
            plan_failures++;
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, PlanOpt{});
            check_vis = false;
            if (invalid || ops.size() > 2 * K) {
                unsafe_plans++;
                restore(st0);
                ops.clear();
            }
            return ops;
        }
        check_vis = false;
        restore(best_state);
        canonicalize();
        return post_optimize(st0, std::move(best_ops), u);
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, k, p, R;
    if (!(std::cin >> n >> k >> p >> R)) return 0;
    std::vector<u64> A(P);
    for (auto& a : A) {
        std::string s;
        std::cin >> s;
        a = 0;
        for (int j = 0; j < N; j++)
            if (s[j] == '1') a |= 1ULL << j;
    }
    if (n != N || k != K || p != P) return 0;
    const auto originalA = A;
    // Window assignment until kMapEnd and its greedy matching climb until kGoptEnd, annealing until
    // kAnnealEnd, climb until kClimbEnd (scaled s).
    constexpr double kMapEnd = 0.50, kGoptEnd = 0.61, kAnnealEnd = 1.305, kClimbEnd = 1.36, kFastAfter = 1.80;
    // A design not initialized by kInitExpiry (or failed after kInitGiveUp) falls back to the emergency design.
    constexpr double kInitGiveUp = 1.30, kInitExpiry = 1.35;
    // The helper tables (Interleave) are left unfinished (no helpers) after kHelperGiveUp.
    constexpr double kHelperGiveUp = 1.55;
    const int map_iters = env_int("MAP_ITERS"), anneal_iters = env_int("ANNEAL_ITERS");
    const int climb_iters = env_int("CLIMB_ITERS");
    std::vector<int> permutation(64);  // original window of each internal window
    int M = 8, G = env_int("EIGHT_G") ? env_int("EIGHT_G") : 40;
    Comparator comp;
    std::mt19937_64 rng(779879);
    std::unique_ptr<Design> des;
    int map_total = 0;
    // A design may fail (no matching of compatible pairs, or no column with both colors): retry with
    // fewer generic windows (32, then 28, without a new assignment the third time), then fall back.
    for (int attempt = 0;; attempt++) {
        A = originalA;
        for (u64& a : A) a &= kActiveWindows;
        std::iota(permutation.begin(), permutation.end(), 0);
        comp.init(M, G, rng);
        if (attempt < 2) {
            const double seconds = map_iters ? 1e9 : attempt == 0 ? kMapEnd - elapsed_sec() : 0.18;
            // the greedy matching climb (until kGoptEnd) on the first assignment only (GOPT_STEPS: fixed
            // steps, -1 none)
            const int gsteps = attempt ? 0 : std::max(0, env_int("GOPT_STEPS"));
            const double gsec = attempt || env_int("GOPT_STEPS") ? 0.0 : std::max(0.0, kGoptEnd - kMapEnd);
            auto ws = assign_windows(A, M, G, comp.edge, comp.polarity, permutation, seconds, map_iters, gsteps, gsec);
            map_total += ws.iterations;
            if (!attempt)
                std::cerr << "gobj_before = " << ws.gobj_before << "\ngobj_after = " << ws.gobj_after
                          << "\ngopt_steps = " << ws.climb_steps << '\n';
        }
        comp.rebuild();
        des = std::make_unique<Design>(A, M, G);
        // gcost: the exact mean number of moves of the generic layer from a uniform order, averaged over
        // the two targets of the pair (gpt6pro-09: the legal distance is not symmetric, and the
        // relations for b are those for a reversed): PosetSums::both_of / 1440 (= the mean of
        // Comparator::mean_moves for a and for b)
        auto estimate = [&](u64 a, u64 b) {
            const auto reach = comp.closure(a, a ^ b);
            u64 r = 0;
            for (int s = 0; s < M; s++) r |= u64(reach[s]) << (8 * s);
            return (Poset8Costs::get().cost(r) - 1) / 80640.0;
        };
        const bool untimed = map_iters > 0;
        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; }))
            break;
        std::cerr << "design_failed = 1\n"; return 0;
    }
    std::cerr << "map_iters = " << map_total << "\nmap_end_sec = " << elapsed_sec() << '\n';
    if (anneal_iters)
        des->anneal(1e9, anneal_iters);
    else
        des->anneal(std::max(0.005, kAnnealEnd - elapsed_sec()), 0);
    std::cerr << "anneal_iters = " << des->anneal_iters << "\nanneal_end_sec = " << elapsed_sec() << '\n';
    std::cerr << "colswap_tried = " << des->colswap_tried << "\ncolswap_accepted = " << des->colswap_accepted
              << "\nreplace_tried = " << des->replace_tried << "\nreplace_accepted = " << des->replace_accepted
              << '\n';
    if (climb_iters >= 0) {
        if (climb_iters)
            des->filler_climb(1e9, climb_iters);
        else
            des->filler_climb(std::max(0.0, kClimbEnd - elapsed_sec()), 0);
    }
    std::cerr << "climb_iters = " << des->climb_iters << "\nclimb_accepted = " << des->climb_accepted
              << "\nproxy_before = " << des->proxy_before / P << "\nproxy_after = " << des->proxy_after / P
              << "\nclimb_end_sec = " << elapsed_sec() << '\n';

    // Restore the cap bit only for the physical papers and online targets.
    // Assignment never moves index 63, and all design calculations used 63 bits.
    for (int u = 0; u < P; ++u) A[u] |= originalA[u] & kCapBit;
    double model_col = 0.0, model_hole = 0.0, model_gc = 0.0;
    for (int c = 0; c < des->H; ++c) model_col += des->colcost(c), model_hole += des->hcost(c);
    for (const auto& u : des->unit) model_gc += des->gc(u);
    std::cerr << "cap_window = " << kCapWindow
              << "\nmodel_cost = " << (model_col + model_hole + model_gc) / P
              << "\nmodel_col = " << model_col / P << "\nmodel_hole = " << model_hole / P
              << "\nmodel_gc = " << model_gc / P << '\n';

    if (env_int("MODEL_ONLY")) return 0;

    // Papers: six generic sheets, the cap, then the columns 0, 1, ... (colors alternate,
    // the more numerous first; singles before pairs within a color).
    std::vector<Paper> papers(K);
    std::vector<int> columns(K, -1), ded(P, -1);
    for (int i = 0; i < M; i++) papers[i] = {comp.opq[i], comp.black[i]};
    papers[kCapPaper] = {kCapBit, kCapBit};
    u64 opaque = low_bits(G) | kCapBit;
    int next = M + 1;
    // as6-majtop: the hole demand at each handle h_c (the targets of the columns above it; a pair that
    // differs there asks for both colors). The column's own papers mostly have the minority color (the
    // design absorbs them there), so the old rule (the more numerous own color first) showed the
    // minority color on most handles at the start; now the demand majority goes on top, the other
    // color second (both colors in the top two, as the design model assumes), then as before.
    std::vector<std::array<int, 2>> demand(des->H, {0, 0});
    for (const auto& u : des->unit)
        for (int c = u.c + 1; c < des->H; c++) {
            demand[c][des->hb[u.a] >> c & 1]++;
            if (u.b >= 0) demand[c][des->hb[u.b] >> c & 1]++;
        }
    for (int c = 0; c < des->H; c++) {
        opaque |= 1ULL << des->handle[c];
        std::array<std::vector<int>, 2> members;
        for (int x = 0; x < des->U; x++)
            if (des->unit[x].c == c) members[des->color(des->unit[x], c)].push_back(x);
        for (auto& group : members)
            std::stable_sort(group.begin(), group.end(),
                             [&](int x, int y) { return des->weight(des->unit[x]) < des->weight(des->unit[y]); });
        const int majority = demand[c][1] > demand[c][0];
        for (int step = 0; !members[0].empty() || !members[1].empty(); step++) {
            int color = members[1].size() > members[0].size();
            if (step < 2 && !members[majority ^ step].empty()) color = majority ^ step;
            int x = members[color].back();
            members[color].pop_back();
            const auto& u = des->unit[x];
            u64 mask = opaque;
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            mask |= kCapBit;
            u64 black = A[u.a] & mask;
            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;
            papers[next] = {mask, black};
            columns[next] = c;
            ded[u.a] = next;
            if (u.b >= 0) ded[u.b] = next;
            next++;
        }
    }
    if (next != K || std::find(ded.begin(), ded.end(), -1) != ded.end()) return 0;
    Solver solver(A);
    solver.M = M;
    solver.G = G;
    solver.H = des->H;
    solver.comparator = comp;
    solver.paper = papers;
    solver.col_of = columns;
    solver.ded = ded;
    solver.handle = des->handle;
    solver.hidx.assign(64, -1);
    for (int c = 0; c < des->H; c++) solver.hidx[solver.handle[c]] = c;
    solver.gmask = low_bits(G);
    solver.hmask = kActiveWindows & ~solver.gmask;
    solver.h_opq.resize(K);
    solver.h_blk.resize(K);
    for (int x = 0; x < K; x++) {
        solver.h_opq[x] = solver.handle_bits(papers[x].opaque);
        solver.h_blk[x] = solver.handle_bits(papers[x].black);
    }
    solver.order.resize(K);
    std::iota(solver.order.begin(), solver.order.end(), 0);
    // Model the one initial legal cap move now; emit it before the first plan.
    solver.order.erase(solver.order.begin() + kCapPaper);
    solver.order.insert(solver.order.begin(), kCapPaper);
    solver.init_adaptive();
    if (M == Interleave::GM && comp.complete) {
        solver.interleave = std::make_shared<Interleave>();
        solver.comparator.build_tables();
        solver.interleave->init(solver.comparator, papers, A, ded, columns, solver.gmask, solver.hmask, kHelperGiveUp);
        solver.init_lookahead();
    }
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\n';
#ifdef SIM_HARNESS
    // Experiments only (-DSIM_HARNESS): SIM_SEQS=n random request sequences (as the generator:
    // uniform, never the same target twice in a row) on copies of the solver; prints the mean moves
    // per request and exits.
    if (int ns = env_int("SIM_SEQS"); ns > 0) {
        double tot = 0;
        long long wr = 0;
        for (int q = 0; q < ns; q++) {
            Solver sim = solver;
            std::mt19937_64 rr(1000003ULL * (q + 1));
            int prev = rr() % P;
            for (int t = 0; t < R; t++) {
                int u = t == 0 ? prev : int(rr() % (P - 1));
                if (t > 0 && u >= prev) u++;
                prev = u;
                tot += sim.process(u).size();
                wr += sim.display() != A[u];
            }
        }
        std::cerr << "sim_moves = " << tot / (double(ns) * R) << "\nsim_wrong = " << double(wr) / ns << '\n';
        return 0;
    }
#endif

    // as6-cap38p0: the cap is output as paper 0 (the generic sheets 0..5 as 1..6, the rest unchanged),
    // so that the initial order already has it on top and no first move is needed. Internally the
    // papers keep their numbers; out_index maps them in the output.
    auto out_index = [](int k) { return k == kCapPaper ? 0 : k < kCapPaper ? k + 1 : k; };
    std::vector<int> out_order(K);
    for (int k = 0; k < K; k++) out_order[out_index(k)] = k;
    std::string output;
    for (int o = 0; o < K; o++) {
        const auto& pp = papers[out_order[o]];
        std::string row(N, '.');
        for (int j = 0; j < N; j++) row[permutation[j]] = !(pp.opaque >> j & 1) ? '.' : (pp.black >> j & 1) ? '1' : '0';
        output += row + '\n';
    }
    std::cout << output << std::flush;
    long long total = 0, generic = 0, wrong = 0;
    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == -1) return 0;
        const double t_req = elapsed_sec();
        // Safety net against a slow machine: the light plan from kFastAfter on.
        if (t_req > kFastAfter) solver.fast_mode = true;
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != A[u];
        output = std::to_string(moves.size()) + '\n';
        for (auto [x, d] : moves) {
            output += std::to_string(out_index(x)) + ' ' + std::to_string(d) + '\n';
            generic += x < M;
        }
        std::cout << output << std::flush;
        total += moves.size();
    }
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total
              << "\nG = " << G << "\nplan_failures = " << solver.plan_failures
              << "\nfast_requests = " << solver.fast_requests << "\npost_saved = " << solver.post_saved
              << "\nhelper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0)
              << "\ninterleave_trials = " << solver.interleave_trials
              << "\ninterleave_selected = " << solver.interleave_selected << "\ntail_hits = " << solver.tail_hits
              << "\nchain_trials = " << solver.chain_trials << "\nchain_selected = " << solver.chain_selected
              << "\nchain_papers = " << solver.chain_papers << "\nunsafe_plans = " << solver.unsafe_plans
              << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
