#!/usr/bin/env python3
"""探索試作を基準から生成。評価・ビルドは別スクリプトで逐次実行する。"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=(HERE.parent/'imp-s2hd/main.cpp').read_text()

def exact(s,n):
    s=s.replace('int last_accept_it = 0;', 'int last_accept_it = 0;\n    long long last_accept_evals = 0;')
    for name in ['kMapStall','kClimbStall']:
        s=s.replace(f'it - last_accept_it >= {name}',f'(exact_evals - last_accept_evals >= {n} || it - last_accept_it >= 8192)')
    s=s.replace('last_accept_it = it;', 'last_accept_it = it; last_accept_evals = exact_evals;')
    return s.replace('    last_accept_it = 0;', '    last_accept_it = 0; last_accept_evals = exact_evals;')

def history(s,n):
    add='''    // Fingerprint only active generic assignments; handle polarity and order are immaterial.
    std::array<std::array<u64, 30>, 64> signatures{};
    XorShift hash_rng{0xf735c2b806a94de1ULL};
    for (auto& row : signatures) for (auto& h : row) h = hash_rng.next();
    auto full_hash = [&] {
        u64 h = 0;
        for (int e = 0; e < ne; ++e)
            for (u64 q = mask[e]; q; q &= q - 1) {
                int a = __builtin_ctzll(q);
                h ^= signatures[a][2 * e + ((pol >> a) & 1)];
            }
        return h;
    };
    u64 state_hash = full_hash();
    constexpr unsigned kHistorySize = 1 << 14, kHistoryTenure = TENURE;
    std::vector<u64> history_hash(kHistorySize, 0);
    std::vector<unsigned> history_epoch(kHistorySize, 0);
    long long history_skips = 0;
    auto move_hash = [&](const Move& mv) {
        auto sig = [&](int a, int e, u64 p) { return signatures[a][2 * e + ((p >> a) & 1)]; };
        u64 h = state_hash ^ sig(mv.a, mv.ea, mv.oldpol);
        if (mv.swindow) return h ^ sig(mv.b, mv.ea, pol);
        if (mv.kind < 3) return h ^ sig(mv.a, mv.ea, pol);
        if (mv.kind < 8)
            return h ^ sig(mv.b, mv.eb, mv.oldpol) ^ sig(mv.a, mv.eb, pol) ^ sig(mv.b, mv.ea, pol);
        return h ^ sig(mv.a, mv.eb, pol);
    };
'''.replace('TENURE',str(n))
    s=s.replace('    auto propose = [&](Move& mv) {', add+'    auto propose = [&](Move& mv) {')
    marker='''        pass_epoch[move_key] = epoch;
        memo_hit = memo_epoch[move_key] == epoch;'''
    s=s.replace(marker,'''        const u64 h = move_hash(mv);
        const unsigned slot = h & (kHistorySize - 1);
        if (history_epoch[slot] && history_hash[slot] == h && epoch - history_epoch[slot] < kHistoryTenure) {
            mask[ea] = olda; mask[eb] = oldb; pol = oldpol;
            reject_epoch[move_key] = epoch;
            ++history_skips;
            return false;
        }
'''+marker)
    s=s.replace('''        ++epoch;
        selected = candidate_selected;''','''        state_hash = move_hash(mv);
        ++epoch;
        history_hash[state_hash & (kHistorySize - 1)] = state_hash;
        history_epoch[state_hash & (kHistorySize - 1)] = epoch;
        selected = candidate_selected;''')
    s=s.replace('''    mask = best_mask, pol = best_pol, order = best_order;''','''    mask = best_mask, pol = best_pol, order = best_order;
    state_hash = full_hash();
    std::fill(history_epoch.begin(), history_epoch.end(), 0);''')
    s=s.replace('''    stats.gobj_after = cur;''','''    std::cerr << "history_skips = " << history_skips << '\\n';
    stats.gobj_after = cur;''')
    return s


def guided(s,penalty,samples=4):
    at='''        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};
'''
    add='''        // Sample several handle destinations for the same generic window. Rank by losses
        // of selected pairs and their handle differences; exact matching remains unchanged.
        if (swindow && selected.size() == unsigned(need)) {
            Move chosen = mv;
            u64 chosen_mask = mask[ea], chosen_pol = pol;
            int best_rank = 1000000;
            for (int sample = 0; sample < SAMPLES; ++sample) {
                if (sample) {
                    ib = g + rng.mod(64 - g); b = order[ib];
                    mask[ea] = olda ^ (1ULL << a) ^ (1ULL << b);
                    pol = (oldpol & ~(1ULL << b)) | ((rng.next() & 1) << b);
                    mv.ib = ib; mv.b = b;
                }
                const int key = 2 * (64 * a + b) + ((pol >> b) & 1);
                if (reject_epoch[key] == epoch) continue;
                const int lost = swap_losses(mv);
                auto rank = [&]() __attribute__((target("popcnt"))) {
                    int db = 0;
                    for (int w = 0; w < 2; ++w)
                        db += __builtin_popcountll(match_colors[b][0][w] | match_colors[b][1][w]);
                    return (lost >= kRejectLoss ? 1000 : 0) + PENALTY * lost - db;
                };
                int value = rank();
                if (value < best_rank) {
                    best_rank = value; chosen = mv; chosen_mask = mask[ea]; chosen_pol = pol;
                }
            }
            mv = chosen; b = mv.b; ib = mv.ib; mask[ea] = chosen_mask; pol = chosen_pol;
        }
'''.replace('SAMPLES',str(samples)).replace('PENALTY',str(penalty))
    return s.replace(at,at+add)

def rescue(s,threshold):
    old='''            if (swap_losses(mv) >= kRejectLoss) {'''
    new='''            const int losses = swap_losses(mv);
            bool reject = losses >= kRejectLoss;
            if (reject && losses < 6) {
                auto gain = [&]() __attribute__((target("popcnt"))) {
                    int delta = 0;
                    for (int w = 0; w < 2; ++w) {
                        delta += __builtin_popcountll(match_colors[b][0][w] | match_colors[b][1][w]);
                        delta -= __builtin_popcountll(match_colors[a][0][w] | match_colors[a][1][w]);
                    }
                    return delta;
                };
                reject = gain() < THRESHOLD * (losses - 3);
            }
            if (reject) {'''.replace('THRESHOLD',str(threshold))
    assert s.count(old)==1
    return s.replace(old,new)

def repair(s,rate=8,unused=True):
    add='''    struct RepairTarget { int pair, window, direction, cost; };
    std::vector<RepairTarget> repair_targets;
    unsigned repair_epoch = 0;
    long long repair_builds = 0, repair_proposals = 0, repair_available = 0;
    auto prepare_repairs = [&] __attribute__((target("popcnt"))) {
        repair_targets.clear();
        std::array<bool, 256> used{};
        for (int p : selected) used[pairs.u[p]] = used[pairs.v[p]] = true;
        const int last = selected.back();
        const int ceiling = 1800 * __builtin_popcountll(pairs.diff[last] & hm) + 5 * (pairs.rel[last] - 1) + full144[last];
        for (int p = 0; p < np; ++p) {
            if (pairs.rel[p] || UNUSED) continue;
            uint32_t conflict = pairs.dir[p] & (pairs.dir[p] >> 16);
            if (!conflict || (conflict & (conflict - 1))) continue;
            const int e = __builtin_ctz(conflict);
            const u64 q = pairs.diff[p] & mask[e], z = pairs.au[p] ^ pol;
            const u64 handles = pairs.diff[p] & hm;
            if (!handles) continue;
            for (int direction = 0; direction < 2; ++direction) {
                const u64 unique = q & (direction ? z : ~z);
                if (!unique || (unique & (unique - 1))) continue;
                const uint32_t arc = direction ? rev[e] : fwd[e];
                const int rel = relations.cost(pairs.dir[p] & ~arc);
                if (!rel) continue;
                const int cost = 1800 * __builtin_popcountll(handles) + 5 * (rel - 1) + full144[p];
                if (cost >= ceiling) continue;
                repair_targets.push_back({p, __builtin_ctzll(unique), direction ^ 1, cost});
            }
        }
        std::sort(repair_targets.begin(), repair_targets.end(), [](const RepairTarget& a, const RepairTarget& b) {
            return a.cost < b.cost;
        });
        if (repair_targets.size() > 8) repair_targets.resize(8);
        repair_epoch = epoch;
        ++repair_builds; repair_available += repair_targets.size();
    };
'''.replace('UNUSED','(used[pairs.u[p]] || used[pairs.v[p]])' if unused else 'false')
    s=s.replace('    auto propose = [&](Move& mv) {',add+'    auto propose = [&](Move& mv) {')
    at='''        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];
'''
    new='''        int desired_color = -1;
        if (swindow && rng.mod(RATE) == 0 && selected.size() == unsigned(need)) {
            if (repair_epoch != epoch) prepare_repairs();
            if (!repair_targets.empty()) {
                const auto& target = repair_targets[rng.mod(repair_targets.size())];
                a = target.window;
                u64 q = pairs.diff[target.pair] & hm;
                int skip = rng.mod(__builtin_popcountll(q));
                while (skip--) q &= q - 1;
                b = __builtin_ctzll(q);
                ia = std::find(order.begin(), order.begin() + g, a) - order.begin();
                ib = std::find(order.begin() + g, order.end(), b) - order.begin();
                ea = eb = which[a];
                desired_color = ((pairs.au[target.pair] >> b) & 1) ^ target.direction;
                ++repair_proposals;
            }
        }
'''.replace('RATE',str(rate))
    s=s.replace(at,at+new)
    s=s.replace('((((oldpol >> a) ^ rng.next()) & 1) << b)', '(u64(desired_color >= 0 ? desired_color : (((oldpol >> a) ^ rng.next()) & 1)) << b)')
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "repair_builds = " << repair_builds << "\\nrepair_proposals = " << repair_proposals
              << "\\nrepair_available = " << repair_available << '\\n';
    stats.gobj_after = cur;''')
    return s

def escape_pool(s,count=4,band=0.02):
    begin=s.index('    Move escape_move{};')
    end=s.index('    long long forced_steps = 0, tabu_skips = 0;',begin)
    add='''    struct Escape {
        double cost;
        Move move;
        u64 ma, mb, pol;
        int key;
    };
    std::array<Escape, COUNT> escape_pool{};
    int escape_count = 0;
    bool escape_valid = false;
    long long direct_steps = 0;
    auto remember_escape = [&](double candidate) {
        if (memo_hit) return;  // distinct neighbors only
        int pos = 0;
        while (pos < escape_count && escape_pool[pos].cost <= candidate) ++pos;
        if (pos == int(escape_pool.size())) return;
        escape_count = std::min(escape_count + 1, int(escape_pool.size()));
        for (int i = escape_count - 1; i > pos; --i) escape_pool[i] = escape_pool[i - 1];
        escape_pool[pos] = {candidate, mv, mask[mv.ea], mask[mv.eb], pol, move_key};
        escape_floor = escape_pool[0].cost;
        escape_valid = true;
    };
    auto install_escape = [&] {
        int count = 1;
        while (count < escape_count && escape_pool[count].cost <= escape_pool[0].cost + BAND) ++count;
        const auto& saved = escape_pool[rng.mod(count)];
        mv = saved.move; move_key = saved.key;
        mask[mv.ea] = saved.ma; mask[mv.eb] = saved.mb; pol = saved.pol;
        escape_floor = saved.cost;
        memo_hit = true; ++memo_hits; ++direct_steps;
    };
'''.replace('COUNT',str(count)).replace('BAND',str(band))
    s=s[:begin]+add+s[end:]
    return s.replace('escape_floor = 1e30; escape_valid = false;', 'escape_floor = 1e30; escape_valid = false; escape_count = 0;')

def profile(s):
    pos='    auto propose = [&](Move& mv) {'
    s=s.replace(pos,'''    std::array<long long, 4> kind_try{}, kind_eval{}, kind_accept{}, kind_best{};
    auto move_kind = [](const Move& mv) { return mv.swindow ? 0 : mv.kind < 3 ? 1 : mv.kind < 8 ? 2 : 3; };
'''+pos)
    pos='        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];'
    s=s.replace(pos,pos+'\n        ++kind_try[swindow ? 0 : kind < 3 ? 1 : kind < 8 ? 2 : 3];')
    s=s.replace('        exact_evals++;','        exact_evals++; ++kind_eval[move_kind(mv)];')
    s=s.replace('        accepted++;','        accepted++; ++kind_accept[move_kind(mv)];')
    s=s.replace('if (cur < best - 1e-9) {', 'if (cur < best - 1e-9) {\n                ++kind_best[move_kind(mv)];')
    s=s.replace('    stats.gobj_after = cur;', '''    for (int k = 0; k < 4; ++k) {
        std::cerr << "kind" << k << "_try = " << kind_try[k] << '\\n';
        std::cerr << "kind" << k << "_eval = " << kind_eval[k] << '\\n';
        std::cerr << "kind" << k << "_accept = " << kind_accept[k] << '\\n';
        std::cerr << "kind" << k << "_best = " << kind_best[k] << '\\n';
    }
    stats.gobj_after = cur;''')
    return s

def rng_mul(s):
    a=s.index('WindowStats assign_windows('); b=s.index('\n    return stats;\n}',a)+len('\n    return stats;\n}')
    return s[:a]+s[a:b].replace('rng.mod(', 'rng.below(')+s[b:]

def merge_cache(s):
    s=s.replace('std::vector<unsigned> memo_epoch(kMemoSize, 0);', 'std::vector<int> memo_epoch(kMemoSize, 0);')
    s=s.replace('    std::vector<unsigned> reject_epoch(kMemoSize, 0), pass_epoch(kMemoSize, 0);\n', '')
    s=s.replace('reject_epoch[move_key] == epoch', 'memo_epoch[move_key] == -int(epoch)')
    s=s.replace('const bool checked = pass_epoch[move_key] == epoch;', 'const bool checked = memo_epoch[move_key] == int(epoch);')
    s=s.replace('reject_epoch[move_key] = epoch;', 'memo_epoch[move_key] = -int(epoch);')
    s=s.replace('        pass_epoch[move_key] = epoch;\n', '')
    return s


def fast_draw(s):
    a=s.index('        int ia = rng.mod(g), ib = rng.mod(g), a = order[ia], b = order[ib];')
    b=s.index('        u64 olda = mask[ea]',a)
    new='''        // Two independent 64-bit words provide four uniform 32-bit fields. Multiplication
        // maps window indices without integer division; separate fields choose type and kind.
        const u64 positions = rng.next(), modes = rng.next();
        const int ia = (u64(uint32_t(positions)) * unsigned(g)) >> 32;
        const bool swindow = uint32_t(modes) < uint32_t(kWindowRate * 4294967296.0);
        const int ib = ((positions >> 32) * unsigned(swindow ? 64 - g : g) >> 32) + (swindow ? g : 0);
        const int a = order[ia], b = order[ib];
        const int kind = ((modes >> 32) * 10) >> 32;
        int ea = which[a], eb = swindow ? ea : which[b];
'''
    s=s[:a]+new+s[b:]
    return rng_mul(s)

def continuous(s):
    a=s.index('    // Search from the annealing best for the original final time interval.')
    b=s.index('    long long climb_forced_steps = 0;',a)
    new='''    // Continue from the current state while keeping the best from both phases. The final
    // interval has the original length and accepts only descent or stagnation escape.
    stats.gobj_before = best;
    escape_floor = 1e30; escape_valid = false;
    last_accept_it = 0;
'''
    return s[:a]+new+s[b:]


def sampler(s,wait=64,once=True):
    pos='    auto propose = [&](Move& mv) {'
    s=s.replace(pos,'''    std::array<u64, 64> swap_options{};
    std::array<unsigned, 64> options_epoch{};
    int state_proposals = 0;
    long long sampler_rows = 0, sampled_swaps = 0;
'''+pos+'\n        ++state_proposals;')
    pos='''        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};
'''
    add='''        if (swindow && selected.size() == unsigned(need) && 64 - g <= 32 && state_proposals > WAIT) {
            if (options_epoch[a] != epoch) {
                swap_losses(mv);  // materialize the color / forbidden bitsets for this row
                auto options = [&]() __attribute__((target("popcnt"))) {
                    u64 result = 0;
                    for (int j = g; j < 64; ++j) for (int c = 0; c < 2; ++c) {
                        const int b = order[j];
                        if (ONCE && memo_epoch[2 * (64 * a + b) + c] == epoch) continue;
                        int lost = 0;
                        for (int w = 0; w < 2; ++w)
                            lost += __builtin_popcountll((match_colors[b][c][w] & forbidden[a][0][w]) |
                                                         (match_colors[b][c ^ 1][w] & forbidden[a][1][w]));
                        if (lost < kRejectLoss) result |= 1ULL << (2 * (j - g) + c);
                    }
                    return result;
                };
                swap_options[a] = options(); options_epoch[a] = epoch; ++sampler_rows;
            }
            u64 available = swap_options[a];
            if (!available) {
                mask[ea] = olda; pol = oldpol; ++screen_rejected;
                return false;
            }
            int skip = rng.below(__builtin_popcountll(available));
            while (skip--) available &= available - 1;
            const int code = __builtin_ctzll(available);
            if (ONCE) swap_options[a] &= ~(1ULL << code);
            ib = g + code / 2; b = order[ib];
            mask[ea] = olda ^ (1ULL << a) ^ (1ULL << b);
            pol = (oldpol & ~(1ULL << b)) | (u64(code & 1) << b);
            mv.ib = ib; mv.b = b;
            ++sampled_swaps;
        }
'''.replace('WAIT',str(wait)).replace('ONCE','true' if once else 'false')
    s=s.replace(pos,pos+add)
    s=s.replace('        ++epoch;\n        selected', '        ++epoch; state_proposals = 0;\n        selected')
    s=s.replace('    ++epoch;\n    mask = best_mask', '    ++epoch; state_proposals = 0;\n    mask = best_mask')
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "sampler_rows = " << sampler_rows << "\\nsampled_swaps = " << sampled_swaps << '\\n';
    stats.gobj_after = cur;''')
    return s

def novelty(s,gap=256):
    s=s.replace('    int last_accept_it = 0;', '    int last_accept_it = 0, last_new_it = 0;')
    for limit in ['kMapStall','kClimbStall']:
        s=s.replace('it - last_accept_it >= '+limit, f'(it - last_new_it >= {gap} || it - last_accept_it >= 8192)')
    s=s.replace('const double candidate = memo_hit ? memo_value[move_key] : matching_cost(nrel.data(), handles_after(mv));',
                'if (!memo_hit) last_new_it = it;\n        const double candidate = memo_hit ? memo_value[move_key] : matching_cost(nrel.data(), handles_after(mv));')
    s=s.replace('last_accept_it = it;', 'last_accept_it = last_new_it = it;')
    s=s.replace('    last_accept_it = 0;', '    last_accept_it = last_new_it = 0;')
    return s

def kinds(s,flip=5,exchange=15):
    old='        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];'
    new=f'''        const int kind_draw = rng.mod(100);
        int kind = kind_draw < {flip} ? 0 : kind_draw < {flip+exchange} ? 3 : 8;
        int ea = which[a], eb = swindow ? ea : which[b];'''
    assert old in s
    return s.replace(old,new)

def record_threshold(s,scale=2):
    old='candidate <= cur || force || rng.real() < std::exp((cur - candidate) / temp)'
    assert old in s
    return s.replace(old, f'candidate <= cur || force || candidate <= best + {scale} * temp')

def transfer_sampler(s,once=True):
    at='    auto propose = [&](Move& mv) {'
    add='''    std::array<uint32_t, 64> transfer_options{};
    std::array<unsigned, 64> transfer_epoch{};
    long long transfer_rows = 0, transfer_samples = 0;
    auto make_transfer_options = [&](int a, int ea) __attribute__((target("bmi2,popcnt"))) {
        uint32_t ones = 0, twos = 0, four = 0;
        const u64 rest = mask[ea] & ~(1ULL << a);
        const uint32_t keep = ~(fwd[ea] | rev[ea]);
        for (int p : selected) {
            if (!(pairs.diff[p] >> a & 1)) continue;
            const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & keep;
            if (q & ~z) r |= fwd[ea];
            if (q & z) r |= rev[ea];
            const u64 c = closure(r);  // deleting one window preserves acyclicity
            // A new x->y arc is forbidden iff y reaches x. Extract columns of the
            // lower triangle in the sheet-pair order, and the upper triangle in one go.
            uint32_t forward = _pext_u64(c, 0x0000010101010100ULL)
                             | (_pext_u64(c, 0x0000020202020000ULL) << 5)
                             | (_pext_u64(c, 0x0000040404000000ULL) << 9)
                             | (_pext_u64(c, 0x0000080800000000ULL) << 12)
                             | (((c >> 44) & 1) << 14);
            uint32_t reverse = _pext_u64(c, 0x00002030383c3eULL);
            uint32_t bad = (pairs.au[p] >> a & 1) ? reverse | (forward << 15) : forward | (reverse << 15);
            // Parallel saturating counters: bit e counts losses for the same candidate.
            const uint32_t carry = ones & bad;
            ones ^= bad;
            four |= twos & carry;
            twos ^= carry;
        }
        return (~four & ((1U << 30) - 1)) & ~((1U << ea) | (1U << (ea + 15)));
    };
'''
    s=s.replace(at,add+at)
    old='''            eb = rng.mod(ne);
            if (ea == eb) return false;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
            if (rng.next() & 1) pol ^= 1ULL << a;'''
    new='''            int new_color = -1;
            if (selected.size() == unsigned(need)) {
                if (transfer_epoch[a] != epoch) {
                    transfer_options[a] = make_transfer_options(a, ea);
                    transfer_epoch[a] = epoch; ++transfer_rows;
                }
                uint32_t available = transfer_options[a];
                if (!available) return false;
                int skip = rng.below(__builtin_popcount(available));
                while (skip--) available &= available - 1;
                const int code = __builtin_ctz(available);
                if (ONCE) transfer_options[a] &= ~(1U << code);
                eb = code % 15; new_color = code / 15;
                ++transfer_samples;
            } else eb = rng.mod(ne);
            if (ea == eb) return false;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
            if (new_color >= 0) pol = (pol & ~(1ULL << a)) | (u64(new_color) << a);
            else if (rng.next() & 1) pol ^= 1ULL << a;'''.replace('ONCE','true' if once else 'false')
    assert old in s
    s=s.replace(old,new)
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "transfer_rows = " << transfer_rows << "\\ntransfer_samples = " << transfer_samples << '\\n';
    stats.gobj_after = cur;''')
    return s

def diversity(s,weight=.005):
    s=s.replace('    std::vector<int> selected, candidate_selected;', '    std::vector<int> selected, candidate_selected;\n    std::vector<unsigned> matching_epoch(np, 0);')
    s=s.replace('selected = candidate_selected;', 'selected = candidate_selected;\n        for (int p : selected) matching_epoch[p] = epoch;')
    s=s.replace('double escape_floor = 1e30;', 'double escape_floor = 1e30, escape_min = 1e30, escape_merit = 1e30;')
    old='''    auto remember_escape = [&](double candidate) {
        if (candidate < escape_floor) {'''
    new='''    auto remember_escape = [&](double candidate) {
        if (memo_hit) return;
        int changed = 0;
        for (int p : candidate_selected) changed += matching_epoch[p] != epoch;
        const double merit = candidate - WEIGHT * changed;
        escape_min = std::min(escape_min, candidate);
        if (escape_floor > escape_min + 0.02 || (candidate <= escape_min + 0.02 && merit < escape_merit)) {
            escape_merit = merit;'''.replace('WEIGHT',str(weight))
    assert old in s
    s=s.replace(old,new)
    return s.replace('escape_floor = 1e30; escape_valid = false;', 'escape_floor = escape_min = escape_merit = 1e30; escape_valid = false;')

def transfer_priority(s,weight=4):
    s=transfer_sampler(s)
    s=s.replace('    std::array<uint32_t, 64> transfer_options{};', '    std::array<uint32_t, 64> transfer_options{};\n    std::array<std::array<unsigned char, 30>, 64> transfer_priority{};')
    s=s.replace('        uint32_t ones = 0, twos = 0, four = 0;', '        uint32_t ones = 0, twos = 0, four = 0;\n        std::array<uint32_t, 7> unknown{};')
    at='''            uint32_t bad = (pairs.au[p] >> a & 1) ? reverse | (forward << 15) : forward | (reverse << 15);'''
    s=s.replace(at,at+'''
            uint32_t incoming = ~(forward | reverse) & ((1U << 15) - 1);
            for (auto& digit : unknown) {
                const uint32_t carry = digit & incoming;
                digit ^= incoming; incoming = carry;
            }''')
    old='''        return (~four & ((1U << 30) - 1)) & ~((1U << ea) | (1U << (ea + 15)));'''
    s=s.replace(old,'''        for (int code = 0; code < 30; ++code) {
            const int edge = code % 15;
            int score = WEIGHT * (((ones >> code) & 1) + 2 * ((twos >> code) & 1));
            for (int digit = 0; digit < 7; ++digit) score += ((unknown[digit] >> edge) & 1) << digit;
            transfer_priority[a][code] = score;
        }
'''.replace('WEIGHT',str(weight))+old)
    old='''                if (!available) return false;
                int skip = rng.below(__builtin_popcount(available));'''
    new='''                if (!available) return false;
                int best_priority = 10000;
                uint32_t shortlist = 0;
                for (uint32_t q = available; q; q &= q - 1) {
                    const int code = __builtin_ctz(q), priority = transfer_priority[a][code];
                    if (priority < best_priority) { best_priority = priority; shortlist = 0; }
                    if (priority == best_priority) shortlist |= 1U << code;
                }
                available = shortlist;
                int skip = rng.below(__builtin_popcount(available));'''
    assert old in s
    return s.replace(old,new)


def fast_kind95():
    s=fast_draw(BASE)
    s=s.replace('const int kind = ((modes >> 32) * 10) >> 32;', 'const int kind_draw = ((modes >> 32) * 100) >> 32;\n        const int kind = kind_draw < 1 ? 0 : kind_draw < 5 ? 3 : 8;')
    return merge_cache(s)

def weighted_rows():
    s=sampler(kinds(BASE,1,4),0,True)
    old='            if (!available) {\n                mask[ea] = olda; pol = oldpol; ++screen_rejected;'
    new='            if (!available || rng.below(8) >= __builtin_popcountll(available)) {\n                mask[ea] = olda; pol = oldpol; ++screen_rejected;'
    assert old in s
    return s.replace(old,new)

def recipes():
    r={}
    for n in [16,32,64,128,256]: r[f'exact{n}']=lambda n=n:exact(BASE,n)
    for n in [16,64,256]: r[f'history{n}']=lambda n=n:history(BASE,n)
    for n in [0,2,4]: r[f'guided{n}']=lambda n=n:guided(BASE,n)
    for n in [0,4,8]: r[f'rescue{n}']=lambda n=n:rescue(BASE,n)
    for n in [2,8]: r[f'repair{n}']=lambda n=n:repair(BASE,n)
    r['repair-all']=lambda:repair(BASE,8,False)
    for n,b in [(2,.01),(4,.02),(4,.05)]:r[f'pool{n}-{int(b*1000)}']=lambda n=n,b=b:escape_pool(BASE,n,b)
    r['profile']=lambda:profile(BASE)
    for n in [30,45,80]:r[f'mix{n}']=lambda n=n:BASE.replace('kWindowRate = 0.6','kWindowRate = '+str(n/100))
    r.update(mul=lambda:rng_mul(BASE),merge=lambda:merge_cache(BASE),fast=lambda:fast_draw(BASE),continuous=lambda:continuous(BASE))
    r['mul-merge']=lambda:merge_cache(rng_mul(BASE));r['fast-merge']=lambda:merge_cache(fast_draw(BASE))
    for n in [128,256,512]:r[f'novel{n}']=lambda n=n:novelty(BASE,n)
    for name,f,e in [('kind60',10,30),('kind80',5,15),('kind95',1,4)]:r[name]=lambda f=f,e=e:kinds(BASE,f,e)
    for n in [1,2,4]:r[f'record{n}']=lambda n=n:record_threshold(BASE,n)
    for name,w,o in [('rows0',0,True),('rows64',64,True),('rows-repeat',64,False)]:r[name]=lambda w=w,o=o:sampler(BASE,w,o)
    for n in [.0025,.005,.01]:r[f'diverse{int(n*10000)}']=lambda n=n:diversity(BASE,n)
    r['fast-kind95']=fast_kind95;r['pool-kind95']=lambda:escape_pool(kinds(BASE,1,4),2,.01)
    r['record-kind95']=lambda:record_threshold(kinds(BASE,1,4),2)
    r['record-texact']=lambda:record_threshold(transfer_exact(BASE,12),2)
    r['transfer-once']=lambda:transfer_sampler(BASE);r['transfer-repeat']=lambda:transfer_sampler(BASE,False)
    r['transfer-kind80']=lambda:transfer_sampler(kinds(BASE))
    for n in [0,4,8]:r[f'tpriority{n}']=lambda n=n:transfer_priority(BASE,n)
    r['rows-kind95']=lambda:sampler(kinds(BASE,1,4),0,True)
    r['rows-kind95-30']=lambda:sampler(kinds(BASE,1,4),0,True).replace('kWindowRate = 0.6','kWindowRate = 0.3')
    r['rows-weighted']=weighted_rows
    for n in [360,720]:r[f'tslack{n}']=lambda n=n:priority_slack(BASE,n)
    for n in [12,14]:r[f'texact{n}']=lambda n=n:transfer_exact(BASE,n)
    return r


def transfer_exact(s,bits=12):
    s=transfer_priority(s,0)
    s=s.replace('std::array<std::array<unsigned char, 30>, 64> transfer_priority{};', 'std::array<std::array<int, 30>, 64> transfer_priority{};')
    at='    auto make_transfer_options ='
    add=f'''    constexpr int kPriorityBits = {bits};
    std::vector<uint32_t> priority_keys(1 << kPriorityBits, ~0U);
    std::vector<std::array<std::int16_t, 30>> priority_values(1 << kPriorityBits);
    long long priority_hits = 0, priority_misses = 0;
'''
    s=s.replace(at,add+at)
    s=s.replace('        std::array<uint32_t, 7> unknown{};', '        std::array<int, 30> added_cost{};')
    old='''            uint32_t incoming = ~(forward | reverse) & ((1U << 15) - 1);
            for (auto& digit : unknown) {
                const uint32_t carry = digit & incoming;
                digit ^= incoming; incoming = carry;
            }'''
    new='''            // Cache the exact increase of the generic-layer cost for each added arc.
            // Equal closures have equal costs, independent of the original arc set.
            const uint32_t closed = reverse | (forward << 16);
            const unsigned slot = ((closed ^ (closed >> 15)) * 0x9e3779b1U) >> (32 - kPriorityBits);
            if (priority_keys[slot] != closed) {
                ++priority_misses;
                const int before = relations.cost(closed);
                for (int e = 0; e < 15; ++e) {
                    const int lo = relations.cost(closed | fwd[e]);
                    const int hi = relations.cost(closed | rev[e]);
                    priority_values[slot][e] = lo ? lo - before : 0;
                    priority_values[slot][e + 15] = hi ? hi - before : 0;
                }
                priority_keys[slot] = closed;
            } else ++priority_hits;
            const auto& delta = priority_values[slot];
            const int color = (pairs.au[p] >> a) & 1;
            for (int e = 0; e < 15; ++e) {
                added_cost[e] += delta[e + 15 * color];
                added_cost[e + 15] += delta[e + 15 * (color ^ 1)];
            }'''
    assert old in s
    s=s.replace(old,new)
    a=s.index('        for (int code = 0; code < 30; ++code) {',s.index('    auto make_transfer_options ='))
    b=s.index('        return (~four',a)
    s=s[:a]+'''        for (int code = 0; code < 30; ++code) transfer_priority[a][code] = added_cost[code];
'''+s[b:]
    s=s.replace('int best_priority = 10000;', 'int best_priority = 1 << 30;')
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "priority_hits = " << priority_hits << "\\npriority_misses = " << priority_misses << '\\n';
    stats.gobj_after = cur;''')
    return s

def priority_slack(s,slack=360):
    s=transfer_exact(s,12)
    old="""                available = shortlist;
                int skip = rng.below(__builtin_popcount(available));"""
    new=f"""                shortlist = 0;
                for (uint32_t q = available; q; q &= q - 1) {{
                    const int code = __builtin_ctz(q);
                    if (transfer_priority[a][code] <= best_priority + {slack}) shortlist |= 1U << code;
                }}
                available = shortlist;
                int skip = rng.below(__builtin_popcount(available));"""
    assert old in s
    return s.replace(old,new)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('names',nargs='*');p.add_argument('--list',action='store_true')
    a=p.parse_args();r=recipes()
    if a.list: print('\n'.join(r))
    for name in a.names:
        if name not in r: p.error('unknown variant: '+name)
        (HERE/(name+'.cpp')).write_text(r[name]())
