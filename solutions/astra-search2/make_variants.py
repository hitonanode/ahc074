from pathlib import Path
H=Path(__file__).resolve().parent
base=(H.parent/'astra-search/main.cpp').read_text()
# Structural rescue for single-window swaps: retain original matching and new edges on unused vertices.
s=base.replace('    auto propose = [&](Move& mv) {',r'''
    long long rescue_checks = 0, rescued = 0;
    unsigned rescue_epoch = 0;
    std::vector<KeyPair> rescue_pool;
    std::vector<int> selected_keys;
    int marginal_key = 0;
    auto rescue_swap = [&](const Move& mv, int lost) __attribute__((target("popcnt"))) {
        if (lost > 6) return false;
        if (rescue_epoch != epoch) {
            rescue_epoch = epoch;
            std::array<unsigned char, 256> used{};
            selected_keys.clear();
            marginal_key = 0;
            for (int p : selected) {
                used[pairs.u[p]] = used[pairs.v[p]] = 1;
                int key = 2340 * __builtin_popcountll(pairs.diff[p] & hm) + 5 * (pairs.rel[p] - 1) + full144[p];
                selected_keys.push_back(key);
                marginal_key = std::max(marginal_key, key);
            }
            rescue_pool.clear();
            for (int p = 0; p < np; ++p) {
                if (used[pairs.u[p]] || used[pairs.v[p]] || pairs.rel[p]) continue;
                const int key = 2340 * __builtin_popcountll(pairs.diff[p] & hm) + full144[p];
                if (key + 12000 < marginal_key) rescue_pool.push_back({uint32_t(key), p});
            }
            auto less = [](const KeyPair& a, const KeyPair& b) { return a.key < b.key || (a.key == b.key && a.pair < b.pair); };
            if (rescue_pool.size() > 48) {
                std::nth_element(rescue_pool.begin(), rescue_pool.begin() + 48, rescue_pool.end(), less);
                rescue_pool.resize(48);
            }
            std::sort(rescue_pool.begin(), rescue_pool.end(), less);
        }
        ++rescue_checks;
        const int c = (pol >> mv.b) & 1;
        int deficit = lost * marginal_key;
        for (int w = 0; w < 2; ++w) {
            u64 bits = (match_colors[mv.b][c][w] & forbidden[mv.a][0][w]) |
                       (match_colors[mv.b][c ^ 1][w] & forbidden[mv.a][1][w]);
            for (; bits; bits &= bits - 1) deficit -= selected_keys[w * 64 + __builtin_ctzll(bits)];
        }
        // The cheap estimate only gates work; the exact original objective decides acceptance.
        const int e = mv.ea;
        const uint32_t keep = uint32_t(~(fwd[e] | rev[e]));
        const u64 nh = hm ^ (1ULL << mv.a) ^ (1ULL << mv.b);
        std::array<unsigned char, 256> used{};
        int gain = 0;
        for (auto item : rescue_pool) {
            const int p = item.pair, u = pairs.u[p], v = pairs.v[p];
            if (used[u] || used[v]) continue;
            if (!(pairs.diff[p] >> mv.a & 1)) continue;
            uint32_t r = pairs.dir[p] & keep;
            if (r & (r >> 16)) continue;
            const u64 q = pairs.diff[p] & mask[e], z = pairs.au[p] ^ pol;
            if (q & ~z) r |= fwd[e];
            if (q & z) r |= rev[e];
            const int rel = relations.cost(r);
            if (!rel) continue;
            int key = 2340 * __builtin_popcountll(pairs.diff[p] & nh) + 5 * (rel - 1) + full144[p];
            if (key >= marginal_key) continue;
            used[u] = used[v] = 1;
            gain += marginal_key - key;
            if (gain + 3000 >= deficit) { ++rescued; return true; }
        }
        return false;
    };
    auto propose = [&](Move& mv) {''')
s=s.replace('if (swap_losses(mv) >= kRejectLoss) {','const int lost = swap_losses(mv);\n            if (lost >= kRejectLoss && !rescue_swap(mv, lost)) {')
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "rescue_checks = " << rescue_checks << "\\nrescued = " << rescued << \'\\n\';\n    stats.gobj_after = cur;')
(H/'rescue.cpp').write_text(s)
# Broader neighborhoods: pair of polarity flips on any two generic windows.
s=base.replace('u64 olda, oldb, oldpol;', 'u64 olda, oldb, oldpol;\n        bool double_flip = false;')
s=s.replace('    auto propose = [&](Move& mv) {', '    long long double_tried = 0, double_accepted = 0;\n    auto propose = [&](Move& mv) {')
s=s.replace('        bool swindow = rng.real() < kWindowRate;', '        const bool double_flip = (rng.next() & 15) == 0;\n        bool swindow = !double_flip && rng.real() < kWindowRate;')
s=s.replace('        if (swindow) {  // generic window a <-> handle window b', '''        if (double_flip) {
            if (a == b) return false;
            pol ^= (1ULL << a) | (1ULL << b);
            kind = 10;
            ++double_tried;
        } else if (swindow) {  // generic window a <-> handle window b''')
s=s.replace('        // Keys distinguish', '        mv.double_flip = double_flip;\n        // Keys distinguish')
s=s.replace('        if (swindow) move_key', '        if (double_flip) move_key = 14400 + 64 * std::min(a,b) + std::max(a,b);\n        else if (swindow) move_key')
s=s.replace('kMemoSize = 1 << 14','kMemoSize = 1 << 15')
s=s.replace('        accepted++;','        accepted++;\n        double_accepted += mv.double_flip;')
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "double_tried = " << double_tried << "\\ndouble_accepted = " << double_accepted << \'\\n\';\n    stats.gobj_after = cur;')
(H/'double.cpp').write_text(s)
# Two polarity changes chosen to repair the cycle of a cheap, currently incompatible pair.
s=(H/'double.cpp').read_text()
s=s.replace('    auto propose = [&](Move& mv) {',r'''
    unsigned target_epoch = 0;
    std::vector<KeyPair> target_pool;
    long long guide_repaired = 0;
    auto guide_flips = [&](int& ia, int& ib, int& a, int& b) __attribute__((target("popcnt"))) {
        if (target_epoch != epoch) {
            target_epoch = epoch;
            std::array<unsigned char, 256> used{};
            for (int p : selected) used[pairs.u[p]] = used[pairs.v[p]] = 1;
            target_pool.clear();
            for (int p = 0; p < np; ++p) {
                if (pairs.rel[p] || used[pairs.u[p]] || used[pairs.v[p]]) continue;
                if (__builtin_popcount(pairs.dir[p] & (pairs.dir[p] >> 16)) > 2) continue;
                const int key = 2340 * __builtin_popcountll(pairs.diff[p] & hm) + full144[p];
                target_pool.push_back({uint32_t(key), p});
            }
            auto less = [](const KeyPair& a, const KeyPair& b) { return a.key < b.key || (a.key == b.key && a.pair < b.pair); };
            if (target_pool.size() > 96) {
                std::nth_element(target_pool.begin(), target_pool.begin()+96, target_pool.end(), less);
                target_pool.resize(96);
            }
        }
        if (target_pool.empty()) return false;
        const int p = target_pool[rng.mod(target_pool.size())].pair;
        const u64 cyc = closure(pairs.dir[p]);
        u64 options = 0;
        for (u64 q = pairs.diff[p] & ~hm; q; q &= q - 1) {
            const int j = __builtin_ctzll(q);
            auto [x,y] = ep[which[j]];
            if (((pairs.au[p] ^ pol) >> j) & 1) std::swap(x,y);
            if ((cyc >> (8*y+x)) & 1) options |= 1ULL << j;
        }
        if (!options) return false;
        int skip = rng.mod(__builtin_popcountll(options));
        while (skip--) options &= options - 1;
        a = __builtin_ctzll(options);
        const int ea = which[a];
        u64 z = pairs.au[p] ^ pol ^ (1ULL << a);
        uint32_t ra = pairs.dir[p] & uint32_t(~(fwd[ea] | rev[ea]));
        u64 q = pairs.diff[p] & mask[ea];
        if (q & ~z) ra |= fwd[ea];
        if (q & z) ra |= rev[ea];
        int choices = 0;
        for (u64 bs = (pairs.diff[p] & ~hm) & ~(1ULL << a); bs; bs &= bs-1) {
            const int j = __builtin_ctzll(bs), eb = which[j];
            const u64 zz = z ^ (1ULL << j), qq = pairs.diff[p] & mask[eb];
            uint32_t r = ra & uint32_t(~(fwd[eb] | rev[eb]));
            if (qq & ~zz) r |= fwd[eb];
            if (qq & zz) r |= rev[eb];
            if ((r & (r >> 16)) || (closure(r) & kDiagonal)) continue;
            if (rng.mod(++choices) == 0) b = j;
        }
        if (!choices) return false;
        ia = int(std::find(order.begin(), order.begin()+g, a) - order.begin());
        ib = int(std::find(order.begin(), order.begin()+g, b) - order.begin());
        ++guide_repaired;
        return true;
    };
    auto propose = [&](Move& mv) {''')
s=s.replace('        bool swindow = !double_flip', '        if (double_flip && !guide_flips(ia, ib, a, b)) return false;\n        bool swindow = !double_flip')
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "guide_repaired = " << guide_repaired << \'\\n\';\n    stats.gobj_after = cur;')
(H/'guided.cpp').write_text(s)
# Weight destroyed selected pairs by their deficit from the last selected edge.
s=base.replace('    auto propose = [&](Move& mv) {',r'''
    unsigned price_epoch = 0;
    std::vector<int> loss_prices;
    int loss_budget = 0;
    long long weighted_rescued = 0, weighted_rejected = 0;
    auto weighted_loss = [&](const Move& mv, int lost) {
        if (lost <= 1) return false;
        if (lost >= 8) return true;
        if (price_epoch != epoch) {
            price_epoch = epoch;
            loss_prices.clear();
            int last = 0, sum = 0;
            for (int p : selected) {
                const int key = 2340 * __builtin_popcountll(pairs.diff[p] & hm) + 5 * (pairs.rel[p]-1) + full144[p];
                loss_prices.push_back(key);
                last = std::max(last, key);
                sum += key;
            }
            for (int& key : loss_prices) key = last - key + 3000;
            loss_budget = 4 * (last - sum / need + 3000);
        }
        const int c = (pol >> mv.b) & 1;
        int price = 0;
        for (int w = 0; w < 2; ++w) {
            u64 bits = (match_colors[mv.b][c][w] & forbidden[mv.a][0][w]) |
                       (match_colors[mv.b][c ^ 1][w] & forbidden[mv.a][1][w]);
            for (; bits; bits &= bits - 1) price += loss_prices[w * 64 + __builtin_ctzll(bits)];
        }
        const bool reject = price >= loss_budget;
        weighted_rescued += !reject && lost >= kRejectLoss;
        weighted_rejected += reject && lost < kRejectLoss;
        return reject;
    };
    auto propose = [&](Move& mv) {''')
s=s.replace('if (swap_losses(mv) >= kRejectLoss)', 'if (weighted_loss(mv, swap_losses(mv)))')
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "weighted_rescued = " << weighted_rescued << "\\nweighted_rejected = " << weighted_rejected << \'\\n\';\n    stats.gobj_after = cur;')
(H/'weighted.cpp').write_text(s)
# The number of accepted states and evaluated neighbors matters more than random-cache-hit attempts.
# Compare slower cooling (same time boundaries and same objective) after the new screen changed the landscape.
for name,end in [('warm',0.005),('hot',0.01)]:
 s=base.replace('0.05 * std::pow(0.00125 / 0.05, progress)',f'0.05 * std::pow({end} / 0.05, progress)')
 (H/(name+'.cpp')).write_text(s)
# Repair an initially rejected swap by a second swap. Enumerate secondary removals and use
# forbidden-direction bitsets to test all insertions at once, preserving at least 67 selected pairs.
s=base.replace('u64 olda, oldb, oldpol;', 'u64 olda, oldb, oldpol;\n        int ic = -1, id = -1, c = -1, d = -1;')
s=s.replace('    auto propose = [&](Move& mv) {',r'''
    long long repair_tried = 0, repair_found = 0, repair_accepted = 0;
    auto repair_swap = [&](Move& mv, int lost) __attribute__((target("popcnt"))) {
        if (lost < 4 || lost > 8) return false;
        ++repair_tried;
        const int ea = mv.ea;
        int best_c = -1, best_d = -1, best_color = 0;
        double best_rank = 1e9;
        for (int ic = 0; ic < g; ++ic) {
            const int c = order[ic], ec = which[c];
            if (c == mv.a) continue;
            const u64 mc = mask[ec] & ~(1ULL << c);
            const u64 ma = ec == ea ? mc : mask[ea];
            const uint32_t keep = uint32_t(~(fwd[ea] | rev[ea] | fwd[ec] | rev[ec]));
            Bits invalid{};
            Colors ban{};
            int invalid_count = 0;
            const auto [x,y] = ep[ec];
            for (int i = 0; i < int(selected.size()); ++i) {
                const int p = selected[i];
                const u64 z = pairs.au[p] ^ pol, qa = pairs.diff[p] & ma, qc = pairs.diff[p] & mc;
                uint32_t r = pairs.dir[p] & keep;
                if (qa & ~z) r |= fwd[ea];
                if (qa & z) r |= rev[ea];
                if (qc & ~z) r |= fwd[ec];
                if (qc & z) r |= rev[ec];
                const u64 closed = closure(r);
                if (closed & kDiagonal) {
                    invalid[i>>6] |= 1ULL << (i&63);
                    if (++invalid_count >= kRejectLoss) break;
                } else {
                    if ((closed >> (8*y+x)) & 1) ban[0][i>>6] |= 1ULL << (i&63);
                    if ((closed >> (8*x+y)) & 1) ban[1][i>>6] |= 1ULL << (i&63);
                }
            }
            if (invalid_count >= kRejectLoss) continue;
            const int dc = __builtin_popcountll(match_colors[c][0][0] | match_colors[c][1][0]) +
                           __builtin_popcountll(match_colors[c][0][1] | match_colors[c][1][1]);
            for (int id = g; id < 64; ++id) {
                const int d = order[id];
                if (d == mv.b) continue;
                const int dd = __builtin_popcountll(match_colors[d][0][0] | match_colors[d][1][0]) +
                               __builtin_popcountll(match_colors[d][0][1] | match_colors[d][1][1]);
                for (int color = 0; color < 2; ++color) {
                    int loss = invalid_count;
                    for (int w = 0; w < 2; ++w)
                        loss += __builtin_popcountll((match_colors[d][color][w] & ban[0][w]) |
                                                     (match_colors[d][color^1][w] & ban[1][w]));
                    if (loss >= kRejectLoss) continue;
                    const double rank = 2.0 * loss + 0.3 * (dc - dd) + rng.real() * 3.0;
                    if (rank < best_rank) {
                        best_rank = rank;
                        best_c = ic; best_d = id; best_color = color;
                    }
                }
            }
        }
        if (best_c < 0) return false;
        mv.ic = best_c; mv.id = best_d;
        mv.c = order[best_c]; mv.d = order[best_d];
        mv.eb = which[mv.c];
        mv.oldb = mv.eb == mv.ea ? mv.olda : mask[mv.eb];
        mask[mv.eb] ^= (1ULL << mv.c) | (1ULL << mv.d);
        pol = (pol & ~(1ULL << mv.d)) | (u64(best_color) << mv.d);
        ++repair_found;
        // A compound candidate gets a private, immediately invalidated cache slot.
        move_key = kMemoSize - 1;
        memo_epoch[move_key] = pass_epoch[move_key] = reject_epoch[move_key] = 0;
        return true;
    };
    auto propose = [&](Move& mv) {''')
s=s.replace('        if (reject_epoch[move_key] == epoch) {', '''        const bool want_repair = swindow && ((rng.next() & 63) == 0);
        if (!want_repair && reject_epoch[move_key] == epoch) {''')
s=s.replace('            if (swap_losses(mv) >= kRejectLoss) {', '''            const int lost = swap_losses(mv);
            if (lost >= kRejectLoss && !(want_repair && repair_swap(mv, lost))) {''')
# After repair, local eb has changed too. Undo uses Move's old fields; failed repair never mutates them.
s=s.replace('        pass_epoch[move_key] = epoch;', '        ea = mv.ea; eb = mv.eb;\n        pass_epoch[move_key] = epoch;')
s=s.replace('return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0);', 'return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0) ^ (mv.ic >= 0 ? (1ULL << mv.c) | (1ULL << mv.d) : 0);')
s=s.replace('        accepted++;', '        accepted++;\n        repair_accepted += mv.ic >= 0;')
s=s.replace('            hm = handles_after(mv);', '''            if (mv.ic >= 0) {
                which[mv.c] = -1;
                which[mv.d] = mv.eb;
                std::swap(order[mv.ic], order[mv.id]);
            }
            hm = handles_after(mv);''')
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "repair_tried = " << repair_tried << "\\nrepair_found = " << repair_found << "\\nrepair_accepted = " << repair_accepted << \'\\n\';\n    stats.gobj_after = cur;')
(H/'repair.cpp').write_text(s)
s=(H/'repair.cpp').read_text()
s=s.replace('    auto propose = [&](Move& mv) {', '    unsigned proposal_epoch = 0;\n    int idle_proposals = 0;\n    auto propose = [&](Move& mv) {\n        if (proposal_epoch != epoch) { proposal_epoch = epoch; idle_proposals = 0; }\n        ++idle_proposals;')
s=s.replace('const bool want_repair = swindow && ((rng.next() & 63) == 0);', 'const bool want_repair = swindow && idle_proposals >= 256 && ((rng.next() & 31) == 0);')
(H/'repair-late.cpp').write_text(s)
# Generic-to-generic edge swaps can simultaneously choose both color orientations.
s=base.replace('kMemoSize = 1 << 14', 'kMemoSize = 1 << 15')
s=s.replace('            mask[eb] ^= (1ULL << a) | (1ULL << b);', '''            mask[eb] ^= (1ULL << a) | (1ULL << b);
            const u64 flips = rng.next();
            pol ^= ((flips & 1) << a) | (((flips >> 1) & 1) << b);''')
s=s.replace('else if (kind < 8) move_key = 8256 + 64 * std::min(a, b) + std::max(a, b);', '''else if (kind < 8) {
            const int lo = std::min(a, b), hi = std::max(a,b);
            move_key = 8256 + 4 * (64 * lo + hi) + ((pol >> lo) & 1) + 2 * ((pol >> hi) & 1);
        }''')
s=s.replace('move_key = 12352 +', 'move_key = 24640 +')
(H/'swap-color.cpp').write_text(s)
(H/'swap-warm.cpp').write_text(s.replace('0.05 * std::pow(0.00125 / 0.05, progress)', '0.05 * std::pow(0.005 / 0.05, progress)'))
# Escape a thoroughly sampled neighborhood via its least costly observed non-tabu uphill edge.
# Tabu applies to immediate inverses for four accepted states; a new best overrides it.
s=base.replace('    for (int it = 0;; it++) {\n        if ((it & 15)', '''    std::vector<unsigned> tabu_epoch(kMemoSize, 0);
    int last_accept_it = 0;
    double escape_floor = 1e30;
    long long forced_steps = 0, tabu_skips = 0;
    for (int it = 0;; it++) {
        if ((it & 15)''',1)
s=s.replace('        if (candidate <= cur || rng.real() < std::exp((cur - candidate) / temp)) {', '''        if (tabu_epoch[move_key] > epoch && candidate >= best - 1e-9) {
            ++tabu_skips;
            undo_move(mv);
            continue;
        }
        escape_floor = std::min(escape_floor, candidate);
        const bool force = it - last_accept_it >= 8192 && candidate <= escape_floor + 1e-9;
        if (candidate <= cur || force || rng.real() < std::exp((cur - candidate) / temp)) {
            forced_steps += force && candidate > cur;
            int reverse_key = move_key;
            if (mv.swindow) reverse_key = 2 * (64 * mv.b + mv.a) + ((mv.oldpol >> mv.a) & 1);
            else if (mv.transfer >= 0) reverse_key = 12352 + 2 * (ne * mv.a + mv.ea) + ((mv.oldpol >> mv.a) & 1);
            tabu_epoch[reverse_key] = epoch + 5;
            last_accept_it = it;
            escape_floor = 1e30;''',1)
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "forced_steps = " << forced_steps << "\\ntabu_skips = " << tabu_skips << \'\\n\';\n    stats.gobj_after = cur;')
(H/'escape.cpp').write_text(s)
(H/'escape-warm.cpp').write_text(s.replace('0.05 * std::pow(0.00125 / 0.05, progress)', '0.05 * std::pow(0.005 / 0.05, progress)'))
(H/'tabu-warm.cpp').write_text(s.replace('0.05 * std::pow(0.00125 / 0.05, progress)', '0.05 * std::pow(0.005 / 0.05, progress)').replace('const bool force = it - last_accept_it >= 8192 && candidate <= escape_floor + 1e-9;', 'const bool force = false;'))
# Continue the same tabu neighborhood walk in the final 0.11 seconds, retaining its best state.
s=(H/'escape-warm.cpp').read_text()
s=s.replace('    stats.gobj_before = cur;', '''    stats.gobj_before = cur;
    best = cur; best_mask = mask; best_pol = pol; best_order = order;
    std::fill(tabu_epoch.begin(), tabu_epoch.end(), 0);
    escape_floor = 1e30;
    last_accept_it = 0;
    long long climb_forced_steps = 0;''')
s=s.replace('            if (candidate <= cur) {\n                apply_move(mv);\n                cur = candidate;', '''            if (tabu_epoch[move_key] > epoch && candidate >= best - 1e-9) {
                ++tabu_skips;
                undo_move(mv);
                continue;
            }
            escape_floor = std::min(escape_floor, candidate);
            const bool force = it - last_accept_it >= 4096 && candidate <= escape_floor + 1e-9;
            if (candidate <= cur || force) {
                climb_forced_steps += force && candidate > cur;
                int reverse_key = move_key;
                if (mv.swindow) reverse_key = 2 * (64 * mv.b + mv.a) + ((mv.oldpol >> mv.a) & 1);
                else if (mv.transfer >= 0) reverse_key = 12352 + 2 * (ne * mv.a + mv.ea) + ((mv.oldpol >> mv.a) & 1);
                tabu_epoch[reverse_key] = epoch + 5;
                last_accept_it = it;
                escape_floor = 1e30;
                apply_move(mv);
                cur = candidate;
                if (cur < best - 1e-9) {
                    best = cur; best_mask = mask; best_pol = pol; best_order = order;
                }''')
s=s.replace('    std::cerr << "search_accept = "', '''    mask = best_mask; pol = best_pol; order = best_order; cur = best;
    std::cerr << "climb_forced_steps = " << climb_forced_steps << '\\n';
    std::cerr << "search_accept = "''')
(H/'tabu-climb.cpp').write_text(s)
s=(H/'tabu-climb.cpp').read_text().replace('0.05 * std::pow(0.005 / 0.05, progress)', '0.05 * std::pow(0.00125 / 0.05, progress)')
(H/'tabu-climb-cold.cpp').write_text(s)
s=(H/'escape.cpp').read_text()
(H/'escape-fast.cpp').write_text(s.replace('it - last_accept_it >= 8192', 'it - last_accept_it >= 2048'))
(H/'escape-slow.cpp').write_text(s.replace('it - last_accept_it >= 8192', 'it - last_accept_it >= 32768'))
s=(H/'tabu-climb-cold.cpp').read_text().replace('it - last_accept_it >= 8192', 'it - last_accept_it >= 2048')
(H/'fast-climb.cpp').write_text(s)
(H/'fast-climb-tabu.cpp').write_text(s.replace('epoch + 5', 'epoch + 17'))
(H/'quick-climb.cpp').write_text(s.replace('it - last_accept_it >= 2048', 'it - last_accept_it >= 512').replace('it - last_accept_it >= 4096', 'it - last_accept_it >= 1024'))
# When stalled, install the best observed neighbor directly rather than waiting to draw it again.
s=(H/'fast-climb.cpp').read_text()
s=s.replace('    double escape_floor = 1e30;', '''    double escape_floor = 1e30;
    Move escape_move{};
    u64 escape_ma = 0, escape_mb = 0, escape_pol = 0;
    int escape_key = 0;
    bool escape_valid = false;
    long long direct_steps = 0;
    auto remember_escape = [&](double candidate) {
        if (candidate < escape_floor) {
            escape_floor = candidate;
            escape_move = mv; escape_key = move_key;
            escape_ma = mask[mv.ea]; escape_mb = mask[mv.eb]; escape_pol = pol;
            escape_valid = true;
        }
    };
    auto install_escape = [&] {
        mv = escape_move; move_key = escape_key;
        mask[mv.ea] = escape_ma; mask[mv.eb] = escape_mb; pol = escape_pol;
        memo_hit = true; ++memo_hits; ++direct_steps;
    };''',1)
s=s.replace('        escape_floor = std::min(escape_floor, candidate);','        remember_escape(candidate);')
s=s.replace('            escape_floor = 1e30;', '            escape_floor = 1e30; escape_valid = false;')
s=s.replace('    escape_floor = 1e30;\n    last_accept_it = 0;', '    escape_floor = 1e30; escape_valid = false;\n    last_accept_it = 0;')
s=s.replace('        if (!propose(mv)) continue;', '''        if (it - last_accept_it >= 2048 && escape_valid) install_escape();
        else if (!propose(mv)) continue;''',1)
s=s.replace('            if (!propose(mv)) continue;', '''            if (it - last_accept_it >= 4096 && escape_valid) install_escape();
            else if (!propose(mv)) continue;''',1)
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "direct_steps = " << direct_steps << \'\\n\';\n    stats.gobj_after = cur;')
(H/'direct.cpp').write_text(s)
s=(H/'fast-climb.cpp').read_text().replace('it - last_accept_it >= 4096', 'it - last_accept_it >= 1024')
(H/'fast-quick-climb.cpp').write_text(s)
s=(H/'direct.cpp').read_text()
s=s.replace('        if (it - last_accept_it >= 2048 && escape_valid) install_escape();\n        else if (!propose(mv)) continue;', '        if (!propose(mv)) continue;',1)
s=s.replace('it - last_accept_it >= 4096', 'it - last_accept_it >= 1024')
(H/'direct-climb.cpp').write_text(s)
