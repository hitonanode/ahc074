// Stage 1 of the legal-operation search (solutions/legal-notes): for every order of a SOTA output,
// search for a legal move sequence from the start order S to exactly the SOTA's end order T with fewer
// moves than the SOTA used.
//
// Usage: same_end INPUT OUTPUT SEED [budget_nodes] [mode] [r_from r_to]
//   mode 0: single-move class only (each paper moves at most once; exact for that class).
//   mode 1: also a multi-move class (a paper may move twice), searched with parking slots.
//   mode 2: multi-move class only (skips the single-move search).
// Prints one line per order: seed r m LB best status nodes [k:d ...]
//   status: opt0 (m == LB: optimal), opt1 (no single-move solution shorter than m), imp (found a shorter
//   single-move solution of length best), unk (node budget exhausted).
//   Mode 1 appends " | best mstatus nodes [k:d ...]" for the multi-move search (mopt: none in the
//   restricted multi-move space, mimp: found, munk: budget exhausted).
//
// Search: IDA* over the full stack. Only visible papers move. Candidate slots of paper x: directly above
// the j-th T-successor of x (j up to the remaining budget) and the bottom. For single-move solutions this
// set is complete (README.md of this directory: the deepest slot consistent with T relative to the papers
// that never move again covers a subset of what any other consistent slot covers).
// Lower bound: the papers that must still move (Must) are those with an inversion (relative order unlike T)
// with an already-moved paper (single-move class) or with more inversions than the remaining budget; the
// other papers need a vertex cover of their inversions (|U| - LIS(U)); a must-move paper that is not
// visible needs all non-must papers above it that are opaque in one of its windows to move first.
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

constexpr int K = 192;
constexpr int N = 64;
using Order = std::array<uint8_t, K>;

struct Bits {
  uint64_t w[3] = {0, 0, 0};
  void set(int i) { w[i >> 6] |= 1ULL << (i & 63); }
  bool test(int i) const { return w[i >> 6] >> (i & 63) & 1; }
  int count() const { return std::popcount(w[0]) + std::popcount(w[1]) + std::popcount(w[2]); }
  bool any() const { return (w[0] | w[1] | w[2]) != 0; }
  Bits operator^(const Bits& o) const { Bits r; for (int i = 0; i < 3; i++) r.w[i] = w[i] ^ o.w[i]; return r; }
  Bits operator&(const Bits& o) const { Bits r; for (int i = 0; i < 3; i++) r.w[i] = w[i] & o.w[i]; return r; }
  Bits operator|(const Bits& o) const { Bits r; for (int i = 0; i < 3; i++) r.w[i] = w[i] | o.w[i]; return r; }
  Bits operator~() const { Bits r; for (int i = 0; i < 3; i++) r.w[i] = ~w[i]; return r; }
};

static uint64_t opq[K];
static uint64_t blk[K];

static int lis_len(const int* a, int n) {
  int tails[K + 1];
  int len = 0;
  for (int i = 0; i < n; i++) {
    int v = a[i];
    int lo = 0, hi = len;
    while (lo < hi) {
      int mid = (lo + hi) >> 1;
      if (tails[mid] < v) lo = mid + 1; else hi = mid;
    }
    tails[lo] = v;
    if (lo == len) len++;
  }
  return len;
}

struct Search {
  int trank[K];
  int tpaper[K];
  Bits aboveT[K];  // papers above paper k in T
  int bound = 0;
  long long nodes = 0, budget = 0;
  bool aborted = false;
  bool single = true;  // single-move class with the canonical-slot assertions
  bool plain = false;  // check mode: single-move class without assertions, lower bound K - LIS only
  int max_moves = 1;   // per paper (multi-move class)
  bool parking = false;
  std::vector<std::pair<int, int>> path, best;
  std::vector<uint64_t> tt_key;
  std::vector<uint8_t> tt_g;
  uint32_t tt_mask = 0;
  uint8_t movecount[K];
  // Single-move class: frozen = never moves again (moved papers, and papers asserted settled because a
  // moved paper was placed directly above them); pending = asserted to move later (the T-successors that a
  // moved paper skipped). The canonical slot of a move is directly above the nearest settled T-successor,
  // so each canonical sequence is generated once, with consistent assertions.
  uint8_t frozen[K], pending[K];
  long long prof_nodes[64] = {}, prof_bound[64] = {}, prof_tt[64] = {}, prof_children[64] = {};
  int npending = 0;
  uint64_t zfrozen[K], zpending[K], zmv[K][3];
  uint64_t zpos[K][K];

  void tt_init(int bits) {
    tt_key.assign(1u << bits, 0);
    tt_g.assign(1u << bits, 255);
    tt_mask = (1u << bits) - 1;
  }
  void tt_clear() {
    std::fill(tt_key.begin(), tt_key.end(), 0);
    std::fill(tt_g.begin(), tt_g.end(), 255);
  }
  bool tt_check(uint64_t key, int g) {
    uint32_t h = (uint32_t)(key ^ (key >> 29)) & tt_mask;
    for (int probe = 0; probe < 4; probe++) {
      uint32_t i = (h + probe) & tt_mask;
      if (tt_key[i] == key) {
        if (tt_g[i] <= g) return true;
        tt_g[i] = (uint8_t)g;
        return false;
      }
      if (tt_g[i] == 255) {
        tt_key[i] = key;
        tt_g[i] = (uint8_t)g;
        return false;
      }
    }
    tt_key[h] = key;
    tt_g[h] = (uint8_t)g;
    return false;
  }

  // Lower bound on the moves still needed from ord (a large value if infeasible).
  // Also fills rk / lend / lstart / L / covbefore for the move generation.
  int lower_bound(const Order& ord, int rem, int* rk, int* lend, int* lstart, int& L, uint64_t* covbefore) {
    for (int i = 0; i < K; i++) rk[i] = trank[ord[i]];
    {
      int fw[K + 1];
      std::memset(fw, 0, sizeof(fw));
      for (int i = 0; i < K; i++) {
        int v = rk[i];
        int b = 0;
        for (int x = v; x > 0; x -= x & -x) b = std::max(b, fw[x]);
        lend[i] = b + 1;
        for (int x = v + 1; x <= K; x += x & -x) fw[x] = std::max(fw[x], lend[i]);
      }
      std::memset(fw, 0, sizeof(fw));
      for (int i = K - 1; i >= 0; i--) {
        int v = K - 1 - rk[i];
        int b = 0;
        for (int x = v; x > 0; x -= x & -x) b = std::max(b, fw[x]);
        lstart[i] = b + 1;
        for (int x = v + 1; x <= K; x += x & -x) fw[x] = std::max(fw[x], lstart[i]);
      }
    }
    L = 0;
    for (int i = 0; i < K; i++) L = std::max(L, lend[i]);
    int h0 = K - L;
    if (h0 > rem) return h0;
    if (h0 == 0) return 0;
    if (plain) {
      uint64_t cov = 0;
      for (int i = 0; i < K; i++) {
        covbefore[i] = cov;
        cov |= opq[ord[i]];
      }
      return h0;
    }
    if (single && npending > rem) return npending;
    Bits above[K];
    Bits acc;
    for (int i = 0; i < K; i++) {
      int p = ord[i];
      above[p] = acc;
      acc.set(p);
    }
    Bits fz;
    if (single) for (int k = 0; k < K; k++) if (frozen[k]) fz.set(k);
    Bits must;
    int deg[K];
    for (int k = 0; k < K; k++) {
      Bits inv = above[k] ^ aboveT[k];
      deg[k] = inv.count();
      if (single && frozen[k] && deg[k]) {
        // the inversions of a paper that never moves again must be fixed by its partners
        if ((inv & fz).any()) return 1000;
        must = must | inv;
      }
    }
    for (int k = 0; k < K; k++) {
      if (single && frozen[k]) continue;
      if (deg[k] > rem || (single && pending[k])) must.set(k);
    }
    if (single) must = must & ~fz;
    int nmust = must.count();
    if (nmust > rem) return nmust;
    // vertex cover of the inversions among the other movable papers
    int sub[K];
    int ns = 0;
    for (int i = 0; i < K; i++) {
      int p = ord[i];
      if (must.test(p)) continue;
      if (single && frozen[p]) continue;
      sub[ns++] = rk[i];
    }
    int vc = ns - lis_len(sub, ns);
    // visibility of the must-move papers
    int visb = 0;
    {
      int cnt[N];
      std::memset(cnt, 0, sizeof(cnt));
      uint64_t blocked = 0;  // windows covered by a frozen paper (never unblocked)
      uint64_t cov = 0;
      for (int i = 0; i < K; i++) {
        int p = ord[i];
        covbefore[i] = cov;
        if (must.test(p)) {
          uint64_t free_w = opq[p] & ~cov;
          if (!free_w) {
            uint64_t cand = opq[p] & ~blocked;
            if (!cand) return 1000;
            int bestc = 1000;
            for (uint64_t c = cand; c; c &= c - 1) bestc = std::min(bestc, cnt[std::countr_zero(c)]);
            visb = std::max(visb, bestc);
          }
        }
        if (single && frozen[p]) {
          blocked |= opq[p];
        } else if (!must.test(p)) {
          for (uint64_t c = opq[p]; c; c &= c - 1) cnt[std::countr_zero(c)]++;
        }
        cov |= opq[p];
      }
    }
    return std::max(h0, nmust + std::max(vc, visb));
  }

  uint64_t key_of(const Order& ord) const {
    uint64_t key = 0;
    for (int i = 0; i < K; i++) key ^= zpos[i][ord[i]];
    for (int k = 0; k < K; k++) {
      if (single && !plain) {
        if (frozen[k]) key ^= zfrozen[k];
        if (pending[k]) key ^= zpending[k];
      } else if (movecount[k]) {
        key ^= zmv[k][movecount[k]];
      }
    }
    return key;
  }

  bool dfs(const Order& ord, int g) {
    if (aborted) return false;
    if (++nodes > budget) { aborted = true; return false; }
    int rk[K], lend[K], lstart[K], L;
    uint64_t covbefore[K];
    int rem = bound - g;
    int h = lower_bound(ord, rem, rk, lend, lstart, L, covbefore);
    prof_nodes[g]++;
    if (h > rem) { prof_bound[g]++; return false; }
    if (L == K) { best = path; return true; }
    if (tt_check(key_of(ord), g)) { prof_tt[g]++; return false; }
    int levelcnt[K + 1];
    std::memset(levelcnt, 0, sizeof(levelcnt));
    for (int i = 0; i < K; i++) if (lend[i] + lstart[i] - 1 == L) levelcnt[lend[i]]++;
    int pos[K];
    for (int i = 0; i < K; i++) pos[ord[i]] = i;
    for (int px = 0; px < K; px++) {
      int x = ord[px];
      if (!(opq[x] & ~covbefore[px])) {
        if (covbefore[px] == ~0ULL) break;
        continue;
      }
      if ((single && !plain) ? (bool)frozen[x] : movecount[x] >= max_moves) continue;
      int rx = rk[px];
      bool ess = (lend[px] + lstart[px] - 1 == L) && levelcnt[lend[px]] == 1;
      int base = L - (ess ? 1 : 0);
      int pre[K + 1], suf[K + 1];
      pre[0] = 0;
      for (int i = 0; i < K; i++) pre[i + 1] = std::max(pre[i], (rk[i] < rx) ? lend[i] : 0);
      suf[K] = 0;
      for (int i = K - 1; i >= 0; i--) suf[i] = std::max(suf[i + 1], (rk[i] > rx) ? lstart[i] : 0);
      // candidates: (cut q in the current order, insertion index d without x, successor count j)
      // j = 0 marks a parking slot; j = K marks the bottom as a canonical slot
      int cq[K + 4], cd[K + 4], cj[K + 4];
      int nc = 0;
      int newp = 0;  // successors 1..j-1 that are not yet pending (single class)
      for (int j = 1; j <= rem && rx + j < K; j++) {
        int s = tpaper[rx + j];
        if (single && !plain) {
          if (j > 1) {
            int sp = tpaper[rx + j - 1];
            if (frozen[sp]) break;  // a skipped successor must move later
            if (!pending[sp]) newp++;
          }
          if (pending[s]) continue;  // s moves later: it cannot be the settled successor
          if (npending - (pending[x] ? 1 : 0) + newp > rem - 1) break;
        }
        int q = pos[s];
        cq[nc] = q;
        cd[nc] = (q > px) ? q - 1 : q;
        cj[nc] = j;
        nc++;
      }
      {
        int nsucc = K - 1 - rx;
        bool ok = nsucc <= rem - 1;
        if (single && !plain && ok) {
          int np = 0;
          for (int j = 1; j <= nsucc; j++) {
            int s = tpaper[rx + j];
            if (frozen[s]) { ok = false; break; }
            if (!pending[s]) np++;
          }
          if (ok && npending - (pending[x] ? 1 : 0) + np > rem - 1) ok = false;
        }
        if (ok) { cq[nc] = K; cd[nc] = K - 1; cj[nc] = K; nc++; }
      }
      if (!single && parking) {
        cq[nc] = 0; cd[nc] = 0; cj[nc] = 0; nc++;                          // top
        cq[nc] = (px < 7) ? 8 : 7; cd[nc] = 7; cj[nc] = 0; nc++;            // below the generic layer + cap
        cq[nc] = K; cd[nc] = K - 1; cj[nc] = 0; nc++;                       // bottom
      }
      for (int c = 0; c < nc; c++) {
        int q = cq[c], d = cd[c], j = cj[c];
        if (d == px) continue;
        if (!single) {
          bool dup = false;
          for (int c2 = 0; c2 < c; c2++) if (cd[c2] == d) { dup = true; break; }
          if (dup) continue;
        }
        int chain = 1 + pre[q] + suf[q];
        int lis_child = std::max(base, chain);
        if (g + 1 + (K - lis_child) > bound) continue;
        Order child;
        {
          uint8_t tmp[K];
          int t = 0;
          for (int i = 0; i < K; i++) if (i != px) tmp[t++] = ord[i];
          int u = 0;
          for (int i = 0; i < K; i++) child[i] = (i == d) ? (uint8_t)x : tmp[u++];
        }
        // assertions
        int setp[K], nsetp = 0;
        int setf = -1;
        bool xpend = pending[x];
        if (single && !plain) {
          int last = (j == K) ? K - 1 - rx : j - 1;
          for (int t = 1; t <= last; t++) {
            int s = tpaper[rx + t];
            if (!pending[s]) { pending[s] = 1; npending++; setp[nsetp++] = s; }
          }
          if (j != K) {
            int s = tpaper[rx + j];
            if (!frozen[s]) { frozen[s] = 1; setf = s; }
          }
          frozen[x] = 1;
          if (xpend) { pending[x] = 0; npending--; }
        }
        path.emplace_back(x, d);
        movecount[x]++;
        prof_children[g]++;
        bool ok = dfs(child, g + 1);
        movecount[x]--;
        path.pop_back();
        if (single && !plain) {
          frozen[x] = 0;
          if (xpend) { pending[x] = 1; npending++; }
          if (setf >= 0) frozen[setf] = 0;
          for (int t = 0; t < nsetp; t++) { pending[setp[t]] = 0; npending--; }
        }
        if (ok) return true;
        if (aborted) return false;
      }
    }
    return false;
  }

  // IDA* from start with bounds lo..hi; returns the found length or -1.
  int run(const Order& start, int lo, int hi, std::vector<std::pair<int, int>>& sol) {
    for (int b = lo; b <= hi; b++) {
      bound = b;
      tt_clear();
      std::memset(movecount, 0, sizeof(movecount));
      std::memset(frozen, 0, sizeof(frozen));
      std::memset(pending, 0, sizeof(pending));
      npending = 0;
      path.clear();
      long long before = nodes;
      bool okb = dfs(start, 0);
      if (getenv("SE_TRACE")) {
        fprintf(stderr, "  bound %d nodes %lld found %d\n", b, nodes - before, (int)okb);
        for (int g = 0; g <= b; g++) {
          if (prof_nodes[g]) fprintf(stderr, "    g %d nodes %lld bound %lld tt %lld children %lld\n", g, prof_nodes[g], prof_bound[g], prof_tt[g], prof_children[g]);
          prof_nodes[g] = prof_bound[g] = prof_tt[g] = prof_children[g] = 0;
        }
      }
      if (okb) { sol = best; return b; }
      if (aborted) return -1;
    }
    return -1;
  }
};

static std::vector<std::string> read_tokens(const char* path) {
  std::ifstream f(path);
  std::vector<std::string> t;
  std::string s;
  while (f >> s) t.push_back(s);
  return t;
}

static void apply_move(Order& o, int k, int d) {
  int px = 0;
  while (o[px] != k) px++;
  uint8_t tmp[K];
  int t = 0;
  for (int i = 0; i < K; i++) if (i != px) tmp[t++] = o[i];
  int u = 0;
  for (int i = 0; i < K; i++) o[i] = (i == d) ? (uint8_t)k : tmp[u++];
}

static void set_target(Search& S, const Order& T) {
  Bits acc;
  for (int i = 0; i < K; i++) {
    S.trank[T[i]] = i;
    S.tpaper[i] = T[i];
    S.aboveT[T[i]] = acc;
    acc.set(T[i]);
  }
}

static int lb_of(const Search& S, const Order& start) {
  int rk[K];
  for (int i = 0; i < K; i++) rk[i] = S.trank[start[i]];
  return K - lis_len(rk, K);
}

static uint64_t trng = 12345;
static uint64_t rnd() {
  trng ^= trng << 13;
  trng ^= trng >> 7;
  trng ^= trng << 17;
  return trng;
}

// Soundness tests from a real start state: random legal single-move sequences (uniform, local and
// top/bottom slots) and dig sequences (blockers of a hidden paper moved below it, then the paper lifted).
// The search (single-move class) must find a solution no longer than the sequence.
static void soundness_tests(Search& S, const Order& start, int seed, int r, int reps) {
  for (int rep = 0; rep < reps; rep++) {
    Order cur = start;
    std::vector<std::pair<int, int>> seq;
    uint8_t used[K];
    std::memset(used, 0, sizeof(used));
    bool dig = rep % 2 == 1;
    if (!dig) {
      int n = 1 + rnd() % 12;
      for (int step = 0; step < n; step++) {
        std::vector<int> vis;
        uint64_t cov = 0;
        for (int i = 0; i < K; i++) {
          int q = cur[i];
          if ((opq[q] & ~cov) && !used[q]) vis.push_back(i);
          cov |= opq[q];
        }
        if (vis.empty()) break;
        int pi = vis[rnd() % vis.size()];
        int x = cur[pi];
        int d;
        int md = rnd() % 3;
        if (md == 0) d = rnd() % K;
        else if (md == 1) d = std::clamp(pi + (int)(rnd() % 21) - 10, 0, K - 1);
        else d = (rnd() % 2) ? K - 1 : (int)(rnd() % 8);
        if (d == pi) continue;
        apply_move(cur, x, d);
        used[x] = 1;
        seq.emplace_back(x, d);
      }
    } else {
      // dig 1-3 hidden papers
      int targets = 1 + rnd() % 3;
      bool ok = true;
      for (int t = 0; t < targets && ok; t++) {
        // a hidden unmoved paper within the top 120 positions
        int py = -1;
        for (int tries = 0; tries < 50; tries++) {
          int cand = rnd() % 120;
          int y = cur[cand];
          if (used[y]) continue;
          uint64_t cov = 0;
          for (int i = 0; i < cand; i++) cov |= opq[cur[i]];
          if (!(opq[y] & ~cov) && opq[y]) { py = cand; break; }
        }
        if (py < 0) break;
        int y = cur[py];
        // choose the window with the fewest blockers
        int bestw = -1, bestc = 1000;
        for (int w = 0; w < N; w++) {
          if (!(opq[y] >> w & 1)) continue;
          int c = 0;
          for (int i = 0; i < py; i++) if (opq[cur[i]] >> w & 1) c++;
          if (c < bestc) { bestc = c; bestw = w; }
        }
        if (bestc > 6) { ok = false; break; }
        // move blockers (topmost first) below y
        for (int it = 0; it < 10; it++) {
          int pyy = 0;
          while (cur[pyy] != y) pyy++;
          int pb = -1;
          for (int i = 0; i < pyy; i++) if (opq[cur[i]] >> bestw & 1) { pb = i; break; }
          if (pb < 0) break;
          int b = cur[pb];
          if (used[b]) { ok = false; break; }
          int lo = pyy;  // in the sequence without b, y is at pyy - 1; insert below it
          int d = std::min(K - 1, lo + (int)(rnd() % 12));
          apply_move(cur, b, d);
          used[b] = 1;
          seq.emplace_back(b, d);
        }
        if (!ok) break;
        // lift y
        int pyy = 0;
        while (cur[pyy] != y) pyy++;
        uint64_t cov = 0;
        for (int i = 0; i < pyy; i++) cov |= opq[cur[i]];
        if (!(opq[y] & ~cov)) { ok = false; break; }
        int d = rnd() % 10;
        if (d == pyy) d = (d + 1) % 10;
        apply_move(cur, y, d);
        used[y] = 1;
        seq.emplace_back(y, d);
      }
      if (!ok) continue;
    }
    int n = seq.size();
    if (!n) continue;
    set_target(S, cur);
    S.single = true;
    S.max_moves = 1;
    S.parking = false;
    // the bound along the sequence
    std::memset(S.movecount, 0, sizeof(S.movecount));
    std::memset(S.frozen, 0, sizeof(S.frozen));
    std::memset(S.pending, 0, sizeof(S.pending));
    S.npending = 0;
    Order st = start;
    for (int i = 0; i <= n; i++) {
      int rk[K], le[K], ls[K], L;
      uint64_t cb[K];
      int h = S.lower_bound(st, n - i, rk, le, ls, L, cb);
      if (h > n - i) printf("BOUND_VIOLATION seed %d r %d rep %d step %d h %d rem %d\n", seed, r, rep, i, h, n - i);
      if (i < n) {
        apply_move(st, seq[i].first, seq[i].second);
        S.movecount[seq[i].first]++;
        S.frozen[seq[i].first] = 1;
      }
    }
    int LB = lb_of(S, start);
    S.nodes = 0;
    S.aborted = false;
    std::vector<std::pair<int, int>> sol;
    int f = S.run(start, LB, n, sol);
    if (f < 0 && !S.aborted) printf("SEARCH_MISS seed %d r %d rep %d dig %d n %d LB %d\n", seed, r, rep, (int)dig, n, LB);
    else if (f < 0) printf("TEST_UNK seed %d r %d dig %d n %d\n", seed, r, (int)dig, n);
    else printf("TEST_OK seed %d r %d dig %d n %d LB %d found %d nodes %lld\n", seed, r, (int)dig, n, LB, f, S.nodes);
  }
}

int main(int argc, char** argv) {
  if (argc < 4) {
    fprintf(stderr, "usage: same_end INPUT OUTPUT SEED [budget] [mode] [r_from r_to]\n");
    return 1;
  }
  int seed = atoi(argv[3]);
  long long budget = argc > 4 ? atoll(argv[4]) : 2000000;
  int mode = argc > 5 ? atoi(argv[5]) : 0;
  int rfrom = argc > 7 ? atoi(argv[6]) : 0;
  int rto = argc > 7 ? atoi(argv[7]) : 1024;
  auto in = read_tokens(argv[1]);
  auto out = read_tokens(argv[2]);
  int R = atoi(in[3].c_str());
  std::vector<int> req(R);
  for (int r = 0; r < R; r++) req[r] = atoi(in[4 + 256 + r].c_str());
  size_t p = 0;
  for (int k = 0; k < K; k++) {
    const std::string& s = out[p++];
    uint64_t o = 0, b = 0;
    for (int j = 0; j < N; j++) {
      if (s[j] != '.') o |= 1ULL << j;
      if (s[j] == '1') b |= 1ULL << j;
    }
    opq[k] = o;
    blk[k] = b;
  }
  // splitmix64 for the zobrist keys (a weak xorshift gave colliding keys and false proofs)
  uint64_t rng = 0x123456789ABCDEFULL + (uint64_t)seed;
  auto next = [&]() {
    uint64_t z = (rng += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
  };

  trng = 0x2545F4914F6CDD1DULL ^ (uint64_t)seed * 0x9E3779B97F4A7C15ULL;
  if (!trng) trng = 1;

  Order ord;
  for (int i = 0; i < K; i++) ord[i] = (uint8_t)i;
  static Search S;
  for (int i = 0; i < K; i++) for (int k = 0; k < K; k++) S.zpos[i][k] = next();
  for (int k = 0; k < K; k++) {
    S.zfrozen[k] = next();
    S.zpending[k] = next();
    S.zmv[k][0] = 0;
    S.zmv[k][1] = next();
    S.zmv[k][2] = next();
  }
  S.tt_init(20);
  S.budget = budget;
  for (int r = 0; r < R; r++) {
    int m = atoi(out[p++].c_str());
    std::vector<std::pair<int, int>> ops(m);
    for (int i = 0; i < m; i++) {
      ops[i].first = atoi(out[p++].c_str());
      ops[i].second = atoi(out[p++].c_str());
    }
    Order start = ord;
    for (auto [k, d] : ops) apply_move(ord, k, d);
    if (r < rfrom || r >= rto) continue;
    if (mode == 9) {
      soundness_tests(S, start, seed, r, 4);
      continue;
    }
    const Order& T = ord;
    set_target(S, T);
    int LB = lb_of(S, start);
    bool sota_single = true;
    {
      uint8_t c[K];
      std::memset(c, 0, sizeof(c));
      for (auto [k, d] : ops) if (c[k]++) sota_single = false;
    }
    std::ostringstream line;
    line << seed << ' ' << r << ' ' << m << ' ' << LB;
    if (mode == 8) {
      // Stage 2b: shorter sequences to other end states that show the request. Candidate end states are
      // built from the SOTA's end order T: (a) one moved paper put back to its place among the unmoved
      // papers (just above its S-successor, or just below its S-predecessor, among them); (b) two moved
      // papers put back and one other paper z inserted where it shows the request on the windows that went
      // wrong (the deepest such depth). Each candidate whose display is the request is searched exactly in
      // the single-move class from S with at most m - 1 moves.
      uint64_t target = 0;
      {
        const std::string& a = in[4 + req[r]];
        for (int j = 0; j < N; j++) if (a[j] == '1') target |= 1ULL << j;
      }
      auto display = [&](const Order& o) {
        uint64_t covered = 0, black = 0;
        for (int i = 0; i < K; i++) {
          black |= blk[o[i]] & ~covered;
          covered |= opq[o[i]];
        }
        return black;
      };
      uint8_t moved[K];
      std::memset(moved, 0, sizeof(moved));
      for (auto [k, d] : ops) moved[k] = 1;
      int spos[K];
      for (int i = 0; i < K; i++) spos[start[i]] = i;
      // x back among the unmoved papers of `base` (deep: just above its S-successor among them)
      auto put_back = [&](const Order& base, int x, bool deep) {
        int succ = -1, pred = -1;
        for (int i = spos[x] + 1; i < K; i++) if (!moved[start[i]]) { succ = start[i]; break; }
        for (int i = spos[x] - 1; i >= 0; i--) if (!moved[start[i]]) { pred = start[i]; break; }
        uint8_t tmp[K];
        int t = 0;
        for (int i = 0; i < K; i++) if (base[i] != x) tmp[t++] = base[i];
        int at;
        if (deep) {
          at = K - 1;
          if (succ >= 0) for (int i = 0; i < K - 1; i++) if (tmp[i] == succ) { at = i; break; }
        } else {
          at = 0;
          if (pred >= 0) for (int i = 0; i < K - 1; i++) if (tmp[i] == pred) { at = i + 1; break; }
        }
        Order o;
        int u = 0;
        for (int i = 0; i < K; i++) o[i] = (i == at) ? (uint8_t)x : tmp[u++];
        return o;
      };
      std::vector<std::pair<Order, std::string>> cands;
      auto add = [&](const Order& o, std::string tag) {
        if (o == T) return;
        for (auto& c : cands) if (c.first == o) return;
        cands.emplace_back(o, std::move(tag));
      };
      std::vector<int> mv;
      for (int k = 0; k < K; k++) if (moved[k]) mv.push_back(k);
      for (int x : mv)
        for (int deep = 1; deep >= 0; deep--) {
          Order o = put_back(T, x, deep);
          if (display(o) == target) add(o, "a" + std::to_string(x));
        }
      for (size_t i = 0; i < mv.size(); i++)
        for (size_t j = i + 1; j < mv.size(); j++) {
          Order o2 = put_back(put_back(T, mv[i], true), mv[j], true);
          const uint64_t wrong = display(o2) ^ target;
          if (!wrong) { add(o2, "b0"); continue; }
          if (std::popcount(wrong) > 12) continue;
          for (int z = 0; z < K; z++) {
            if (z == mv[i] || z == mv[j]) continue;
            if ((opq[z] & wrong) != wrong || ((blk[z] ^ target) & wrong)) continue;
            uint8_t tmp[K];
            int t = 0;
            for (int q = 0; q < K; q++) if (o2[q] != z) tmp[t++] = o2[q];
            // the deepest depth where z shows on all wrong windows and the request wherever it shows
            uint64_t cov = 0;
            int best = -1;
            for (int d = 0; d < K; d++) {
              const uint64_t vis = opq[z] & ~cov;
              if ((vis & wrong) != wrong) break;
              if (!((blk[z] ^ target) & vis)) best = d;
              if (d < K - 1) cov |= opq[tmp[d]];
            }
            if (best < 0) continue;
            Order o3;
            int u2 = 0;
            for (int q = 0; q < K; q++) o3[q] = (q == best) ? (uint8_t)z : tmp[u2++];
            if (display(o3) == target) add(o3, "b" + std::to_string(z));
          }
        }
      int nc = cands.size(), searched = 0, found = -1, unknown = 0, impossible = 0;
      long long nodes = 0;
      std::vector<std::pair<int, int>> bestsol;
      std::string besttag;
      for (auto& [o, tag] : cands) {
        if (searched >= 300) { unknown++; continue; }
        set_target(S, o);
        int lb = lb_of(S, start);
        int hi = (found >= 0 ? found : m) - 1;
        if (lb > hi) { impossible++; continue; }
        searched++;
        S.single = true;
        S.max_moves = 1;
        S.parking = false;
        S.nodes = 0;
        S.aborted = false;
        std::vector<std::pair<int, int>> sol;
        int f = S.run(start, lb, hi, sol);
        nodes += S.nodes;
        if (f >= 0) {
          found = f;
          bestsol = sol;
          besttag = tag;
        } else if (S.aborted) unknown++;
        else impossible++;
      }
      const char* st = found >= 0 ? "dimp" : nc == 0 ? "dnocand" : unknown ? "dunk" : "dnone";
      std::cout << seed << ' ' << r << ' ' << m << ' ' << LB << ' ' << (found >= 0 ? found : m) << ' ' << st << ' '
                << nc << ' ' << impossible << ' ' << unknown << ' ' << nodes;
      if (found >= 0) {
        std::cout << ' ' << besttag;
        for (auto [k, d] : bestsol) std::cout << ' ' << k << ':' << d;
      }
      std::cout << '\n';
      std::cout.flush();
      continue;
    }
    if (mode == 6) {
      // moves of the SOTA that this order's display does not need: deleting one move (or two) keeps every
      // remaining move legal (the same depths) and the requested display
      uint64_t target = 0;
      {
        const std::string& a = in[4 + req[r]];
        for (int j = 0; j < N; j++) if (a[j] == '1') target |= 1ULL << j;
      }
      auto legal_display = [&](const std::vector<std::pair<int, int>>& seq) {
        Order cur = start;
        for (auto [k, d] : seq) {
          int px = 0;
          while (cur[px] != k) px++;
          uint64_t cov = 0;
          for (int i = 0; i < px; i++) cov |= opq[cur[i]];
          if (!(opq[k] & ~cov) || px == d) return false;
          apply_move(cur, k, d);
        }
        uint64_t covered = 0, black = 0;
        for (int i = 0; i < K; i++) {
          black |= blk[cur[i]] & ~covered;
          covered |= opq[cur[i]];
        }
        return black == target;
      };
      int one = 0, two = 0;
      std::string which;
      for (int i = 0; i < m; i++) {
        auto seq = ops;
        seq.erase(seq.begin() + i);
        if (legal_display(seq)) { one++; which += std::to_string(i) + ","; }
      }
      for (int i = 0; i < m && m <= 24; i++)
        for (int j = i + 1; j < m; j++) {
          auto seq = ops;
          seq.erase(seq.begin() + j);
          seq.erase(seq.begin() + i);
          if (legal_display(seq)) two++;
        }
      std::cout << seed << ' ' << r << ' ' << m << ' ' << LB << " del " << one << ' ' << two << ' ' << (which.empty() ? "-" : which) << '\n';
      continue;
    }
    if (mode == 7) {
      // per move of the SOTA: 1 if it raised the LCS with T by one (a move of the visibility-free lower bound)
      std::ostringstream l7;
      l7 << seed << ' ' << r << ' ' << m << ' ' << LB << " flags ";
      Order cur = start;
      int prev = K - LB;
      for (auto [k, d] : ops) {
        apply_move(cur, k, d);
        int rk2[K];
        for (int i = 0; i < K; i++) rk2[i] = S.trank[cur[i]];
        int now = lis_len(rk2, K);
        l7 << (now - prev);
        prev = now;
      }
      std::cout << l7.str() << '\n';
      continue;
    }
    if (m == LB) {
      line << ' ' << m << " opt0 0";
      std::cout << line.str() << '\n';
      continue;
    }
    if (mode == 4) {
      // a fast rule's yield: only orders where the SOTA moves a paper twice, one IDA* iteration at bound m - 1
      // with the node budget (the single-move class with the assertions)
      if (sota_single) continue;
      S.single = true;
      S.max_moves = 1;
      S.parking = false;
      S.nodes = 0;
      S.aborted = false;
      std::vector<std::pair<int, int>> sol;
      int f = S.run(start, m - 1, m - 1, sol);
      line << ' ' << (f >= 0 ? f : m) << ' ' << (f >= 0 ? "imp" : S.aborted ? "unk" : "none") << ' ' << S.nodes;
      if (f >= 0) for (auto [k, d] : sol) line << ' ' << k << ':' << d;
      std::cout << line.str() << '\n';
      continue;
    }
    if (mode == 5) {
      // check of the pruning: the single-move class without assertions and with the bound K - LIS only
      S.single = true;
      S.plain = true;
      S.max_moves = 1;
      S.parking = false;
      S.nodes = 0;
      S.aborted = false;
      std::vector<std::pair<int, int>> sol;
      int f = S.run(start, LB, m - 1, sol);
      const char* st = f >= 0 ? "imp" : S.aborted ? "unk" : "opt1";
      line << ' ' << (f >= 0 ? f : m) << ' ' << st << ' ' << S.nodes;
      S.plain = false;
      std::cout << line.str() << '\n';
      std::cout.flush();
      continue;
    }
    int found = -1;
    if (mode != 2) {
      // single-move class, bounds LB..m (bound m checks that the SOTA's own length is found when the SOTA
      // moved every paper at most once)
      S.single = true;
      S.max_moves = 1;
      S.parking = false;
      S.nodes = 0;
      S.aborted = false;
      std::vector<std::pair<int, int>> sol;
      int f = S.run(start, LB, m, sol);
      const char* st;
      if (f >= 0 && f < m) st = "imp";
      else if (f == m) st = "opt1";
      else if (S.aborted) st = "unk";
      else st = sota_single ? "BUG" : "opt1m";  // opt1m: no single-move solution <= m (SOTA used a double)
      if (f >= 0 && f < m) found = f;
      line << ' ' << (f >= 0 ? f : m) << ' ' << st << ' ' << S.nodes;
      if (f >= 0 && f < m) for (auto [k, d] : sol) line << ' ' << k << ':' << d;
    }
    // the multi-move class can be shorter than m only if m - LB >= 2 (|M| <= m - 2 papers when one moves twice)
    if (mode >= 1 && found < 0 && m - LB >= 2) {
      S.single = false;
      S.max_moves = 2;
      S.parking = true;
      S.nodes = 0;
      S.aborted = false;
      std::vector<std::pair<int, int>> sol;
      int mf = S.run(start, LB, m - 1, sol);
      if (mf >= 0) {
        line << " | " << mf << " mimp " << S.nodes;
        for (auto [k, d] : sol) line << ' ' << k << ':' << d;
      } else if (S.aborted) {
        line << " | " << m << " munk " << S.nodes;
      } else {
        line << " | " << m << " mopt " << S.nodes;
      }
    }
    std::cout << line.str() << '\n';
    std::cout.flush();
  }
  return 0;
}
