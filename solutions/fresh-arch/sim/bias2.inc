// BIAS=2: SA over (assignment incl. column sizes, handle windows) with the estimated per-request cost
//   dig  = sum_c s_c (s_c-1)/2 / K
//   fix  = sum_{c'>=1} n_{c'} * 2 m (1-m) / K   (lazy toggle model, n = targets above c', m = minority share)
//   own-column must contain both colors at its handle (penalty), size >= 2
{
  vector<array<int,2>> above(C, {0,0}); // per handle: color counts of targets in columns < c'
  vector<array<int,2>> own(C, {0,0});
  vector<int> sz(C, 0);
  auto rebuild = [&]() { for (int c = 0; c < C; c++) { above[c] = {0,0}; own[c] = {0,0}; sz[c] = 0; }
    for (int t = 0; t < K; t++) { sz[colOf[t]]++; for (int cp = 0; cp < C; cp++) { int b = bitOf(t, cp); if (colOf[t] < cp) above[cp][b]++; if (colOf[t] == cp) own[cp][b]++; } } };
  auto handleCost = [&](int cp) { double n = above[cp][0] + above[cp][1]; if (n == 0) return 0.0; double m = min(above[cp][0], above[cp][1]) / n; double c = HW * n * 2 * m * (1 - m);
    if (own[cp][0] == 0 || own[cp][1] == 0) c += 50; return c; };
  auto total = [&]() { double t = 0; for (int c = 0; c < C; c++) { t += sz[c] * (sz[c] - 1) / 2.0; if (sz[c] < 2) t += 1000; t += handleCost(c); } return t; };
  rebuild(); double cur = total();
  int ITER = 300000; double T0 = 3, T1 = 0.02; uniform_int_distribution<int> U(0, K - 1);
  auto applyMove = [&](int t, int to) { int from = colOf[t]; for (int cp = 0; cp < C; cp++) { int b = bitOf(t, cp); if (from < cp) above[cp][b]--; if (from == cp) own[cp][b]--; if (to < cp) above[cp][b]++; if (to == cp) own[cp][b]++; } sz[from]--; sz[to]++; colOf[t] = to; };
  for (int it = 0; it < ITER; it++) {
    double T = T0 * pow(T1 / T0, (double)it / ITER);
    if (rng() % 2) { // move one target
      int t = U(rng); int from = colOf[t]; int to = rng() % C; if (to == from) continue;
      applyMove(t, to); double nw = total(); double d = nw - cur;
      if (d <= 0 || exp(-d / T) > uniform_real_distribution<double>(0, 1)(rng)) cur = nw; else applyMove(t, from);
    } else { // swap two targets
      int a = U(rng), b = U(rng); int ca = colOf[a], cb = colOf[b]; if (ca == cb) continue;
      applyMove(a, cb); applyMove(b, ca); double nw = total(); double d = nw - cur;
      if (d <= 0 || exp(-d / T) > uniform_real_distribution<double>(0, 1)(rng)) cur = nw; else { applyMove(a, ca); applyMove(b, cb); }
    }
    if (it % 3000 == 0) { // re-pick a handle window
      int cp = rng() % C; int best = h[cp]; double bc = 1e18;
      for (int w = 0; w < 64; w++) { bool clash = false; for (int c = 0; c < C; c++) if (c != cp && h[c] == w) clash = true; if (clash) continue;
        h[cp] = w; rebuild(); double cc = total(); if (cc < bc) { bc = cc; best = w; } }
      h[cp] = best; rebuild(); cur = total();
    }
  }
  if (getenv("PROF")) { rebuild(); for (int c = 0; c < C; c++) { double n = above[c][0] + above[c][1]; fprintf(stderr, "c=%2d size=%2d above=%3.0f minority=%.2f own=(%d,%d) cost/K=%.3f\n", c, sz[c], n, n ? min(above[c][0], above[c][1]) / n : 0.0, own[c][0], own[c][1], handleCost(c) / K); } }
  if (getenv("VERB")) { fprintf(stderr, "est cost/K = %.3f sizes:", cur / K); for (int c = 0; c < C; c++) fprintf(stderr, " %d", sz[c]); fprintf(stderr, "\n"); }
}
