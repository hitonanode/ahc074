"""同じ比較器の二つの窓を一緒に交換する近傍。"""
def doublewindow(s, divisor):
    s=s.replace('        u64 olda, oldb, oldpol;\n    };', '        u64 olda, oldb, oldpol;\n        int ia2 = -1, ib2 = -1, a2 = -1, b2 = -1;\n    };',1)
    s=s.replace('    auto propose = [&](Move& mv) {', '''    long long double_proposals = 0, double_evals = 0, double_accepts = 0;
    auto propose = [&](Move& mv) {''',1)
    s=s.replace('        int transfer = -1;', '        int transfer = -1, ia2 = -1, ib2 = -1, a2 = -1, b2 = -1;',1)
    needle='''            pol = (pol & ~(1ULL << b)) | ((((oldpol >> a) ^ rng.next()) & 1) << b);'''
    new=needle+f'''
            if (kind == 9 && counts[ea] >= 2 && (rng.next() % {divisor}) == 0) {{
                u64 choices = olda & ~(1ULL << a);
                int skip = rng.below(__builtin_popcountll(choices));
                while (skip--) choices &= choices-1;
                a2 = __builtin_ctzll(choices);
                ia2 = int(std::find(order.begin(), order.begin()+g, a2) - order.begin());
                ib2 = g + rng.mod(63-g);
                if (ib2 >= ib) ++ib2;
                b2 = order[ib2];
                mask[ea] ^= (1ULL << a2) | (1ULL << b2);
                pol = (pol & ~(1ULL << b2)) | ((rng.next() & 1) << b2);
                ++double_proposals;
            }}'''
    assert needle in s;s=s.replace(needle,new,1)
    needle='        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};'
    s=s.replace(needle,needle+'\n        mv.ia2 = ia2; mv.ib2 = ib2; mv.a2 = a2; mv.b2 = b2;',1)
    needle='        if (memo_epoch[move_key] == 2 * epoch) {'
    assert needle in s
    s=s.replace(needle,'''        // Composite moves use a scratch objective slot, never a neighbor-cache hit.
        if (ia2 >= 0) move_key = kMemoSize - 1;
        if (ia2 < 0 && memo_epoch[move_key] == 2 * epoch) {''',1)
    s=s.replace('memo_hit = memo_epoch[move_key] == 2 * epoch + 1;', 'memo_hit = ia2 < 0 && memo_epoch[move_key] == 2 * epoch + 1;',1)
    s=s.replace('if (!checked && selected.size() == unsigned(need) && swindow)', 'if (!checked && selected.size() == unsigned(need) && swindow && ia2 < 0)',1)
    s=s.replace('        exact_evals++;', '        exact_evals++;\n        double_evals += ia2 >= 0;',1)
    needle='    auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };'
    assert needle in s
    s=s.replace(needle,'''    auto handles_after = [&](const Move& mv) {
        u64 next = hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0);
        if (mv.ia2 >= 0) next ^= (1ULL << mv.a2) | (1ULL << mv.b2);
        return next;
    };''',1)
    s=s.replace('''            std::swap(order[mv.ia], order[mv.ib]);
            hm = handles_after(mv);''','''            std::swap(order[mv.ia], order[mv.ib]);
            if (mv.ia2 >= 0) {
                which[mv.a2] = -1; which[mv.b2] = mv.ea;
                std::swap(order[mv.ia2], order[mv.ib2]);
                ++double_accepts;
            }
            hm = handles_after(mv);''',1)
    s=s.replace('        memo_hit = true; ++memo_hits; ++direct_steps;', '        memo_value[move_key] = escape_floor;  // Scratch slots may have been overwritten.\n        memo_hit = true; ++memo_hits; ++direct_steps;',1)
    s=s.replace('if (mv.swindow) reverse_key =', 'if (mv.ia2 >= 0) reverse_key = kMemoSize - 1;\n            else if (mv.swindow) reverse_key =')
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "double_proposals = " << double_proposals << "\\ndouble_evals = " << double_evals
              << "\\ndouble_accepts = " << double_accepts << '\\n';
    stats.gobj_after = cur;''')
    return s

def guided(s, samples):
    # s already contains doublewindow(). Share the exact current-matching bitsets.
    start=s.index('        if (screen_dirty) {',s.index('    auto swap_losses ='))
    end=s.index('        const int a = mv.a, e = mv.ea;',start)
    body=s[start:end]
    s=s[:start]+'        ensure_screen();\n'+s[end:]
    at=s.index('    auto swap_losses =')
    s=s[:at]+'''    auto ensure_screen = [&] {
'''+body+'''    };
    std::array<Colors, 15> double_forbidden{};
    std::array<unsigned, 15> double_epoch{};
'''+s[at:]
    start=s.index('        if (swindow) {  // generic window a <-> handle window b')
    end=s.index('        } else if (kind < 3)',start)
    new=f'''        if (swindow) {{  // generic window(s) a <-> handle window(s) b
            int new_color = ((oldpol >> a) ^ rng.next()) & 1, new_color2 = 0;
            if (kind == 9 && counts[ea] == 2 && selected.size() == unsigned(need)) {{
                ++double_proposals;
                ensure_screen();
                if (double_epoch[ea] != epoch) {{
                    double_forbidden[ea] = {{}};
                    const auto [x,y] = ep[ea];
                    const uint32_t keep = ~(fwd[ea] | rev[ea]);
                    for (int i = 0; i < need; ++i) {{
                        const u64 c = closure(pairs.dir[selected[i]] & keep), bit = 1ULL << (i & 63);
                        if (c >> (8*y+x) & 1) double_forbidden[ea][0][i >> 6] |= bit;
                        if (c >> (8*x+y) & 1) double_forbidden[ea][1][i >> 6] |= bit;
                    }}
                    double_epoch[ea] = epoch;
                }}
                int best_rank = 1 << 30;
                for (int trial = 0; trial < {samples}; ++trial) {{
                    const int j = g + rng.mod(64-g);
                    int k = g + rng.mod(63-g); if (k >= j) ++k;
                    const int u = order[j], v = order[k];
                    const unsigned colors = rng.next() & 3;
                    const int cu = colors & 1, cv = colors >> 1;
                    int lost = 0, differences = 0;
                    for (int w = 0; w < 2; ++w) {{
                        const u64 f = match_colors[u][cu][w] | match_colors[v][cv][w];
                        const u64 r = match_colors[u][cu ^ 1][w] | match_colors[v][cv ^ 1][w];
                        lost += __builtin_popcountll((f & r) | (f & double_forbidden[ea][0][w])
                                                            | (r & double_forbidden[ea][1][w]));
                        differences += __builtin_popcountll(match_colors[u][0][w] | match_colors[u][1][w]);
                        differences += __builtin_popcountll(match_colors[v][0][w] | match_colors[v][1][w]);
                    }}
                    if (lost >= kRejectLoss) continue;
                    const int rank = 16 * lost - differences;
                    if (rank < best_rank) {{
                        best_rank = rank; ib = j; ib2 = k; b = u; b2 = v;
                        new_color = cu; new_color2 = cv;
                    }}
                }}
                if (ib2 < 0) {{ ++screen_rejected; return false; }}
                a2 = __builtin_ctzll(olda & ~(1ULL << a));
                ia2 = int(std::find(order.begin(), order.begin()+g, a2) - order.begin());
                mask[ea] ^= (1ULL << a2) | (1ULL << b2);
                pol = (pol & ~(1ULL << b2)) | (u64(new_color2) << b2);
            }}
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | (u64(new_color) << b);
'''
    s=s[:start]+new+s[end:]
    s=s.replace('} else if (!checked && selected.size() == unsigned(need) && transfer < 0)', '} else if (!checked && selected.size() == unsigned(need) && transfer < 0 && ia2 < 0)')
    return s
