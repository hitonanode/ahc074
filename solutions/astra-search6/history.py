"""過去に多く訪ねた状態への停滞脱出を、低い優先度にする。"""
def history(t, weight):
    t=t.replace('    auto handles_after =', r'''    // Hash the complete assignment, ignoring irrelevant colors on handle windows.
    // Visits affect only the choice of a forced escape, never matching_cost or the best state.
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
    std::vector<unsigned> visited_count(1 << 16);
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
    long long state_revisits = 0;
    auto record_state = [&] {
        const unsigned slot = hash_slot(current_hash);
        if (visited_hash[slot] != current_hash) {
            visited_hash[slot] = current_hash; visited_count[slot] = 0;
        }
        state_revisits += visited_count[slot] != 0;
        ++visited_count[slot];
    };
    record_state();
    auto handles_after =''',1)
    t=t.replace('        ++epoch;\n        selected = candidate_selected;', '        current_hash = next_hash(mv);\n        record_state();\n        ++epoch;\n        selected = candidate_selected;',1)
    t=t.replace('    double escape_floor = 1e30;', '    double escape_rank = 1e30, escape_floor = 1e30;',1)
    t=t.replace('''        if (candidate < escape_floor) {''', '''        const u64 hash = next_hash(mv);
        const unsigned slot = hash_slot(hash);
        const int visits = visited_hash[slot] == hash ? visited_count[slot] : 0;
        const double rank = candidate + VISIT_WEIGHT * visits;
        if (rank < escape_rank) {
            escape_rank = rank;'''.replace('VISIT_WEIGHT',str(weight)),1)
    t=t.replace('escape_floor = 1e30; escape_valid = false;', 'escape_rank = escape_floor = 1e30; escape_valid = false;')
    t=t.replace('    stats.gobj_before = cur;', '    current_hash = hash_state();\n    record_state();\n    stats.gobj_before = cur;',1)
    t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "state_revisits = " << state_revisits << \'\\n\';\n    stats.gobj_after = cur;',1)
    return t
