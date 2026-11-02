"""近くの状態で繰り返し現れる同じ割り当ての厳密目的値を再利用する。"""
def globalmemo(t,bits):
    needle='    auto propose = [&](Move& mv) {'
    helper=r'''    struct AssignmentMemo {
        u64 hash=0, polarity=0;
        std::array<u64,15> masks{};
        double value=0;
        bool used=false;
    };
    std::vector<AssignmentMemo> assignment_memo(1<<BITS);
    std::array<std::array<u64,30>,64> assignment_random;
    XorShift hash_rng{0xf239c0173d9a68b1ULL};
    for (auto& row:assignment_random) for (auto& v:row) v=hash_rng.next();
    auto hash_state = [&] {
        u64 h=0;
        for (int e=0;e<ne;++e) for (u64 q=mask[e];q;q&=q-1) {
            const int a=__builtin_ctzll(q);
            h ^= assignment_random[a][2*e+int(pol>>a&1)];
        }
        return h;
    };
    u64 assignment_hash=hash_state(), proposed_hash=0;
    long long assignment_hits=0, assignment_checks=0;
    auto hash_move = [&](const Move& mv) {
        u64 h=assignment_hash;
        const int ca=(mv.oldpol>>mv.a)&1, cb=(mv.oldpol>>mv.b)&1;
        if (mv.swindow) {
            h ^= assignment_random[mv.a][2*mv.ea+ca] ^ assignment_random[mv.b][2*mv.eb+int(pol>>mv.b&1)];
        } else if (mv.transfer>=0) {
            h ^= assignment_random[mv.a][2*mv.ea+ca] ^ assignment_random[mv.a][2*mv.eb+int(pol>>mv.a&1)];
        } else if (mv.kind<3) {
            h ^= assignment_random[mv.a][2*mv.ea+ca] ^ assignment_random[mv.a][2*mv.ea+int(pol>>mv.a&1)];
        } else {
            h ^= assignment_random[mv.a][2*mv.ea+ca] ^ assignment_random[mv.a][2*mv.eb+ca];
            h ^= assignment_random[mv.b][2*mv.eb+cb] ^ assignment_random[mv.b][2*mv.ea+cb];
        }
        return h;
    };
    auto proposed_polarity = [&](const Move& mv) {
        const u64 handles=hm ^ (mv.swindow ? (1ULL<<mv.a)|(1ULL<<mv.b) : 0);
        return pol & kActiveWindows & ~handles;
    };
    auto assignment_hit = [&](const Move& mv) {
        ++assignment_checks;
        const auto& entry=assignment_memo[proposed_hash&((1<<BITS)-1)];
        if (!entry.used || entry.hash!=proposed_hash || entry.polarity!=proposed_polarity(mv) ||
            !std::equal(mask.begin(),mask.end(),entry.masks.begin())) return false;
        // Comparing every group and active polarity makes hash collisions harmless.
        memo_value[move_key]=entry.value;
        ++assignment_hits;
        return true;
    };
    auto save_assignment = [&](const Move& mv,double value) {
        auto& entry=assignment_memo[proposed_hash&((1<<BITS)-1)];
        entry.used=true; entry.hash=proposed_hash; entry.polarity=proposed_polarity(mv); entry.value=value;
        std::copy(mask.begin(),mask.end(),entry.masks.begin());
    };
'''.replace('BITS',str(bits))
    t=t.replace(needle,helper+needle,1)
    needle='        memo_hit = memo_epoch[move_key] == 2 * epoch + 1;'
    t=t.replace(needle,'        proposed_hash=hash_move(mv);\n'+needle,1)
    needle='        if (memo_hit) { memo_hits++; return true; }'
    t=t.replace(needle,needle+'\n        if (assignment_hit(mv)) { memo_hit=true; return true; }',1)
    t=t.replace('        ++epoch;\n        selected = candidate_selected;', '        assignment_hash=proposed_hash;\n        ++epoch;\n        selected = candidate_selected;',1)
    needle='        memo_hit = true; ++memo_hits; ++direct_steps;'
    t=t.replace(needle,'        proposed_hash=hash_move(mv);\n'+needle,1)
    needle='        memo_value[move_key] = candidate;'
    assert t.count(needle)==2;t=t.replace(needle,needle+'\n        save_assignment(mv,candidate);')
    needle='    stats.gobj_before = cur;'
    t=t.replace(needle,'    assignment_hash=hash_state();\n'+needle,1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "assignment_hits = " << assignment_hits << "\nassignment_checks = " << assignment_checks << '\n';
    stats.gobj_after = cur;''',1)
    return t
