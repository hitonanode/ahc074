// Common simulator core: papers, stack, visibility, moves (same rules as the tester).
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>
#include <random>
#include <fstream>
#include <cassert>
#include <array>
#include <climits>
#include <cmath>
using u64 = uint64_t;
using namespace std;
struct Paper { u64 op = 0, bk = 0; };
struct Inst { vector<u64> A; vector<int> req; };
inline Inst load(int seed) {
  char buf[256]; snprintf(buf, sizeof buf, "/home/sato/ahc074/tools/in/%04d.txt", seed);
  ifstream f(buf); int N, K, P, R; f >> N >> K >> P >> R; Inst in; in.A.resize(P);
  for (int i = 0; i < P; i++) { string s; f >> s; u64 m = 0; for (int j = 0; j < N; j++) if (s[j] == '1') m |= 1ull << j; in.A[i] = m; }
  in.req.resize(R); for (auto &x : in.req) f >> x; return in;
}
struct Stack {
  vector<Paper> P; vector<int> ord; long moves = 0;
  int pos(int k) const { for (int i = 0; i < (int)ord.size(); i++) if (ord[i] == k) return i; return -1; }
  bool visible(int k) const {
    u64 cov = 0; for (int i = 0; i < (int)ord.size(); i++) { if (ord[i] == k) return (P[k].op & ~cov) != 0; cov |= P[ord[i]].op; } return false;
  }
  // move paper k to final index d (0 = top). Aborts on illegal move.
  void mv(int k, int d) {
    if (!visible(k)) { fprintf(stderr, "illegal move: paper %d not visible\n", k); abort(); }
    int p = pos(k);
    if (p < d) rotate(ord.begin() + p, ord.begin() + p + 1, ord.begin() + d + 1);
    else rotate(ord.begin() + d, ord.begin() + p, ord.begin() + p + 1);
    moves++;
  }
  u64 display() const { u64 cov = 0, b = 0; for (int k : ord) { b |= P[k].bk & ~cov; cov |= P[k].op; } return b; }
  // color shown at window w (0/1) and which paper shows it (-1 none)
  int shower(int w) const { for (int k : ord) if (P[k].op >> w & 1) return k; return -1; }
};
