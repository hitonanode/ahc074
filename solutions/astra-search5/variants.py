#!/usr/bin/env python3
"""提出元を変えず、assign_windows 内だけを書き換えた実験ソースを作る。"""
from pathlib import Path
import json
import argparse
p=argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--window-options', action='store_true')
p.add_argument('--rank', type=int, default=-1, help='不適合対の概算追加費用。-1は順位なし')
p.add_argument('--stall', type=int, default=1024)
p.add_argument('--rate', type=float, default=.6)
p.add_argument('--kind', type=int, default=10)
p.add_argument('--bitcount', action='store_true')
p.add_argument('--cheap-rank', type=int, default=-1)
p.add_argument('--state-tabu', type=int, default=0)
p.add_argument('--temperature', type=float, default=1.0)
p.add_argument('--tournament', type=int, default=1)
p.add_argument('--precut', type=int, default=-1)
p.add_argument('--climb-stall', type=int, default=0)
p.add_argument('--native-propose', action='store_true')
p.add_argument('--cross', type=int, default=0, help='窓交換の1/nを別の比較器の組への交換にする')
a=p.parse_args()
h=Path(__file__).resolve().parent
s=(h.parent/'astra-search4/main.cpp').read_text()
start=s.index('WindowStats assign_windows(')
end=s.index('// kBitLanes',start)
t=s[start:end]
t=t.replace('kMapStall = 1024, kClimbStall = 2048',f'kMapStall = {a.stall}, kClimbStall = {2*a.stall}')
if a.climb_stall: t=t.replace(f'kClimbStall = {2*a.stall}',f'kClimbStall = {a.climb_stall}')
t=t.replace('kWindowRate = 0.6',f'kWindowRate = {a.rate}')
t=t.replace('int kind = rng.mod(10)',f'int kind = rng.mod({a.kind})')
t=t.replace('const double temp = 0.05 *',f'const double temp = {0.05*a.temperature} *')
if a.window_options:
    needle='    auto propose = [&](Move& mv) {'
    insert='''    // Each row contains all handle/color replacements that preserve at least 68 pairs.
    // Consume a row without replacement in the current state; acceptance invalidates all rows.
    std::array<Colors, 64> unused_swap_placeholder{};
    std::array<Bits, 64> window_options{};
    std::array<unsigned, 64> window_epoch{};
    std::array<std::array<int, 128>, 64> window_priority{};
    long long window_rows = 0, window_samples = 0;
    auto prepare_windows = [&](int a, int ea) __attribute__((target("popcnt"))) {
        Move probe{}; probe.a = a; probe.b = __builtin_ctzll(hm); probe.ea = ea;
        probe.olda = mask[ea]; probe.oldpol = pol;
        swap_losses(probe); // Refresh selected colors and the closure after removing a.
        Bits available{};
        for (u64 q = hm; q; q &= q-1) {
            const int b = __builtin_ctzll(q);
            for (int color = 0; color < 2; ++color) {
                int loss = 0;
                for (int w = 0; w < 2; ++w)
                    loss += __builtin_popcountll((match_colors[b][color][w] & forbidden[a][0][w]) |
                                                (match_colors[b][color^1][w] & forbidden[a][1][w]));
                if (loss < kRejectLoss) available[color] |= 1ULL << b;
            }
        }
        ++window_rows;
        return available;
    };
'''.replace('    std::array<Colors, 64> unused_swap_placeholder{};\n','')
    if a.bitcount:
        bstart=insert.index('        Bits available{};')
        bend=insert.index('        ++window_rows;',bstart)
        insert=insert[:bstart]+'''        // Count losses for all 128 window/color choices in parallel. Saturate at 3.
        Bits once{}, twice{}, rejected{};
        for (int w = 0; w < 2; ++w) {
            for (u64 q = forbidden[a][0][w] | forbidden[a][1][w]; q; q &= q-1) {
                const int bit = __builtin_ctzll(q), p = selected[64*w+bit];
                const u64 f = 0ULL - ((forbidden[a][0][w] >> bit) & 1);
                const u64 r = 0ULL - ((forbidden[a][1][w] >> bit) & 1);
                const u64 d = pairs.diff[p], au = pairs.au[p];
                const Bits bad{d & ((~au & f) | (au & r)), d & ((au & f) | (~au & r))};
                for (int c = 0; c < 2; ++c) {
                    rejected[c] |= twice[c] & bad[c];
                    twice[c] |= once[c] & bad[c];
                    once[c] ^= bad[c];
                }
                if (!((~rejected[0] | ~rejected[1]) & hm)) {
                    ++window_rows;
                    return Bits{};
                }
            }
        }
        Bits available{hm & ~rejected[0], hm & ~rejected[1]};
'''+insert[bend:]
    if a.cheap_rank>=0:
        needle2='        ++window_rows;\n        return available;'
        insert=insert.replace(needle2,'''        // Cheap priority: handle differences saved and matching pairs lost.
        for (int c = 0; c < 2; ++c)
            for (u64 q = available[c]; q; q &= q-1) {
                const int b = __builtin_ctzll(q);
                int diff = 0, loss = 0;
                for (int w = 0; w < 2; ++w) {
                    diff += __builtin_popcountll(match_colors[b][0][w] | match_colors[b][1][w]);
                    loss += __builtin_popcountll((match_colors[b][c][w] & forbidden[a][0][w]) |
                                                (match_colors[b][c^1][w] & forbidden[a][1][w]));
                }
                window_priority[a][64*c+b] = -1800*diff + CHEAP_PENALTY*loss;
            }
'''.replace('CHEAP_PENALTY',str(a.cheap_rank))+needle2)
    if a.rank>=0:
        needle2='        ++window_rows;\n        return available;'
        rank='''        // Estimate the delta on the current matching. The final evaluation always
        // rebuilds the original greedy matching; this estimate only orders proposals.
        const uint32_t keep = ~(fwd[ea] | rev[ea]);
        const u64 rest = mask[ea] & ~(1ULL << a);
        for (int color = 0; color < 2; ++color)
            for (u64 bits = available[color]; bits; bits &= bits-1) {
                const int b = __builtin_ctzll(bits);
                int delta = 0;
                for (int p : selected) {
                    const u64 d = pairs.diff[p], z = pairs.au[p] ^ pol, q = d & rest;
                    uint32_t r = pairs.dir[p] & keep;
                    if (q & ~z) r |= fwd[ea];
                    if (q & z) r |= rev[ea];
                    if (d >> b & 1) r |= (((pairs.au[p] >> b) & 1) == color) ? fwd[ea] : rev[ea];
                    const int cost = relations.cost(r);
                    delta += cost ? 5 * (cost - pairs.rel[p]) : RANK_PENALTY;
                    delta += 1800 * (int(d >> a & 1) - int(d >> b & 1));
                }
                window_priority[a][64*color+b] = delta;
            }
'''.replace('RANK_PENALTY',str(a.rank))
        insert=insert.replace(needle2,rank+needle2)
    t=t.replace(needle,insert+needle)
    old='''            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | ((((oldpol >> a) ^ rng.next()) & 1) << b);'''
    new='''            int color = ((oldpol >> a) ^ rng.next()) & 1;
            if (selected.size() == unsigned(need)) {
                if (window_epoch[a] != epoch) {
                    window_options[a] = prepare_windows(a, ea);
                    window_epoch[a] = epoch;
                }
                Bits options = window_options[a];
                if (!(options[0] | options[1])) return false;
WINDOW_RANK
                int skip = rng.below(__builtin_popcountll(options[0]) + __builtin_popcountll(options[1]));
                const int first = __builtin_popcountll(options[0]);
                color = skip >= first;
                if (color) skip -= first;
                u64 bits = options[color];
                while (skip--) bits &= bits-1;
                b = __builtin_ctzll(bits);
                ib = g;
                while (order[ib] != b) ++ib;
                window_options[a][color] &= ~(1ULL << b);
                ++window_samples;
            }
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | (u64(color) << b);'''
    rank='''                int best_priority = 1 << 30;
                Bits shortlist{};
                for (int c = 0; c < 2; ++c)
                    for (u64 q = options[c]; q; q &= q-1) {
                        const int j = __builtin_ctzll(q), value = window_priority[a][64*c+j];
                        if (value < best_priority) { best_priority = value; shortlist = {}; }
                        if (value == best_priority) shortlist[c] |= 1ULL << j;
                    }
                options = shortlist;'''
    t=t.replace(old,new.replace('WINDOW_RANK',rank if max(a.rank,a.cheap_rank)>=0 else ''))
    if a.tournament>1:
        assert max(a.rank,a.cheap_rank)>=0
        needle='''            int color = ((oldpol >> a) ^ rng.next()) & 1;
            if (selected.size() == unsigned(need)) {'''
        sample='''            if (selected.size() == unsigned(need)) {
                int chosen_index = -1, chosen_priority = 1 << 30;
                for (int attempt = 0; attempt < TOURNAMENT; ++attempt) {
                    const int at = attempt ? generic_index() : ia, x = order[at], ex = which[x];
                    if (window_epoch[x] != epoch) {
                        window_options[x] = prepare_windows(x, ex);
                        window_epoch[x] = epoch;
                    }
                    for (int c = 0; c < 2; ++c)
                        for (u64 q = window_options[x][c]; q; q &= q-1) {
                            const int j = __builtin_ctzll(q), value = window_priority[x][64*c+j];
                            if (value < chosen_priority) { chosen_priority = value; chosen_index = at; }
                        }
                }
                if (chosen_index < 0) return false;
                ia = chosen_index; a = order[ia]; ea = eb = which[a]; olda = oldb = mask[ea];
            }
'''.replace('TOURNAMENT',str(a.tournament))
        assert needle in t
        t=t.replace(needle,sample+needle,1)
    if a.precut>=0:
        assert a.rank>=0
        needle='''                b = __builtin_ctzll(bits);
                ib = g;'''
        t=t.replace(needle,'''                b = __builtin_ctzll(bits);
                if (window_priority[a][64*color+b] > PRE_CUT) {
                    window_options[a][color] &= ~(1ULL << b);
                    return false;
                }
                ib = g;'''.replace('PRE_CUT',str(a.precut)),1)
    t=t.replace('const bool checked = false;', 'const bool checked = swindow;')
    t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "window_rows = " << window_rows << "\\nwindow_samples = " << window_samples << \'\\n\';\n    stats.gobj_after = cur;')
if a.state_tabu:
    t=t.replace('    auto handles_after =', '''    // An exact hash tag prevents short cycles involving more than a single reverse move.
    // Hash collisions only replace old entries; a full 64-bit tag is checked before forbidding.
    std::array<std::array<u64,31>,64> state_codes{};
    XorShift hash_rng{0x9b44a2c862809ef1ULL};
    for (auto& row : state_codes) for (auto& code : row) code = hash_rng.next();
    auto hash_state = [&] {
        u64 hash = 0;
        for (int j = 0; j < 64; ++j)
            hash ^= state_codes[j][which[j] < 0 ? 0 : 1+2*which[j]+int(pol >> j & 1)];
        return hash;
    };
    u64 current_hash = hash_state();
    std::vector<u64> visited_hash(1 << 16);
    std::vector<unsigned> visited_epoch(1 << 16);
    auto hash_slot = [](u64 hash) { return unsigned((hash ^ (hash >> 32)) & 65535); };
    auto next_hash = [&](const Move& mv) {
        const int a = mv.a, b = mv.b, ea = mv.ea, eb = mv.eb;
        u64 hash = current_hash ^ state_codes[a][1+2*ea+int(mv.oldpol >> a & 1)];
        if (mv.swindow) {
            hash ^= state_codes[a][0] ^ state_codes[b][0] ^ state_codes[b][1+2*ea+int(pol >> b & 1)];
        } else if (mv.transfer >= 0) {
            hash ^= state_codes[a][1+2*eb+int(pol >> a & 1)];
        } else if (mv.kind < 3) {
            hash ^= state_codes[a][1+2*ea+int(pol >> a & 1)];
        } else {
            hash ^= state_codes[a][1+2*eb+int(pol >> a & 1)] ^
                    state_codes[b][1+2*eb+int(mv.oldpol >> b & 1)] ^ state_codes[b][1+2*ea+int(pol >> b & 1)];
        }
        return hash;
    };
    auto record_state = [&] {
        const unsigned slot = hash_slot(current_hash);
        visited_hash[slot] = current_hash; visited_epoch[slot] = epoch;
    };
    record_state();
    long long state_tabu_skips = 0;
    auto handles_after =''',1)
    t=t.replace('        ++epoch;\n        selected = candidate_selected;', '        current_hash = next_hash(mv);\n        ++epoch;\n        record_state();\n        selected = candidate_selected;',1)
    # Both search phases use the same candidate-state test. Escapes only store eligible moves.
    needle='        if (tabu_epoch[move_key] > epoch && candidate >= best - 1e-9) {'
    check='''        const u64 proposed_hash = next_hash(mv);
        const unsigned proposed_slot = hash_slot(proposed_hash);
        if (visited_hash[proposed_slot] == proposed_hash && visited_epoch[proposed_slot] + STATE_TENURE > epoch &&
            candidate >= best - 1e-9) {
            ++state_tabu_skips;
            undo_move(mv);
            continue;
        }
'''.replace('STATE_TENURE',str(a.state_tabu))
    assert t.count(needle)==2
    t=t.replace(needle,check+needle)
    t=t.replace('    stats.gobj_before = cur;', '    current_hash = hash_state();\n    std::fill(visited_epoch.begin(), visited_epoch.end(), 0);\n    std::fill(visited_hash.begin(), visited_hash.end(), 0);\n    record_state();\n    stats.gobj_before = cur;',1)
    t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "state_tabu_skips = " << state_tabu_skips << \'\\n\';\n    stats.gobj_after = cur;',1)
if a.cross:
    assert not a.state_tabu and a.tournament==1
    t=t.replace('kMemoSize = 1 << 14','kMemoSize = 1 << 18')
    t=t.replace('    auto propose =', '    long long cross_tried = 0, cross_exact = 0, cross_accepted = 0;\n    auto propose =',1)
    needle='''        if (swindow) {  // generic window a <-> handle window b
'''
    addition='''        // Replace a generic window by a handle on a different comparator edge.
        // This two-edge move may connect assignments separated by inadmissible intermediate moves.
        const bool cross = swindow && rng.mod(CROSS_RATE) == 0;
        if (cross) {
            ++cross_tried;
            if (counts[ea] < 2) return false;
            eb = (ea + 1 + rng.mod(ne-1)) % ne;
            oldb = mask[eb];
            mask[ea] &= ~(1ULL << a);
            mask[eb] |= 1ULL << b;
            pol = (pol & ~(1ULL << b)) | ((rng.next() & 1) << b);
        } else '''.replace('CROSS_RATE',str(a.cross))
    assert needle in t
    t=t.replace(needle,addition+needle.lstrip(),1)
    t=t.replace('''        if (swindow) move_key =''', '''        if (cross) move_key = 16384 + 2 * (ne * (64*a+b) + eb) + int(pol >> b & 1);
        else if (swindow) move_key =''',1)
    t=t.replace('const bool checked = swindow;', 'const bool checked = swindow && !cross;',1)
    t=t.replace('selected.size() == unsigned(need) && swindow)', 'selected.size() == unsigned(need) && swindow && !cross)',1)
    t=t.replace('''        exact_evals++;
''','''        exact_evals++;
        cross_exact += cross;
''',1)
    t=t.replace('''            which[mv.b] = mv.ea;''','''            which[mv.b] = mv.eb;
            if (mv.ea != mv.eb) { --counts[mv.ea]; ++counts[mv.eb]; ++cross_accepted; }''',1)
    old='''if (mv.swindow) reverse_key = 2 * (64 * mv.b + mv.a) + ((mv.oldpol >> mv.a) & 1);'''
    new='''if (mv.swindow && mv.ea != mv.eb)
                reverse_key = 16384 + 2 * (ne * (64*mv.b+mv.a) + mv.ea) + int(mv.oldpol >> mv.a & 1);
            else if (mv.swindow) reverse_key = 2 * (64 * mv.b + mv.a) + ((mv.oldpol >> mv.a) & 1);'''
    assert t.count(old)==2
    t=t.replace(old,new)
    t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "cross_tried = " << cross_tried << "\\ncross_exact = " << cross_exact << "\\ncross_accepted = " << cross_accepted << \'\\n\';\n    stats.gobj_after = cur;',1)
if a.native_propose:
    t=t.replace('auto propose = [&](Move& mv) {', 'auto propose = [&](Move& mv) __attribute__((target("popcnt"))) {',1)
s=s[:start]+t+s[end:]
(h/(a.name+'.cpp')).write_text(s)
(h/(a.name+'.md')).write_text(f'''# 実験 {a.name}

改良元: solutions/astra-search4

窓交換候補の一括列挙: {a.window_options}。列挙した候補は同じ状態で重複して選ばない。
順位付けの不適合対費用: {a.rank}（-1なら無作為）。70対での概算費用差は提案順序だけに使う。
停滞時の試行数: {a.stall} / {2*a.stall}。窓交換率: {a.rate}。他近傍の種類乱数の上限: {a.kind}。
`window_rows` は候補を列挙した窓数、`window_samples` はそこから提案した回数。
目的関数と時間区切り、他の段は同じ。
ビット並列の損失カウンタ: {a.bitcount}。簡易順位付けの損失ペナルティ: {a.cheap_rank}。
状態ハッシュの再訪禁止: {a.state_tabu} 受理分（0なら無効）。
焼きなまし温度の倍率: {a.temperature}。
交換元の候補数: {a.tournament}。概算費用の除外上限: {a.precut}（-1は無効）。
最後の区間だけの停滞試行数: {a.climb_stall or 2*a.stall}。
近傍生成のpopcnt属性: {a.native_propose}。
窓交換と組変更の複合手の頻度: 窓交換の1/{a.cross}（0は無効）。
''')
(h/(a.name+'-config.json')).write_text(json.dumps(vars(a),indent=2)+'\n')
