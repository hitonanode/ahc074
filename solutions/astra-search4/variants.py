#!/usr/bin/env python3
"""imp-comboから割り当て探索の試作だけを再生成する。"""
from pathlib import Path
import argparse
from moves import doublewindow, guided
from optimize import deferred, buckets, tight, lazypriority, directpriority, noisyescape, rescue, nearpriority, losslimit, phaseloss
HERE=Path(__file__).resolve().parent
BASE=(HERE.parent/'imp-combo/main.cpp').read_text()

def make(name):
    if name == 'selected':
        return selected_source(make('loss3-short'))
    if name in ('phase63','phase34'):
        return phaseloss(make('tight'), 6 if name=='phase63' else 3, 3 if name=='phase63' else 4, 0.2 if name=='phase63' else 1.0)
    if name == 'loss3-record':
        return nearpriority(make('loss3-direct'),512).replace('rng.real() < std::exp((cur - candidate) / temp)', 'candidate <= best + 2.0 * temp')
    if name in ('loss3-lazy','loss3-direct','loss3-short','loss3-kind95'):
        out=losslimit(make('lazyprior' if name=='loss3-lazy' else 'directprior'),3)
        if name=='loss3-short':out=out.replace('kMapStall = 2048, kClimbStall = 4096','kMapStall = 1024, kClimbStall = 2048')
        if name=='loss3-kind95':
            a=out.index('WindowStats assign_windows(');b=out.index('    return stats;',out.index('    stats.gobj_after = cur;',a))
            part=out[a:b].replace('int kind = rng.mod(10)', 'int kind = rng.mod(100)')
            part=part.replace('kind < 3','kind < 1').replace('kind < 8','kind < 5').replace('kind >= 3','kind >= 1')
            out=out[:a]+part+out[b:]
        return out
    if name.startswith('loss'):
        return losslimit(make('tight'), int(name[4:]))
    if name.startswith('tabu'):
        return make('tight').replace('kTabuAccepted = 4', 'kTabuAccepted = '+name[4:])
    if name.startswith('guide'):
        return guided(doublewindow(make('tight'), 1), int(name[5:]))
    if name.startswith('double'):
        return doublewindow(make('tight'), int(name[6:]))
    if name.startswith('near'):
        return nearpriority(make('directprior'), int(name[4:]))
    if name in ('record2','record2-near512'):
        return make('near512' if name.endswith('near512') else 'directprior').replace('rng.real() < std::exp((cur - candidate) / temp)', 'candidate <= best + 2.0 * temp')
    if name.startswith('rescue'):
        return rescue(make('tight'), int(name[6:]))
    if name == 'directprior':
        return directpriority(make('lazyprior'))
    if name.startswith('noise'):
        return noisyescape(make('tight'),float(name[5:])/1000)
    if name == 'lazyprior':
        return lazypriority(make('tight'))
    if name == 'tight':
        return tight(make('bitremove'))
    if name == 'native':
        return make('tight').replace('WindowStats assign_windows(', '__attribute__((target("avx2,bmi2,popcnt"))) WindowStats assign_windows(')
    if name in ('greedy','greedy512','temp01','temp025','temp2','constant003','constant01'):
        out=make('stall512' if name=='greedy512' else 'bitremove')
        if name.startswith('greedy'):
            return out.replace('candidate <= cur || force || rng.real() < std::exp((cur - candidate) / temp)', 'candidate <= cur || force')
        expression={'temp01':'0.005 * std::pow(0.00125 / 0.05, progress)',
                    'temp025':'0.0125 * std::pow(0.00125 / 0.05, progress)',
                    'temp2':'0.10 * std::pow(0.00125 / 0.05, progress)',
                    'constant003':'0.003', 'constant01':'0.01'}[name]
        return out.replace('0.05 * std::pow(0.00125 / 0.05, progress)',expression)
    if name in ('bucket','bucketfilter'):
        return buckets(make('bitremove'), name=='bucketfilter')
    if name.startswith('batch'):
        return batches(make('bitremove'), int(name[5:]))
    if name == 'deferred':
        return deferred(make('bitremove'), BASE)
    if name.startswith('cycle') or name.startswith('restart'):
        return cycles(make('bitremove'), int(name[-1]), name.startswith('restart'))
    if name.startswith('stall'):
        k=int(name[5:]);return make('bitremove').replace('kMapStall = 2048, kClimbStall = 4096',f'kMapStall = {k}, kClimbStall = {2*k}')
    if name.startswith('late'):
        return late(make('bitremove'),int(name[4:]))
    if name == 'bitremove':
        return bitremove(make('incremental'))
    if name == 'incremental':
        return incremental(make('fast'))
    s=BASE
    if name in ('light','lightvec','lightinc','fast'):
        s=s.replace('} else if (!checked && selected.size() == unsigned(need)) {','} else if (!checked && selected.size() == unsigned(need) && transfer < 0) {')
    if name in ('lightvec','fast'):
        s=s.replace('std::array<std::int16_t, 30>', 'std::array<std::int16_t, 32>')
        s=s.replace('auto make_transfer_options = [&](int a, int ea) __attribute__((target("bmi2,popcnt")))', 'auto make_transfer_options = [&](int a, int ea) __attribute__((target("avx2,bmi2,popcnt")))')
        s=s.replace('std::array<int, 30> added_cost{};', 'alignas(32) std::array<int, 32> added_cost{};')
        s=s.replace('priority_values[slot][e + 15]', 'priority_values[slot][e + 16]')
        old='''            for (int e = 0; e < 15; ++e) {
                added_cost[e] += delta[e + 15 * color];
                added_cost[e + 15] += delta[e + 15 * (color ^ 1)];
            }'''
        new='''            // Two padded 16-entry halves permit four exact eight-lane sums.
            for (int h = 0; h < 2; ++h)
                for (int k = 0; k < 16; k += 8) {
                    const __m256i d = _mm256_cvtepi16_epi32(_mm_loadu_si128(
                        (const __m128i*)(delta.data() + 16 * (color ^ h) + k)));
                    int* out = added_cost.data() + 16 * h + k;
                    _mm256_store_si256((__m256i*)out, _mm256_add_epi32(
                        _mm256_load_si256((const __m256i*)out), d));
                }'''
        assert old in s;s=s.replace(old,new)
        s=s.replace('transfer_priority[a][code] = added_cost[code];', 'transfer_priority[a][code] = added_cost[code + (code >= 15)];')
    if name in ('lightinc','fast'):
        old='''                const int before = relations.cost(closed);
                for (int e = 0; e < 15; ++e) {
                    const int lo = relations.cost(closed | fwd[e]);
                    const int hi = relations.cost(closed | rev[e]);
                    priority_values[slot][e] = lo ? lo - before : 0;
                    priority_values[slot][e + OFFSET] = hi ? hi - before : 0;
                }'''.replace('OFFSET', '16' if name=='fast' else '15')
        new='''                const int before = sums.both_of(c);
                for (int e = 0; e < 15; ++e) {
                    const auto [x, y] = ep[e];
                    int lo = 0, hi = 0;
                    if (!((forward | reverse) >> e & 1)) {
                        // For incomparable x,y, adding x->y connects every ancestor of x
                        // (including x) to every descendant of y (including y).
                        const u64 from_x = ((c >> x) & 0x010101010101ULL) | (1ULL << (8*x));
                        const u64 from_y = ((c >> y) & 0x010101010101ULL) | (1ULL << (8*y));
                        lo = sums.both_of(c | (from_x * (((c >> (8*y)) & 63) | (1ULL << y)))) - before;
                        hi = sums.both_of(c | (from_y * (((c >> (8*x)) & 63) | (1ULL << x)))) - before;
                    }
                    priority_values[slot][e] = lo;
                    priority_values[slot][e + OFFSET] = hi;
                }'''.replace('OFFSET', '16' if name=='fast' else '15')
        assert old in s;s=s.replace(old,new)
    if name not in ('light','lightvec','lightinc','fast'): raise ValueError(name)
    return s

def incremental(s):
    s=s.replace('    std::vector<u64> match_closed;', """    std::vector<u64> match_closed;
    std::vector<int> screen_selected, screen_pos(np, -1);
    std::vector<unsigned> screen_present(np, 0);
    std::vector<uint32_t> screen_dirs;
    unsigned screen_serial = 0;
    long long screen_color_pairs = 0, screen_refreshes = 0;""")
    start=s.index('        if (screen_dirty) {',s.index('WindowStats assign_windows'))
    end=s.index('        const int a = mv.a, e = mv.ea;',start)
    s=s[:start]+"""        if (screen_dirty) {
            ++screen_refreshes;
            auto toggle_colors = [&](int i, int p) {
                ++screen_color_pairs;
                const u64 bit = 1ULL << (i & 63);
                for (u64 q = pairs.diff[p]; q; q &= q - 1) {
                    const int j = __builtin_ctzll(q);
                    match_colors[j][(pairs.au[p] >> j) & 1][i >> 6] ^= bit;
                }
            };
            if (screen_selected.size() != selected.size()) {
                match_colors = {};
                std::fill(screen_pos.begin(), screen_pos.end(), -1);
                screen_selected = selected;
                for (int i = 0; i < int(selected.size()); ++i) {
                    screen_pos[selected[i]] = i;
                    toggle_colors(i, selected[i]);
                }
                match_closed.resize(selected.size());
                screen_dirs.assign(selected.size(), ~0U);
            } else {
                // Keep surviving pairs in their bit positions. Only removed/new pairs
                // need color-bit updates, even when their matching cost order changes.
                ++screen_serial;
                for (int p : selected) screen_present[p] = screen_serial;
                std::array<int, 70> empty{};
                int count = 0;
                for (int i = 0; i < int(screen_selected.size()); ++i) {
                    const int p = screen_selected[i];
                    if (screen_present[p] == screen_serial) continue;
                    toggle_colors(i, p);
                    screen_pos[p] = -1;
                    empty[count++] = i;
                }
                for (int p : selected) if (screen_pos[p] < 0) {
                    const int i = empty[--count];
                    screen_selected[i] = p;
                    screen_pos[p] = i;
                    toggle_colors(i, p);
                }
                selected = screen_selected;
            }
            forbidden_ready = {};
            for (int i = 0; i < int(selected.size()); ++i) {
                const uint32_t r = pairs.dir[selected[i]];
                if (screen_dirs[i] != r) {
                    screen_dirs[i] = r;
                    match_closed[i] = closure(r);
                }
            }
            screen_dirty = false;
        }
"""+s[end:]
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "screen_color_pairs = " << screen_color_pairs << "\\nscreen_refreshes = " << screen_refreshes << '\\n';
    stats.gobj_after = cur;''')
    return s

def bitremove(s):
    s=s.replace('    std::array<unsigned char, 64> forbidden_ready{};', '    std::array<unsigned char, 64> forbidden_ready{};\n    std::array<Colors, 15> group_forbidden{};\n    std::array<unsigned char, 15> group_ready{};')
    s=s.replace('            forbidden_ready = {};', '            forbidden_ready = {};\n            group_ready = {};')
    start=s.index('        if (!forbidden_ready[a]) {',s.index('WindowStats assign_windows'))
    end=s.index('        const int b = mv.b, c = (pol >> b) & 1;',start)
    s=s[:start]+"""        if (!forbidden_ready[a]) {
            const auto [x, y] = ep[e];
            if (!group_ready[e]) {
                group_forbidden[e] = {};
                for (int i = 0; i < int(selected.size()); ++i) {
                    const u64 c = match_closed[i], bit = 1ULL << (i & 63);
                    if (c >> (8 * y + x) & 1) group_forbidden[e][0][i >> 6] |= bit;
                    if (c >> (8 * x + y) & 1) group_forbidden[e][1][i >> 6] |= bit;
                }
                group_ready[e] = 1;
            }
            forbidden[a] = group_forbidden[e];
            Colors remaining{};
            for (u64 q = mv.olda & ~(1ULL << a); q; q &= q - 1) {
                const int j = __builtin_ctzll(q), color = (mv.oldpol >> j) & 1;
                for (int w = 0; w < 2; ++w) {
                    remaining[0][w] |= match_colors[j][color][w];
                    remaining[1][w] |= match_colors[j][color ^ 1][w];
                }
            }
            const int color = (mv.oldpol >> a) & 1;
            for (int w = 0; w < 2; ++w) {
                const u64 lost_fwd = match_colors[a][color][w] & ~remaining[0][w];
                const u64 lost_rev = match_colors[a][color ^ 1][w] & ~remaining[1][w];
                // Only a pair losing its last arc in this direction needs a new closure.
                for (u64 q = lost_fwd | lost_rev; q; q &= q - 1) {
                    const int bit = __builtin_ctzll(q), i = 64*w + bit;
                    const u64 flag = 1ULL << bit;
                    uint32_t r = pairs.dir[selected[i]];
                    r &= ~uint32_t((lost_fwd & flag) ? fwd[e] : rev[e]);
                    const u64 c = closure(r);
                    forbidden[a][0][w] &= ~flag;
                    forbidden[a][1][w] &= ~flag;
                    if (c >> (8 * y + x) & 1) forbidden[a][0][w] |= flag;
                    if (c >> (8 * x + y) & 1) forbidden[a][1][w] |= flag;
                }
            }
            forbidden_ready[a] = 1;
        }
"""+s[end:]
    return s

def cycles(s, count, restart):
    restore_start=s.index('    ++epoch;\n    mask = best_mask')
    restore_end=s.index('    stats.gobj_before = cur;',restore_start)
    restore=s[restore_start:restore_end]
    if restart:
        code='    int restart_segment = 0;\n    auto restore_best = [&] {\nRESTORE\n        std::fill(tabu_epoch.begin(), tabu_epoch.end(), 0);\n        escape_floor = 1e30; escape_valid = false;\n    };\n'.replace('RESTORE',restore)
        s=s.replace('    long long forced_steps = 0, tabu_skips = 0;',code+'    long long forced_steps = 0, tabu_skips = 0;')
        code=f"""        const int segment = std::min({count-1}, int(progress*{count}));
        if (segment > restart_segment) {{
            restore_best();
            last_accept_it = it;
            restart_segment = segment;
        }}
"""
        s=s.replace('        if (it - last_accept_it >= kMapStall && escape_valid)',code+'        if (it - last_accept_it >= kMapStall && escape_valid)',1)
    s=s.replace('0.00125 / 0.05, progress)',f'0.00125 / 0.05, progress*{count} - int(progress*{count}))')
    return s

def late(s,count):
    s=s.replace('    long long forced_steps = 0, tabu_skips = 0;', f'    std::array<double, {count}> late_history; late_history.fill(cur);\n    unsigned late_pos = 0;\n    long long forced_steps = 0, tabu_skips = 0;')
    s=s.replace('        const double temp = 0.05', f'        const double late_limit = late_history[late_pos % {count}];\n        if (!memo_hit) late_history[late_pos++ % {count}] = cur;\n        const double temp = 0.05',1)
    s=s.replace('rng.real() < std::exp((cur - candidate) / temp)', 'candidate <= late_limit')
    return s

def batches(s, size):
    s=s.replace('    int last_accept_it = 0;', '    int last_accept_it = 0, state_evals = 0;')
    s=s.replace('it - last_accept_it >= kMapStall && escape_valid', f'(it - last_accept_it >= kMapStall || state_evals >= {size}) && escape_valid')
    s=s.replace('it - last_accept_it >= kClimbStall && escape_valid', f'(it - last_accept_it >= kClimbStall || state_evals >= {size}) && escape_valid')
    s=s.replace('        memo_epoch[move_key] = epoch;', '        if (!memo_hit) ++state_evals;\n        memo_epoch[move_key] = epoch;')
    s=s.replace('it - last_accept_it >= kMapStall && candidate', f'(it - last_accept_it >= kMapStall || state_evals >= {size}) && candidate')
    s=s.replace('it - last_accept_it >= kClimbStall && candidate', f'(it - last_accept_it >= kClimbStall || state_evals >= {size}) && candidate')
    s=s.replace('if (candidate <= cur || force || rng.real() < std::exp((cur - candidate) / temp))', 'if (force)')
    s=s.replace('if (candidate <= cur || force)', 'if (force)')
    s=s.replace('last_accept_it = it;', 'last_accept_it = it; state_evals = 0;')
    s=s.replace('    last_accept_it = 0;', '    last_accept_it = 0; state_evals = 0;')
    return s

def selected_source(s):
    for line in [
        '    constexpr int kPriorityBits = 12;\n',
        '    std::vector<uint32_t> priority_keys(1 << kPriorityBits, ~0U);\n',
        '    std::vector<std::array<std::int16_t, 32>> priority_values(1 << kPriorityBits);\n',
        '    long long priority_hits = 0, priority_misses = 0;\n',
        '    std::cerr << "priority_hits = " << priority_hits << "\\npriority_misses = " << priority_misses << \'\\n\';\n',
    ]:
        assert line in s
        s=s.replace(line,'',1)
    s=s.replace('Once every destination has lost four pairs, later pairs cannot rescue it.',
                'Once every destination meets the rejection threshold, later pairs cannot rescue it.')
    s=s.replace('the original remainder mapping, so fixed-iteration trajectories are identical.',
                'the original remainder mapping. This arithmetic change preserves every draw.')
    s=s.replace('fallback dimensions keep','other dimensions keep')
    return s
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args()
    for n in a.names:(HERE/(n+'.cpp')).write_text(make(n))
