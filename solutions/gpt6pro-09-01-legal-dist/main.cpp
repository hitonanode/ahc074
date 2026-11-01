// Ported from other_agents/gpt6pro-09-solution.cpp: <bits/stdc++.h> replaced by
// individual headers (stderr statistics were already `name = value` lines).
// AHC074: Layered Barcode Display -- standalone C++20 solution.
// Derived from the user-supplied comparator/column solution.
// Structural changes:
//   1. Optimize the disjoint 70-pair matching used by the design.
//   2. Use exact legal six-paper distances, with both dual posets scored.
//   3. Memoize identical generic plans and complete planning prefixes.
// The table below is an exhaustive combinatorial computation, not test data.
// Default time budgets are unchanged from the supplied implementation.
// Build: g++ -std=c++20 -O3 -march=native solution.cpp -o solution
// Read one request per response; every response is explicitly flushed.

#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include <immintrin.h>
using u64 = std::uint64_t;
namespace {
    constexpr int N = 64, K = 192, P = 256;
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
    const auto kStartTime = std::chrono::steady_clock::now();
    double elapsed_sec() {
        return CLOCK_SCALE * std::chrono::duration < double >(std::chrono::steady_clock::now() - kStartTime).count();
    }
    int env_int(const char * n) {
        const char * s = std::getenv(n);
        return s ? std::atoi(s) : 0;
    }
    u64 low_bits(int n) {
        return n == 64 ? ~0ULL :(1ULL << n) - 1;
    }
    struct XorShift {
        u64 x;
        u64 next() {
            x ^= x << 7;
            x ^= x >> 9;
            return x;
        }
        int mod(int n) {
            return int(next() % n);
        }
        int below(int n) {
            return int(((unsigned __int128) next() * unsigned(n)) >> 64);
        }
        double real() {
            return(next() >> 11) * 0x1.0p-53;
        }
    };
    struct Comparator {
        int M = 0, G = 0;
        bool complete = false;
        std::vector < std::pair < int, int >> edge;
        std::vector < int > polarity;
        std::vector < u64 > opq, black;
        void init(int m, int g, std::mt19937_64 & rng) {
            M = m;
            G = g;
            std::vector < std::pair < int, int >> all;
            for (int a = 0; a < M; a++) for (int b = a + 1; b < M; b++) all.emplace_back(a, b);
            std::shuffle(all.begin(), all.end(), rng);
            edge.resize(G);
            polarity.resize(G);
            for (int j = 0; j < G; j++) {
                edge[j] = all[j % all.size()];
                polarity[j] = int(rng() & 1);
            }
            rebuild();
        }
        void rebuild() {
            assert(1 < M && M <= 12 && 0 < G && G <= 64);
            opq.assign(M, 0);
            black.assign(M, 0);
            std::array < unsigned, 12 > adj {
            };
            for (int j = 0; j < G; j++) {
                auto[a, b] = edge[j];
                u64 bit = 1ULL << j;
                opq[a] |= bit;
                opq[b] |= bit;
                black[polarity[j] ? a : b] |= bit;
                adj[a] |= 1U << b;
                adj[b] |= 1U << a;
            }
            complete = true;
            for (int i = 0; i < M; i++) complete &=(adj[i] |(1U << i)) ==(1U << M) - 1;
        }
        std::array < unsigned, 12 > closure(u64 target, u64 holes) const {
            std::array < unsigned, 12 > reach {
            };
            holes &= low_bits(G);
            while (holes) {
                int j = __builtin_ctzll(holes);
                holes &= holes - 1;
                auto[a, b] = edge[j];
                if (int((target >> j) & 1) != polarity[j]) std::swap(a, b);
                reach[a] |= 1U << b;
            }
            for (int k = 0; k < M; k++) for (int a = 0; a < M; a++) if ((reach[a] >> k) & 1) reach[a] |= reach[k];
            return reach;
        }
        bool compatible(u64 a, u64 b) const {
            auto reach = closure(a, a ^ b);
            for (int i = 0; i < M; i++) if ((reach[i] >> i) & 1) return false;
            return true;
        }
        std::vector < std::vector < int >> perms;
        std::vector < std::vector < unsigned >> below;
        std::vector < uint8_t > dist;
        void build_tables() {
            if (!perms.empty()) return;
            std::vector < int > o(M);
            std::iota(o.begin(), o.end(), 0);
            do perms.push_back(o);
            while (std::next_permutation(o.begin(), o.end()));
            const int n = perms.size();
            below.assign(n, std::vector < unsigned >(M, 0));
            for (int t = 0; t < n; t++) for (int i = M - 1, acc = 0; i >= 0; i--) {
                below[t][perms[t][i]] = acc;
                acc |= 1 << perms[t][i];
            }
            dist.resize(n * n);
            std::vector < int > dp((M + 1) *(M + 1));
            for (int a = 0; a < n; a++) for (int b = 0; b < n; b++) {
                for (int i = 1; i <= M; i++) for (int j = 1; j <= M; j++) dp[i *(M + 1) + j] = perms[a][i - 1] == perms[b][j - 1] ? dp[(i - 1) *(M + 1) + j - 1] + 1 : std::max(dp[(i - 1) *(M + 1) + j],
                dp[i *(M + 1) + j - 1]);
                dist[a * n + b] = M - dp[M *(M + 1) + M];
            }
        }
        std::vector < std::pair < u64, double >> memo;
        double mean_moves(u64 target, u64 holes) {
            build_tables();
            auto reach = closure(target, holes);
            u64 key = 0;
            for (int a = 0; a < M; a++) key |= u64(reach[a]) <<(6 * a);
            auto it = std::lower_bound(memo.begin(), memo.end(), std::make_pair(key, - 1.0));
            if (it != memo.end() && it->first == key) return it->second;
            const int n = perms.size();
            std::vector < int > sat;
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
                    for (int t : sat) if ((m = std::min < int >(m, dist[s * n + t])) == 0) break;
                    sum += m;
                }
                mean = sum / n;
            }
            memo.insert(it, {
                key, mean
            });
            return mean;
        }
        std::vector < std::pair < int, int >> plan(const std::vector < int > & current, u64 target, u64 holes) const {
            if (!complete || int(current.size()) != M) return {
                {
                    - 1, - 1
                }
            };
            auto reach = closure(target, holes);
            for (int i = 0; i < M; i++) if ((reach[i] >> i) & 1) return {
                {
                    - 1, - 1
                }
            };
            bool satisfied = true;
            for (int i = 0; i < M; i++) for (int j = 0; j < i; j++) if ((reach[current[i]] >> current[j]) & 1) satisfied = false;
            if (satisfied) return {
            };
            std::array < unsigned, 12 > conflict {
            };
            for (int i = 0; i < M; i++) for (int j = 0; j < i; j++) if ((reach[current[i]] >> current[j]) & 1) {
                conflict[current[i]] |= 1U << current[j];
                conflict[current[j]] |= 1U << current[i];
            }
            std::array < unsigned char, 1 << 12 > valid {
            };
            valid[0] = 1;
            unsigned kept = 0;
            int best_count = - 1, witness = - 1;
            const int bottom = current.back();
            const unsigned bottom_bit = 1U << bottom, end = 1U << M;
            for (unsigned mask = 1; mask < end; mask++) {
                unsigned rest = mask &(mask - 1);
                int a = __builtin_ctz(mask);
                valid[mask] = valid[rest] && !(rest & conflict[a]);
                if (!valid[mask]) continue;
                int count = __builtin_popcount(mask);
                if (count <= best_count) continue;
                bool legal = mask & bottom_bit;
                int w = - 1;
                if (!legal) for (int b = 0; b < M; b++) {
                    if ((mask >> b & 1) || b == bottom) continue;
                    if (!(reach[b] &(mask | bottom_bit))) {
                        w = b;
                        legal = true;
                        break;
                    }
                }
                if (legal) {
                    kept = mask;
                    best_count = count;
                    witness = w;
                }
            }
            if (best_count < 0) return {
                {
                    - 1, - 1
                }
            };
            auto required = reach;
            int last = - 1;
            for (int a : current) if (kept >> a & 1) {
                if (last >= 0) required[last] |= 1U << a;
                last = a;
            }
            if (witness >= 0) {
                required[last] |= 1U << witness;
                required[bottom] |= 1U << witness;
            }
            std::array < unsigned, 12 > pred {
            };
            for (int a = 0; a < M; a++) for (int b = 0; b < M; b++) if (required[a] >> b & 1) pred[b] |= 1U << a;
            std::vector < int > goal;
            unsigned placed = 0;
            for (int step = 0; step < M; step++) {
                int next = - 1;
                for (int a : current) if (!(placed >> a & 1) && !(pred[a] & ~placed)) {
                    next = a;
                    break;
                }
                if (next < 0) return {
                    {
                        - 1, - 1
                    }
                };
                goal.push_back(next);
                placed |= 1U << next;
            }
            std::vector < int > order = current;
            std::vector < std::pair < int, int >> moves;
            for (int a : current) if (!(kept >> a & 1)) {
                u64 covered = 0;
                bool visible = false;
                for (int b : order) {
                    if (b == a) {
                        visible =(opq[a] & ~covered) != 0;
                        break;
                    }
                    covered |= opq[b];
                }
                if (!visible) return {
                    {
                        - 1, - 1
                    }
                };
                int successor = - 1;
                bool passed = false;
                for (int b : goal) {
                    if (passed &&(kept >> b & 1)) {
                        successor = b;
                        break;
                    }
                    if (b == a) passed = true;
                }
                int old = std::find(order.begin(), order.end(), a) - order.begin();
                order.erase(order.begin() + old);
                int depth = successor < 0 ? M - 1 : int(std::find(order.begin(), order.end(), successor) - order.begin());
                order.insert(order.begin() + depth, a);
                if (old != depth) moves.emplace_back(a, depth);
                kept |= 1U << a;
            }
            if (order != goal) return {
                {
                    - 1, - 1
                }
            };
            return moves;
        }
    };
    u64 closure8(u64 r, int m) {
        for (int k = 0; k < m; k++) r |=((r >> k) & 0x0101010101010101ULL) *((r >>(8 * k)) & 255);
        return r;
    }
    constexpr u64 kDiagonal = 0x8040201008040201ULL;
    struct WindowPairs {
        int n = 0, n4 = 0;
        std::vector < u64 > au, diff, dir;
        std::vector < double > base, w;
        std::vector < long long > rel;
        std::vector < int > u, v;
        void push(u64 a, u64 d, u64 r, int uu, int vv, double b, double ww, long long rr) {
            au.push_back(a);
            diff.push_back(d);
            dir.push_back(r);
            u.push_back(uu);
            v.push_back(vv);
            base.push_back(b);
            w.push_back(ww);
            rel.push_back(rr);
            n++;
        }
        void pad() {
            const int real = n;
            while (n % 4) push(0, 0, 0, 0, 0, 1., 0., 0);
            n4 = n;
            n = real;
        }
    };
#define AVX2_TARGET __attribute__((target("avx2,popcnt")))
    AVX2_TARGET inline __m256i set1_u64(u64 x) {
        return _mm256_set1_epi64x((long long) x);
    }
    AVX2_TARGET inline __m256i pick_nonzero(__m256i x, __m256i f) {
        return _mm256_andnot_si256(_mm256_cmpeq_epi64(x, _mm256_setzero_si256()), f);
    }
    AVX2_TARGET int evaluate_move(const WindowPairs & P, u64 pol, u64 erase, u64 ma, u64 mb, u64 fa, u64 ra, u64 fb,
    u64 rb, int a, int b, double f0, double f2, u64 * ndir, double * nbase, double * nw, long long * nrel, int * changed,
    double * delta) {
        const __m256i zero = _mm256_setzero_si256(), vpol = set1_u64(pol), vkeep = set1_u64(~erase), vma = set1_u64(ma),
        vmb = set1_u64(mb), vfa = set1_u64(fa), vra = set1_u64(ra), vfb = set1_u64(fb), vrb = set1_u64(rb), vbita = set1_u64(1ULL << a),
        vbitb = set1_u64(1ULL << b), c7 = set1_u64(0x00AA00AA00AA00AAULL), c14 = set1_u64(0x0000CCCC0000CCCCULL), c28 = set1_u64(0x00000000F0F0F0F0ULL);
        const __m256d one = _mm256_set1_pd(1.), vf0 = _mm256_set1_pd(f0), vf2 = _mm256_set1_pd(f2), zd = _mm256_setzero_pd();
        static const std::array < std::array < int, 4 >, 16 > kLanes =[] {
            std::array < std::array < int, 4 >, 16 > t {
            };
            for (int s = 0; s < 16; s++) for (int l = 0, k = 0; l < 4; l++) if (s >> l & 1) t[s][k++] = l;
            return t;
        }
        ();
        const u64 * const pau = P.au.data(), * const pdiff = P.diff.data(), * const pdir = P.dir.data();
        const double * const pbase = P.base.data(), * const pw = P.w.data();
        const long long * const prel = P.rel.data();
        const int * const pu = P.u.data(), * const pv = P.v.data();
        const int n4 = P.n4;
        int nch = 0;
        for (int p = 0; p < n4; p += 4) {
            const __m256i au = _mm256_loadu_si256((const __m256i *)(pau + p)), diff = _mm256_loadu_si256((const __m256i *)(pdiff + p)),
            dir = _mm256_loadu_si256((const __m256i *)(pdir + p)), z = _mm256_xor_si256(au, vpol), da = _mm256_and_si256(diff,
            vma), db = _mm256_and_si256(diff, vmb);
            __m256i r = _mm256_and_si256(dir, vkeep);
            r = _mm256_or_si256(r, pick_nonzero(_mm256_andnot_si256(z, da), vfa));
            r = _mm256_or_si256(r, pick_nonzero(_mm256_and_si256(z, da), vra));
            r = _mm256_or_si256(r, pick_nonzero(_mm256_andnot_si256(z, db), vfb));
            r = _mm256_or_si256(r, pick_nonzero(_mm256_and_si256(z, db), vrb));
            const __m256i na = _mm256_cmpeq_epi64(_mm256_and_si256(diff, vbita), zero), nb = _mm256_cmpeq_epi64(_mm256_and_si256(diff,
            vbitb), zero);
            const __m256d fa_only = _mm256_castsi256_pd(_mm256_andnot_si256(na, nb)), fb_only = _mm256_castsi256_pd(_mm256_andnot_si256(nb,
            na)), fac = _mm256_blendv_pd(_mm256_blendv_pd(one, vf0, fa_only), vf2, fb_only), base = _mm256_loadu_pd(pbase + p),
            w = _mm256_loadu_pd(pw + p), nbase4 = _mm256_mul_pd(base, fac);
            const __m256i rsame = _mm256_cmpeq_epi64(r, dir);
            const int chg = 15 & ~_mm256_movemask_pd(_mm256_and_pd(_mm256_castsi256_pd(rsame), _mm256_cmp_pd(nbase4, base, _CMP_EQ_OQ)));
            __m256i t = _mm256_and_si256(_mm256_xor_si256(r, _mm256_srli_epi64(r, 7)), c7), x = _mm256_xor_si256(r, _mm256_xor_si256(t,
            _mm256_slli_epi64(t, 7)));
            t = _mm256_and_si256(_mm256_xor_si256(x, _mm256_srli_epi64(x, 14)), c14);
            x = _mm256_xor_si256(x, _mm256_xor_si256(t, _mm256_slli_epi64(t, 14)));
            t = _mm256_and_si256(_mm256_xor_si256(x, _mm256_srli_epi64(x, 28)), c28);
            x = _mm256_xor_si256(x, _mm256_xor_si256(t, _mm256_slli_epi64(t, 28)));
            const __m256i noboth = _mm256_cmpeq_epi64(_mm256_and_si256(r, x), zero);
            const int need = _mm256_movemask_pd(_mm256_castsi256_pd(_mm256_andnot_si256(rsame, noboth)));
            const __m256d ok = _mm256_and_pd(_mm256_castsi256_pd(rsame), _mm256_cmp_pd(w, zd, _CMP_GT_OQ)), nw4 = _mm256_and_pd(ok,
            nbase4);
            _mm256_storeu_si256((__m256i *)(ndir + p), r);
            _mm256_storeu_pd(nbase + p, nbase4);
            _mm256_storeu_pd(nw + p, nw4);
            _mm256_storeu_si256((__m256i *)(nrel + p), _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i *)(prel + p))));
            for (int l = need; l; l &= l - 1) {
                const int i = p + __builtin_ctz(l);
                const u64 cl = closure8(ndir[i], 8);
                if (!(cl & kDiagonal)) nw[i] = nbase[i];
                nrel[i] = __builtin_popcountll(cl);
            }
            const int dl = _mm256_movemask_pd(_mm256_cmp_pd(_mm256_sub_pd(nw4, w), zd, _CMP_NEQ_UQ)) | need;
            for (int l = dl; l; l &= l - 1) {
                const int i = p + __builtin_ctz(l);
                if (const double dw = nw[i] - pw[i]; dw != 0) {
                    delta[pu[i]] += dw;
                    delta[pv[i]] += dw;
                }
            }
            _mm_storeu_si128((__m128i *)(changed + nch), _mm_add_epi32(_mm_set1_epi32(p), _mm_loadu_si128((const __m128i *) kLanes[chg].data())));
            nch += __builtin_popcount(chg);
        }
        return nch;
    }
    struct WindowStats {
        int iterations = 0;
        double score = 0, gobj_before = 0, gobj_after = 0;
        int climb_steps = 0;
    };
    static constexpr std::array < std::pair < u64, uint16_t >, 318 > kExactPosetCost = {
        {
            {
                0x0ULL, 0
            }, {
                0x10101010100ULL, 600
            }, {
                0x10102020000ULL, 960
            }, {
                0x10202020000ULL, 900
            }, {
                0x10204000000ULL, 1080
            }, {
                0x20202020000ULL, 576
            }, {
                0x20404000000ULL, 840
            }, {
                0x30102020000ULL, 1020
            }, {
                0x30202020000ULL, 936
            }, {
                0x30301020000ULL, 1080
            }, {
                0x30302020000ULL, 1056
            }, {
                0x30303020000ULL, 1116
            }, {
                0x30303030000ULL, 1152
            }, {
                0x30303030100ULL, 1176
            }, {
                0x30306020000ULL, 1394
            }, {
                0x30404000000ULL, 1000
            }, {
                0x30505010100ULL, 1440
            }, {
                0x30506000000ULL, 1380
            }, {
                0x30604000000ULL, 1239
            }, {
                0x30606020000ULL, 1398
            }, {
                0x30a02010000ULL, 1336
            }, {
                0x30a02020000ULL, 1278
            }, {
                0x30c00000000ULL, 1120
            }, {
                0x30c04000000ULL, 1300
            }, {
                0x40404000000ULL, 540
            }, {
                0x40800000000ULL, 720
            }, {
                0x50204000000ULL, 1140
            }, {
                0x50505010100ULL, 1140
            }, {
                0x50604000000ULL, 1214
            }, {
                0x50606000000ULL, 1324
            }, {
                0x50901010100ULL, 1320
            }, {
                0x50a02010000ULL, 1500
            }, {
                0x60204000000ULL, 954
            }, {
                0x60404000000ULL, 892
            }, {
                0x60601000000ULL, 1240
            }, {
                0x60604000000ULL, 1010
            }, {
                0x60606000000ULL, 1068
            }, {
                0x60606020000ULL, 1110
            }, {
                0x60800000000ULL, 900
            }, {
                0x60a02020000ULL, 1280
            }, {
                0x60c04000000ULL, 1210
            }, {
                0x70204000000ULL, 1164
            }, {
                0x70303020000ULL, 1406
            }, {
                0x70304000000ULL, 1306
            }, {
                0x70305010100ULL, 1524
            }, {
                0x70306020000ULL, 1481
            }, {
                0x70404000000ULL, 1004
            }, {
                0x70505010100ULL, 1452
            }, {
                0x70506000000ULL, 1404
            }, {
                0x70604000000ULL, 1250
            }, {
                0x70606000000ULL, 1340
            }, {
                0x70606020000ULL, 1416
            }, {
                0x70703020000ULL, 1516
            }, {
                0x70704000000ULL, 1332
            }, {
                0x70705010100ULL, 1560
            }, {
                0x70706000000ULL, 1436
            }, {
                0x70706020000ULL, 1520
            }, {
                0x70707000000ULL, 1476
            }, {
                0x70707010100ULL, 1608
            }, {
                0x70707020000ULL, 1566
            }, {
                0x70707030000ULL, 1632
            }, {
                0x70707030100ULL, 1680
            }, {
                0x70800000000ULL, 960
            }, {
                0x70901010100ULL, 1440
            }, {
                0x70a02020000ULL, 1396
            }, {
                0x70b01020000ULL, 1558
            }, {
                0x70b02020000ULL, 1476
            }, {
                0x70b03020000ULL, 1639
            }, {
                0x70b03030000ULL, 1720
            }, {
                0x70b03030100ULL, 1800
            }, {
                0x70c04000000ULL, 1316
            }, {
                0x70d05010100ULL, 1710
            }, {
                0x70e04000000ULL, 1396
            }, {
                0x70e06000000ULL, 1544
            }, {
                0x70e06020000ULL, 1659
            }, {
                0x80800000000ULL, 480
            }, {
                0x90901010100ULL, 1080
            }, {
                0xa0a02010000ULL, 1340
            }, {
                0xa0a02020000ULL, 1050
            }, {
                0xa0c00000000ULL, 1084
            }, {
                0xb0301020000ULL, 1348
            }, {
                0xb0302020000ULL, 1308
            }, {
                0xb0601020000ULL, 1529
            }, {
                0xb0a02010000ULL, 1423
            }, {
                0xb0a02020000ULL, 1316
            }, {
                0xb0b01020000ULL, 1458
            }, {
                0xb0b02020000ULL, 1402
            }, {
                0xb0b03020000ULL, 1514
            }, {
                0xb0b03030000ULL, 1572
            }, {
                0xb0b03030100ULL, 1620
            }, {
                0xb0c00000000ULL, 1170
            }, {
                0xb0d01010100ULL, 1524
            }, {
                0xb0e02020000ULL, 1481
            }, {
                0xc0800000000ULL, 810
            }, {
                0xc0c00000000ULL, 920
            }, {
                0xc0c04000000ULL, 1000
            }, {
                0xd0604000000ULL, 1325
            }, {
                0xd0901010100ULL, 1350
            }, {
                0xd0d01010100ULL, 1440
            }, {
                0xd0d05010100ULL, 1560
            }, {
                0xd0e00000000ULL, 1228
            }, {
                0xd0e04000000ULL, 1408
            }, {
                0xe0302020000ULL, 1398
            }, {
                0xe0304000000ULL, 1379
            }, {
                0xe0604000000ULL, 1241
            }, {
                0xe0800000000ULL, 912
            }, {
                0xe0a02020000ULL, 1311
            }, {
                0xe0c00000000ULL, 1120
            }, {
                0xe0c04000000ULL, 1252
            }, {
                0xe0e00000000ULL, 1188
            }, {
                0xe0e02020000ULL, 1400
            }, {
                0xe0e04000000ULL, 1334
            }, {
                0xe0e06000000ULL, 1440
            }, {
                0xe0e06020000ULL, 1520
            }, {
                0xf0301020000ULL, 1456
            }, {
                0xf0302020000ULL, 1410
            }, {
                0xf0304000000ULL, 1412
            }, {
                0xf0604000000ULL, 1340
            }, {
                0xf0703020000ULL, 1679
            }, {
                0xf0704000000ULL, 1432
            }, {
                0xf0705010100ULL, 1746
            }, {
                0xf0706000000ULL, 1580
            }, {
                0xf0706020000ULL, 1693
            }, {
                0xf0800000000ULL, 966
            }, {
                0xf0901010100ULL, 1452
            }, {
                0xf0a02010000ULL, 1568
            }, {
                0xf0a02020000ULL, 1411
            }, {
                0xf0b01020000ULL, 1603
            }, {
                0xf0b02020000ULL, 1515
            }, {
                0xf0b03020000ULL, 1684
            }, {
                0xf0b03030000ULL, 1760
            }, {
                0xf0b03030100ULL, 1836
            }, {
                0xf0c00000000ULL, 1192
            }, {
                0xf0c04000000ULL, 1340
            }, {
                0xf0d01010100ULL, 1560
            }, {
                0xf0d05010100ULL, 1752
            }, {
                0xf0e00000000ULL, 1260
            }, {
                0xf0e02020000ULL, 1518
            }, {
                0xf0e04000000ULL, 1440
            }, {
                0xf0e06000000ULL, 1592
            }, {
                0xf0e06020000ULL, 1704
            }, {
                0xf0f00000000ULL, 1296
            }, {
                0xf0f01010100ULL, 1608
            }, {
                0xf0f01020000ULL, 1668
            }, {
                0xf0f02020000ULL, 1564
            }, {
                0xf0f03020000ULL, 1754
            }, {
                0xf0f03030000ULL, 1840
            }, {
                0xf0f03030100ULL, 1920
            }, {
                0xf0f04000000ULL, 1484
            }, {
                0xf0f05010100ULL, 1824
            }, {
                0xf0f06000000ULL, 1652
            }, {
                0xf0f06020000ULL, 1770
            }, {
                0xf0f07000000ULL, 1728
            }, {
                0xf0f07010100ULL, 1920
            }, {
                0xf0f07020000ULL, 1856
            }, {
                0xf0f07030000ULL, 1960
            }, {
                0xf0f07030100ULL, 2040
            }, {
                0x100000000000ULL, 360
            }, {
                0x110101010100ULL, 960
            }, {
                0x110102020000ULL, 1220
            }, {
                0x120201020000ULL, 1220
            }, {
                0x120202020000ULL, 930
            }, {
                0x130102020000ULL, 1232
            }, {
                0x130201020000ULL, 1250
            }, {
                0x130202020000ULL, 1050
            }, {
                0x130301020000ULL, 1336
            }, {
                0x130302020000ULL, 1278
            }, {
                0x130303020000ULL, 1394
            }, {
                0x130303030000ULL, 1452
            }, {
                0x130303030100ULL, 1500
            }, {
                0x130306020000ULL, 1610
            }, {
                0x140402000000ULL, 1110
            }, {
                0x140404000000ULL, 880
            }, {
                0x150402000000ULL, 1230
            }, {
                0x150503010100ULL, 1680
            }, {
                0x150505010100ULL, 1440
            }, {
                0x160204000000ULL, 1140
            }, {
                0x160404000000ULL, 1000
            }, {
                0x160601000000ULL, 1380
            }, {
                0x160603020000ULL, 1624
            }, {
                0x160604000000ULL, 1217
            }, {
                0x160605000000ULL, 1516
            }, {
                0x160606000000ULL, 1324
            }, {
                0x160606020000ULL, 1402
            }, {
                0x170204000000ULL, 1242
            }, {
                0x170303020000ULL, 1514
            }, {
                0x170304000000ULL, 1408
            }, {
                0x170305010100ULL, 1710
            }, {
                0x170306020000ULL, 1644
            }, {
                0x170404000000ULL, 1060
            }, {
                0x170505010100ULL, 1560
            }, {
                0x170506000000ULL, 1548
            }, {
                0x170603020000ULL, 1653
            }, {
                0x170604000000ULL, 1330
            }, {
                0x170606000000ULL, 1436
            }, {
                0x170606020000ULL, 1518
            }, {
                0x170703020000ULL, 1694
            }, {
                0x170704000000ULL, 1436
            }, {
                0x170705010100ULL, 1752
            }, {
                0x170706000000ULL, 1592
            }, {
                0x170706020000ULL, 1696
            }, {
                0x170707000000ULL, 1644
            }, {
                0x170707010100ULL, 1824
            }, {
                0x170707020000ULL, 1763
            }, {
                0x170707030000ULL, 1858
            }, {
                0x170707030100ULL, 1932
            }, {
                0x180000000000ULL, 600
            }, {
                0x180800000000ULL, 780
            }, {
                0x190101010100ULL, 1080
            }, {
                0x190901010100ULL, 1320
            }, {
                0x1a0202010000ULL, 1340
            }, {
                0x1a0202020000ULL, 1050
            }, {
                0x1a0a02010000ULL, 1540
            }, {
                0x1a0a02020000ULL, 1285
            }, {
                0x1b0102020000ULL, 1340
            }, {
                0x1b0202010000ULL, 1352
            }, {
                0x1b0202020000ULL, 1110
            }, {
                0x1b0301020000ULL, 1456
            }, {
                0x1b0302020000ULL, 1398
            }, {
                0x1b0303020000ULL, 1514
            }, {
                0x1b0303030000ULL, 1572
            }, {
                0x1b0303030100ULL, 1620
            }, {
                0x1b0a02010000ULL, 1569
            }, {
                0x1b0a02020000ULL, 1401
            }, {
                0x1b0b01020000ULL, 1610
            }, {
                0x1b0b02020000ULL, 1517
            }, {
                0x1b0b03020000ULL, 1682
            }, {
                0x1b0b03030000ULL, 1766
            }, {
                0x1b0b03030100ULL, 1830
            }, {
                0x1c0000000000ULL, 660
            }, {
                0x1c0404000000ULL, 1000
            }, {
                0x1c0800000000ULL, 900
            }, {
                0x1c0c00000000ULL, 1080
            }, {
                0x1c0c04000000ULL, 1220
            }, {
                0x1d0101010100ULL, 1140
            }, {
                0x1d0505010100ULL, 1560
            }, {
                0x1d0901010100ULL, 1440
            }, {
                0x1d0d01010100ULL, 1560
            }, {
                0x1d0d05010100ULL, 1740
            }, {
                0x1e0000000000ULL, 696
            }, {
                0x1e0202020000ULL, 1110
            }, {
                0x1e0204000000ULL, 1230
            }, {
                0x1e0404000000ULL, 1060
            }, {
                0x1e0604000000ULL, 1331
            }, {
                0x1e0606000000ULL, 1440
            }, {
                0x1e0606020000ULL, 1520
            }, {
                0x1e0800000000ULL, 960
            }, {
                0x1e0a02020000ULL, 1401
            }, {
                0x1e0c00000000ULL, 1180
            }, {
                0x1e0c04000000ULL, 1330
            }, {
                0x1e0e00000000ULL, 1260
            }, {
                0x1e0e02020000ULL, 1520
            }, {
                0x1e0e04000000ULL, 1442
            }, {
                0x1e0e06000000ULL, 1590
            }, {
                0x1e0e06020000ULL, 1695
            }, {
                0x1f0000000000ULL, 720
            }, {
                0x1f0101010100ULL, 1176
            }, {
                0x1f0102020000ULL, 1400
            }, {
                0x1f0202020000ULL, 1146
            }, {
                0x1f0204000000ULL, 1290
            }, {
                0x1f0301020000ULL, 1516
            }, {
                0x1f0302020000ULL, 1458
            }, {
                0x1f0303020000ULL, 1574
            }, {
                0x1f0303030000ULL, 1632
            }, {
                0x1f0303030100ULL, 1680
            }, {
                0x1f0304000000ULL, 1472
            }, {
                0x1f0305010100ULL, 1800
            }, {
                0x1f0306020000ULL, 1734
            }, {
                0x1f0404000000ULL, 1096
            }, {
                0x1f0505010100ULL, 1620
            }, {
                0x1f0506000000ULL, 1626
            }, {
                0x1f0604000000ULL, 1388
            }, {
                0x1f0606000000ULL, 1496
            }, {
                0x1f0606020000ULL, 1578
            }, {
                0x1f0703020000ULL, 1769
            }, {
                0x1f0704000000ULL, 1492
            }, {
                0x1f0705010100ULL, 1836
            }, {
                0x1f0706000000ULL, 1664
            }, {
                0x1f0706020000ULL, 1780
            }, {
                0x1f0707000000ULL, 1728
            }, {
                0x1f0707010100ULL, 1920
            }, {
                0x1f0707020000ULL, 1856
            }, {
                0x1f0707030000ULL, 1960
            }, {
                0x1f0707030100ULL, 2040
            }, {
                0x1f0800000000ULL, 996
            }, {
                0x1f0901010100ULL, 1500
            }, {
                0x1f0a02010000ULL, 1646
            }, {
                0x1f0a02020000ULL, 1459
            }, {
                0x1f0b01020000ULL, 1681
            }, {
                0x1f0b02020000ULL, 1575
            }, {
                0x1f0b03020000ULL, 1762
            }, {
                0x1f0b03030000ULL, 1850
            }, {
                0x1f0b03030100ULL, 1926
            }, {
                0x1f0c00000000ULL, 1228
            }, {
                0x1f0c04000000ULL, 1384
            }, {
                0x1f0d01010100ULL, 1620
            }, {
                0x1f0d05010100ULL, 1830
            }, {
                0x1f0e00000000ULL, 1302
            }, {
                0x1f0e02020000ULL, 1578
            }, {
                0x1f0e04000000ULL, 1496
            }, {
                0x1f0e06000000ULL, 1662
            }, {
                0x1f0e06020000ULL, 1779
            }, {
                0x1f0f00000000ULL, 1344
            }, {
                0x1f0f01010100ULL, 1680
            }, {
                0x1f0f01020000ULL, 1764
            }, {
                0x1f0f02020000ULL, 1636
            }, {
                0x1f0f03020000ULL, 1862
            }, {
                0x1f0f03030000ULL, 1960
            }, {
                0x1f0f03030100ULL, 2040
            }, {
                0x1f0f04000000ULL, 1552
            }, {
                0x1f0f05010100ULL, 1932
            }, {
                0x1f0f06000000ULL, 1746
            }, {
                0x1f0f06020000ULL, 1872
            }, {
                0x1f0f07000000ULL, 1824
            }, {
                0x1f0f07010100ULL, 2040
            }, {
                0x1f0f07020000ULL, 1970
            }, {
                0x1f0f07030000ULL, 2098
            }, {
                0x1f0f07030100ULL, 2190
            },
        }
    };
    // Uniform mean distance is invariant under relabeling the six papers.
    // kExactPosetCost stores (transitively closed order, sum of the 720 legal directed distances)
    // for all 318 unlabeled six-element partial orders. It is generated exhaustively
    // from all subsets of the 15 forward arcs of a total order.
    struct ExactGenericMean {
        static constexpr unsigned LG = 18, SIZE = 1U << LG;
        std::vector < u64 > keys;
        std::vector < uint16_t > values, pair_values;
        static unsigned hash(u64 x) {
            x ^= x >> 27;
            x *= 0x3c79ac492ba7b653ULL;
            x ^= x >> 33;
            return unsigned(x) &(SIZE - 1);
        }
        ExactGenericMean() : keys(SIZE, ~0ULL), values(SIZE), pair_values(SIZE) {
            std::array < int, 6 > permutation = {
                0, 1, 2, 3, 4, 5
            };
            unsigned inserted = 0;
            do {
                std::array < u64, 48 > mapped {
                };
                for (int a = 0; a < 6; a++) for (int b = 0; b < 6; b++) mapped[8 * a + b] = 1ULL <<(8 * permutation[a] + permutation[b]);
                for (auto[canonical, cost] : kExactPosetCost) {
                    u64 r = 0;
                    for (u64 x = canonical; x; x &= x - 1) r |= mapped[__builtin_ctzll(x)];
                    unsigned slot = hash(r);
                    while (keys[slot] != ~0ULL && keys[slot] != r) slot =(slot + 1) &(SIZE - 1);
                    if (keys[slot] == ~0ULL) {
                        keys[slot] = r;
                        values[slot] = cost;
                        inserted++;
                    } else assert(values[slot] == cost);
                }
            } while (std::next_permutation(permutation.begin(), permutation.end()));
            assert(inserted == 130023);
            for (unsigned slot = 0; slot < SIZE; slot++) if (keys[slot] != ~0ULL) pair_values[slot] = values[slot] + sum(transpose(keys[slot]));
        }
        static u64 transpose(u64 r) {
            u64 t =(r ^(r >> 7)) & 0x00AA00AA00AA00AAULL;
            r ^= t ^(t << 7);
            t =(r ^(r >> 14)) & 0x0000CCCC0000CCCCULL;
            r ^= t ^(t << 14);
            t =(r ^(r >> 28)) & 0x00000000F0F0F0F0ULL;
            r ^= t ^(t << 28);
            return r;
        }
        uint16_t pair_sum(u64 closure) const {
            unsigned slot = hash(closure);
            while (keys[slot] != closure) {
                assert(keys[slot] != ~0ULL);
                slot =(slot + 1) &(SIZE - 1);
            }
            return pair_values[slot];
        }
        uint16_t sum(u64 closure) const {
            unsigned slot = hash(closure);
            while (keys[slot] != closure) {
                assert(keys[slot] != ~0ULL);
                slot =(slot + 1) &(SIZE - 1);
            }
            return values[slot];
        }
        static const ExactGenericMean & instance() {
            static const ExactGenericMean cache;
            return cache;
        }
    };
    double exact_generic_mean(const Comparator & cmp, u64 target, u64 holes) {
        assert(cmp.M == 6);
        auto reach = cmp.closure(target, holes);
        u64 relation = 0;
        for (int a = 0; a < 6; a++) relation |= u64(reach[a]) <<(8 * a);
        return ExactGenericMean::instance().sum(relation) / 720.0;
    }
    double legal_pair_generic_mean(const Comparator & cmp, u64 a, u64 b) {
        assert(cmp.M == 6);
        auto reach = cmp.closure(a, a ^ b);
        u64 r = 0;
        for (int i = 0; i < 6; i++) r |= u64(reach[i]) <<(8 * i);
        return ExactGenericMean::instance().pair_sum(r) / 1440.0;
    }
    WindowStats assign_windows(std::vector < u64 > & A, int m, int g, std::vector < std::pair < int, int >> & edges,
    std::vector < int > & polarity, std::vector < int > & permutation, double seconds, int fixed_iters, int climb_steps,
    double climb_seconds) {
        constexpr int kCutoff = 26, kHdQ = 4, kRelQ = 2;
        constexpr double kGenericWeight = 0.70, kWindowRate = 0.6;
        WindowStats stats;
        if (m > 8 || m < 2 || g >= 64 || g < m *(m - 1) / 2) return stats;
        const int n = A.size(), need = 256 -(192 - m);
        const auto start = std::chrono::steady_clock::now();
        XorShift rng {
            0x71eb2566be932e31ULL
        };
        std::vector < std::pair < int, int >> ep;
        int index[8][8];
        std::memset(index, - 1, sizeof (index));
        for (int a = 0; a < m; a++) for (int b = a + 1; b < m; b++) {
            index[a][b] = index[b][a] = ep.size();
            ep.emplace_back(a, b);
        }
        const int ne = ep.size();
        std::vector < u64 > mask(ne), fwd(ne), rev(ne);
        std::vector < int > which(64, - 1), counts(ne), order(64);
        std::iota(order.begin(), order.end(), 0);
        u64 pol = 0, hm = ~low_bits(g);
        for (int e = 0; e < ne; e++) {
            auto[a, b] = ep[e];
            fwd[e] = 1ULL <<(8 * a + b);
            rev[e] = 1ULL <<(8 * b + a);
        }
        for (int j = 0; j < g; j++) {
            auto[a, b] = edges[j];
            int e = index[a][b];
            which[j] = e;
            mask[e] |= 1ULL << j;
            counts[e]++;
            int c = polarity[j];
            if (a > b) c ^= 1;
            if (c) pol |= 1ULL << j;
        }
        for (int c : counts) if (!c) return stats;
        WindowPairs pairs;
        const double center = 24 *(1 -(1 - kGenericWeight) * g / 64.0);
        double bfactor[3];
        for (int d = - 1; d <= 1; d++) bfactor[d + 1] = std::exp(.35 *(1 - kGenericWeight) * d);
        for (int u = 0; u < n; u++) for (int v = u + 1; v < n; v++) {
            u64 d = A[u] ^ A[v];
            int h = __builtin_popcountll(d);
            if (h > kCutoff) continue;
            u64 r = 0, z = A[u] ^ pol;
            for (int e = 0; e < ne; e++) {
                u64 q = d & mask[e];
                if (q & ~z) r |= fwd[e];
                if (q & z) r |= rev[e];
            }
            const u64 cl = closure8(r, m);
            int hg = __builtin_popcountll(d & ~hm);
            double base = std::exp((center - h +(1 - kGenericWeight) * hg) * .35);
            pairs.push(A[u], d, r, u, v, base, cl & kDiagonal ? 0 : base, __builtin_popcountll(cl));
        }
        pairs.pad();
        const int np = pairs.n, np4 = pairs.n4;
        std::vector < u64 > ndir(np4);
        std::vector < double > nbase(np4), nw(np4), delta(n);
        std::vector < long long > nrel(np4);
        std::vector < int > changed(np4 + 4);
        // The exact initial-pair objective has denominator 3600:
        // .65*handle_distance + (forward_sum+dual_sum)/720 + .04*full_distance.
        // Stable two-pass nine-bit radix sorting preserves the pair-index tie order.
        struct KeyPair {
            uint32_t key;
            uint16_t pair;
        };
        std::vector < KeyPair > keyed(np), tmp(np), sorted(np);
        const ExactGenericMean & exact = ExactGenericMean::instance();
        auto matching_cost =[&](const double * valid, const u64 * dir, u64 handle_mask) {
            std::array < int, 512 > low {
            }, high {
            };
            int size = 0;
            for (int p = 0; p < np; p++) if (valid[p] > 0) {
                int hd = __builtin_popcountll(pairs.diff[p] & handle_mask);
                int full = __builtin_popcountll(pairs.diff[p]);
                int sum = exact.pair_sum(closure8(dir[p], 6));
                int key = 2340 * hd + 5 * sum + 144 * full;
                assert(key <(1 << 18));
                keyed[size++] = {
                    uint32_t(key), uint16_t(p)
                };
                low[key & 511]++;
                high[key >> 9]++;
            }
            int l = 0, h = 0;
            for (int i = 0; i < 512; i++) {
                int a = low[i], b = high[i];
                low[i] = l;
                high[i] = h;
                l += a;
                h += b;
            }
            for (int i = 0; i < size; i++) tmp[low[keyed[i].key & 511]++] = keyed[i];
            for (int i = 0; i < size; i++) sorted[high[tmp[i].key >> 9]++] = tmp[i];
            std::array < u64, 4 > used {
            };
            int matched = 0, total = 0;
            for (int i = 0; i < size; i++) {
                int p = sorted[i].pair, u = pairs.u[p], v = pairs.v[p];
                if ((used[u >> 6] >>(u & 63) & 1) ||(used[v >> 6] >>(v & 63) & 1)) continue;
                used[u >> 6] |= 1ULL <<(u & 63);
                used[v >> 6] |= 1ULL <<(v & 63);
                total += sorted[i].key;
                if (++ matched == need) break;
            }
            return double(total) /(need * 3600) +(need - matched) * 10.0;
        };
        struct Move {
            int ia, ib, a, b, kind, ea, eb, transfer;
            bool swindow;
            u64 olda, oldb, oldpol;
        };
        int nchanged = 0;
        auto propose =[&](Move & mv) {
            int ia = rng.mod(g), ib = rng.mod(g), a = order[ia], b = order[ib];
            bool swindow = rng.real() < kWindowRate;
            if (swindow) {
                ib = g + rng.mod(64 - g);
                b = order[ib];
            }
            int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];
            u64 olda = mask[ea], oldb = mask[eb], oldpol = pol;
            int transfer = - 1;
            if (swindow) {
                mask[ea] ^=(1ULL << a) |(1ULL << b);
                pol =(pol & ~(1ULL << b)) |(((oldpol >> a) & 1) << b);
            } else if (kind < 3) {
                pol ^= 1ULL << a;
                eb = ea;
                oldb = olda;
            } else if (kind < 8) {
                if (ea == eb) return false;
                mask[ea] ^=(1ULL << a) |(1ULL << b);
                mask[eb] ^=(1ULL << a) |(1ULL << b);
            } else {
                if (counts[ea] < 2) return false;
                eb = rng.mod(ne);
                if (ea == eb) return false;
                oldb = mask[eb];
                mask[ea] ^= 1ULL << a;
                mask[eb] |= 1ULL << a;
                transfer = eb;
            }
            mv = {
                ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol
            };
            std::fill(delta.begin(), delta.end(), 0.0);
            nchanged = evaluate_move(pairs, pol, fwd[ea] | rev[ea] | fwd[eb] | rev[eb], mask[ea], mask[eb], fwd[ea], rev[ea],
            fwd[eb], rev[eb], a, b, swindow ? bfactor[0] : 1.0, swindow ? bfactor[2] : 1.0, ndir.data(), nbase.data(), nw.data(),
            nrel.data(), changed.data(), delta.data());
            return true;
        };
        auto apply =[&](const Move & mv) {
            for (int i = 0; i < nchanged; i++) {
                int p = changed[i];
                pairs.dir[p] = ndir[p];
                pairs.base[p] = nbase[p];
                pairs.w[p] = nw[p];
                pairs.rel[p] = nrel[p];
            }
            if (mv.swindow) {
                which[mv.a] = - 1;
                which[mv.b] = mv.ea;
                std::swap(order[mv.ia], order[mv.ib]);
                hm ^=(1ULL << mv.a) |(1ULL << mv.b);
            } else {
                if (mv.kind >= 3 && mv.kind < 8) std::swap(which[mv.a], which[mv.b]);
                if (mv.transfer >= 0) {
                    counts[mv.ea]--;
                    counts[mv.eb]++;
                    which[mv.a] = mv.eb;
                }
            }
        };
        auto undo =[&](const Move & mv) {
            mask[mv.ea] = mv.olda;
            mask[mv.eb] = mv.oldb;
            pol = mv.oldpol;
        };
        double cur = matching_cost(pairs.w.data(), pairs.dir.data(), hm), best = cur;
        auto best_mask = mask;
        auto best_order = order;
        u64 best_pol = pol;
        double elapsed = 0;
        for (int it = 0;; it++) {
            if ((it & 15) == 0) {
                elapsed = CLOCK_SCALE * std::chrono::duration < double >(std::chrono::steady_clock::now() - start).count();
                if (elapsed >= seconds ||(fixed_iters > 0 && it >= fixed_iters)) break;
            }
            stats.iterations++;
            double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;
            Move mv;
            if (!propose(mv)) continue;
            u64 next_hm = hm ^(mv.swindow ?((1ULL << mv.a) |(1ULL << mv.b)) : 0);
            double candidate = matching_cost(nw.data(), ndir.data(), next_hm);
            double temperature = .2 * std::pow(.005 / .2, progress);
            if (candidate <= cur || rng.real() < std::exp((cur - candidate) / temperature)) {
                apply(mv);
                cur = candidate;
                if (cur < best - 1e-9) {
                    best = cur;
                    best_mask = mask;
                    best_order = order;
                    best_pol = pol;
                }
            } else undo(mv);
        }
        // Restore the best annealed state; the following pure matching climb has no
        // degree floor, so unused singleton products impose no artificial constraint.
        mask = best_mask;
        order = best_order;
        pol = best_pol;
        std::fill(which.begin(), which.end(), - 1);
        hm = ~0ULL;
        for (int e = 0; e < ne; e++) {
            counts[e] = __builtin_popcountll(mask[e]);
            hm &= ~mask[e];
            for (u64 x = mask[e]; x; x &= x - 1) which[__builtin_ctzll(x)] = e;
        }
        for (int p = 0; p < np; p++) {
            u64 r = 0, z = pairs.au[p] ^ pol, d = pairs.diff[p];
            for (int e = 0; e < ne; e++) {
                u64 q = d & mask[e];
                if (q & ~z) r |= fwd[e];
                if (q & z) r |= rev[e];
            }
            u64 cl = closure8(r, m);
            int h = __builtin_popcountll(d), hg = __builtin_popcountll(d & ~hm);
            pairs.dir[p] = r;
            pairs.base[p] = std::exp((center - h +(1 - kGenericWeight) * hg) * .35);
            pairs.w[p] = cl & kDiagonal ? 0 : pairs.base[p];
            pairs.rel[p] = __builtin_popcountll(cl);
        }
        cur = matching_cost(pairs.w.data(), pairs.dir.data(), hm);
        stats.gobj_before = cur;
        const auto climb_start = std::chrono::steady_clock::now();
        if (climb_steps > 0 || climb_seconds > 0) for (int it = 0;; it++) {
            if (climb_steps > 0 ? it >= climb_steps :((it & 15) == 0 && CLOCK_SCALE * std::chrono::duration < double >(std::chrono::steady_clock::now() - climb_start).count() >= climb_seconds)) break;
            stats.climb_steps = it + 1;
            Move mv;
            if (!propose(mv)) continue;
            u64 next_hm = hm ^(mv.swindow ?((1ULL << mv.a) |(1ULL << mv.b)) : 0);
            double candidate = matching_cost(nw.data(), ndir.data(), next_hm);
            if (candidate <= cur) {
                apply(mv);
                cur = candidate;
            } else undo(mv);
        }
        stats.gobj_after = cur;
        stats.score = - cur;
        for (int j = 0; j < g; j++) {
            int x = order[j], e = 0;
            while (e < ne && !(mask[e] >> x & 1)) e++;
            assert(e < ne);
            edges[j] = ep[e];
            polarity[j] = pol >> x & 1;
        }
        auto oldperm = permutation;
        for (int j = 0; j < 64; j++) permutation[j] = oldperm[order[j]];
        for (u64 & a : A) {
            u64 b = 0;
            for (int j = 0; j < 64; j++) b |=((a >> order[j]) & 1) << j;
            a = b;
        }
        return stats;
    }
    alignas(32) const std::array < std::array < float, 8 >, 256 > kBitLanes =[] {
        std::array < std::array < float, 8 >, 256 > a {
        };
        for (int v = 0; v < 256; v++) for (int i = 0; i < 8; i++) a[v][i] = float(v >> i & 1);
        return a;
    }
    ();
    struct Design {
        struct Unit {
            int a = - 1, b = - 1, c = - 1;
        };
        static constexpr double kHoleWeight = .40, kRankPriority = .85;
        XorShift rng {
            0x6176abcd1349ULL
        };
        int M, G, H, U, need;
        std::vector < u64 > A, hb;
        std::vector < int > handle, owner;
        std::vector < Unit > unit;
        std::vector < std::vector < int >> partners;
        std::array < std::array < uint8_t, 256 >, 256 > ok {
        };
        std::array < std::array < float, 256 >, 256 > gcost {
        };
        std::vector < int > nc, nt, n1, pairOne;
        std::vector < std::array < int, 2 >> hn;
        std::vector < double > cval;
        std::vector < std::vector < int >> cu;
        std::vector < int > cpos;
        double cur = 0;
        int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
        double proxy_before = 0, proxy_after = 0;
        static int pc(u64 x) {
            return __builtin_popcountll(x);
        }
        Design(const std::vector < u64 > & a, int m, int g) : M(m), G(g), H(64 - g), U(192 - m), need(256 - U), A(a) {
            handle.resize(H);
            std::iota(handle.begin(), handle.end(), G);
            hb.resize(256);
            for (int i = 0; i < 256; i++) hb[i] = A[i] >> G;
            owner.assign(256, - 1);
            partners.resize(256);
            nc.resize(H);
            nt.resize(H);
            n1.resize(H);
            pairOne.resize(H);
            hn.resize(H);
        }
        bool valid(const Unit & u, int c) const {
            return u.b < 0 ||(((hb[u.a] ^ hb[u.b]) >> c) & 1) == 0;
        }
        int invalid_bit(const Unit & u, int c) const {
            return int(((hb[u.a] ^ hb[u.b & 255]) &(u64(0) - u64(u.b >= 0))) >> c & 1);
        }
        int color(const Unit & u, int c) const {
            return hb[u.a] >> c & 1;
        }
        int weight(const Unit & u) const {
            return u.b < 0 ? 1 : 2;
        }
        u64 holes(const Unit & u) const {
            u64 d = u.b < 0 ? 0 : hb[u.a] ^ hb[u.b];
            return(low_bits(H) & ~low_bits(u.c + 1)) | d;
        }
        __attribute__((always_inline)) static double colcost_of(int nc, int nt, int n1, int p1) {
            const int imb = std::max(0, std::abs(nc - 2 * n1) - 1), p0 = nt - nc - p1;
            int firstPair = std::max(p0, p1);
            firstPair = 2 * n1 > nc ? p1 : firstPair;
            firstPair = 2 * n1 < nc ? p0 : firstPair;
            const int base2 = nt *(nc - 1), alt2 = nc *(nc - 1) + 2 *(p0 * p0 + p1 * p1 - firstPair);
            const double retrieval = base2 * .5 - kRankPriority *(std::max(0, base2 - alt2) * .5);
            return retrieval + 5. *(imb * imb) + 100000. * int((n1 == 0) |(n1 == nc));
        }
        double colcost(int c) const {
            return colcost_of(nc[c], nt[c], n1[c], pairOne[c]);
        }
        __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
            const int imb = std::max(0, std::abs(nc - 2 * n1) - 1), p0 = nt - nc - p1;
            int firstPair = std::max(p0, p1);
            firstPair = 2 * n1 > nc ? p1 : firstPair;
            firstPair = 2 * n1 < nc ? p0 : firstPair;
            const int base2 = nt *(nc - 1), alt2 = nc *(nc - 1) + 2 *(p0 * p0 + p1 * p1 - firstPair);
            return 20 * base2 - 17 * std::max(0, base2 - alt2) + 200 *(imb * imb) + 4000000 * int((n1 == 0) |(n1 == nc));
        }
        static const std::array < double, 257 * 257 > & hole_table() {
            static const std::array < double, 257 * 257 > table =[] {
                std::array < double, 257 * 257 > t {
                };
                for (int x = 0; x <= 256; x++) for (int y = 0; y <= 256; y++) if (x + y) t[x * 257 + y] = kHoleWeight *(4. * x * y /(x + y));
                return t;
            }
            ();
            return table;
        }
        double hcost(int j) const {
            return hole_table()[hn[j][0] * 257 + hn[j][1]];
        }
        double gc(const Unit & u) const {
            return u.b < 0 ? 0 : gcost[u.a][u.b] * 2;
        }
        void update(const Unit & u, int sgn) {
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
        void move_col(const Unit & u, int c2) {
            const int c1 = u.c;
            if (c1 == c2) return;
            Unit v = u;
            v.c = c2;
            cur -= cval[c1];
            nc[c1]--;
            nt[c1] -= weight(u);
            n1[c1] -= color(u, c1);
            if (u.b >= 0) pairOne[c1] -= color(u, c1);
            cur += cval[c1] = colcost(c1);
            cur -= cval[c2];
            nc[c2]++;
            nt[c2] += weight(u);
            n1[c2] += color(u, c2);
            if (u.b >= 0) pairOne[c2] += color(u, c2);
            cur += cval[c2] = colcost(c2);
            const u64 h1 = holes(u), h2 = holes(v);
            for (int sgn = - 1; sgn <= 1; sgn += 2) for (u64 s = sgn < 0 ? h1 & ~h2 : h2 & ~h1; s; s &= s - 1) {
                int j = __builtin_ctzll(s);
                cur -= hcost(j);
                hn[j][hb[u.a] >> j & 1] += sgn;
                if (u.b >= 0) hn[j][hb[u.b] >> j & 1] += sgn;
                cur += hcost(j);
            }
        }
        void relist(int x, int from, int to) {
            if (from == to) return;
            auto & v = cu[from];
            const int last = v.back();
            v[cpos[x]] = last;
            cpos[last] = cpos[x];
            v.pop_back();
            cpos[x] = cu[to].size();
            cu[to].push_back(x);
        }
        void rebuild() {
            std::fill(nc.begin(), nc.end(), 0);
            std::fill(nt.begin(), nt.end(), 0);
            std::fill(n1.begin(), n1.end(), 0);
            std::fill(pairOne.begin(), pairOne.end(), 0);
            std::fill(hn.begin(), hn.end(), std::array < int, 2 > {
                0, 0
            });
            cu.assign(H, {
            });
            cpos.assign(U, - 1);
            for (int x = 0; x <(int) unit.size(); x++) if (unit[x].c >= 0) cpos[x] = cu[unit[x].c].size(), cu[unit[x].c].push_back(x);
            cur = 0;
            cval.assign(H, 0.);
            for (int j = 0; j < H; j++) cur += cval[j] = colcost(j);
            for (const auto & u : unit) update(u, 1);
            for (int x = 0; x < U; x++) {
                owner[unit[x].a] = x;
                if (unit[x].b >= 0) owner[unit[x].b] = x;
            }
        }
        template < class Compatible, class Estimate, class Expired > bool initialize(Compatible compatible, Estimate estimate,
        Expired expired) {
            struct E {
                double w;
                int a, b;
            };
            std::vector < E > edges;
            for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++) {
                if ((b & 31) == 0 && expired()) return false;
                if (!compatible(A[a], A[b])) continue;
                ok[a][b] = ok[b][a] = 1;
                partners[a].push_back(b);
                partners[b].push_back(a);
                u64 d = A[a] ^ A[b];
                gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]);
                edges.push_back({
                    (2340 * pc(d >> G) + 5 * std::llround(gcost[a][b] * 1440.0) + 144 * pc(d)) / 3600.0, a, b
                });
            }
            std::stable_sort(edges.begin(), edges.end(),[](const E & a, const E & b) {
                return a.w < b.w;
            });
            std::vector < char > used(256, 0);
            for (const auto & e : edges) {
                if (int(unit.size()) == need) break;
                if (used[e.a] || used[e.b]) continue;
                used[e.a] = used[e.b] = 1;
                unit.push_back({
                    e.a, e.b, - 1
                });
            }
            auto edgeCost =[&](int a, int b) {
                u64 d = A[a] ^ A[b];
                return(2340 * pc(d >> G) + 5 * std::llround(gcost[a][b] * 1440.0) + 144 * pc(d)) / 3600.0;
            };
            while (int(unit.size()) < need) {
                double best = 1e100;
                int bx = - 1, bu = - 1, bv = - 1, flip = 0;
                for (int x = 0; x < int(unit.size()); x++) for (int f = 0; f < 2; f++) {
                    if (expired()) return false;
                    int a = f ? unit[x].b : unit[x].a, b = f ? unit[x].a : unit[x].b;
                    for (int u : partners[a]) if (!used[u]) for (int v : partners[b]) if (!used[v] && u != v) {
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
                unit[bx] = {
                    a, bu, - 1
                };
                unit.push_back({
                    b, bv, - 1
                });
                used[bu] = used[bv] = 1;
            }
            if (int(unit.size()) < need) return false;
            for (int a = 0; a < 256; a++) if (!used[a]) unit.push_back({
                a, - 1, - 1
            });
            std::vector < int > perm(U);
            std::iota(perm.begin(), perm.end(), 0);
            for (int i = U - 1; i > 0; i--) std::swap(perm[i], perm[rng.below(i + 1)]);
            auto take =[&](int c, int colorWanted, bool pairFirst) {
                for (int pass = 0; pass < 2; pass++) for (int x : perm) {
                    auto & u = unit[x];
                    if (u.c >= 0 ||(u.b >= 0) !=(pairFirst ^(pass != 0)) || !valid(u, c) || color(u, c) != colorWanted) continue;
                    u.c = c;
                    nc[c]++;
                    n1[c] += colorWanted;
                    return true;
                }
                return false;
            };
            for (int c = 0; c < H; c++) for (int v = 0; v < 2; v++) if (!take(c, v, false)) return false;
            std::vector < int > cap(H, 2);
            int tot = H * 2;
            while (tot + 2 <= U) {
                int best = 0;
                double val = 1e100;
                for (int c = 0; c < H; c++) {
                    double q =(cap[c] + 1.) /(c + 1.5);
                    if (q < val) val = q, best = c;
                }
                cap[best] += 2;
                tot += 2;
            }
            for (int c = H - 1; c >= 0; c--) while (nc[c] < cap[c]) {
                int v = 2 * n1[c] < nc[c] ? 1 : 0;
                if (!take(c, v, true) && !take(c, v ^ 1, true)) break;
            }
            for (auto & u : unit) if (u.c < 0) {
                int best = - 1;
                double cost = 1e100;
                for (int c = 0; c < H; c++) if (valid(u, c)) {
                    double q = weight(u) *(nc[c] * .5 + .5 *(H - 1 - c)) + nc[c] * .5 + 3 * std::abs(nc[c] + 1 - 2 *(n1[c] + color(u,
                    c)));
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
        void anneal(double seconds, int fixedIterations = 0) {
            if (H <= 32) Annealer < 4 >(* this).run(seconds, fixedIterations);
            else Annealer < 5 >(* this).run(seconds, fixedIterations);
        }
        static const std::array < double, 16384 > & anneal_logs() {
            static const std::array < double, 16384 > logs =[]() {
                std::array < double, 16384 > a {
                };
                for (int i = 0; i < 16384; i++) a[i] = - std::log((i + .5) / 16384);
                return a;
            }
            ();
            return logs;
        }
#define ANNEAL_TARGET __attribute__((target("avx2,fma,bmi,bmi2,popcnt")))
        template < int NR > struct Annealer {
            static constexpr int L = 8 * NR;
            static constexpr double kHoleScale = 4 * kHoleWeight;
            struct ColRow {
                alignas(32) float t1[L], u1[L], p1[L], pd[L];
            };
            Design & D;
            const int H, U;
            alignas(32) float n0[L] = {
            }, n1[L] = {
            }, hq[L] = {
            };
            std::vector < ColRow > rows;
            std::array < int, 64 > cnc {
            }, cnt {
            }, cn1 {
            }, cp1 {
            }, cv {
            };
            std::vector < int > key;
            double cur = 0, temp = 2.;
            const double * const logs = anneal_logs().data();
            static const float * bit_lanes(unsigned v) {
                return kBitLanes[v].data();
            }
            ANNEAL_TARGET static float qf(float a, float b) {
                const float s = a + b;
                return a * b /(s > 1.f ? s : 1.f);
            }
            ANNEAL_TARGET static float hsum(__m256 v) {
                __m128 x = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
                x = _mm_add_ps(x, _mm_movehl_ps(x, x));
                x = _mm_add_ss(x, _mm_shuffle_ps(x, x, 1));
                return _mm_cvtss_f32(x);
            }
            ANNEAL_TARGET static void add_bits(__m256 * acc, u64 m, float k) {
                const __m256 kv = _mm256_set1_ps(k);
                for (int r = 0; r < NR; r++) acc[r] = _mm256_fmadd_ps(_mm256_load_ps(bit_lanes((m >>(8 * r)) & 255)), kv, acc[r]);
            }
            ANNEAL_TARGET static void add_bits(float * row, u64 m, float k) {
                const __m256 kv = _mm256_set1_ps(k);
                for (int r = 0; r < NR; r++) _mm256_store_ps(row + 8 * r, _mm256_add_ps(_mm256_load_ps(row + 8 * r), _mm256_mul_ps(_mm256_load_ps(bit_lanes((m >>(8 * r)) & 255)),
                kv)));
            }
            ANNEAL_TARGET float eval_holes(const __m256 * d0, const __m256 * d1, __m256 * N0, __m256 * N1, __m256 * Q) const {
                const __m256 one = _mm256_set1_ps(1.f);
                __m256 dif[NR];
                for (int r = 0; r < NR; r++) {
                    N0[r] = _mm256_add_ps(_mm256_load_ps(n0 + 8 * r), d0[r]);
                    N1[r] = _mm256_add_ps(_mm256_load_ps(n1 + 8 * r), d1[r]);
                    const __m256 s = _mm256_max_ps(_mm256_add_ps(N0[r], N1[r]), one);
                    Q[r] = _mm256_div_ps(_mm256_mul_ps(N0[r], N1[r]), s);
                    dif[r] = _mm256_sub_ps(Q[r], _mm256_load_ps(hq + 8 * r));
                }
                __m256 acc = _mm256_add_ps(_mm256_add_ps(dif[0], dif[1]), _mm256_add_ps(dif[2], dif[3]));
                if constexpr(NR == 5) acc = _mm256_add_ps(acc, dif[4]);
                return hsum(acc);
            }
            ANNEAL_TARGET void commit_holes(const __m256 * N0, const __m256 * N1, const __m256 * Q) {
                for (int r = 0; r < NR; r++) {
                    _mm256_store_ps(n0 + 8 * r, N0[r]);
                    _mm256_store_ps(n1 + 8 * r, N1[r]);
                    _mm256_store_ps(hq + 8 * r, Q[r]);
                }
            }
            ANNEAL_TARGET void unit_rows(const Unit & u, float sgn) {
                auto & row = rows[u.c];
                const u64 ha = D.hb[u.a];
                add_bits(row.t1, ha, sgn);
                add_bits(row.u1, ha, sgn);
                if (u.b >= 0) {
                    add_bits(row.t1, D.hb[u.b], sgn);
                    add_bits(row.p1, ha, sgn);
                    add_bits(row.pd, ha ^ D.hb[u.b], sgn);
                }
            }
            int unit_key(const Unit & u) const {
                return u.c * 2 + D.color(u, u.c);
            }
            bool accept(double d) {
                return d <= 0 || d < temp * logs[D.rng.next() & 16383];
            }
            explicit Annealer(Design & d) : D(d), H(d.H), U(d.U), rows(d.H), key(d.U) {
                std::memset(static_cast < void * >(rows.data()), 0, rows.size() * sizeof (ColRow));
                for (int j = 0; j < H; j++) n0[j] = float(D.hn[j][0]), n1[j] = float(D.hn[j][1]), hq[j] = qf(n0[j], n1[j]);
                for (int c = 0; c < H; c++) cnc[c] = D.nc[c], cnt[c] = D.nt[c], cn1[c] = D.n1[c], cp1[c] = D.pairOne[c];
                for (int c = 0; c < H; c++) cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c]);
                for (const auto & u : D.unit) unit_rows(u, 1.f);
                for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
                cur = D.cur;
            }
            ANNEAL_TARGET void column_move(int x, int y, const Unit & ox, const Unit & oy, const Unit & nx, const Unit & ny) {
                const int P = ox.c, Q = nx.c;
                int dnc[2] = {
                    0, 0
                }, dnt[2] = {
                    0, 0
                }, dn1[2] = {
                    0, 0
                }, dp1[2] = {
                    0, 0
                };
                for (const auto &[u, to] : {
                    std::pair < const Unit &, int > {
                        ox, nx.c
                    }, std::pair < const Unit &, int > {
                        oy, ny.c
                    }
                }) {
                    const int f = u.c == P ? 0 : 1, t = to == P ? 0 : 1, w = D.weight(u), cf = D.color(u, u.c), ct = D.color(u, to),
                    pr = u.b >= 0;
                    dnc[f]--;
                    dnt[f] -= w;
                    dn1[f] -= cf;
                    dp1[f] -= pr * cf;
                    dnc[t]++;
                    dnt[t] += w;
                    dn1[t] += ct;
                    dp1[t] += pr * ct;
                }
                const int cvP = colcost40(cnc[P] + dnc[0], cnt[P] + dnt[0], cn1[P] + dn1[0], cp1[P] + dp1[0]), cvQ = colcost40(cnc[Q] + dnc[1],
                cnt[Q] + dnt[1], cn1[Q] + dn1[1], cp1[Q] + dp1[1]);
                __m256 d0[NR], d1[NR];
                for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
                for (const auto &[u, to] : {
                    std::pair < const Unit &, int > {
                        ox, nx.c
                    }, std::pair < const Unit &, int > {
                        oy, ny.c
                    }
                }) {
                    const u64 ha = D.hb[u.a], d = u.b >= 0 ? ha ^ D.hb[u.b] : 0, m =(low_bits(u.c + 1) ^ low_bits(to + 1)) & ~d;
                    const float k = float((to > u.c ? - 1 : 1) * D.weight(u));
                    add_bits(d1, m & ha, k);
                    add_bits(d0, m & ~ha, k);
                }
                __m256 N0[NR], N1[NR], Qv[NR];
                const float dq = eval_holes(d0, d1, N0, N1, Qv);
                const double delta =((cvP - cv[P]) +(cvQ - cv[Q])) *(1. / 40) + kHoleScale * dq;
                if (!accept(delta)) return;
                cur += delta;
                commit_holes(N0, N1, Qv);
                cnc[P] += dnc[0];
                cnt[P] += dnt[0];
                cn1[P] += dn1[0];
                cp1[P] += dp1[0];
                cv[P] = cvP;
                cnc[Q] += dnc[1];
                cnt[Q] += dnt[1];
                cn1[Q] += dn1[1];
                cp1[Q] += dp1[1];
                cv[Q] = cvQ;
                unit_rows(ox, - 1.f);
                unit_rows(nx, 1.f);
                D.unit[x] = nx;
                key[x] = unit_key(nx);
                if (ny.c != oy.c) {
                    unit_rows(oy, - 1.f);
                    unit_rows(ny, 1.f);
                    D.unit[y] = ny;
                    key[y] = unit_key(ny);
                }
            }
            ANNEAL_TARGET void target_move(int x, int y, const Unit & ox, const Unit & oy, const Unit & nx, const Unit & ny) {
                const int cx = ox.c, cy = oy.c, iy = cx == cy ? 0 : 1;
                int dnt[2] = {
                    0, 0
                }, dn1[2] = {
                    0, 0
                }, dp1[2] = {
                    0, 0
                };
                __m256 d0[NR], d1[NR];
                for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
                for (const auto &[u, i, sgn] : {
                    std::tuple < const Unit &, int, int > {
                        ox, 0, - 1
                    }, std::tuple < const Unit &, int, int > {
                        nx, 0, 1
                    }, std::tuple < const Unit &, int, int > {
                        oy, iy, - 1
                    }, std::tuple < const Unit &, int, int > {
                        ny, iy, 1
                    }
                }) {
                    const int cl = D.color(u, u.c);
                    dnt[i] += sgn * D.weight(u);
                    dn1[i] += sgn * cl;
                    dp1[i] += sgn *(u.b >= 0) * cl;
                    const u64 hs = D.holes(u);
                    for (int t : {
                        u.a, u.b
                    }) {
                        if (t < 0) continue;
                        add_bits(d1, hs & D.hb[t], float(sgn));
                        add_bits(d0, hs & ~D.hb[t], float(sgn));
                    }
                }
                const int cvx = colcost40(cnc[cx], cnt[cx] + dnt[0], cn1[cx] + dn1[0], cp1[cx] + dp1[0]), cvy = iy ? colcost40(cnc[cy],
                cnt[cy] + dnt[1], cn1[cy] + dn1[1], cp1[cy] + dp1[1]) : 0;
                __m256 N0[NR], N1[NR], Qv[NR];
                const float dq = eval_holes(d0, d1, N0, N1, Qv);
                const double dcol =((cvx - cv[cx]) +(iy ? cvy - cv[cy] : 0)) *(1. / 40), delta = dcol + kHoleScale * dq +((D.gc(nx) + D.gc(ny)) -(D.gc(ox) + D.gc(oy)));
                if (!accept(delta)) return;
                cur += delta;
                commit_holes(N0, N1, Qv);
                cnt[cx] += dnt[0];
                cn1[cx] += dn1[0];
                cp1[cx] += dp1[0];
                cv[cx] = cvx;
                if (iy) {
                    cnt[cy] += dnt[1];
                    cn1[cy] += dn1[1];
                    cp1[cy] += dp1[1];
                    cv[cy] = cvy;
                }
                unit_rows(ox, - 1.f);
                unit_rows(oy, - 1.f);
                unit_rows(nx, 1.f);
                unit_rows(ny, 1.f);
                D.unit[x] = nx;
                D.unit[y] = ny;
                key[x] = unit_key(nx);
                key[y] = unit_key(ny);
                D.owner[nx.a] = x;
                if (nx.b >= 0) D.owner[nx.b] = x;
                D.owner[ny.a] = y;
                if (ny.b >= 0) D.owner[ny.b] = y;
            }
            ANNEAL_TARGET void mutate(int x, int y, const Unit & nx, const Unit & ny) {
                if (D.invalid_bit(nx, nx.c) | D.invalid_bit(ny, ny.c)) return;
                const Unit ox = D.unit[x], oy = D.unit[y];
                if (nx.a == ox.a && nx.b == ox.b && ny.a == oy.a && ny.b == oy.b) column_move(x, y, ox, oy, nx, ny);
                else {
                    if ((nx.b >= 0 && !D.ok[nx.a][nx.b]) ||(ny.b >= 0 && !D.ok[ny.a][ny.b])) return;
                    target_move(x, y, ox, oy, nx, ny);
                }
            }
            ANNEAL_TARGET void handle_swap(int a, int b) {
                if (rows[a].pd[b] != 0 || rows[b].pd[a] != 0) return;
                const int n1a = int(rows[a].u1[b]), n1b = int(rows[b].u1[a]), pa = int(rows[a].p1[b]), pb = int(rows[b].p1[a]);
                int tot = 0;
                float mb_old1 = 0, mb_new1 = 0, ma_old = 0, ma_new = 0;
                for (int c = a; c < b; c++) {
                    tot += cnt[c];
                    mb_old1 += rows[c].t1[b];
                    mb_new1 += rows[c].t1[a];
                    ma_old += rows[c].pd[a];
                    ma_new += rows[c].pd[b];
                }
                const float na0 = n0[b] -(float(tot) - mb_old1) + ma_new, na1 = n1[b] - mb_old1 + ma_new, nb0 = n0[a] - ma_old +(float(tot) - mb_new1),
                nb1 = n1[a] - ma_old + mb_new1, qa = qf(na0, na1), qb = qf(nb0, nb1);
                const int cva = colcost40(cnc[a], cnt[a], n1a, pa), cvb = colcost40(cnc[b], cnt[b], n1b, pb);
                const double delta = kHoleScale *((qa - hq[a]) +(qb - hq[b])) +((cva + cvb) -(cv[a] + cv[b])) *(1. / 40);
                if (!accept(delta)) return;
                cur += delta;
                std::swap(D.handle[a], D.handle[b]);
                for (auto & h : D.hb) if (((h >> a) ^(h >> b)) & 1) h ^=(u64(1) << a) |(u64(1) << b);
                for (auto & row : rows) {
                    std::swap(row.t1[a], row.t1[b]);
                    std::swap(row.u1[a], row.u1[b]);
                    std::swap(row.p1[a], row.p1[b]);
                    std::swap(row.pd[a], row.pd[b]);
                }
                n0[a] = na0;
                n1[a] = na1;
                hq[a] = qa;
                n0[b] = nb0;
                n1[b] = nb1;
                hq[b] = qb;
                cn1[a] = n1a;
                cn1[b] = n1b;
                cp1[a] = pa;
                cp1[b] = pb;
                cv[a] = cva;
                cv[b] = cvb;
                for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
            }
            ANNEAL_TARGET void run(double seconds, int fixedIterations) {
                auto start = std::chrono::steady_clock::now();
                double progress = 0;
                constexpr int kHandleSwapRate = 150;
                auto & rng = D.rng;
                auto & unit = D.unit;
                std::vector < Unit > best = unit;
                std::vector < int > bestHandle = D.handle;
                double bestCost = cur;
                for (int it = 0;; it++) {
                    D.anneal_iters = it;
                    if ((it & 255) == 0) {
                        double elapsed = CLOCK_SCALE * std::chrono::duration < double >(std::chrono::steady_clock::now() - start).count();
                        progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                        if (progress >= 1 || elapsed >= seconds) break;
                        temp = 2. * std::pow(.015 / 2., progress);
                    }
                    int type = rng.below(1000);
                    if (type < kHandleSwapRate) {
                        int a = rng.below(H), b = rng.below(H);
                        if (a == b) continue;
                        if (a > b) std::swap(a, b);
                        handle_swap(a, b);
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
                                const auto & p = D.partners[fixed];
                                if (p.empty()) continue;
                                int newTarget = p[rng.below(p.size())];
                                y = D.owner[newTarget];
                                if (x == y) continue;
                                ny = unit[y];
                                iy = ny.a == newTarget ? 0 : 1;
                            }
                            int & a = ix == 0 ? nx.a : nx.b;
                            int & b = iy == 0 ? ny.a : ny.b;
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
                            const int want = 2 * c + 1 - D.color(nx, c);
                            int z = - 1;
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
                    for (int j = 0; j < H; j++) D.hb[i] |=((D.A[i] >> D.handle[j]) & 1) << j;
                }
                D.rebuild();
            }
        };
#undef ANNEAL_TARGET
        static double filler_gain(u64 tb, int l, u64 yb, u64 dy, int c, const double * q) {
            constexpr int kT = 3;
            u64 range = low_bits(c + 1) & ~dy & ~low_bits(l + 1), mis =(yb ^ tb) & range;
            if (mis >> c & 1) return 0.;
            int lvl = mis ? 64 - __builtin_clzll(mis) : 0;
            u64 cov = range & low_bits(c) & ~low_bits(lvl);
            if (!cov) return 0.;
            int lo = __builtin_ctzll(cov);
            double g = q[c] - q[lo];
            for (u64 d = dy & low_bits(c) & ~low_bits(lo); d; d &= d - 1) {
                int m = __builtin_ctzll(d);
                g -= q[m + 1] - q[m];
            }
            return std::max(0., g - kT);
        }
        void filler_climb(double seconds, int fixedIterations = 0) {
            constexpr double kW = .3;
            auto start = std::chrono::steady_clock::now();
            std::vector < u64 > diffb(U, 0);
            for (int x = 0; x < U; x++) if (unit[x].b >= 0) diffb[x] = hb[unit[x].a] ^ hb[unit[x].b];
            std::vector < std::vector < double >> pq(256, std::vector < double >(H + 1, 0.));
            for (int t = 0; t < 256; t++) for (int m = 0; m < H; m++) {
                int n = hn[m][0] + hn[m][1];
                double p1 = n ? double(hn[m][1]) / n : .5, pc =(hb[t] >> m & 1) ? p1 : 1 - p1;
                pq[t][m + 1] = pq[t][m] + 2 *(1 - pc);
            }
            std::vector < std::vector < int >> colm(H);
            for (int x = 0; x < U; x++) colm[unit[x].c].push_back(x);
            auto tcol =[&](int t) {
                return unit[owner[t]].c;
            };
            auto gval =[&](int t, int l, int y, int c) {
                return filler_gain(hb[t], l, hb[unit[y].a], diffb[y], c, pq[t].data());
            };
            std::vector < std::vector < double >> colsum(256, std::vector < double >(H, 0.));
            auto recompute =[&](int t) {
                int l = tcol(t);
                for (int c = 0; c < H; c++) {
                    colsum[t][c] = 0;
                    if (c <= l) continue;
                    for (int y : colm[c]) colsum[t][c] += gval(t, l, y, c);
                }
            };
            for (int t = 0; t < 256; t++) recompute(t);
            auto proxy =[&](int t) {
                int l = tcol(t);
                double s = 0;
                for (int c = l + 1; c < H; c++) if (!colm[c].empty()) s += colsum[t][c] / colm[c].size();
                return s;
            };
            proxy_before = 0;
            for (int t = 0; t < 256; t++) proxy_before += proxy(t);
            std::vector < int > others, moved;
            std::vector < std::array < double, 2 >> dlt;
            std::vector < std::vector < double >> saved;
            for (int it = 0;; it++) {
                if (fixedIterations > 0 ? it >= fixedIterations :((it & 63) == 0 && CLOCK_SCALE * std::chrono::duration < double >(std::chrono::steady_clock::now() - start).count() >= seconds)) break;
                climb_iters = it + 1;
                int x = rng.below(U), y = rng.below(U), a = unit[x].c, b = unit[y].c;
                if (a == b ||(unit[x].b >= 0) !=(unit[y].b >= 0)) continue;
                Unit nx = unit[x], ny = unit[y];
                nx.c = b;
                ny.c = a;
                if (!valid(nx, b) || !valid(ny, a)) continue;
                if (color(nx, b) != color(unit[y], b) || color(ny, a) != color(unit[x], a)) continue;
                double old = cur;
                Unit ox = unit[x], oy = unit[y];
                update(ox, - 1);
                update(oy, - 1);
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
                        dlt.push_back({
                            da, db
                        });
                        dproxy += da / na + db / nb;
                    }
                }
                moved.clear();
                for (int t : {
                    ox.a, ox.b, oy.a, oy.b
                }) if (t >= 0) moved.push_back(t);
                saved.resize(moved.size());
                for (size_t i = 0; i < moved.size(); i++) {
                    dproxy -= proxy(moved[i]);
                    saved[i] = colsum[moved[i]];
                }
                auto apply =[&](int cx, int cy) {
                    auto & ma = colm[unit[x].c];
                    ma.erase(std::find(ma.begin(), ma.end(), x));
                    auto & mb = colm[unit[y].c];
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
                if (dmodel - kW * dproxy < - 1e-9) {
                    climb_accepted++;
                    for (size_t i = 0; i < others.size(); i++) {
                        colsum[others[i]][a] += dlt[i][0];
                        colsum[others[i]][b] += dlt[i][1];
                    }
                } else {
                    apply(a, b);
                    for (size_t i = 0; i < moved.size(); i++) colsum[moved[i]] = saved[i];
                    update(nx, - 1);
                    update(ny, - 1);
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
    struct Solver {
        int M = 6, G = 36, H = 28;
        Comparator comparator;
        std::vector < u64 > A;
        std::vector < int > handle, hidx;
        u64 gmask = 0, hmask = 0;
        std::vector < Paper > paper;
        std::vector < u64 > h_opq, h_blk;
        std::vector < int > col_of, ded;
        static constexpr int base_paper = 0;
        std::vector < int > order;
        int top_d = - 1;
        struct Filler {
            int paper;
            int lvl = 0, hi = 0;
        };
        std::vector < Filler > fillers;
        std::vector < std::pair < int, int >> ops;
        explicit Solver(std::vector < u64 > a) : A(std::move(a)) {
        }
        u64 handle_bits(u64 windows) const {
            u64 r = 0;
            for (int j = 0; j < H; j++) r |=(windows >> handle[j] & 1) << j;
            return r;
        }
        int cached_generic_u = - 1;
        u64 cached_generic_holes = 0;
        std::vector < int > cached_generic_order;
        std::vector < std::pair < int, int >> cached_generic_moves;
        void set_generic(int u, u64 holes) {
            holes &= gmask;
            if (!holes) return;
            int offset = - 1;
            for (int i = 0; i < K; i++) if (order[i] < M) {
                offset = i;
                break;
            }
            if (offset < 0 || offset + M > K) {
                invalid = true;
                return;
            }
            std::vector < int > local;
            for (int i = 0; i < M; i++) {
                int k = order[offset + i];
                if (k < 0 || k >= M) {
                    invalid = true;
                    return;
                }
                local.push_back(k);
            }
            if (cached_generic_u != u || cached_generic_holes != holes || cached_generic_order != local) {
                cached_generic_u = u;
                cached_generic_holes = holes;
                cached_generic_order = local;
                cached_generic_moves = comparator.plan(local, A[u], holes);
            }
            const auto & path = cached_generic_moves;
            for (auto[k, d] : path) {
                if (k < 0 || k >= M || d < 0 || d >= M) {
                    invalid = true;
                    return;
                }
                move(k, offset + d);
                if (invalid) return;
            }
        }
        int adaptive_request = - 1;
        bool adaptive_initialized = false;
        std::vector < double > adaptive_weights;
        std::vector < std::array < double, 2 >> adaptive_holes;
        static constexpr double kTopPenalty = .35, kEndWeight = 1.;
        bool fast_mode = false;
        long long fast_requests = 0, plan_failures = 0;
        void init_adaptive() {
            if (adaptive_initialized) return;
            adaptive_initialized = true;
            adaptive_weights.assign(K, 0.);
            adaptive_holes.assign(H, {
                0., 0.
            });
            for (int u = 0; u < P; u++) {
                int d = ded[u];
                if (d < 0) continue;
                adaptive_weights[d] += 1.;
                for (int c = 0; c < H; c++) if (!(paper[d].opaque >> handle[c] & 1)) adaptive_holes[c][A[u] >> handle[c] & 1] += 1. / P;
            }
        }
        double adaptive_next_cost() const {
            std::vector < int > rank(H, 0);
            std::vector < std::array < int, 2 >> first(H);
            std::vector < std::array < bool, 2 >> available(H, {
                false, false
            });
            for (auto & f : first) f = {
                - 1, - 1
            };
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
            for (int c = 0; c < H; c++) for (int color = 0; color < 2; color++) {
                int fixes = available[c][color] ? 0 : first[c][color];
                if (fixes < 0) fixes = rank[c];
                cost += adaptive_holes[c][color] * fixes;
            }
            return cost;
        }
        void adaptive_insert(int x, int u, int barrier = - 1, int mode = 2) {
            const int c = col_of[x], cx = paper[x].black >> handle[c] & 1;
            std::vector < int > v;
            for (int k : order) if (k != x && in_column(k, c)) v.push_back(k);
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
            std::vector < double > suffix(n + 1, 0.);
            std::array < int, 2 > first = {
                n, n
            };
            for (int i = n - 1; i >= 0; i--) {
                suffix[i] = suffix[i + 1] + adaptive_weights[v[i]];
                first[paper[v[i]].black >> handle[c] & 1] = i;
            }
            int requested = u >= 0 ? ded[u] : - 1;
            bool need = requested >= 0 && c != col_of[requested] && !(paper[requested].opaque >> handle[c] & 1);
            int desired = u >= 0 ?(A[u] >> handle[c] & 1) : 0;
            double best = 1e100;
            int gap = n;
            for (int i = lo; i <= n; i++) {
                std::array < int, 2 > fc;
                for (int color = 0; color < 2; color++) {
                    fc[color] = first[color] +(first[color] >= i);
                    if (color == cx) fc[color] = std::min(fc[color], i);
                }
                double rank = adaptive_weights[x] * i + suffix[i], value = rank / P + adaptive_holes[c][0] * fc[0] + adaptive_holes[c][1] * fc[1];
                if (need && barrier < 0) value += fc[desired];
                if (mode == 1 && i == 0 && n) value += kTopPenalty;
                value += 1e-7 *(n - i);
                if (value < best) {
                    best = value;
                    gap = i;
                }
            }
            if (x == top_d) top_d = - 1;
            drop_filler(x);
            if (!n) {
                int anchor = - 1;
                for (int k : order) {
                    if (k == x || k == top_d || is_filler(k)) continue;
                    if (k < M ||(col_of[k] >= 0 && col_of[k] < c)) anchor = k;
                }
                if (anchor < 0) move(x, 0);
                else move_after(x, anchor);
            } else if (gap < n) {
                int from = index_of(x), to = index_of(v[gap]);
                move(x, from < to ? to - 1 : to);
            } else move_after(x, v.back());
        }
        int index_of(int k) const {
            for (int i = 0; i < K; i++) if (order[i] == k) return i;
            return - 1;
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
        void move(int k, int d) {
            int i = index_of(k);
            if (i == d) return;
            if (check_vis && !visible(k)) invalid = true;
            order.erase(order.begin() + i);
            order.insert(order.begin() + d, k);
            ops.push_back({
                k, d
            });
        }
        void move_after(int k, int x) {
            int i = index_of(k);
            if (index_of(x) + 1 == i) return;
            if (check_vis && !visible(k)) invalid = true;
            order.erase(order.begin() + i);
            int j = 0;
            while (order[j] != x) j++;
            order.insert(order.begin() + j + 1, k);
            ops.push_back({
                k, j + 1
            });
        }
        bool is_filler(int k) const {
            for (auto & f : fillers) if (f.paper == k) return true;
            return false;
        }
        void drop_filler(int k) {
            std::erase_if(fillers,[&](const Filler & f) {
                return f.paper == k;
            });
        }
        bool in_column(int k, int l) const {
            return col_of[k] == l && k != top_d && !is_filler(k);
        }
        void column_tops(int l, int n, std::vector < int > & top) const {
            top.clear();
            for (int k : order) if (in_column(k, l)) {
                top.push_back(k);
                if ((int) top.size() >= n) break;
            }
        }
        int column_top(int l) const {
            for (int k : order) if (in_column(k, l)) return k;
            return - 1;
        }
        void dig(int l, int barrier = - 1) {
            int t = column_top(l);
            if (t < 0) {
                invalid = true;
                return;
            }
            if (barrier < 0) for (int k : order) if (in_column(k, l)) barrier = k;
            if (t != barrier) adaptive_insert(t, adaptive_request, barrier, 2);
        }
        void lift(int d) {
            int c = col_of[d];
            for (int it = 0; column_top(c) != d; it++) {
                if (it >= K || invalid) {
                    invalid = true;
                    return;
                }
                dig(c, d);
            }
            move(d, 0);
            top_d = d;
        }
        void set_handle(int l, int color) {
            int barrier = - 1;
            for (int k : order) if (in_column(k, l) && int(paper[k].black >> handle[l] & 1) == color) {
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
            for (int j = 0; j < H; j++) if (hh >> handle[j] & 1) set_handle(j, A[u] >> handle[j] & 1);
        }
        int handle_fix_cost(int l, int c) const {
            int i = 0;
            for (int k : order) {
                if (!in_column(k, l)) continue;
                if ((int)(paper[k].black >> handle[l] & 1) == c) return i;
                i++;
            }
            return 0;
        }
        std::vector < int > fix_costs(int u, u64 hh) const {
            std::vector < int > fix(H, 0);
            for (int j = 0; j < H; j++) if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
            return fix;
        }
        int level_past(u64 wrong) const {
            int lvl = 0;
            for (u64 x = wrong; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
            return lvl;
        }
        u64 shown_by(const Filler & f) const {
            u64 m = 0;
            for (int j = f.lvl; j <= f.hi; j++) if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
            return m;
        }
        static bool reaches_deeper(int lvl, int c, const std::vector < Filler > & placed) {
            for (auto & f : placed) if (f.lvl > lvl && c >= f.lvl) return true;
            return false;
        }
        void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
            int q = K, last_above = - 1;
            for (int i = 0; i < K; i++) {
                int k = order[i];
                if (below_generic && k == base_paper) last_above = i;
                if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
                if (col_of[k] < lvl) last_above = i;
                else if (q == K) q = i;
            }
            int xi = index_of(x);
            if (lazy && xi < q && xi > last_above) return;
            move(x, xi < q ? q - 1 : q);
        }
        void place_filler(int c, int depth, int lvl, u64 & hh) {
            std::vector < int > top;
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
            fillers.push_back({
                x, lvl, c
            });
            hh &= ~shown_by(fillers.back());
        }
        void return_paper(int x, int u, int mode) {
            const int d = u >= 0 ? ded[u] : - 1;
            adaptive_insert(x, u, d >= 0 && d != x && col_of[d] == col_of[x] && in_column(d, col_of[x]) ? d : - 1, mode);
        }
        struct PrefixMemo {
            std::vector < int > order;
            std::vector < Filler > fillers;
            std::vector < std::pair < int, int >> ops;
            int top;
            u64 cov;
            bool kept;
        };
        std::vector < PrefixMemo > prefix_memo;
        bool repeated_prefix(bool kept, u64 cov) {
            for (auto & p : prefix_memo) {
                if (p.top != top_d || p.cov != cov || p.kept != kept || p.ops != ops || p.fillers.size() != fillers.size() || p.order != order) continue;
                bool equal = true;
                for (size_t i = 0; i < fillers.size(); i++) if (p.fillers[i].paper != fillers[i].paper || p.fillers[i].lvl != fillers[i].lvl || p.fillers[i].hi != fillers[i].hi) {
                    equal = false;
                    break;
                }
                if (equal) return true;
            }
            prefix_memo.push_back({
                order, fillers, ops, top_d, cov, kept
            });
            return false;
        }
        struct PlanOpt {
            int ret_mode = 0, fret_mode = 0;
            bool use_filler = false, keep = false;
            int fret_ret = 1;
        };
        struct FillerPick {
            int c = - 1, depth = 0, lvl = 0;
            bool post = false;
        };
        struct Cand {
            int lvl;
            double gain;
            int c, depth;
            int kind = 0, idx = - 1;
            bool post = false;
        };
        std::vector < Cand > best_intervals(const std::vector < std::vector < Cand >> & cand) const {
            std::vector < double > best(H + 1, 0);
            std::vector < int > pick(H + 1, - 1);
            for (int c = 0; c < H; c++) {
                best[c + 1] = best[c];
                for (int i = 0; i <(int) cand[c].size(); i++) if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9) {
                    best[c + 1] = best[cand[c][i].lvl] + cand[c][i].gain;
                    pick[c + 1] = i;
                }
            }
            std::vector < Cand > res;
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
        static constexpr int kFillerDepth = 3, kFillerCost = 1, kMaxFillers = 8;
        std::vector < FillerPick > choose_fillers_dp(int u, int d, u64 hh) const {
            auto fix = fix_costs(u, hh);
            std::vector < std::vector < Cand >> cand(H);
            std::vector < int > top;
            for (int c = 0; c < H; c++) {
                if (!(hh >> handle[c] & 1)) continue;
                column_tops(c, kFillerDepth + 1, top);
                if (top.empty() || top[0] == d) continue;
                for (int depth = 0; depth <(int) top.size(); depth++) {
                    u64 shown = paper[top[depth]].opaque & hh;
                    int lvl = level_past((paper[top[depth]].black ^ A[u]) & shown);
                    if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                    int save = 0;
                    for (int j = lvl; j <= c; j++) if ((j != c || depth) &&(shown >> handle[j] & 1)) save += fix[j];
                    int gain = save - kFillerCost - depth;
                    if (gain > 0) cand[c].push_back({
                        lvl,(double) gain, c, depth
                    });
                }
            }
            std::vector < FillerPick > res;
            for (auto & cd : best_intervals(cand)) res.push_back({
                cd.c, cd.depth, cd.lvl, false
            });
            std::reverse(res.begin(), res.end());
            return res;
        }
        int level_for(int x, int d, u64 hh, int u, u64 & cov) const {
            int cx = col_of[x], l = col_of[d];
            u64 shown = paper[x].opaque & hh;
            int lvl = level_past((paper[x].black ^ A[u]) & shown);
            if (cx >= l &&(paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
            cov = 0;
            for (int j = lvl; j <= cx; j++) if (shown >> handle[j] & 1) cov |= 1ULL << handle[j];
            return cov ? lvl : - 1;
        }
        bool gen_harm(int x, int d, int u) const {
            if (d < 0 || index_of(x) > index_of(base_paper)) return false;
            return(paper[x].opaque & gmask & ~paper[d].opaque &(paper[x].black ^ A[u])) != 0;
        }
        void refill_or_return(int u, const std::vector < Filler > & olds, u64 & pre_cov, std::vector < Filler > & placed,
        int mode, bool keep_harmless) {
            int d = ded[u];
            for (int i =(int) olds.size() - 1; i >= 0; i--) {
                int x = olds[i].paper, cf = col_of[x];
                bool use = false;
                int lvl = 0;
                u64 cov = 0;
                if (d >= 0 && x != d && visible(x)) {
                    lvl = level_for(x, d, hmask & ~paper[d].opaque & ~pre_cov, u, cov);
                    if (lvl >= 0 && !reaches_deeper(lvl, cf, placed)) {
                        int save = 0;
                        for (int j = lvl; j <= cf; j++) if (cov >> handle[j] & 1) save += handle_fix_cost(j, A[u] >> handle[j] & 1);
                        use = save >= 2;
                    }
                }
                if (!use && keep_harmless && d >= 0 && x != d) {
                    int L = olds[i].lvl, l = col_of[d];
                    bool harm =(L <= l && l <= cf &&(paper[x].opaque >> handle[l] & 1)) || reaches_deeper(L, cf, placed);
                    u64 hcov = 0;
                    for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
                    hcov &= paper[x].opaque & hmask & ~paper[d].opaque & ~pre_cov;
                    if ((paper[x].black ^ A[u]) & hcov || gen_harm(x, d, u)) harm = true;
                    if (!harm && visible(x)) {
                        drop_filler(x);
                        placed.push_back(olds[i]);
                        pre_cov |= hcov;
                        continue;
                    }
                }
                if (!use) {
                    return_paper(x, u, mode);
                    continue;
                }
                drop_filler(x);
                move_to_level(x, lvl, true, gen_harm(x, d, u));
                placed.push_back({
                    x, lvl, cf
                });
                pre_cov |= cov;
            }
        }
        static constexpr double kRelevel = .5, kStay = .8;
        int depth_in_column(int x) const {
            int i = 0;
            for (int k : order) {
                if (k == x) return i;
                if (in_column(k, col_of[x])) i++;
            }
            return - 1;
        }
        void run_joint(int u, const PlanOpt & opt) {
            int d = ded[u];
            if (d < 0 || d == top_d) {
                invalid = true;
                return;
            }
            const int l = col_of[d];
            const u64 hole_all =(gmask | hmask) & ~paper[d].opaque;
            u64 hh = hole_all & ~gmask;
            auto fix = fix_costs(u, hh);
            const bool d_out = is_filler(d);
            std::vector < Filler > olds;
            for (auto & f : fillers) if (f.paper != d) olds.push_back(f);
            const int x0 = top_d;
            std::vector < std::vector < Cand >> cand(H);
            auto mism_level =[&](int x) {
                return level_past((paper[x].black ^ A[u]) & paper[x].opaque & hh);
            };
            auto saved =[&](int x, int lvl, int c, bool skip_c) {
                int sv = 0;
                for (int j = lvl; j <= c; j++) if ((hh >> handle[j] & 1) &&(paper[x].opaque >> handle[j] & 1) && !(skip_c && j == c)) sv += fix[j];
                return sv;
            };
            auto covers =[&](int x, int j) {
                return(hh >> handle[j] & 1) &&(paper[x].opaque >> handle[j] & 1);
            };
            auto add_old =[&](int x, int idx, int L, bool is_x0) {
                int c = col_of[x], lvl = mism_level(x);
                if (!is_x0 && gen_harm(x, d, u)) L = - 2;
                if (!d_out && c >= l &&(paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
                if (lvl <= c) {
                    int sv = saved(x, lvl, c, false);
                    double g = sv - kRelevel;
                    if (!is_x0 && lvl == L) g = sv + 1 - kStay;
                    if (g > 0) cand[c].push_back({
                        lvl, g, c, 0, is_x0 ? 3 :(lvl == L ? 2 : 1), idx
                    });
                }
                if (!is_x0 && L > lvl && L <= c) {
                    bool harm = !d_out && L <= l && l <= c &&(paper[x].opaque >> handle[l] & 1);
                    double g = saved(x, L, c, false) + 1 - kStay;
                    if (!harm && g > 0) cand[c].push_back({
                        L, g, c, 0, 2, idx
                    });
                }
                for (int lv = lvl + 1; lv <= c; lv++) {
                    if (!covers(x, lv) ||(!is_x0 && lv == L)) continue;
                    double g = saved(x, lv, c, false) - kRelevel;
                    if (g > 0) cand[c].push_back({
                        lv, g, c, 0, is_x0 ? 3 : 1, idx
                    });
                }
            };
            for (int i = 0; i <(int) olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
            if (x0 >= 0) add_old(x0, - 1, - 1, true);
            std::vector < int > top;
            for (int c = 0; c < H; c++) {
                bool hole_c = hh >> handle[c] & 1;
                if (c == l ||(d_out && !hole_c)) continue;
                column_tops(c, kFillerDepth + 1, top);
                for (int depth = 0; depth <(int) top.size(); depth++) {
                    int f = top[depth], lvl = mism_level(f);
                    for (int lv = lvl; lv <= c; lv++) {
                        if (lv > lvl && !covers(f, lv)) continue;
                        bool post = d_out ||(c > l && lv <= l &&(paper[f].opaque >> handle[l] & 1));
                        int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                        if (g >= kFillerCost) cand[c].push_back({
                            lv,(double) g, c, 0, 0, f, post
                        });
                    }
                }
            }
            const auto picks = best_intervals(cand);
            std::vector < int > old_dec(olds.size(), 0), old_lvl(olds.size(), - 1);
            int x0_lvl = - 1;
            for (auto & cd : picks) {
                if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
                if (cd.kind == 3) x0_lvl = cd.lvl;
            }
            Filler fd {
                d
            };
            for (auto & f : fillers) if (f.paper == d) fd = f;
            fillers = olds;
            if (d_out) fillers.push_back(fd);
            std::vector < char > done(olds.size(), 0);
            for (int i =(int) olds.size() - 1; i >= 0; i--) {
                if (old_dec[i] != 0 || !visible(olds[i].paper)) continue;
                return_paper(olds[i].paper, u, opt.fret_ret);
                done[i] = 1;
            }
            if (x0 >= 0) {
                if (x0_lvl >= 0) {
                    top_d = - 1;
                    move_to_level(x0, x0_lvl, true, gen_harm(x0, d, u));
                    fillers.push_back({
                        x0, x0_lvl, col_of[x0]
                    });
                } else return_paper(x0, u, opt.ret_mode);
            }
            for (int i =(int) olds.size() - 1; i >= 0; i--) if (old_dec[i] == 0 && !done[i]) return_paper(olds[i].paper, u,
            opt.fret_ret);
            for (int i = 0; i <(int) olds.size(); i++) {
                if (old_dec[i] == 0) continue;
                int x = olds[i].paper;
                for (auto & f : fillers) if (f.paper == x) f.lvl = old_lvl[i], f.hi = col_of[x];
                if (old_dec[i] == 1) move_to_level(x, old_lvl[i], true, gen_harm(x, d, u));
            }
            for (auto & f : fillers) if (f.paper != d) hh &= ~shown_by(f);
            set_generic(u, hole_all);
            for (auto & cd : picks) if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
            if (d_out) {
                drop_filler(d);
                move(d, 0);
                top_d = d;
            } else lift(d);
            for (auto & cd : picks) if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
            fix_handles(u, hh);
        }
        void run_plan(int u, const PlanOpt & opt) {
            if (opt.fret_mode == 5) {
                run_joint(u, opt);
                return;
            }
            const bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
            u64 pre_cov = 0;
            int stay = - 1;
            if (opt.ret_mode == 4) {
                int d = ded[u];
                if (top_d < 0 || kept || d < 0 || d == top_d ||(gmask & ~paper[d].opaque & paper[top_d].opaque)) {
                    invalid = true;
                    return;
                }
                stay = top_d;
                top_d = - 1;
            }
            if (top_d >= 0 && !kept && opt.ret_mode == 3) {
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
                std::vector < Filler > vis_old, def_old;
                for (auto & f : fillers)(visible(f.paper) ? vis_old : def_old).push_back(f);
                std::vector < Filler > placed = {
                    {
                        x, lvl, lp
                    }
                };
                pre_cov |= cov0;
                auto put_back =[&](const std::vector < Filler > & olds) {
                    if (opt.fret_mode >= 3) refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
                    else for (int i =(int) olds.size() - 1; i >= 0; i--) return_paper(olds[i].paper, u, opt.fret_mode);
                };
                put_back(vis_old);
                move_to_level(x, lvl);
                top_d = - 1;
                put_back(def_old);
                for (auto & f : placed) fillers.push_back(f);
            } else {
                if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
                if (opt.fret_mode >= 3) {
                    std::vector < Filler > olds = fillers, placed;
                    refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
                    for (auto & f : placed) fillers.push_back(f);
                } else while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode);
            }
            if (stay >= 0) {
                fillers.push_back({
                    stay, 0, col_of[stay]
                });
                pre_cov |= shown_by(fillers.back());
            }
            if (opt.use_filler && repeated_prefix(kept, pre_cov)) {
                invalid = true;
                return;
            }
            if (ded[u] < 0) {
                set_generic(u, gmask);
                for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
                return;
            }
            const int d = ded[u];
            const u64 holes =(gmask | hmask) & ~paper[d].opaque;
            set_generic(u, holes);
            u64 hh = holes & ~gmask & ~pre_cov;
            if (!kept && opt.use_filler) {
                auto picks = choose_fillers_prelift(u, d, hh);
                for (auto & pk : picks) if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
                lift(d);
                for (auto & pk : picks) if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            } else {
                if (!kept) lift(d);
                if (opt.use_filler) for (auto & pk : choose_fillers_dp(u, d, hh)) {
                    if ((int) fillers.size() >= kMaxFillers) break;
                    place_filler(pk.c, pk.depth, pk.lvl, hh);
                }
            }
            fix_handles(u, hh);
        }
        std::vector < FillerPick > choose_fillers_prelift(int u, int d, u64 hh) const {
            const int l = col_of[d];
            const u64 hole_all = hmask & ~paper[d].opaque;
            u64 covered = 0;
            for (auto & f : fillers) covered |= shown_by(f);
            auto fix = fix_costs(u, hh);
            std::vector < std::vector < Cand >> cand(H);
            std::vector < int > top;
            for (int c = 0; c < H; c++) {
                if (c == l ||(covered >> handle[c] & 1)) continue;
                bool hole_c = hole_all >> handle[c] & 1;
                column_tops(c, kFillerDepth + 1, top);
                for (int depth = 0; depth <(int) top.size(); depth++) {
                    int f = top[depth];
                    u64 shown = paper[f].opaque & hh;
                    int lvl = level_past((paper[f].black ^ A[u]) & shown);
                    if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                    for (int lv = lvl; lv <= c; lv++) {
                        if (lv > lvl &&(!(shown >> handle[lv] & 1) || reaches_deeper(lv, c, fillers))) continue;
                        bool post = c > l && lv <= l &&(paper[f].opaque >> handle[l] & 1);
                        int save = 0;
                        for (int j = lv; j <= c; j++) if ((shown >> handle[j] & 1) &&(j != c || depth || !hole_c)) save += fix[j];
                        int gain = save - kFillerCost - depth;
                        if (gain > 0) cand[c].push_back({
                            lv,(double) gain, c, depth, 0, - 1, post
                        });
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
            std::vector < Stack > stacks;
            auto hib =[](u64 x) {
                return x ? 63 - __builtin_clzll(x) : - 1;
            };
            auto upto =[](int b)->u64 {
                return b < 0 ? 0 : b >= 63 ? ~0ULL :(1ULL <<(b + 1)) - 1;
            };
            const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
            std::vector < std::array < int, kFillerDepth + 1 >> tops(H);
            std::vector < int > ntop(H, 0);
            for (int k : order) {
                int c = col_of[k];
                if (c < 0 || ntop[c] > kFillerDepth || !in_column(k, c)) continue;
                tops[c][ntop[c]++] = k;
            }
            std::vector < PC > pcs;
            std::vector < int > first_of(H + 1, 0);
            for (int c = 0; c < H; c++) {
                first_of[c] = pcs.size();
                if (c == l ||(covered >> handle[c] & 1)) continue;
                for (int dpt = 0; dpt < ntop[c]; dpt++) {
                    int k = tops[c][dpt];
                    PC pc {
                        c, dpt, h_opq[k] & upto(c), 0, 0,(bool)(hole_all >> handle[c] & 1), 0
                    };
                    pc.shown = pc.opq & hh_i;
                    pc.bad = pc.shown &(h_blk[k] ^ au_i);
                    for (u64 x = pc.shown; x; x &= x - 1) pc.fsum += fix[__builtin_ctzll(x)];
                    pcs.push_back(pc);
                }
            }
            first_of[H] = pcs.size();
            for (auto & L : pcs) {
                if (!L.bad) continue;
                for (int ui = first_of[std::max(hib(L.bad), 0)]; ui < first_of[L.c]; ui++) {
                    const PC & U = pcs[ui];
                    if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 2) continue;
                    int aU = hib(U.bad) + 1;
                    if (aU > U.c) continue;
                    int a = std::max(aU, hib(L.bad & ~U.opq & upto(U.c)) + 1);
                    if (a > U.c) continue;
                    bool postU = U.c > l && a <= l &&(U.opq >> l & 1), postL = postU ||(L.c > l && a <= l &&(L.opq >> l & 1));
                    if ((postU && !U.hole_c) ||(postL && !L.hole_c) || reaches_deeper(a, L.c, fillers)) continue;
                    u64 from_a = ~upto(a - 1), covU = U.shown & from_a & upto(U.c), covL = L.shown & ~U.opq & from_a & upto(L.c);
                    if (U.depth == 0 && U.hole_c) covU &= ~(1ULL << U.c);
                    if (L.depth == 0 && L.hole_c) covL &= ~(1ULL << L.c);
                    int save = 0;
                    for (u64 x = covU | covL; x; x &= x - 1) save += fix[__builtin_ctzll(x)];
                    int gain = save - 2 * kFillerCost - U.depth - L.depth;
                    if (gain < 2) continue;
                    stacks.push_back({
                        U.c, U.depth, L.c, L.depth, postU, postL
                    });
                    cand[L.c].push_back({
                        a,(double) gain, L.c, -(int) stacks.size()
                    });
                }
            }
            std::vector < FillerPick > res;
            for (auto & cd : best_intervals(cand)) {
                if (cd.depth < 0) {
                    const Stack & st = stacks[- 1 - cd.depth];
                    res.push_back({
                        st.cL, st.dL, cd.lvl, st.postL
                    });
                    res.push_back({
                        st.cU, st.dU, cd.lvl, st.postU
                    });
                } else res.push_back({
                    cd.c, cd.depth, cd.lvl, cd.post
                });
            }
            std::reverse(res.begin(), res.end());
            return res;
        }
        bool fillers_reachable() const {
            for (auto & f : fillers) {
                u64 e = paper[f.paper].opaque;
                bool vis = false;
                for (int x : order) {
                    if (x == top_d) continue;
                    if (x == f.paper) {
                        vis = e != 0;
                        break;
                    }
                    e &= ~paper[x].opaque;
                }
                if (!vis) return false;
            }
            return true;
        }
        void merge_double_moves(const std::vector < int > & start, std::vector < std::pair < int, int >> & mvs) const {
            bool dup = false;
            for (size_t i = 0; i < mvs.size() && !dup; i++) for (size_t j = i + 1; j < mvs.size() && !dup; j++) dup = mvs[i].first == mvs[j].first;
            if (!dup) return;
            struct M {
                int k, anchor, pos;
            };
            auto apply =[](std::vector < int > & ord, const M & m) {
                ord.erase(std::find(ord.begin(), ord.end(), m.k));
                if (m.anchor == - 2) ord.insert(ord.begin() + m.pos, m.k);
                else if (m.anchor < 0) ord.insert(ord.begin(), m.k);
                else ord.insert(std::find(ord.begin(), ord.end(), m.anchor) + 1, m.k);
            };
            auto vis =[&](const std::vector < int > & ord, int k) {
                u64 cov = 0;
                for (int x : ord) {
                    if (x == k) return(paper[k].opaque & ~cov) != 0;
                    cov |= paper[x].opaque;
                }
                return false;
            };
            std::vector < int > want = start;
            std::vector < M > mv;
            for (auto[k, d] : mvs) {
                want.erase(std::find(want.begin(), want.end(), k));
                mv.push_back({
                    k, d == 0 ? - 1 : want[d - 1], 0
                });
                want.insert(want.begin() + d, k);
            }
            auto replay_ok =[&](const std::vector < M > & ms, int skip) {
                std::vector < int > ord = start;
                for (int t = 0; t <(int) ms.size(); t++) {
                    if (t == skip) continue;
                    if (ms[t].anchor == ms[t].k || !vis(ord, ms[t].k)) return false;
                    apply(ord, ms[t]);
                }
                return ord == want;
            };
            for (bool again = true; again;) {
                again = false;
                for (int i = 0; i <(int) mv.size() && !again; i++) for (int j = i + 1; j <(int) mv.size(); j++) {
                    if (mv[j].k != mv[i].k) continue;
                    int k = mv[i].k;
                    std::vector < int > st = start;
                    for (int t = 0; t < i; t++) apply(st, mv[t]);
                    std::vector < int > s2 = st;
                    for (int t = i; t <= j; t++) apply(s2, mv[t]);
                    int pj = std::find(s2.begin(), s2.end(), k) - s2.begin();
                    st.erase(std::find(st.begin(), st.end(), k));
                    int pa = mv[j].anchor < 0 ? 0 :(int)(std::find(st.begin(), st.end(), mv[j].anchor) - st.begin()) + 1;
                    for (int p : {
                        pj, pa
                    }) {
                        if (p >(int) st.size()) continue;
                        auto m2 = mv;
                        m2[i] = {
                            k, - 2, p
                        };
                        if (replay_ok(m2, j)) {
                            m2.erase(m2.begin() + j);
                            mv = m2;
                            again = true;
                            break;
                        }
                    }
                    if (!again && replay_ok(mv, i)) {
                        mv.erase(mv.begin() + i);
                        again = true;
                    }
                    break;
                }
            }
            std::vector < int > ord = start;
            mvs.clear();
            for (auto & m : mv) {
                int before = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
                apply(ord, m);
                int after = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
                if (after != before) mvs.push_back({
                    m.k, after
                });
            }
        }
        void canonicalize() {
            std::vector < char > inpl(K, 0);
            std::vector < int > lv(K, - 1);
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
                } else lv[k] = gen_seen ? 0 : std::min(cur, c);
            }
            int ntop = - 1;
            std::vector < Filler > nf;
            for (int i = 0; i < K; i++) {
                int k = order[i];
                if (col_of[k] < 0 || inpl[k]) continue;
                if (i == 0) ntop = k;
                else nf.push_back({
                    k, lv[k], col_of[k]
                });
            }
            std::vector < Filler > res;
            for (auto & f : fillers) for (auto & g : nf) if (g.paper == f.paper) res.push_back(g);
            for (auto & g : nf) if (!is_filler(g.paper)) res.push_back(g);
            top_d = ntop;
            fillers = res;
        }
        struct State {
            std::vector < int > order;
            int top_d;
            std::vector < Filler > fillers;
        };
        State save() const {
            return {
                order, top_d, fillers
            };
        }
        void restore(const State & st) {
            order = st.order;
            top_d = st.top_d;
            fillers = st.fillers;
        }
        static constexpr double kFillerCharge = .6;
        std::vector < std::pair < int, int >> process(int u) {
            prefix_memo.clear();
            init_adaptive();
            adaptive_request = u;
            if (fast_mode) {
                fast_requests++;
                ops.clear();
                invalid = false;
                check_vis = true;
                run_plan(u, PlanOpt {
                });
                check_vis = false;
                canonicalize();
                return ops;
            }
            const State st0 = save();
            const int top0 = top_d, d = ded[u];
            const bool prev_ok = top0 >= 0 && d >= 0 && d != top0, any_out = !fillers.empty();
            const std::vector < int > fms = any_out ? std::vector < int > {
                1, 2, 3, 4
            }
            : std::vector < int > {
                1
            }, frets = any_out ? std::vector < int > {
                1, 0
            }
            : std::vector < int > {
                1
            };
            auto frets_of =[&](int fm) {
                return fm >= 3 ? frets : std::vector < int > {
                    1
                };
            };
            std::vector < PlanOpt > opts;
            for (int rm = 1; rm <=(prev_ok ? 3 : 2); rm++) for (int fm : fms) for (int kp = 0; kp <((top0 >= 0 && d == top0) ? 2 : 1); kp++) for (int fr : frets_of(fm)) opts.push_back({
                rm, fm, true, kp == 1, fr
            });
            if (d >= 0 && d != top0) for (int rm = 1; rm <= 2; rm++) for (int fr : frets) opts.push_back({
                rm, 5, true, false, fr
            });
            if (prev_ok) for (int fm : fms) for (int fr : frets_of(fm)) opts.push_back({
                4, fm, true, false, fr
            });
            double best = 1e18;
            std::vector < std::pair < int, int >> best_ops;
            State best_state;
            check_vis = true;
            for (const PlanOpt & o : opts) {
                restore(st0);
                ops.clear();
                invalid = false;
                run_plan(u, o);
                if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
                merge_double_moves(st0.order, ops);
                double future = kEndWeight * adaptive_next_cost(), cost = ops.size() + kFillerCharge * fillers.size() + future;
                if (cost < best) best = cost, best_ops = ops, best_state = save();
            }
            check_vis = false;
            if (best > 1e17) {
                plan_failures++;
                restore(st0);
                ops.clear();
                invalid = false;
                run_plan(u, PlanOpt {
                });
                return ops;
            }
            restore(best_state);
            canonicalize();
            return best_ops;
        }
    };
    int emergency_design(const std::vector < u64 > & A, int R) {
        std::string output;
        for (int k = 0; k < K; k++) {
            std::string row(N, '.');
            if (k < 128) row[k % 64] = k < 64 ? '0' : '1';
            output += row + '\n';
        }
        std::cout << output << std::flush;
        u64 current = 0;
        long long total = 0;
        for (int r = 0; r < R; r++) {
            int u;
            if (!(std::cin >> u) || u == - 1) return 0;
            u64 different = current ^ A[u];
            output = std::to_string(__builtin_popcountll(different)) + '\n';
            for (u64 s = different; s; s &= s - 1) {
                int j = __builtin_ctzll(s), k = j +((current >> j & 1) ? 64 : 0);
                output += std::to_string(k) + " 191\n";
                total++;
            }
            current = A[u];
            std::cout << output << std::flush;
        }
        std::cerr << "total_moves = " << total << "\nemergency_design = 1\n";
        return 0;
    }
}
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, k, p, R;
    if (!(std::cin >> n >> k >> p >> R)) return 0;
    std::vector < u64 > A(P);
    for (auto & a : A) {
        std::string s;
        std::cin >> s;
        a = 0;
        for (int j = 0; j < N; j++) if (s[j] == '1') a |= 1ULL << j;
    }
    if (n != N || k != K || p != P) return 0;
    const auto originalA = A;
#ifdef FORCE_EMERGENCY_DESIGN
    return emergency_design(originalA, R);
#endif
    constexpr double kMapEnd = .50, kGoptEnd = .61, kAnnealEnd = 1.425, kClimbEnd = 1.48, kFastAfter = 1.80, kInitGiveUp = 1.30,
    kInitExpiry = 1.35;
    const int map_iters = env_int("MAP_ITERS"), anneal_iters = env_int("ANNEAL_ITERS"), climb_iters = env_int("CLIMB_ITERS");
    std::vector < int > permutation(64);
    int M = 6, G = 36;
    Comparator comp;
    std::mt19937_64 rng(779879);
    std::unique_ptr < Design > des;
    int map_total = 0;
    for (int attempt = 0;; attempt++) {
        A = originalA;
        std::iota(permutation.begin(), permutation.end(), 0);
        comp.init(M, G, rng);
        if (attempt < 2) {
            const double seconds = map_iters ? 1e9 : attempt == 0 ? kMapEnd - elapsed_sec() : .18;
            const int gsteps = attempt ? 0 : std::max(0, env_int("GOPT_STEPS"));
            const double gsec = attempt || env_int("GOPT_STEPS") ? 0. : std::max(0., kGoptEnd - kMapEnd);
            auto ws = assign_windows(A, M, G, comp.edge, comp.polarity, permutation, seconds, map_iters, gsteps, gsec);
            map_total += ws.iterations;
            if (!attempt) std::cerr << "gobj_before = " << ws.gobj_before << "\ngobj_after = " << ws.gobj_after << "\ngopt_steps = " << ws.climb_steps << '\n';
        }
        comp.rebuild();
        des = std::make_unique < Design >(A, M, G);
        auto estimate =[&](u64 a, u64 b) {
            return legal_pair_generic_mean(comp, a, b);
        };
        const bool untimed = map_iters > 0;
        if (des->initialize([&](u64 a, u64 b) {
            return comp.compatible(a, b);
        }, estimate,[&]() {
            return !untimed && elapsed_sec() > kInitExpiry;
        })) break;
        if (attempt >= 2 ||(!untimed && elapsed_sec() > kInitGiveUp)) return emergency_design(originalA, R);
        G = attempt == 0 ? 32 : 28;
    }
    std::cerr << "map_iters = " << map_total << "\nmap_end_sec = " << elapsed_sec() << '\n';
    if (anneal_iters) des->anneal(1e9, anneal_iters);
    else des->anneal(std::max(.005, kAnnealEnd - elapsed_sec()), 0);
    std::cerr << "anneal_iters = " << des->anneal_iters << "\nanneal_end_sec = " << elapsed_sec() << '\n';
    if (climb_iters >= 0) {
        if (climb_iters) des->filler_climb(1e9, climb_iters);
        else des->filler_climb(std::max(0., kClimbEnd - elapsed_sec()), 0);
    }
    std::cerr << "climb_iters = " << des->climb_iters << "\nclimb_accepted = " << des->climb_accepted << "\nproxy_before = " << des->proxy_before / P << "\nproxy_after = " << des->proxy_after / P << "\nclimb_end_sec = " << elapsed_sec() << '\n';
    std::vector < Paper > papers(K);
    std::vector < int > columns(K, - 1), ded(P, - 1);
    for (int i = 0; i < M; i++) papers[i] = {
        comp.opq[i], comp.black[i]
    };
    u64 opaque = low_bits(G);
    int next = M;
    for (int c = 0; c < des->H; c++) {
        opaque |= 1ULL << des->handle[c];
        std::array < std::vector < int >, 2 > members;
        for (int x = 0; x < des->U; x++) if (des->unit[x].c == c) members[des->color(des->unit[x], c)].push_back(x);
        for (auto & group : members) std::stable_sort(group.begin(), group.end(),[&](int x, int y) {
            return des->weight(des->unit[x]) < des->weight(des->unit[y]);
        });
        while (!members[0].empty() || !members[1].empty()) {
            int color = members[1].size() > members[0].size();
            int x = members[color].back();
            members[color].pop_back();
            const auto & u = des->unit[x];
            u64 mask = opaque;
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            papers[next] = {
                mask, A[u.a] & mask
            };
            columns[next] = c;
            ded[u.a] = next;
            if (u.b >= 0) ded[u.b] = next;
            next++;
        }
    }
    if (next != K || std::find(ded.begin(), ded.end(), - 1) != ded.end()) return emergency_design(originalA, R);
    Solver solver(A);
    solver.M = M;
    solver.G = G;
    solver.H = des->H;
    solver.comparator = comp;
    solver.paper = papers;
    solver.col_of = columns;
    solver.ded = ded;
    solver.handle = des->handle;
    solver.hidx.assign(64, - 1);
    for (int c = 0; c < des->H; c++) solver.hidx[solver.handle[c]] = c;
    solver.gmask = low_bits(G);
    solver.hmask = ~solver.gmask;
    solver.h_opq.resize(K);
    solver.h_blk.resize(K);
    for (int x = 0; x < K; x++) {
        solver.h_opq[x] = solver.handle_bits(papers[x].opaque);
        solver.h_blk[x] = solver.handle_bits(papers[x].black);
    }
    solver.order.resize(K);
    std::iota(solver.order.begin(), solver.order.end(), 0);
    solver.init_adaptive();
#ifdef SIM_HARNESS
    if (int ns = env_int("SIM_SEQS"); ns > 0) {
        double tot = 0;
        long long wr = 0;
        for (int q = 0; q < ns; q++) {
            Solver sim = solver;
            std::mt19937_64 rr(1000003ULL *(q + 1));
            int prev = rr() % P;
            for (int t = 0; t < R; t++) {
                int u = t == 0 ? prev : int(rr() %(P - 1));
                if (t > 0 && u >= prev) u++;
                prev = u;
                tot += sim.process(u).size();
                wr += sim.display() != A[u];
            }
        }
        std::cerr << "sim_moves = " << tot /(double(ns) * R) << "\nsim_wrong = " << double(wr) / ns << '\n';
        return 0;
    }
#endif
    std::string output;
    for (const auto & pp : papers) {
        std::string row(N, '.');
        for (int j = 0; j < N; j++) row[permutation[j]] = !(pp.opaque >> j & 1) ? '.' :(pp.black >> j & 1) ? '1' : '0';
        output += row + '\n';
    }
    std::cout << output << std::flush;
    long long total = 0, generic = 0, wrong = 0;
    double req_sec = 0;
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == - 1) return 0;
        const double t_req = elapsed_sec();
        if (t_req > kFastAfter) solver.fast_mode = true;
#ifdef FORCE_FAST_MODE
        solver.fast_mode = true;
#endif
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != A[u];
        output = std::to_string(moves.size()) + '\n';
        for (auto[x, d] : moves) {
            output += std::to_string(x) + ' ' + std::to_string(d) + '\n';
            generic += x < M;
        }
        std::cout << output << std::flush;
        total += moves.size();
    }
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total << "\nG = " << G << "\nplan_failures = " << solver.plan_failures << "\nfast_requests = " << solver.fast_requests << "\nreq_sec = " << req_sec << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
