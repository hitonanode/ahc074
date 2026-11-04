struct MixedDesign {
    struct Unit {
        int a = -1, b = -1, c = -1;
    };
    #ifndef PRIORITY_NUM
#define PRIORITY_NUM 20
#endif
    static constexpr double kHoleWeight = 0.40, kRankPriority = PRIORITY_NUM/20.;
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
    static constexpr double reset_strength = 2.0;
    int own0=-1,own1=-1;
    std::array<double,P> single_cost{};
    bool mixed()const{return own0>=0;}
    std::vector<float> reset_targets;
    std::vector<double> cval;              // colcost of the current counts
    double cur = 0;
    int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
    int colswap_tried = 0, colswap_accepted = 0, replace_tried = 0, replace_accepted = 0;  // (anneal)
    double proxy_before = 0, proxy_after = 0;

    static int pc(u64 x) { return __builtin_popcountll(x); }
    MixedDesign(const std::vector<u64>& a, int m, int g) : M(m), G(g), H(63 - g), U(191 - m), need(256 - U), A(a) {
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
        reset_targets.assign(H,0);
    }
    bool valid(const Unit& u, int c) const { return !invalid_bit(u,c); }
    // valid without branches: the pair differences of u (0 for a single) at column c
    int invalid_bit(const Unit& u, int c) const {
        if(mixed()){
            bool own=u.a==own0||u.a==own1||u.b==own0||u.b==own1;
            if(own)return u.b>=0||c!=0;
            if(c==0)return 1;
        }
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
    static_assert(PRIORITY_NUM>=0&&PRIORITY_NUM<=20);
    __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        const int base2 = nt * (nc - 1);
        const int minimum2 = nc * (nc - 1) + np * (np - 1) + 2 * correction;
        return (20-PRIORITY_NUM)*base2 + PRIORITY_NUM*minimum2 + 4000000 * int((n1 == 0) | (n1 == nc));
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
    double hcost(int j) const {
        if(mixed()&&j==0)return 0;
        double x=hn[j][0],y=hn[j][1],t=reset_targets[j];
        return 4*kHoleWeight*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);
    }
    void refresh_reset(){
        for(int c=0;c<H;c++)reset_targets[c]=float(reset_strength*nt[c]);
        rebuild();
    }
    double gc(const Unit& u) const { return u.b < 0 ? single_cost[u.a] : gcost[u.a][u.b] * 2; }
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
                if (mixed()&&(a==own0||a==own1||b==own0||b==own1))continue;
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
            refresh_reset();
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
        MixedDesign& D;
        const int H, U;
        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {}, reset[L] = {}, hole_weight[L] = {};
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
            const __m128i retrieval = _mm_add_epi32(_mm_mullo_epi32(base2,_mm_set1_epi32(20-PRIORITY_NUM)),_mm_mullo_epi32(minimum2,_mm_set1_epi32(PRIORITY_NUM)));
            const __m128i penalty = _mm_and_si128(_mm_set1_epi32(4000000),
                _mm_or_si128(_mm_cmpeq_epi32(n1, z), _mm_cmpeq_epi32(n1, nc)));
            return _mm_add_epi32(retrieval, penalty);
        }
        static const float* bit_lanes(unsigned v) { return kBitLanes[v].data(); }
        ANNEAL_TARGET static float qf(float a, float b,float reset) {  // the same operations as eval_holes per lane
            const float s = a + b + reset;
            return (a*b+.5f*reset*std::min(a,b))/(s>1.f?s:1.f);
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
                const __m256 reset_count=_mm256_load_ps(reset+8*r);
                const __m256 s = _mm256_max_ps(_mm256_add_ps(_mm256_add_ps(N0[r],N1[r]),reset_count),one);
                const __m256 numerator=_mm256_fmadd_ps(_mm256_mul_ps(_mm256_set1_ps(.5f),reset_count),_mm256_min_ps(N0[r],N1[r]),_mm256_mul_ps(N0[r],N1[r]));
                Q[r] = _mm256_mul_ps(_mm256_div_ps(numerator,s),_mm256_load_ps(hole_weight+8*r));
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

        explicit Annealer(MixedDesign& d) : D(d), H(d.H), U(d.U), rows(d.H), key(d.U) {
            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            for(int j=0;j<L;j++)hole_weight[j]=D.mixed()&&j==0?0:1;
            for(int j=0;j<H;j++){reset[j]=D.reset_targets[j];n0[j]=float(D.hn[j][0]);n1[j]=float(D.hn[j][1]);hq[j]=qf(n0[j],n1[j],reset[j])*hole_weight[j];}
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
            if(D.mixed()&&(a==0||b==0))return;
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
            const float qa = qf(na0, na1,reset[a]), qb = qf(nb0, nb1,reset[b]);
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
            if(D.mixed()&&(a==0||b==0))return;
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
            for(int i=0;i<k;i++)if(D.invalid_bit(nu[i],nu[i].c))return;
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
#ifdef VERIFY_RESET_COST
                if((it&4095)==0){for(auto u:D.unit)assert(D.valid(u,u.c));MixedDesign check=D;check.rebuild();assert(std::abs(check.cur-cur)<.03);}
#endif
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
    // Expected positive benefit of a donor, including the shared paper's
    // internal holes. Independent wrong-color probabilities approximate the
    // current column heads; 1.6 moves account for placement and later return.
    static constexpr double demand_weight = 1.0;
    static double filler_gain(u64 tb, int l, u64 targetdiff, u64 yb, u64 dy, int c, const double* q) {
        if (c == l) return 0;
        u64 holes = ~low_bits(l + 1);
        holes |= targetdiff;
        u64 range = low_bits(c + 1) & ~dy & holes;
        u64 mis = (yb ^ tb) & range;
        int level = mis ? 64 - __builtin_clzll(mis) : 0;
        if (level > c) return 0;
        u64 covered = range & low_bits(c) & ~low_bits(level);
        double p0 = 1, p1 = 0, expected = 0;
        for (u64 z = covered; z; z &= z - 1) {
            int j = __builtin_ctzll(z);
            double p = 0.5 * (q[j + 1] - q[j]);
            expected += p;
            p1 = p1 * (1 - p) + p0 * p;
            p0 *= 1 - p;
        }
        return std::max(0.0, expected - (1 - p0) - 0.6 * (1 - p0 - p1));
    }
    static constexpr double head_mix = 1.0;
    // Sum each paper's potential over all requests, then model a column head as
    // a mixture of a random paper of its color and its strongest eligible paper.
    // Eligibility keeps the largest direct frequency (pairs ahead of singles).
    void filler_climb(double seconds, int fixedIterations = 0) {
        refresh_reset();
        auto start = std::chrono::steady_clock::now();
        std::vector<u64> diffb(U);
        for (int x=0;x<U;x++) if(unit[x].b>=0)diffb[x]=hb[unit[x].a]^hb[unit[x].b];
        std::vector<std::vector<double>> q(256,std::vector<double>(H+1));
        std::vector<std::array<double,2>> color_probability(H);
        std::vector<std::array<int,2>> max_weight(H);
        std::vector<std::vector<int>> members(H);
        for(int c=0;c<H;c++){
            double n=hn[c][0]+hn[c][1];double p=n?hn[c][1]/n:.5;
            color_probability[c]={1-p,p};
        }
        for(int t=0;t<256;t++)for(int c=0;c<H;c++)q[t][c+1]=q[t][c]+2*color_probability[c][(hb[t]>>c&1)^1];
        for(int x=0;x<U;x++){auto u=unit[x];members[u.c].push_back(x);max_weight[u.c][color(u,u.c)]=std::max(max_weight[u.c][color(u,u.c)],weight(u));}
        auto gain=[&](int t,int y,int c){return filler_gain(hb[t],unit[owner[t]].c,diffb[owner[t]],hb[unit[y].a],diffb[y],c,q[t].data());};
        std::vector<double> utility(U);
        for(int y=0;y<U;y++)for(int t=0;t<256;t++)utility[y]+=gain(t,y,unit[y].c);
        auto column_value=[&](int c){
            std::array<double,2>sum{},best{};std::array<int,2>count{};
            for(int y:members[c]){int b=color(unit[y],c);sum[b]+=utility[y];count[b]++;if(weight(unit[y])==max_weight[c][b])best[b]=std::max(best[b],utility[y]);}
            double value=0;for(int b=0;b<2;b++)if(count[b])value+=color_probability[c][b]*((1-head_mix)*sum[b]/count[b]+head_mix*best[b]);
            return value;
        };
        std::vector<double> colvalue(H);
        double proxy=0;for(int c=0;c<H;c++)proxy+=colvalue[c]=column_value(c);proxy_before=proxy;
        for(int it=0;;it++){
            if(fixedIterations>0?it>=fixedIterations:((it&63)==0&&CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>=seconds))break;
            climb_iters=it+1;int x=rng.below(U),y=rng.below(U),a=unit[x].c,b=unit[y].c;
            if(a==b||(unit[x].b>=0)!=(unit[y].b>=0))continue;
            Unit ox=unit[x],oy=unit[y],nx=ox,ny=oy;nx.c=b;ny.c=a;
            if(!valid(nx,b)||!valid(ny,a)||color(nx,b)!=color(oy,b)||color(ny,a)!=color(ox,a))continue;
            std::vector<int>moved;for(int t:{ox.a,ox.b,oy.a,oy.b})if(t>=0)moved.push_back(t);
            auto old_utility=utility;
            // Moving a target changes the contribution to every donor; moving
            // the two donors also changes their opacity and allowed placement.
            for(int z=0;z<U;z++)if(z!=x&&z!=y)for(int t:moved)utility[z]-=gain(t,z,unit[z].c);
            unit[x]=nx;unit[y]=ny;
            utility[x]=utility[y]=0;
            for(int t=0;t<256;t++)utility[x]+=gain(t,x,b),utility[y]+=gain(t,y,a);
            for(int z=0;z<U;z++)if(z!=x&&z!=y)for(int t:moved)utility[z]+=gain(t,z,unit[z].c);
            auto ix=std::find(members[a].begin(),members[a].end(),x),iy=std::find(members[b].begin(),members[b].end(),y);*ix=y;*iy=x;
            double next=0;for(int c=0;c<H;c++)next+=column_value(c);
            double old=cur;update(ox,-1);update(oy,-1);update(nx,1);update(ny,1);
            if(cur-old-demand_weight*(next-proxy)<-1e-9){proxy=next;climb_accepted++;}
            else{
                update(nx,-1);update(ny,-1);update(ox,1);update(oy,1);cur=old;
                unit[x]=ox;unit[y]=oy;*ix=x;*iy=y;utility=std::move(old_utility);
            }
        }
        
#ifdef VERIFY_HEAD_CLIMB
        std::vector<double> full(U);
        for(int y=0;y<U;y++)for(int t=0;t<256;t++)full[y]+=gain(t,y,unit[y].c);
        for(int y=0;y<U;y++)assert(std::abs(full[y]-utility[y])<1e-7);
        double exact_proxy=0;for(int c=0;c<H;c++)exact_proxy+=column_value(c);
        assert(std::abs(proxy-exact_proxy)<1e-7);
        double exact_cur=cur;rebuild();assert(std::abs(cur-exact_cur)<1e-6);
#endif
        proxy_after=proxy;rebuild();
    }

};
