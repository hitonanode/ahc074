// Full-setting staircase sim: 256 targets on 192 papers (64 shared pairs chosen by min Hamming distance).
// Shared paper: holes at D (where the 2 targets differ) + lower handles. D windows that are handles are
// served by column-top toggles (counted); D windows on body windows are NOT simulated (they need a separate
// mechanism; reported as bodyD bits per request). Compares unbiased vs bias-aware column/handle assignment.
#include "common.h"
int NODH = 0; int C = 26, BIAS = 0, CHECK = 0, NP = 64, REPAIR = 0; double WH = 0.45, WB = 0.11; long SAITER = 400000;
u64 lastH = 0;
struct Res { double fixS = 0, nS = 0, confl = 0, mismS = 0, lift = 0, ret = 0, dig = 0, fix = 0, holes = 0, mism = 0, bodyD = 0, err = 0, minority = 0; long n = 0; };
Res run(int seed, mt19937_64 &rng, u64 Hpref = 0);
Res run(int seed, mt19937_64 &rng, u64 Hpref) {
  Inst in = load(seed); vector<u64> A = in.A; const int T = 256;
  // ---- pairing: greedy smallest distance
  vector<array<int,3>> cand; for (int i = 0; i < T; i++) for (int j = i + 1; j < T; j++) cand.push_back({__builtin_popcountll(A[i] ^ A[j]), i, j});
  if (Hpref) for (auto &c : cand) { u64 d = A[c[1]] ^ A[c[2]]; c[0] = (int)(100 * (WH * __builtin_popcountll(d & Hpref) + WB * __builtin_popcountll(d & ~Hpref))); }
  sort(cand.begin(), cand.end()); vector<int> used(T, 0); vector<vector<int>> tg; 
  for (auto &c : cand) { if ((int)tg.size() >= NP) break; if (used[c[1]] || used[c[2]]) continue; used[c[1]] = used[c[2]] = 1; tg.push_back({c[1], c[2]}); }
  for (int t = 0; t < T; t++) if (!used[t]) tg.push_back({t});
  const int K = tg.size(); // 192
  vector<int> paperOf(T); for (int k = 0; k < K; k++) for (int t : tg[k]) paperOf[t] = k;
  vector<u64> Dm(K, 0); for (int k = 0; k < K; k++) if (tg[k].size() == 2) Dm[k] = A[tg[k][0]] ^ A[tg[k][1]];
  vector<int> wt(K); for (int k = 0; k < K; k++) wt[k] = tg[k].size();
  // ---- initial assignment: sizes by weight, random
  vector<int> colOf(K), h(C);
  { vector<int> p(K); iota(p.begin(), p.end(), 0); shuffle(p.begin(), p.end(), rng);
    // sizes growing with depth (roughly the formula shape)
    vector<int> s(C, 2); int rest = K - 2 * C; for (int i = 0; rest > 0; i = (i + 1) % C) { for (int c = i; c < C && rest > 0; c++) { s[c]++; rest--; } }
    int i = 0; for (int c = 0; c < C; c++) for (int j = 0; j < s[c]; j++) colOf[p[i++]] = c; }
  { vector<int> uw(64, 0); for (int c = C - 1; c >= 0; c--) { int best = -1, bs = 1 << 30; for (int w = 0; w < 64; w++) if (!uw[w]) { int b = 0, n = 0, bad = 0; for (int k = 0; k < K; k++) if (colOf[k] == c) { n++; b += A[tg[k][0]] >> w & 1; if (Dm[k] >> w & 1) bad++; } int sc = abs(2 * b - n) + 100 * bad; if (sc < bs) { bs = sc; best = w; } } h[c] = best; uw[best] = 1; } }
  // exposure counts: ex[c'][color] = number of (target) exposures at handle c' ; own[c'][color]
  vector<array<double,2>> ex(C), own(C); vector<double> W(C), S(C); vector<int> ownBad(C);
  auto contrib = [&](int k, int sgn) {
    int c = colOf[k]; W[c] += sgn * wt[k]; S[c] += sgn;
    for (int cp = 0; cp < C; cp++) { int w = h[cp]; bool inD = Dm[k] >> w & 1;
      if (cp == c) { if (inD) ownBad[cp] += sgn; else own[cp][A[tg[k][0]] >> w & 1] += sgn; continue; }
      if (NODH) { if (cp > c && !inD) for (int t : tg[k]) ex[cp][A[t] >> w & 1] += sgn; }
      else if (cp > c || inD) for (int t : tg[k]) ex[cp][A[t] >> w & 1] += sgn; } };
  auto rebuild = [&]() { for (int c = 0; c < C; c++) { ex[c] = {0,0}; own[c] = {0,0}; W[c] = S[c] = 0; ownBad[c] = 0; } for (int k = 0; k < K; k++) contrib(k, +1); };
  auto total = [&]() { double tot = 0; for (int c = 0; c < C; c++) { tot += W[c] * (S[c] - 1) / 2; if (S[c] < 2) tot += 1000;
      double n = ex[c][0] + ex[c][1]; if (n > 0) { double m = min(ex[c][0], ex[c][1]) / n; tot += BIAS ? n * 2 * m * (1 - m) : n * 0.5; }
      if (own[c][0] == 0 || own[c][1] == 0) tot += 50; tot += 1000 * ownBad[c]; } return tot; };
  rebuild(); double cur = total(); uniform_int_distribution<int> U(0, K - 1);
  for (long it = 0; it < SAITER; it++) {
    double Tm = 3 * pow(0.02 / 3, (double)it / SAITER);
    if (rng() % 2) { int k = U(rng); int from = colOf[k], to = rng() % C; if (to == from) continue; contrib(k, -1); colOf[k] = to; contrib(k, +1); double nw = total();
      if (nw <= cur || exp(-(nw - cur) / Tm) > uniform_real_distribution<double>(0, 1)(rng)) cur = nw; else { contrib(k, -1); colOf[k] = from; contrib(k, +1); } }
    else { int a = U(rng), b = U(rng); int ca = colOf[a], cb = colOf[b]; if (ca == cb) continue; contrib(a, -1); contrib(b, -1); colOf[a] = cb; colOf[b] = ca; contrib(a, +1); contrib(b, +1); double nw = total();
      if (nw <= cur || exp(-(nw - cur) / Tm) > uniform_real_distribution<double>(0, 1)(rng)) cur = nw; else { contrib(a, -1); contrib(b, -1); colOf[a] = ca; colOf[b] = cb; contrib(a, +1); contrib(b, +1); } }
    if (it % 4000 == 0) { int cp = rng() % C; int best = h[cp]; double bc = 1e18; for (int w = 0; w < 64; w++) { bool cl = false; for (int c = 0; c < C; c++) if (c != cp && h[c] == w) cl = true; if (cl) continue; h[cp] = w; rebuild(); double cc = total(); if (cc < bc) { bc = cc; best = w; } } h[cp] = best; rebuild(); cur = total(); }
  }
  u64 Hset = 0; for (int c = 0; c < C; c++) Hset |= 1ull << h[c]; lastH = Hset;
  Res r; { double mn = 0, nn = 0; for (int c = 0; c < C; c++) { mn += min(ex[c][0], ex[c][1]); nn += ex[c][0] + ex[c][1]; } r.minority = mn / nn; }
  // majority per handle
  vector<int> maj(C); for (int c = 0; c < C; c++) maj[c] = ex[c][1] >= ex[c][0];
  u64 lowerMask[64]; for (int c = 0; c < C; c++) { lowerMask[c] = 0; for (int q = c + 1; q < C; q++) lowerMask[c] |= 1ull << h[q]; }
  Stack st; st.P.resize(K);
  for (int k = 0; k < K; k++) { st.P[k].op = ~lowerMask[colOf[k]] & ~Dm[k]; st.P[k].bk = A[tg[k][0]] & st.P[k].op; }
  vector<vector<int>> col(C); for (int k = 0; k < K; k++) col[colOf[k]].push_back(k); for (auto &v : col) shuffle(v.begin(), v.end(), rng);
  auto bitP = [&](int k, int c) { return (int)(A[tg[k][0]] >> h[c] & 1); }; // color of paper k at handle c (not in D)
  int top = -1; auto colStart = [&](int c) { int p = (top >= 0); for (int q = 0; q < c; q++) p += col[q].size(); return p; };
  st.ord.clear(); for (auto &v : col) for (int k : v) st.ord.push_back(k);
  int prevT = -1;
  for (int q = 0; q < 1024; q++) {
    int t = prevT < 0 ? rng() % T : rng() % (T - 1); if (prevT >= 0 && t >= prevT) t++; prevT = t;
    int v = paperOf[t]; int c = colOf[v];
    if (top == v) { // same paper (pair mate requested): only the handle bits in D may change
    } else {
      if (top >= 0) { int p = top, cp = colOf[p]; int d = colStart(cp) - 1;
        auto score = [&](int dep) { vector<int> tmp = col[cp]; tmp.insert(tmp.begin() + dep, p); int sc = 0;
          if (tmp.size() >= 2 && bitP(tmp[0], cp) != bitP(tmp[1], cp)) sc += 10; if (tmp.size() >= 3 && bitP(tmp[1], cp) != bitP(tmp[2], cp)) sc += 3;
          if (bitP(tmp[0], cp) == maj[cp]) sc += 1; if (cp > c || (Dm[v] >> h[cp] & 1)) sc += (bitP(tmp[0], cp) == (int)(A[t] >> h[cp] & 1)) ? 20 : 0; return sc; };
        int bd = 0, bs = -1; for (int dep = 0; dep <= min(2, (int)col[cp].size()); dep++) { int sc = score(dep); if (sc > bs) { bs = sc; bd = dep; } }
        st.mv(p, d + bd); top = -1; col[cp].insert(col[cp].begin() + bd, p); r.ret += 1; }
      int j = find(col[c].begin(), col[c].end(), v) - col[c].begin(); long md = st.moves;
      if (j > 0) { vector<int> Dg(col[c].begin(), col[c].begin() + j); vector<int> order, pool = Dg;
        auto take = [&](int colr) { for (size_t i = 0; i < pool.size(); i++) if (bitP(pool[i], c) == colr) { int x = pool[i]; pool.erase(pool.begin() + i); return x; } return -1; };
        int a = take(maj[c]); if (a >= 0) order.push_back(a); int b2 = take(1 - maj[c]); if (b2 >= 0) order.push_back(b2); for (int x : pool) order.push_back(x);
        for (int i = 0; i < j; i++) { int x = col[c][0]; int vi = find(col[c].begin(), col[c].end(), v) - col[c].begin();
          int rk = 0; for (int y : order) { if (y == x) break; if (find(col[c].begin() + vi + 1, col[c].end(), y) != col[c].end()) rk++; }
          st.mv(x, colStart(c) + vi + rk); col[c].erase(col[c].begin()); col[c].insert(col[c].begin() + vi + rk, x); } }
      r.dig += st.moves - md;
      if (colStart(c) != 0) { st.mv(v, 0); r.lift += 1; } col[c].erase(col[c].begin()); top = v;
    }
    long mf = st.moves;
    for (int cp = 0; cp < C; cp++) { if (cp == c) continue; bool exposed = cp > c || (Dm[v] >> h[cp] & 1); if (NODH && (Dm[v] >> h[cp] & 1)) exposed = false; if (!exposed) continue;
      r.holes += 1; int need = A[t] >> h[cp] & 1; if (col[cp].empty()) { r.err++; continue; }
      if (bitP(col[cp][0], cp) == need) continue; r.mism += 1;
      if (col[cp].size() >= 2 && bitP(col[cp][1], cp) == need) { int x = col[cp][0]; st.mv(x, colStart(cp) + 1); col[cp].erase(col[cp].begin()); col[cp].insert(col[cp].begin() + 1, x); continue; }
      int k2 = 0; while (k2 < (int)col[cp].size() && bitP(col[cp][k2], cp) != need) k2++; if (k2 == (int)col[cp].size()) { r.err++; continue; }
      for (int i = 0; i < k2; i++) { int x = col[cp][0]; st.mv(x, colStart(cp) + k2); col[cp].erase(col[cp].begin()); col[cp].insert(col[cp].begin() + k2, x); } }
    r.fix += st.moves - mf; if (tg[v].size() == 2) { r.fixS += st.moves - mf; r.nS += 1; u64 hm2 = 0; for (int cc = 0; cc < C; cc++) hm2 |= 1ull << h[cc]; r.confl += __builtin_popcountll(Dm[v] & hm2); }
    u64 hm = 0; for (int cc = 0; cc < C; cc++) hm |= 1ull << h[cc];
    r.bodyD += __builtin_popcountll(Dm[v] & ~hm);
    if (CHECK) { u64 chk = NODH ? ~Dm[v] : ~(Dm[v] & ~hm); if ((st.display() ^ A[t]) & chk) r.err += 1000; }
    r.n++;
  }
  return r;
}
int main(int argc, char **argv) {
  int seeds = 6; for (int i = 1; i < argc; i++) { string a = argv[i]; auto eq = a.find('='); string k = a.substr(0, eq), v = a.substr(eq + 1);
    if (k == "C") C = stoi(v); else if (k == "bias") BIAS = stoi(v); else if (k == "seeds") seeds = stoi(v); else if (k == "check") CHECK = stoi(v); else if (k == "iter") SAITER = stol(v); else if (k == "repair") REPAIR = stoi(v); else if (k == "nodh") NODH = stoi(v); else if (k == "wh") WH = stod(v); }
  Res tot; mt19937_64 rng(4242); double mino = 0;
  for (int s = 0; s < seeds; s++) { Res r = run(s, rng); if (REPAIR) { u64 H = lastH; r = run(s, rng, H); } tot.lift += r.lift; tot.ret += r.ret; tot.dig += r.dig; tot.fix += r.fix; tot.holes += r.holes; tot.mism += r.mism; tot.bodyD += r.bodyD; tot.err += r.err; tot.n += r.n; tot.fixS += r.fixS; tot.nS += r.nS; tot.confl += r.confl; mino += r.minority; }
  double n = tot.n;
  printf("shared requests %.3f of all; fix per shared req %.3f, per dedicated req %.3f; D∩handles per shared req %.2f\n", tot.nS / n, tot.fixS / tot.nS, (tot.fix - tot.fixS) / (n - tot.nS), tot.confl / tot.nS);
  printf("C=%d bias=%d | minority %.3f err %.0f | lift %.3f ret %.3f dig %.3f fix %.3f (handle holes %.2f mism %.2f fix/hole %.3f) | staircase total %.3f | bodyD bits/req %.2f\n",
    C, BIAS, mino / seeds, tot.err, tot.lift / n, tot.ret / n, tot.dig / n, tot.fix / n, tot.holes / n, tot.mism / n, tot.fix / tot.holes, (tot.lift + tot.ret + tot.dig + tot.fix) / n, tot.bodyD / n);
}
