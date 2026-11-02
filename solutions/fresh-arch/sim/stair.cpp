// Staircase reference sim (dedicated papers only: 192 targets = 192 papers, requests uniform over them).
// Measures lift / return / dig / handle-fix costs. Options: column sizes, assignment bias (SA), fix policy.
#include "common.h"
double HW = 1.0; double r_minority = 0; int C = 30; double F_HOLE = 0.39; int BIAS = 0; int CHECK = 0; int POLICY = 0;
// column sizes from the marginal formula
vector<int> sizes(int K, int C, double f) {
  vector<int> s(C, 2);
  for (int it = 0; it < K - 2 * C; it++) { int bi = 0; double bm = 1e18; for (int i = 0; i < C; i++) { double m = s[i] + f * (C - 1 - i); if (m < bm) { bm = m; bi = i; } } s[bi]++; }
  return s;
}
struct Res { double cerr = 0, err = 0, lift = 0, ret = 0, dig = 0, fix = 0, holes = 0, mism = 0; long n = 0; };
Res run(int seed, mt19937_64 &rng) {
  Inst in = load(seed);
  const int K = 192;
  vector<u64> A(in.A.begin(), in.A.begin() + K);
  vector<int> s = sizes(K, C, F_HOLE);
  // assignment: target t -> column; handles h[c] = window
  vector<int> colOf(K), h(C);
  for (int c = 0; c < C; c++) h[c] = c; // windows 0..C-1 (random targets: arbitrary)
  { vector<int> perm(K); iota(perm.begin(), perm.end(), 0); shuffle(perm.begin(), perm.end(), rng); int i = 0; for (int c = 0; c < C; c++) for (int j = 0; j < s[c]; j++) colOf[perm[i++]] = c; }
  // majority color target for handle c' among targets above (used by POLICY 1)
  auto bitOf = [&](int t, int c) { return (int)(A[t] >> h[c] & 1); };
  { vector<int> usedw(64, 0);
    for (int c = C - 1; c >= 0; c--) { // pick most balanced unused window among column members
      int best = -1, bs = 1 << 30; for (int w = 0; w < 64; w++) if (!usedw[w]) { int b = 0, n = 0; for (int t = 0; t < K; t++) if (colOf[t] == c) { n++; b += A[t] >> w & 1; } int sc = abs(2 * b - n); if (sc < bs) { bs = sc; best = w; } }
      h[c] = best; usedw[best] = 1; } }
  if (BIAS == 2) {
#include "bias2.inc"
  }
  if (BIAS == 1) {
    // simulated annealing on assignment (swap two targets' columns) and handle windows,
    // objective: sum over targets u and lower handles c'>col(u) of [A_u(h_c') != maj_c'], where maj is majority among targets above c'.
    // Simplified objective: sum over c' of min(#black,#white) among targets with col < c'.
    vector<int> used(64, 0);
    auto cost = [&]() { long tot = 0; for (int cp = 1; cp < C; cp++) { int b = 0, n = 0; for (int t = 0; t < K; t++) if (colOf[t] < cp) { n++; b += bitOf(t, cp); } tot += min(b, n - b); } return tot; };
    // incremental: maintain counts cnt[c'][col][bit]
    vector<vector<array<int,2>>> cnt(C, vector<array<int,2>>(C, {0,0}));
    auto rebuild = [&]() { for (auto &x : cnt) for (auto &y : x) y = {0,0}; for (int t = 0; t < K; t++) for (int cp = 0; cp < C; cp++) cnt[cp][colOf[t]][bitOf(t, cp)]++; };
    auto colcost = [&](int cp) { int b = 0, w = 0; for (int c = 0; c < cp; c++) { b += cnt[cp][c][1]; w += cnt[cp][c][0]; }
      int own1 = cnt[cp][cp][1], own0 = cnt[cp][cp][0]; int pen = (own1 == 0 || own0 == 0) ? 1000 : 0; return min(b, w) + pen; };
    // choose handle windows greedily too: try all 64 windows for each handle at the end
    rebuild();
    long cur = 0; for (int cp = 0; cp < C; cp++) cur += colcost(cp);
    double T0 = 2.0, T1 = 0.05; int ITER = 200000;
    uniform_int_distribution<int> U(0, K - 1);
    for (int it = 0; it < ITER; it++) {
      double T = T0 * pow(T1 / T0, (double)it / ITER);
      int a = U(rng), b = U(rng); if (colOf[a] == colOf[b]) continue;
      int ca = colOf[a], cb = colOf[b]; int lo = min(ca, cb), hi = max(ca, cb);
      long before = 0; for (int cp = lo; cp < C; cp++) before += colcost(cp);
      for (int cp = 0; cp < C; cp++) { cnt[cp][ca][bitOf(a, cp)]--; cnt[cp][cb][bitOf(b, cp)]--; cnt[cp][cb][bitOf(a, cp)]++; cnt[cp][ca][bitOf(b, cp)]++; }
      swap(colOf[a], colOf[b]);
      long after = 0; for (int cp = lo; cp < C; cp++) after += colcost(cp);
      long d = after - before;
      if (d <= 0 || exp(-d / T) > uniform_real_distribution<double>(0, 1)(rng)) cur += d;
      else { swap(colOf[a], colOf[b]); for (int cp = 0; cp < C; cp++) { cnt[cp][cb][bitOf(a, cp)]--; cnt[cp][ca][bitOf(b, cp)]--; cnt[cp][ca][bitOf(a, cp)]++; cnt[cp][cb][bitOf(b, cp)]++; } }
      // occasionally re-pick handle window of a random column
      if (it % 2000 == 0) {
        int cp = 1 + rng() % (C - 1); int best = h[cp]; long bestc = LONG_MAX;
        for (int w = 0; w < 64; w++) { bool clash = false; for (int c = 0; c < C; c++) if (c != cp && h[c] == w) clash = true; if (clash) continue;
          int old = h[cp]; h[cp] = w; rebuild(); long cc = 0; for (int q = 0; q < C; q++) cc += colcost(q); if (cc < bestc) { bestc = cc; best = w; } h[cp] = old; }
        h[cp] = best; rebuild(); cur = 0; for (int q = 0; q < C; q++) cur += colcost(q);
      }
    }
  }
  { long mn = 0, tot = 0; for (int cp = 1; cp < C; cp++) { int b = 0, n = 0; for (int t = 0; t < K; t++) if (colOf[t] < cp) { n++; b += bitOf(t, cp); } mn += min(b, n - b); tot += n; } r_minority += (double)mn / tot; }
  u64 lowerMask[64]; // handles strictly below column c
  for (int c = 0; c < C; c++) { lowerMask[c] = 0; for (int q = c + 1; q < C; q++) lowerMask[c] |= 1ull << h[q]; }
  Stack st; st.P.resize(K);
  for (int t = 0; t < K; t++) { st.P[t].op = ~0ull & ~lowerMask[colOf[t]]; st.P[t].bk = A[t] & st.P[t].op; }
  vector<vector<int>> col(C);
  for (int t = 0; t < K; t++) col[colOf[t]].push_back(t);
  for (auto &v : col) shuffle(v.begin(), v.end(), rng);
  // majority bit per handle among targets above it
  vector<int> maj(C, 0); for (int cp = 1; cp < C; cp++) { int b = 0, n = 0; for (int t = 0; t < K; t++) if (colOf[t] < cp) { n++; b += bitOf(t, cp); } maj[cp] = (2 * b >= n); }
  int top = -1; // lifted paper (index 0 of stack) or -1
  auto rebuildOrder = [&]() { st.ord.clear(); if (top >= 0) st.ord.push_back(top); for (auto &v : col) for (int t : v) st.ord.push_back(t); };
  auto colStart = [&](int c) { int p = (top >= 0); for (int q = 0; q < c; q++) p += col[q].size(); return p; };
  rebuildOrder();
  Res r; int prev = -1;
  // request stream: uniform over 192 targets, no immediate repeat (use own rng to mimic)
  uniform_int_distribution<int> UK(0, K - 2);
  int R = 1024;
  for (int q = 0; q < R; q++) {
    int v = (prev < 0) ? (int)(rng() % K) : UK(rng); if (prev >= 0 && v >= prev) v++;
    prev = v;
    long m0 = st.moves;
    // 1. return previous lifted paper (if any) to its column top (POLICY: choose depth 0 or 1 by majority)
    if (top >= 0) {
      int p = top; int c = colOf[p];
      int d = colStart(c) - 1; // index after removing p from top
      int depth = 0;
      if (POLICY == 1 && !col[c].empty() && c > 0) { // put the majority-colored one on top
        int want = maj[c]; if (bitOf(p, c) != want && bitOf(col[c][0], c) == want) depth = 1; }
      if (POLICY >= 2 && c > 0) {
        auto score = [&](int dep) { vector<int> tmp = col[c]; tmp.insert(tmp.begin() + dep, p); int sc = 0;
          if (tmp.size() >= 2 && bitOf(tmp[0], c) != bitOf(tmp[1], c)) sc += 10;
          if (tmp.size() >= 3 && bitOf(tmp[1], c) != bitOf(tmp[2], c)) sc += 3;
          if (POLICY >= 3 && bitOf(tmp[0], c) == maj[c]) sc += 1;
          if (POLICY >= 4 && c > colOf[v]) { sc += (bitOf(tmp[0], c) == bitOf(v, c)) ? 20 : 0; }
          return sc; };
        int bd = 0, bs = -1; for (int dep = 0; dep <= min(2, (int)col[c].size()); dep++) { int sc = score(dep); if (sc > bs) { bs = sc; bd = dep; } } depth = bd; }
      st.mv(p, d + depth); top = -1; col[c].insert(col[c].begin() + depth, p);
      r.ret += 1;
    }
    // 2. dig
    int c = colOf[v]; int j = find(col[c].begin(), col[c].end(), v) - col[c].begin();
    long md = st.moves;
    if (POLICY >= 4 && j > 0) {
      vector<int> Dg(col[c].begin(), col[c].begin() + j); vector<int> Rest(col[c].begin() + j + 1, col[c].end());
      // desired final order of dug papers: first majority-colored, then minority-colored, then others
      int want0 = (c > 0) ? maj[c] : 0; vector<int> order;
      vector<int> pool = Dg; auto takeColor = [&](int colr) { for (size_t i = 0; i < pool.size(); i++) if (bitOf(pool[i], c) == colr) { int x = pool[i]; pool.erase(pool.begin() + i); return x; } return -1; };
      int a = takeColor(want0); if (a >= 0) order.push_back(a); int b2 = takeColor(1 - want0); if (b2 >= 0) order.push_back(b2); for (int x : pool) order.push_back(x);
      if (c == 0) order = Dg;
      // move dug papers one by one (top first) to the slot below v realizing 'order'
      for (int i = 0; i < j; i++) {
        int x = col[c][0]; int vi = find(col[c].begin(), col[c].end(), v) - col[c].begin();
        int rk = 0; for (int y : order) { if (y == x) break; if (find(col[c].begin() + vi + 1, col[c].end(), y) != col[c].end()) rk++; }
        int target = vi + 1 + rk; // index in column after removal of x: vi-1 is v's new index, so slot = vi + rk
        st.mv(x, colStart(c) + vi + rk); col[c].erase(col[c].begin()); col[c].insert(col[c].begin() + vi + rk, x); (void)target;
      }
      j = 0;
    }
    for (int i = 0; i < j; i++) { // move the current top of column c to just below v
      int x = col[c][0]; int vp = 1; // v is at index (j - i) within col; after moving x below v
      int base = colStart(c); int vidx = base + (j - i); st.mv(x, vidx);
      col[c].erase(col[c].begin()); int vi = find(col[c].begin(), col[c].end(), v) - col[c].begin(); col[c].insert(col[c].begin() + vi + 1, x); (void)vp;
    }
    r.dig += st.moves - md;
    // 3. lift
    { int base = colStart(c); assert(col[c][0] == v); if (base != 0) { st.mv(v, 0); r.lift += 1; } col[c].erase(col[c].begin()); top = v; }
    // 4. fix lower handles
    long mf = st.moves;
    for (int cp = c + 1; cp < C; cp++) {
      r.holes += 1; int need = bitOf(v, cp);
      if (col[cp].empty()) { abort(); }
      if (bitOf(col[cp][0], cp) == need) continue;
      r.mism += 1;
      if (POLICY >= 2 && col[cp].size() >= 2 && bitOf(col[cp][1], cp) == need) {
        int x = col[cp][0]; st.mv(x, colStart(cp) + 1); col[cp].erase(col[cp].begin()); col[cp].insert(col[cp].begin() + 1, x); continue; }
      int k = 0; while (k < (int)col[cp].size() && bitOf(col[cp][k], cp) != need) k++;
      if (k == (int)col[cp].size()) { r.err += 1; continue; }
      // move the k wrong-colored papers above to the bottom of the column
      for (int i = 0; i < k; i++) { int x = col[cp][0]; int endIdx = colStart(cp) + col[cp].size() - 1; st.mv(x, endIdx); col[cp].erase(col[cp].begin()); col[cp].push_back(x); }
    }
    r.fix += st.moves - mf;
    if (CHECK) { rebuildOrder(); /* consistency */ if (st.display() != A[v]) r.cerr += 1; }
    r.n++;
  }

  return r;
}
int main(int argc, char **argv) {
  int seeds = 10;
  for (int i = 1; i < argc; i++) { string a = argv[i]; auto eq = a.find('='); string k = a.substr(0, eq), v = a.substr(eq + 1);
    if (k == "C") C = stoi(v); else if (k == "f") F_HOLE = stod(v); else if (k == "bias") BIAS = stoi(v); else if (k == "check") CHECK = stoi(v); else if (k == "seeds") seeds = stoi(v); else if (k == "policy") POLICY = stoi(v); else if (k == "hw") HW = stod(v); }
  Res tot; mt19937_64 rng(12345);
  for (int s = 0; s < seeds; s++) { Res r = run(s, rng); tot.lift += r.lift; tot.ret += r.ret; tot.dig += r.dig; tot.fix += r.fix; tot.holes += r.holes; tot.mism += r.mism; tot.n += r.n; tot.err += r.err; tot.cerr += r.cerr; }
  double n = tot.n;
  printf("minority %.3f err %.4f cerr %.4f | C=%d f=%.2f bias=%d policy=%d | lift %.3f ret %.3f dig %.3f fix %.3f (holes %.2f, mism %.2f, fix/hole %.3f) total %.3f\n", r_minority / seeds, tot.err / n, tot.cerr / n, C, F_HOLE, BIAS, POLICY,
    tot.lift / n, tot.ret / n, tot.dig / n, tot.fix / n, tot.holes / n, tot.mism / n, tot.fix / tot.holes, (tot.lift + tot.ret + tot.dig + tot.fix) / n);
}
