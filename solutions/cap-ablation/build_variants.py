from pathlib import Path
s=Path('solutions/assign-search/main.cpp').read_text()
def replace(old,new,n=None):
 global s
 count=s.count(old)
 assert count and (n is None or count==n),(old,count,n)
 s=s.replace(old,new)
replace('// The 63 active windows initially comprise 38 comparisons and 25 column handles;\n// window 63 belongs to a fixed black cap. A partial target is feasible iff its comparisons form a DAG.', '// All 64 windows are assigned to comparisons or column handles; there is no cap.\n// A partial target is feasible iff its comparisons form a DAG.',1)
replace('constexpr int kCapWindow = 63, kCapPaper = 6;\nconstexpr u64 kCapBit = 1ULL << kCapWindow;\nconstexpr u64 kActiveWindows = kCapBit - 1;', 'constexpr int kCapWindow = -1;  // metric: this ablation has no cap\nconstexpr u64 kActiveWindows = ~0ULL;',1)
replace('need = 71 vertex-disjoint pairs','need = 70 vertex-disjoint pairs',1)
replace('mean over the 71 pairs','mean over the 70 pairs',1)
replace('256 - (191 - m)', '256 - (K - m)',1)
replace('// cap is neither generic nor a handle', '// every non-generic window is a handle',1)
replace('remainders by g and 63 - g','remainders by g and 64 - g',1)
replace('case 38: return int(x % 38);','case 38: return int(x % 38);\n            case 39: return int(x % 39);',1)
replace('case 38: return int(x % 25);','case 38: return int(x % 26);\n            case 39: return int(x % 25);',1)
replace('case 32: return int(x % 31);','case 32: return int(x % 32);',1)
replace('case 28: return int(x % 35);','case 28: return int(x % 36);',1)
replace('default: return int(x % (63 - g));','default: return int(x % (64 - g));',1)
replace('G(g), H(63 - g), U(191 - m)', 'G(g), H(N - g), U(K - m)',1)
replace('int M = 6, H = 25;','int M = 6, H = 26;',1)
replace('for (int k = M + 1; k < K; k++)','for (int k = M; k < K; k++)',3)
replace('''    // The cap stays above the generic layer. A dedicated sheet printed white
    // at the cap window requests black by stopping immediately below the cap;
    // otherwise the usual top insertion shows its own (correct) printed color.
    void move_to_target_top(int d) {
        OP_LABEL(kOpLift);
        const bool needs_cap = (A[adaptive_request] & kCapBit) && !(paper[d].black & kCapBit);
        if (!needs_cap)
            move(d, 0);
        else {
            const int cp = index_of(kCapPaper), dp = index_of(d);
            move(d, cp + int(dp > cp));
        }
    }
    // Digs the column of d until d is its top, and performs its cap-aware lift.''','''    // A lifted product goes above the generic layer.
    void move_to_target_top(int d) {
        OP_LABEL(kOpLift);
        move(d, 0);
    }
    // Digs the column of d until d is its top, then lifts it.''',1)
replace('i == 0 || (i == 1 && order[0] == kCapPaper)', 'i == 0',1)
replace('position == 0 || (position == 1 && order[0] == kCapPaper)', 'position == 0',1)
replace('for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth + 1);','for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth);',2)
replace('move(pk.paper, 1 + pk.depth + (after_target ? 1 : 0));','move(pk.paper, pk.depth + (after_target ? 1 : 0));',1)
replace('move(x, 1 + depth + placed + (lifted ? 1 : 0));','move(x, depth + placed + (lifted ? 1 : 0));',1)
replace('        if (order[0] != kCapPaper) return;\n','',1)
replace('if (order[i + 1] >= M) return;','if (order[i] >= M) return;',1)
replace('std::vector<int> current(order.begin() + 1, order.begin() + 1 + M);','std::vector<int> current(order.begin(), order.begin() + M);',1)
replace('const int out = k == kCapPaper ? 0 : k < kCapPaper ? k + 1 : k;','const int out = k;',1)
replace('''                // The same final cap invariant as below, checked before the more costly legality
                // replay. The cap is never moved, and its predecessor chain is already available.
                for (int k = next[root]; k != root && k != kCapPaper; k = next[k])
                    if (k < M) return false;
''','',1)
replace('''            // Preserve the invariant needed by contiguous generic planning
            // and the +1 offset of helper insertion. The cap itself is never
            // an edit, so this also prevents a generic edit crossing the cap.
            for (int j = 0, cap = find_paper(ord, kCapPaper); j < cap; j++)
                if (ord[j] < M) return false;
''','',1)
replace('k != kCapPaper && possible[k]','possible[k]',1)
replace('(one || two) && k != kCapPaper','one || two',1)
replace('static constexpr int kFirst = kCapPaper + 1;','static constexpr int kFirst = 6;',1)
replace('the targets on the internal windows (with the cap)','the targets on the internal windows',1)
replace('column of each paper (-1: a generic sheet or the cap)','column of each paper (-1: a generic sheet)',1)
replace('''    // Model the one initial legal cap move now; emit it before the first plan.
    std::rotate(solver.order.begin(), solver.order.begin() + kCapPaper, solver.order.begin() + kCapPaper + 1);
''','',1)
replace('int M = 6, G = 38;', 'int M = 6, G = std::getenv("CAP_G") ? env_int("CAP_G") : 38;\n    G = std::clamp(G, 15, 63);',1)
replace('''    // Restore the cap bit only for the physical papers and online targets.
    // Assignment never moves index 63, and all design calculations used 63 bits.
    for (int u = 0; u < P; ++u) A[u] |= originalA[u] & kCapBit;
''','',1)
replace('''    // Papers: six generic sheets, the cap, then the columns 0, 1, ... (colors alternate,''','''    // Papers: six generic sheets, then the columns 0, 1, ... (colors alternate,''',1)
replace('    papers[kCapPaper] = {kCapBit, kCapBit};\n','',1)
replace('u64 opaque = low_bits(G) | kCapBit;','u64 opaque = low_bits(G);',1)
replace('int next = M + 1;','int next = M;',1)
replace('            mask |= kCapBit;\n','',1)
replace('            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;\n','',1)
replace('state.G + state.H > 63','state.G + state.H != N',1)
replace('//   role     cap (the black cap on window 63), generic (a sheet of the comparator), pair / single (a','//   role     generic (a sheet of the comparator), pair / single (a',1)
replace('''        if (k == kCapPaper)
            role[k] = "cap";
        else if (k < state.M)''','''        if (k < state.M)''',1)
replace('''    // Output the cap as paper 0, with generic sheets shifted to 1..6, so it starts on top.
    // Internal indices remain unchanged; out_index translates papers and moves.
    auto out_index = [](int k) { return k == kCapPaper ? 0 : k < kCapPaper ? k + 1 : k; };''','''    // Internal and output paper numbers agree: generic sheets first, then product columns.
    auto out_index = [](int k) { return k; };''',1)
assert 'kCapPaper' not in s and 'kCapBit' not in s
Path('solutions/cap-ablation/main.cpp').write_text(s)
