#!/usr/bin/env python3
"""基準を保ち、assign_windows 内だけを変更する実験ソースを生成。"""
from pathlib import Path
import argparse,json
from sparse import sparse
from history import history
from kernel import kernel
from cross import cross, cached_cross, rank_cross
p=argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--loss',type=int,default=3)
p.add_argument('--climb-loss',type=int,default=0)
p.add_argument('--unstick',action='store_true')
p.add_argument('--cross-rank',type=int,default=0)
p.add_argument('--cross-fast',action='store_true')
p.add_argument('--cross',type=int,default=0)
p.add_argument('--kernel',default='')
p.add_argument('--lean',action='store_true')
p.add_argument('--early',action='store_true')
p.add_argument('--flip-screen',action='store_true')
p.add_argument('--history',type=float,default=0)
p.add_argument('--groupflip',type=int,default=0)
p.add_argument('--sparse',type=int,default=0)
p.add_argument('--cached',action='store_true')
p.add_argument('--colored',type=int,default=0,help='汎用窓交換の1/nで両窓の色も無作為に選ぶ')
p.add_argument('--native',action='store_true')
p.add_argument('--unique',action='store_true')
p.add_argument('--exact-stall',type=int,default=0)
p.add_argument('--const38',action='store_true')
a=p.parse_args();h=Path(__file__).resolve().parent
s=(h.parent/'as5-g38/main.cpp').read_text();start=s.index('WindowStats assign_windows(');end=s.index('// kBitLanes',start);t=s[start:end]
if a.loss != 3 or a.climb_loss:
    assert a.loss in (1,2,3,4) and a.climb_loss in (0,1,2,3,4)
    t=t.replace('constexpr int kRejectLoss = 3, kMemoSize = 1 << 14;',f'int kRejectLoss = {a.loss};\n    constexpr int kMemoSize = 1 << 14;')
    t=t.replace('(eight | four | (twos & ones))','(eight | four | (kRejectLoss == 1 ? (ones|twos) : kRejectLoss == 2 ? twos : kRejectLoss == 3 ? (twos&ones) : 0U))')
    if a.climb_loss:
        t=t.replace('    stats.gobj_before = cur;',f'    kRejectLoss = {a.climb_loss};\n    stats.gobj_before = cur;',1)
if a.const38:
    t=t.replace('g == 36 ? x % 36 : x % g','g == 38 ? x % 38 : x % g').replace('g == 36 ? x % 28 : x % (64-g)','g == 38 ? x % 26 : x % (64-g)')
    t=t.replace('normal 36/28 split','normal 38/26 split')
if a.cached:
    t=t.replace('    std::array<unsigned char, 64> forbidden_ready{};', '''    std::array<unsigned char, 64> forbidden_ready{};
    // Surviving matching slots keep their bit positions. If this comparator group's
    // windows/colors are unchanged, only slots with changed relations or targets need repair.
    std::array<Bits, 64> forbidden_dirty{};
    std::array<u64, 64> forbidden_mask{}, forbidden_pol{};
    std::array<int, 64> forbidden_edge{};
    long long forbidden_partial = 0, forbidden_repaired = 0;''')
    t=t.replace('            ++screen_refreshes;', '            ++screen_refreshes;\n            Bits changed_slots{};',1)
    t=t.replace('                const u64 bit = 1ULL << (i & 63);','                const u64 bit = 1ULL << (i & 63);\n                changed_slots[i >> 6] |= bit;',1)
    t=t.replace('                    screen_dirs[i] = r;','                    changed_slots[i >> 6] |= 1ULL << (i & 63);\n                    screen_dirs[i] = r;',1)
    t=t.replace('            screen_dirty = false;', '''            for (int a = 0; a < 64; ++a)
                for (int w = 0; w < 2; ++w) forbidden_dirty[a][w] |= changed_slots[w];
            screen_dirty = false;''',1)
    needle='''            const auto [x, y] = ep[e];
            if (!group_ready[e]) {'''
    new='''            const auto [x, y] = ep[e];
            if (forbidden_edge[a] == e && forbidden_mask[a] == mv.olda && forbidden_pol[a] == (mv.oldpol & mv.olda)) {
                ++forbidden_partial;
                const u64 rest = mv.olda & ~(1ULL << a);
                const uint32_t keep = ~uint32_t(fwd[e] | rev[e]);
                for (int w = 0; w < 2; ++w)
                    for (u64 bits = forbidden_dirty[a][w]; bits; bits &= bits-1) {
                        const int bit = __builtin_ctzll(bits), i = 64*w+bit;
                        if (i >= int(selected.size())) continue;
                        const int p = selected[i];
                        const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ mv.oldpol;
                        uint32_t r = pairs.dir[p] & keep;
                        if (q & ~z) r |= fwd[e];
                        if (q & z) r |= rev[e];
                        const u64 c = closure(r), flag = 1ULL << bit;
                        forbidden[a][0][w] &= ~flag; forbidden[a][1][w] &= ~flag;
                        if (c >> (8*y+x) & 1) forbidden[a][0][w] |= flag;
                        if (c >> (8*x+y) & 1) forbidden[a][1][w] |= flag;
                        ++forbidden_repaired;
                    }
            } else {
            if (!group_ready[e]) {'''
    assert needle in t;t=t.replace(needle,new,1)
    needle='''            forbidden_ready[a] = 1;'''
    t=t.replace(needle,'''            }
            forbidden_edge[a] = e;
            forbidden_mask[a] = mv.olda;
            forbidden_pol[a] = mv.oldpol & mv.olda;
            forbidden_dirty[a] = {};
'''+needle,1)
    # A change in matching size reindexes all slots: invalidate the persistent rows.
    t=t.replace('                match_colors = {};','                match_colors = {};\n                forbidden_mask = {};',1)
    t=t.replace('    stats.gobj_after = cur;', '''    std::cerr << "forbidden_partial = " << forbidden_partial << "\\nforbidden_repaired = " << forbidden_repaired << '\\n';
    stats.gobj_after = cur;''',1)
if a.colored:
    t=t.replace('kMemoSize = 1 << 14','kMemoSize = 1 << 15')
    needle='''            if (ea == eb) return false;
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            mask[eb] ^= (1ULL << a) | (1ULL << b);'''
    assert needle in t
    t=t.replace(needle,needle+'''
            // A pair exchange can require a simultaneous color change to stay acyclic.
            // Keep all four resulting color choices distinct in the objective cache.
            if (rng.mod(COLOR_RATE) == 0) {
                const unsigned colors = rng.mod(4);
                pol = (pol & ~((1ULL << a) | (1ULL << b))) |
                      (u64(colors & 1) << a) | (u64(colors >> 1) << b);
            }'''.replace('COLOR_RATE',str(a.colored)),1)
    t=t.replace('8256 + 64 * std::min(a, b) + std::max(a, b)', '8256 + 4 * (64 * std::min(a, b) + std::max(a, b)) + int(pol >> std::min(a,b) & 1) + 2 * int(pol >> std::max(a,b) & 1)')
    t=t.replace('12352 + 2 *','24640 + 2 *')
    needle='''            else if (mv.transfer >= 0) reverse_key = 24640 + 2 * (ne * mv.a + mv.ea) + ((mv.oldpol >> mv.a) & 1);'''
    assert t.count(needle)==2
    t=t.replace(needle,needle+'''
            else if (mv.kind >= 3) reverse_key = 8256 + 4 * (64 * std::min(mv.a,mv.b) + std::max(mv.a,mv.b)) +
                int(mv.oldpol >> std::min(mv.a,mv.b) & 1) + 2 * int(mv.oldpol >> std::max(mv.a,mv.b) & 1);''')
if a.groupflip:
    t=t.replace('kMemoSize = 1 << 14','kMemoSize = 1 << 15')
    needle2="""            pol ^= 1ULL << a;
            eb = ea;"""
    new="""            // Inverting every window of one comparator group preserves all direct
            // consistency constraints inside that group, unlike separate one-window flips.
            if (counts[ea] > 1 && rng.mod(GROUP_RATE) == 0) {
                pol ^= mask[ea]; kind = -1;
            } else pol ^= 1ULL << a;
            eb = ea;""".replace('GROUP_RATE',str(a.groupflip))
    assert needle2 in t;t=t.replace(needle2,new,1)
    t=t.replace('        else if (kind < 3) move_key =', '        else if (kind < 0) move_key = 16384 + ea;\n        else if (kind < 3) move_key =',1)
if a.unique:
    # In a state, a non-improving exact neighbor cannot improve on a repeated draw.
    # Avoid repeat evaluations of non-window moves as well; annealing may still revisit states.
    t=t.replace('if (memo_hit) { memo_hits++; return true; }', '''if (memo_hit) {
            memo_hits++;
            mask[ea] = olda; mask[eb] = oldb; pol = oldpol;
            return false;
        }''')
if a.exact_stall:
    t=t.replace('    long long forced_steps = 0, tabu_skips = 0;', '    long long last_accept_exact = exact_evals;\n    long long forced_steps = 0, tabu_skips = 0;')
    t=t.replace('it - last_accept_it >= kMapStall',f'(exact_evals - last_accept_exact >= {a.exact_stall} || it - last_accept_it >= 4096)')
    t=t.replace('it - last_accept_it >= kClimbStall',f'(exact_evals - last_accept_exact >= {a.exact_stall*2} || it - last_accept_it >= 8192)')
    t=t.replace('            last_accept_it = it;', '            last_accept_it = it; last_accept_exact = exact_evals;')
    t=t.replace('    last_accept_it = 0;', '    last_accept_it = 0; last_accept_exact = exact_evals;')
if a.early:
    old="""                int loss = 0;
                for (int w = 0; w < 2; ++w)
                    loss += __builtin_popcountll((match_colors[b][color][w] & forbidden[a][0][w]) |
                                                (match_colors[b][color^1][w] & forbidden[a][1][w]));"""
    new="""                int loss = __builtin_popcountll((match_colors[b][color][0] & forbidden[a][0][0]) |
                                                (match_colors[b][color^1][0] & forbidden[a][1][0]));
                // The first 64 selected pairs reject most choices; avoid the last word then.
                if (loss >= kRejectLoss) continue;
                loss += __builtin_popcountll((match_colors[b][color][1] & forbidden[a][0][1]) |
                                             (match_colors[b][color^1][1] & forbidden[a][1][1]));"""
    assert old in t;t=t.replace(old,new,1)
if a.lean:
    start2=t.index('        int ia = generic_index(), ib = generic_index(), a = order[ia], b = order[ib];')
    end2=t.index('        u64 olda = mask[ea], oldb = mask[eb], oldpol = pol;',start2)
    t=t[:start2]+"""        // Draw only indices used by this move. Multiplication maps into variable ranges
        // without division; the 60:12:20:8 neighborhood probabilities stay unchanged.
        int ia = rng.below(g), ib = ia, a = order[ia], b = a;
        const int type = rng.below(100);
        bool swindow = type < 60;
        int kind = type < 72 ? 0 : type < 92 ? 3 : 8;
        if (!swindow && kind == 3) { ib = rng.below(g); b = order[ib]; }
        else if (swindow && selected.size() != unsigned(need)) {
            ib = g + rng.below(64-g); b = order[ib];
        }
        int ea = which[a], eb = swindow ? ea : which[b];
"""+t[end2:]
    t=t.replace('            int color = ((oldpol >> a) ^ rng.next()) & 1;', '            int color = selected.size() == unsigned(need) ? 0 : int(rng.next() & 1);',1)
if a.flip_screen:
    needle2='        // Window replacements and transfers have already passed their candidate tables.'
    code2="""        if (selected.size() == unsigned(need) && !swindow && kind >= 0 && kind < 3) {
            Move probe = mv; probe.b = probe.a;
            if (swap_losses(probe) >= kRejectLoss) {
                mask[ea] = olda; mask[eb] = oldb; pol = oldpol;
                ++screen_rejected; memo_epoch[move_key] = 2*epoch;
                return false;
            }
        }
"""
    t=t.replace(needle2,code2+needle2,1)
    t=t.replace('selected.size() == unsigned(need) && !swindow && transfer < 0)', 'selected.size() == unsigned(need) && !swindow && transfer < 0 && (kind < 0 || kind >= 3))',1)
if a.unstick:
    t=t.replace('    long long forced_steps = 0, tabu_skips = 0;', '    long long tabu_resets = 0;\n    long long forced_steps = 0, tabu_skips = 0;')
    for threshold in ('kMapStall','kClimbStall'):
        needle2=f'        if (it - last_accept_it >= {threshold} && escape_valid) install_escape();'
        addition=f"""        // Tabu tenure normally advances only on acceptance. If every surviving
        // neighbor is tabu, clear the taboo and re-open consumed candidate rows.
        if (it - last_accept_it >= 2*{threshold} && !escape_valid &&
            ((it-last_accept_it) % (2*{threshold})) == 0) {{
            std::fill(tabu_epoch.begin(),tabu_epoch.end(),0);
            window_epoch.fill(0); transfer_epoch.fill(0); ++tabu_resets;
        }}
"""
        assert needle2 in t;t=t.replace(needle2,addition+needle2,1)
    t=t.replace('    stats.gobj_after = cur;','    std::cerr << "tabu_resets = " << tabu_resets << std::endl;\n    stats.gobj_after = cur;',1)
if a.cross:
    assert not a.history and not a.colored and not a.groupflip
    t=cross(t,a.cross)
    if a.cross_fast: t=cached_cross(t)
    if a.cross_rank: t=rank_cross(t,a.cross_rank)
if a.history:
    assert not a.groupflip
    t=history(t,a.history)
if a.sparse: t=sparse(t,a.sparse)
if a.kernel: t=kernel(t,s,a.kernel)
if a.native:
    t=t.replace('    auto propose = [&](Move& mv) {','    auto propose = [&](Move& mv) __attribute__((target("avx2,bmi2,popcnt"))) {')
out=s[:start]+t+s[end:]
(h/(a.name+'.cpp')).write_text(out)
(h/(a.name+'-README.md')).write_text(f'''改良元: solutions/as5-g38

assign_windows の変更: {vars(a)}。
閉包の差分キャッシュは、同じ比較器組の窓・色が変わらない間に残る商品対の結果を再利用する。
色付き交換は汎用窓どうしの組交換で、両窓の色も同時に選ぶ。
uniqueは同じ状態で厳密評価済みの手を再提案しない。exact-stallは停滞脱出を新規の全対評価数で判定する。
目的関数、距離上限26、G=38、時間0.50/0.61秒、ほかの段は変えない。
''')
meta=h/'experiments-config.json';d=json.loads(meta.read_text()) if meta.exists() else {};d[a.name]=vars(a);meta.write_text(json.dumps(d,indent=2)+'\n')
