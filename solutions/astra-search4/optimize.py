"""全対更新の書込みを遅らせる試作。variants.pyから呼ぶ。"""
def deferred(s, base):
    start=base.index('AVX2_TARGET int evaluate_move(')
    end=base.index('\n}\n',start)+2
    kernel=base[start:end]
    kernel=kernel.replace('AVX2_TARGET int evaluate_move(', '    auto evaluate_deferred = []<bool TwoEdges>(')
    kernel=kernel.replace('int* pending) {', 'int* pending) __attribute__((target("avx2,popcnt"))) {')
    kernel=kernel[:-1]+'};'
    kernel=kernel.replace('    int npending = 0;', '    int npending = 0, potential = 0;')
    kernel=kernel.replace('''            _mm256_storeu_si256((__m256i*)(ndir + p), r);
            const __m256i kept = _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i*)(prel + p)));
            _mm256_storeu_si256((__m256i*)(nrel + p), kept);''', '''            const __m256i kept = _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i*)(prel + p)));
            const int candidates = need | _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(kept, zero)));
            // Entries outside this candidate list are never read by matching_cost.
            // On acceptance the original dense evaluator rebuilds the complete state.
            if (need) _mm256_storeu_si256((__m256i*)(ndir + p), r);
            if (candidates) _mm256_storeu_si256((__m256i*)(nrel + p), kept);
            _mm256_storeu_si256((__m256i*)(valid + potential), _mm256_add_epi32(
                _mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[candidates].data())));
            potential += __builtin_popcount(candidates);''')
    a=kernel.index('    int nvalid = 0;')
    b=kernel.index('    return nvalid;',a)
    kernel=kernel[:a]+'''    int nvalid = 0;
    for (int k = 0; k < potential; ++k) {
        const int p = valid[k];
        if (nrel[p]) valid[nvalid++] = p;
    }
'''+kernel[b:]
    s=s.replace('    auto propose = [&](Move& mv) {',kernel+'\n    auto propose = [&](Move& mv) {',1)
    a=s.index('    auto propose = [&](Move& mv) {')
    b=s.index('    auto handles_after = ',a)
    s=s[:a]+s[a:b].replace('evaluate_move<', 'evaluate_deferred.template operator()<')+s[b:]
    s=s.replace('    auto apply_move = [&](const Move& mv) {\n        if (memo_hit) {', '    auto apply_move = [&](const Move& mv) {\n        {  // Deferred evaluation leaves invalid entries stale; rebuild on every acceptance.')
    return s

def buckets(s, filter_used):
    a=s.index('    auto matching_cost =',s.index('WindowStats assign_windows'))
    b=s.index('    // A move:',a)
    old=s[a:b]
    begin=old[:old.index('        std::array<int, 256> low{};')]
    function=begin+'''        std::array<int, 512> counts{}, ends{};
        int lo = 511, hi = 0, size = 0;
        for (int i = 0; i < nvalid; ++i) {
            const int p = valid[i];
            const int key = 1800 * __builtin_popcountll(pairs.diff[p] & handle_mask)
                          + 5 * int(rel[p] - 1) + full144[p];
            assert(key < (1 << 17));
            keyed[size++] = {uint32_t(key), p};
            const int bin = key >> 8;
            ++counts[bin]; lo = std::min(lo, bin); hi = std::max(hi, bin);
        }
        for (int i = lo, prefix = 0; i <= hi; ++i) {
            const int count = counts[i];
            counts[i] = prefix;
            prefix += count;
            ends[i] = prefix;
        }
        for (int i = 0; i < size; ++i) tmp[counts[keyed[i].key >> 8]++] = keyed[i];
        candidate_selected.clear();
        std::array<unsigned char, 256> used{};
        int matched = 0;
        long long total = 0;
        for (int bin = lo, first = 0; bin <= hi && matched < need; ++bin) {
            const int end = ends[bin];
            int count = 0;
            for (int i = first; i < end; ++i) {
                const int p = tmp[i].pair;
FILTER
                sorted[count++] = tmp[i];
            }
            first = end;
            // High bytes are already ordered. Sort only this small bucket; ties
            // retain the original pair order by using the pair index explicitly.
            std::sort(sorted.begin(), sorted.begin()+count, [](const KeyPair& a, const KeyPair& b) {
                return a.key < b.key || (a.key == b.key && a.pair < b.pair);
            });
            for (int i = 0; i < count; ++i) {
                const int p = sorted[i].pair, u = pairs.u[p], v = pairs.v[p];
                if (used[u] || used[v]) continue;
                used[u] = used[v] = 1;
                candidate_selected.push_back(p);
                total += sorted[i].key;
                if (++matched == need) break;
            }
        }
        return double(total) / (need * 3600) + (need - matched) * 10.0;
    };
'''.replace('FILTER','                if (used[pairs.u[p]] || used[pairs.v[p]]) continue;' if filter_used else '')
    return s[:a]+function+s[b:]

def tight(s):
    s=s.replace('    std::vector<unsigned> reject_epoch(kMemoSize, 0), pass_epoch(kMemoSize, 0);\n','')
    s=s.replace('if (reject_epoch[move_key] == epoch)', 'if (memo_epoch[move_key] == 2 * epoch)')
    s=s.replace('reject_epoch[move_key] = epoch;', 'memo_epoch[move_key] = 2 * epoch;')
    s=s.replace('        const bool checked = pass_epoch[move_key] == epoch;', '''        // One generation tag distinguishes rejection, exact objective, and unseen.
        memo_hit = memo_epoch[move_key] == 2 * epoch + 1;
        if (memo_hit) { memo_hits++; return true; }
        const bool checked = false;''')
    s=s.replace('''        pass_epoch[move_key] = epoch;
        memo_hit = memo_epoch[move_key] == epoch;
        if (memo_hit) { memo_hits++; return true; }
''','')
    s=s.replace('memo_epoch[move_key] = epoch;', 'memo_epoch[move_key] = 2 * epoch + 1;')
    s=s.replace('    auto propose = [&](Move& mv) {', '''    // The normal 36/28 split uses constant divisors; fallback dimensions keep
    // the original remainder mapping, so fixed-iteration trajectories are identical.
    auto generic_index = [&] { const u64 x = rng.next(); return int(g == 36 ? x % 36 : x % g); };
    auto handle_index = [&] { const u64 x = rng.next(); return int(g == 36 ? x % 28 : x % (64-g)); };
    auto propose = [&](Move& mv) {''')
    s=s.replace('rng.mod(g)', 'generic_index()').replace('rng.mod(64 - g)', 'handle_index()')
    return s

def lazypriority(s):
    start=s.index('    auto make_transfer_options =')
    end=s.index('    auto propose =',start)
    # Preserve constant-modulus helpers inserted by tight().
    helper=s.find('    // The normal 36/28 split',start,end)
    if helper>=0:end=helper
    old=s[start:end]
    cost_start=old.index('            // Cache the exact increase')
    cost_end=old.index('            // Parallel saturating counters',cost_start)
    costs=old[cost_start:cost_end]
    costs=costs.replace('const int color = (pairs.au[p] >> a) & 1;', 'const int color = saved[i].color;')
    new='''    long long transfer_empty = 0, transfer_single = 0, transfer_many = 0;
    auto make_transfer_options = [&](int a, int ea) __attribute__((target("avx2,bmi2,popcnt"))) {
        uint32_t ones = 0, twos = 0, four = 0;
        const uint32_t allowed = ((1U << 30)-1) & ~((1U << ea) | (1U << (ea+15)));
        struct Saved { u64 closure; uint32_t forward, reverse; int color; };
        std::array<Saved, 70> saved;
        int size = 0;
        const u64 rest = mask[ea] & ~(1ULL << a);
        const uint32_t keep = ~(fwd[ea] | rev[ea]);
        for (int p : selected) {
            if (!(pairs.diff[p] >> a & 1)) continue;
            const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & keep;
            if (q & ~z) r |= fwd[ea];
            if (q & z) r |= rev[ea];
            const u64 c = closure(r);
            uint32_t forward = _pext_u64(c, 0x0000010101010100ULL)
                             | (_pext_u64(c, 0x0000020202020000ULL) << 5)
                             | (_pext_u64(c, 0x0000040404000000ULL) << 9)
                             | (_pext_u64(c, 0x0000080800000000ULL) << 12)
                             | (((c >> 44) & 1) << 14);
            uint32_t reverse = _pext_u64(c, 0x00002030383c3eULL);
            const int color = (pairs.au[p] >> a) & 1;
            const uint32_t bad = color ? reverse | (forward << 15) : forward | (reverse << 15);
            saved[size++] = {c, forward, reverse, color};
            const uint32_t carry = ones & bad;
            ones ^= bad; four |= twos & carry; twos ^= carry;
            // Once every destination has lost four pairs, later pairs cannot rescue it.
            if (!(allowed & ~four)) { ++transfer_empty; return 0U; }
        }
        const uint32_t available = allowed & ~four;
        if (!(available & (available-1))) {
            // With one destination there is no ranking to compute.
            transfer_priority[a][__builtin_ctz(available)] = 0;
            ++transfer_single;
            return available;
        }
        ++transfer_many;
        alignas(32) std::array<int, 32> added_cost{};
        for (int i = 0; i < size; ++i) {
            const u64 c = saved[i].closure;
            const uint32_t forward = saved[i].forward, reverse = saved[i].reverse;
COSTS
        }
        for (int code = 0; code < 30; ++code) transfer_priority[a][code] = added_cost[code + (code >= 15)];
        return available;
    };
'''.replace('COSTS',costs)
    s=s[:start]+new+s[end:]
    s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "transfer_empty = " << transfer_empty << "\\ntransfer_single = " << transfer_single
              << "\\ntransfer_many = " << transfer_many << '\\n';
    stats.gobj_after = cur;''')
    return s

def directpriority(s):
    a=s.index('        alignas(32) std::array<int, 32> added_cost{};',s.index('    long long transfer_empty'))
    b=s.index('        return available;',a)
    new='''        // Compute only the destinations surviving the loss screen.
        for (uint32_t options = available; options; options &= options-1) {
            const int code = __builtin_ctz(options), e = code % 15;
            int cost = 0;
            for (int i = 0; i < size; ++i) {
                if ((saved[i].forward | saved[i].reverse) >> e & 1) continue;
                auto [x,y] = ep[e];
                if ((code / 15) ^ saved[i].color) std::swap(x,y);
                const u64 c = saved[i].closure;
                const u64 from = ((c >> x) & 0x010101010101ULL) | (1ULL << (8*x));
                const u64 to = ((c >> (8*y)) & 63) | (1ULL << y);
                cost += sums.both_of(c | (from*to)) - sums.both_of(c);
            }
            transfer_priority[a][code] = cost;
        }
'''
    return s[:a]+new+s[b:]

def noisyescape(s, noise):
    s=s.replace('    double escape_floor = 1e30;', '    double escape_floor = 1e30, escape_rank = 1e30;')
    s=s.replace('''        if (candidate < escape_floor) {
            escape_floor = candidate;''', f'''        // Deterministic perturbation changes only the choice at stagnation.
        u64 h = (u64(epoch) << 32) | unsigned(move_key);
        h ^= h >> 27; h *= 0x3c79ac492ba7b653ULL; h ^= h >> 33;
        const double rank = candidate - {noise} * ((h >> 11) * 0x1.0p-53);
        if (rank < escape_rank) {{
            escape_rank = rank;
            escape_floor = candidate;''')
    s=s.replace('escape_floor = 1e30; escape_valid = false;', 'escape_floor = escape_rank = 1e30; escape_valid = false;')
    return s

def rescue(s, rate):
    s=s.replace('    auto propose = [&](Move& mv) {', f'''    auto propose = [&](Move& mv) {{
        const bool rescue = (rng.next() & {rate-1}) == 0;
        const int loss_limit = kRejectLoss + (rescue ? 2 : 0);''')
    s=s.replace('if (memo_epoch[move_key] == 2 * epoch)', 'if (!rescue && memo_epoch[move_key] == 2 * epoch)')
    s=s.replace('swap_losses(mv) >= kRejectLoss', 'swap_losses(mv) >= loss_limit')
    s=s.replace('++lost >= kRejectLoss', '++lost >= loss_limit')
    return s

def nearpriority(s, margin):
    start=s.index('                int best_priority = 1 << 30;')
    end=s.index('                available = shortlist;',start)
    replacement=f'''                int best_priority = 1 << 30;
                for (uint32_t q = available; q; q &= q-1)
                    best_priority = std::min(best_priority, transfer_priority[a][__builtin_ctz(q)]);
                uint32_t shortlist = 0;
                for (uint32_t q = available; q; q &= q-1) {{
                    const int code = __builtin_ctz(q);
                    if (transfer_priority[a][code] <= best_priority + {margin}) shortlist |= 1U << code;
                }}
'''
    return s[:start]+replacement+s[end:]

def losslimit(s, limit):
    s=s.replace('kRejectLoss = 4,',f'kRejectLoss = {limit},')
    s=s.replace('uint32_t ones = 0, twos = 0, four = 0;', 'uint32_t ones = 0, twos = 0, four = 0, eight = 0;')
    s=s.replace('''            four |= twos & carry;
            twos ^= carry;''', '''            const uint32_t carry2 = twos & carry;
            twos ^= carry;
            eight |= four & carry2;
            four ^= carry2;''')
    rejected={3:'eight | four | (twos & ones)',5:'eight | (four & (ones | twos))',6:'eight | (four & twos)'}[limit]
    s=s.replace('ones ^= bad; four |= twos & carry; twos ^= carry;', 'ones ^= bad; const uint32_t carry2 = twos & carry; twos ^= carry; eight |= four & carry2; four ^= carry2;')
    s=s.replace('allowed & ~four', 'allowed & ~(' + rejected + ')')
    s=s.replace('        return (~four & ((1U << 30) - 1))',f'        const uint32_t rejected = {rejected};\n        return (~rejected & ((1U << 30) - 1))')
    return s

def phaseloss(s, first, last, fraction):
    s=losslimit(s,6)
    s=s.replace('    WindowStats stats;',f'    WindowStats stats;\n    int loss_limit = {first};\n    double phase_progress = 0;',1)
    s=s.replace('>= kRejectLoss', '>= loss_limit')
    s=s.replace('const uint32_t rejected = eight | (four & twos);', 'const uint32_t rejected = loss_limit == 3 ? eight | four | (twos & ones) : loss_limit == 4 ? eight | four : eight | (four & twos);')
    s=s.replace('''        ++epoch;
        selected = candidate_selected;''',f'''        ++epoch;
        loss_limit = phase_progress < {fraction} ? {first} : {last};
        selected = candidate_selected;''',1)
    needle='        double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;'
    s=s.replace(needle,needle+'\n        phase_progress = progress;',1)
    s=s.replace('    stats.gobj_before = cur;',f'    phase_progress = 1; loss_limit = {last};\n    stats.gobj_before = cur;',1)
    return s
