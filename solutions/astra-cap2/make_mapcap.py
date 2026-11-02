from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'research.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:80]
 s=s.replace(a,b)
sub('u64 hm = kActiveWindows & ~low_bits(g);', 'int map_cap = 63;\n    long long cap_map_moves = 0;\n    u64 hm = kActiveWindows & ~low_bits(g);')
sub('if (__builtin_popcountll(d & kActiveWindows) > kCutoff || !cap_compatible(A[u], A[v])) continue;', 'if (__builtin_popcountll(d) > kCutoff) continue;')
sub('144 * __builtin_popcountll(pairs.diff[p] & kActiveWindows)', '144 * __builtin_popcountll(pairs.diff[p])')
sub('auto matching_cost = [&](const int* rel, u64 handle_mask)', 'auto matching_cost = [&](const int* rel, u64 handle_mask, int cap_window)')
sub('+ full144[p];', '+ full144[p] - 144 * int((pairs.diff[p] >> cap_window) & 1);')
sub('return int(x % (64-kCapWidth-g));', 'return int(x % (64-g));')
sub('for (u64 q = hm & kActiveWindows; q;', 'for (u64 q = hm | (1ULL << map_cap); q;')
sub('auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };', '''// A generic/cap exchange leaves every handle unchanged. The cap becomes
    // the old generic coordinate, whereas ordinary generic/handle swaps flip
    // the two bits in the handle mask.
    auto cap_after = [&](const Move& mv) {return mv.swindow && mv.ib==63 ? mv.a : map_cap;};
    auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow && mv.ib!=63 ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };''')
sub('matching_cost(nrel.data(), handles_after(mv))','matching_cost(nrel.data(), handles_after(mv), cap_after(mv))')
sub('matching_cost(pairs.rel.data(), hm)','matching_cost(pairs.rel.data(), hm, map_cap)')
sub('            hm = handles_after(mv);', '            hm = handles_after(mv);\n            cap_map_moves += mv.ib==63;\n            map_cap = cap_after(mv);')
sub('    hm = kActiveWindows;', '    map_cap = order[63];\n    hm = ~(1ULL << map_cap);')
sub('    stats.gobj_after = cur;', '    std::cerr<<"cap_map_moves = "<<cap_map_moves<<"\\nmap_cap_window = "<<permutation[order[63]]<<\'\\n\';\n    stats.gobj_after = cur;')
(r/'mapcap.cpp').write_text(s)
(r/'work/mapcap-README.md').write_text('''# キャップ窓を比較器の割り当てと同時に探索\n\n改良元: `solutions/as6-cap38`。\n\n汎用紙 6 枚、汎用窓 38、1 窓キャップ、25 ハンドルを維持する。比較器の窓割り当て探索で、汎用窓とキャップ窓の交換も候補にする。キャップの元の座標もバーコードに残し、交換後のキャップ窓を除いたハンドル差分・全距離と汎用層費用で 71 対のマッチングを評価する。汎用窓とキャップの交換ではハンドル集合は変わらない。\n\n汎用窓・ハンドル・キャップの物理座標への対応は探索後に一括して置き換える。注文処理は元と同じ。`cap_map_moves` は探索中の汎用窓とキャップの交換受理数、`map_cap_window` は選ばれた物理窓。補助表の期限 1.48 秒、簡易処理への移行 1.68 秒（CLOCK_SCALE 込み）。結果は親ディレクトリの `REPORT.md` に記す。\n''')
