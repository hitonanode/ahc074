from pathlib import Path
p=Path(__file__).parent
s=Path('solutions/argon-des-perf-latew105/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90]);s=s.replace(a,b,1)
sub('    Moves post_optimize(const State& initial, Moves input_ops,','''    struct MidDiag {
        long long pairs, illegal, exposable, blockers, placements, legal, repairable, tails, valid, better, same;
        double gain, sec;
    };
    inline static MidDiag mid_total{}, mid_current{};
    Moves post_optimize(const State& initial, Moves input_ops,''')
sub('        int trial_operator = 0, best_operator = 0;','        int trial_operator = 0, best_operator = 0;\n        bool mid_probe = false;\n        double mid_post_gain = 0;')
sub('''            F3_DIAG(fp_legal[fp_op]++;)
            if (neutral_collect && cfg.collect) {''','''            F3_DIAG(fp_legal[fp_op]++;)
            if (mid_probe) {
                ++mid_current.valid;
                mid_current.same += order == best_state.order;
                if (value < best_score - 1e-9) {
                    ++mid_current.better;
                    mid_post_gain = std::max(mid_post_gain, best_score - value);
                }
                return false;
            }
            if (neutral_collect && cfg.collect) {''')
sub('''        F3_DIAG(
            fp_switch(fp_op);
            const std::string header''','''        if (eject && neutral_collect && cfg.two && input_ops.size() >= 2) {
            const double began = elapsed_sec();
            mid_probe = true;
            const auto original = anchorize(initial_bytes, input_ops OP_TAG(, tags));
            neutral_repairs(original, u, initial_bytes, evaluate, 2, &seed, nullptr, true);
            mid_probe = false;
            mid_current.gain = std::max(mid_current.gain, mid_post_gain);
            mid_current.sec += elapsed_sec() - began;
        }
        F3_DIAG(
            fp_switch(fp_op);
            const std::string header''')
# input tags were moved into best_tags; keep original tags for the measurement replay.
sub('''        auto edits = anchorize(initial_bytes, input_ops OP_TAG(, tags));''','''        auto edits = anchorize(initial_bytes, input_ops OP_TAG(, tags));
        const auto mid_original_edits = edits;''')
sub('''            const auto original = anchorize(initial_bytes, input_ops OP_TAG(, tags));
            neutral_repairs(original,''','''            neutral_repairs(mid_original_edits,''')
# Reuse the exact single-paper repair generator with no deletion, at the tail only.
sub('''        for (int j = n - 1; j >= (removed == 1 ? 0 : 1); j--)
            for (int i = removed == 1 ? -1 : j - 1; i >= (removed == 1 ? -1 : 0); i--) {''','''        for (int j = removed == 0 ? -1 : n - 1; j >= (removed == 0 ? -1 : removed == 1 ? 0 : 1); j--)
            for (int i = removed == 2 ? j - 1 : -1; i >= (removed == 2 ? 0 : -1); i--) {''')
sub('                eject_pairs++;','                if (removed) eject_pairs++;')
sub('''                    if (latest < 0) continue;
                    for (int pass = 0; pass < (earliest == latest ? 1 : 2); pass++) {
                        const int t = pass ? latest : earliest;''','''                    if (latest < 0 || (removed == 0 && latest != length)) continue;
                    for (int pass = 0; pass < (removed == 0 || earliest == latest ? 1 : 2); pass++) {
                        const int t = removed == 0 ? length : pass ? latest : earliest;''')
sub('''                            eject_trials++;
                            if (evaluate(next)) {
                                eject_accepts++;
                                eject_inside += t < length;''','''                            if (removed) eject_trials++;
                            else mid_current.tails++;
                            if (evaluate(next)) {
                                if (removed) eject_accepts++;
                                eject_inside += removed && t < length;''')
marker='''    template <class Evaluate>
    void neutral_repairs('''
helper='''    // At the first invisible edit, one move can expose its paper only by moving
    // a first owner whose second owner is that paper. Enumerate every deeper gap,
    // legally replay the suffix, then reuse the one-paper tail repair generator.
    template<class Evaluate>
    void probe_mid_repair(const std::vector<Edit>& shortened, int failed, const ByteOrder& stopped,
                          const ByteOrder& initial_bytes, int u, Evaluate& evaluate) {
        ++mid_current.illegal;
        const std::vector<Edit> original = shortened;  // eject_repairs reuses eject_trial
        const int target = original[failed].paper, pt = find_paper(stopped, target);
        std::array<int, N> owners;
        owners.fill(-1);
        std::array<bool, K> blocks{};
        u64 seen = 0, twice = 0;
        for (int t=0; t<=pt; ++t) {
            const int k = stopped[t];
            const u64 one = paper[k].opaque & ~seen;
            const u64 two = paper[k].opaque & seen & ~twice;
            for (u64 b=one;b;b&=b-1) owners[__builtin_ctzll(b)] = k;
            if (k == target) for (u64 b=two;b;b&=b-1)
                if (owners[__builtin_ctzll(b)] != kCapPaper) blocks[owners[__builtin_ctzll(b)]] = true;
            twice |= paper[k].opaque & seen;
            seen |= paper[k].opaque;
        }
        bool has_blocker = false, repairable = false;
        State initial;
        initial.order = initial_bytes;
        for (int f=0;f<K;++f) if (blocks[f]) {
            has_blocker = true;
            ++mid_current.blockers;
            const int pf = find_paper(stopped, f);
            for (int depth=pt; depth<K; ++depth) {
                ++mid_current.placements;
                ByteOrder replay = stopped;
                shift_byte(replay, pf, depth);
                bool legal = true;
                for (int i=failed; i<int(original.size()); ++i) {
                    const auto& e = original[i];
                    const int at = find_paper(replay, e.paper);
                    int dest = e.anchor < 0 ? 0 : find_paper(replay, e.anchor) + 1;
                    dest -= at < dest;
                    if (at == dest) continue;
                    u64 cover = 0;
                    for (int t=0;t<at;++t) cover |= paper[replay[t]].opaque;
                    if (!(paper[e.paper].opaque & ~cover)) { legal=false; break; }
                    shift_byte(replay, at, dest);
                }
                if (!legal) continue;
                ++mid_current.legal; repairable = true;
                auto path = original;
                path.insert(path.begin()+failed, {f, int(stopped[depth])});
                u64 covered = 0, view = 0;
                for (int k:replay) { view |= paper[k].black & ~covered; covered |= paper[k].opaque; }
                if (view == A[u]) {
                    ++mid_current.tails;
                    evaluate(path);
                } else {
                    eject_repairs(initial, path, u, post_context.next, post_context.prev,
                                  initial_bytes, evaluate, 0);
                }
            }
        }
        mid_current.exposable += has_blocker;
        mid_current.repairable += repairable;
    }
'''
sub(marker,helper+marker)
sub('''int removed = 2, const State* reference = nullptr, const std::array<bool, K>* initial_extra = nullptr) {''','''int removed = 2, const State* reference = nullptr, const std::array<bool, K>* initial_extra = nullptr,
                         bool interior_only = false) {''')
sub('''                trial = base;
                trial.erase(trial.begin() + y);''','''                if (interior_only) ++mid_current.pairs;
                trial = base;
                trial.erase(trial.begin() + y);''')
sub('''                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor;''','''                int step = 0;
                for (; step<int(trial.size()); ++step) {
                    const Edit& e = trial[step];
                    const int k = e.paper, a = e.anchor;''')
sub('''                if (!legal) continue;
                if (cfg.joint_limit''','''                if (!legal) {
                    if (interior_only) probe_mid_repair(trial, step, ord, initial_bytes, u, evaluate);
                    continue;
                }
                if (interior_only) continue;
                if (cfg.joint_limit''')
sub('''    Moves process(int u) {
        CF_SCOPE(process);''','''    Moves process(int u) {
        CF_SCOPE(process);
        mid_current = {};''')
fields='pairs illegal exposable blockers placements legal repairable tails valid better same gain sec'.split()
a='''        post_secondary_saved += original_length - int(chosen_path.size());'''
b=''.join(f'        mid_total.{f} += mid_current.{f};\n' for f in fields)
b+='''        OP_TAG(heavy_log += "#midorder " + std::to_string(request_counter - 1)
            + ' ' + std::to_string(mid_current.pairs) + ' ' + std::to_string(mid_current.illegal)
            + ' ' + std::to_string(mid_current.exposable) + ' ' + std::to_string(mid_current.repairable)
            + ' ' + std::to_string(mid_current.valid) + ' ' + trace_value(mid_current.gain) + '\\n';)
'''+a
sub(a,b)
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
'''+''.join(f'    std::cerr << "mid_{f} = " << solver.mid_total.{f} << \'\\n\';\n' for f in fields))
(p/'main.cpp').write_text(s)
