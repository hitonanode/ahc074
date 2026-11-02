// Non-staircase structure: "free-order groups". Each paper is opaque everywhere except holes at the
// handles of all OTHER groups. Stack order is arbitrary; a paper is visible iff it is the topmost of its group.
// No return step is needed (the lifted paper simply stays on top as its group's top).
#include "common.h"
int G = 14; int CHECK = 0;
int main(int argc, char **argv) {
  int seeds = 6; for (int i = 1; i < argc; i++) { string a = argv[i]; auto eq = a.find('='); string k = a.substr(0, eq), v = a.substr(eq + 1); if (k == "G") G = stoi(v); else if (k == "seeds") seeds = stoi(v); else if (k == "check") CHECK = stoi(v); }
  mt19937_64 rng(777); double Tl = 0, Td = 0, Tf = 0, Th = 0, Tm = 0, n = 0; long bad = 0;
  for (int seed = 0; seed < seeds; seed++) {
    Inst in = load(seed); const int K = 192; vector<u64> A(in.A.begin(), in.A.begin() + K);
    vector<int> grp(K); { vector<int> p(K); iota(p.begin(), p.end(), 0); shuffle(p.begin(), p.end(), rng); for (int i = 0; i < K; i++) grp[p[i]] = i % G; }
    vector<int> h(G); { vector<int> used(64, 0); for (int g = 0; g < G; g++) { int best = -1, bs = 1 << 30; for (int w = 0; w < 64; w++) if (!used[w]) { int b = 0, m = 0; for (int t = 0; t < K; t++) if (grp[t] == g) { m++; b += A[t] >> w & 1; } int sc = abs(2 * b - m); if (sc < bs) { bs = sc; best = w; } } h[g] = best; used[best] = 1; } }
    u64 hm = 0; for (int g = 0; g < G; g++) hm |= 1ull << h[g];
    Stack st; st.P.resize(K); for (int t = 0; t < K; t++) { st.P[t].op = ~(hm & ~(1ull << h[grp[t]])); st.P[t].bk = A[t] & st.P[t].op; }
    st.ord.resize(K); iota(st.ord.begin(), st.ord.end(), 0); shuffle(st.ord.begin(), st.ord.end(), rng);
    auto bit = [&](int t, int g) { return (int)(A[t] >> h[g] & 1); };
    auto groupList = [&](int g) { vector<int> v; for (int k : st.ord) if (grp[k] == g) v.push_back(k); return v; };
    int prev = -1;
    for (int q = 0; q < 1024; q++) {
      int v = prev < 0 ? rng() % K : rng() % (K - 1); if (prev >= 0 && v >= prev) v++; prev = v; int g = grp[v];
      long m0 = st.moves;
      // dig: move group-g papers above v to just below v (first one with opposite color directly below v)
      vector<int> L = groupList(g); int j = find(L.begin(), L.end(), v) - L.begin();
      for (int i = 0; i < j; i++) { int x = L[i]; int pv = st.pos(v); st.mv(x, pv); }
      long m1 = st.moves; Td += m1 - m0;
      if (st.ord[0] != v) { st.mv(v, 0); Tl += 1; }
      long m2 = st.moves;
      for (int gp = 0; gp < G; gp++) if (gp != g) {
        Th += 1; vector<int> M = groupList(gp); int need = bit(v, gp);
        if (bit(M[0], gp) == need) continue; Tm += 1;
        int k = 0; while (k < (int)M.size() && bit(M[k], gp) != need) k++;
        if (k == (int)M.size()) { bad++; continue; }
        // move the k wrong papers to just below M[k] (keeps alternation as well as possible)
        for (int i = 0; i < k; i++) { int x = M[i]; int pk = st.pos(M[k]); st.mv(x, pk); }
      }
      Tf += st.moves - m2; n += 1;
      if (CHECK && st.display() != A[v]) bad++;
    }
  }
  printf("G=%d | lift %.3f ret 0 dig %.3f fix %.3f (holes %.2f mism %.2f fix/hole %.3f) total %.3f bad %ld\n", G, Tl / n, Td / n, Tf / n, Th / n, Tm / n, Tf / Th, (Tl + Td + Tf) / n, bad);
}
