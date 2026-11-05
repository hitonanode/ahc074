"""Build a restore-only post-rematch probe from PR145; no evaluations here."""
from pathlib import Path

base = Path('solutions/argon-des-perf-rematch-v2')
dst = Path('solutions/argon-des-perf-restoreonly')
assert not dst.exists()
s = (base/'main.cpp').read_text()
s = s.replace('//   Saving and loading the design state (LOCAL_BENCH: DesignStore)',
              '//   design_papers: restoring holes after reassignment\n//   Saving and loading the design state (LOCAL_BENCH: DesignStore)',1)
old = '''    void run(double weight) {
        AF_SCOPE(perforation, 1);'''
assert s.count(old)==1
s = s.replace(old,'''    void run(double weight, bool restore_only = false) {
        AF_SCOPE(perforation, 1);''')
old = '''            if (k != heads[c][b]) continue;
            for (u64 bits = allowed[k] & low_bits(c); bits; bits &= bits - 1)
                candidates.push_back({k, __builtin_ctzll(bits)});'''
new = '''            if (!restore_only && k != heads[c][b]) continue;
            // Old extra holes may belong to a paper which is no longer a head.
            u64 bits = allowed[k] & low_bits(c);
            if (restore_only) bits &= ~opacity[k];
            for (; bits; bits &= bits - 1) candidates.push_back({k, __builtin_ctzll(bits)});'''
assert s.count(old)==1
s=s.replace(old,new)
needle='''    return state;
}

#ifdef LOCAL_BENCH
// ==== Saving and loading'''
assert s.count(needle)==1
stage='''    // ==== design_papers: restoring holes after reassignment ====

    const double restore_start = elapsed_sec();
    // Reuse the unchanged comparator, but replace every field read by Perforation.
    solver.paper = state.papers;
    solver.ded = state.ded;
    for (int k = 0; k < K; ++k) {
        solver.h_opq[k] = solver.handle_bits(state.papers[k].opaque);
        solver.h_blk[k] = solver.handle_bits(state.papers[k].black);
    }
    auto restore = [&]<int Capacity>() {
        Perforation<Capacity> p(solver);
        for (const auto& u : des->unit) {
            const int k = state.ded[u.a];
            // Only colors shared by all owners may be printed back into a hole.
            p.allowed[k] = low_bits(des->H) & ~des->holes(u);
            p.colors[k] = des->hb[u.a] & p.allowed[k];
        }
        const int before = p.holes();
        const double cost_before = p.hole_cost;
        p.run(0.7, true);
        for (int k = Perforation<Capacity>::kFirst; k < K; ++k) {
            // Initial perforation only clears opacity. This pass can restore it.
            for (u64 z = p.opacity[k] & ~solver.h_opq[k]; z; z &= z - 1) {
                const int c = __builtin_ctzll(z);
                const u64 bit = u64(1) << state.handle[c];
                state.papers[k].opaque |= bit;
                if (p.colors[k] >> c & 1) state.papers[k].black |= bit;
                else state.papers[k].black &= ~bit;
            }
        }
        std::cerr << "d2_restore_trials = " << p.trials
                  << "\\nd2_restore_accepts = " << p.accepted
                  << "\\nd2_restore_before = " << before
                  << "\\nd2_restore_after = " << p.holes()
                  << "\\nd2_restore_cost = " << (p.hole_cost - cost_before) / P
                  << "\\nd2_restore_owner = " << p.accepted_owner_corrected / P
                  << "\\nd2_restore_donor = " << p.accepted_donor / P
                  << "\\nd2_restore_sec = " << elapsed_sec() - restore_start
                  << "\\nd2_restore_end_sec = " << elapsed_sec() << '\\n';
    };
    if (solver.H <= 25) restore.template operator()<25>();
    else restore.template operator()<64>();
'''
s=s.replace(needle,stage+needle)
dst.mkdir()
(dst/'main.cpp').write_text(s)
(dst/'README.md').write_text('''改良元: solutions/argon-des-perf-rematch-v2

穿孔後の再割当を終えてから、既存の追加穴だけを復元候補にする。
現在の所有目標が同色を要求する窓だけを許し、自然なペア穴と自身のハンドルは変更しない。
現在の頭・色確率・32層化標本を作り直し、既存の条件付きowner利益とdonor利益で受理する。
復元候補はhead以外の紙にも広げる。新しい穴は追加しない。受理係数は0.7。

元の全ログとスイッチを保持。d2_restore_trials/acceptsは試行・受理数、before/afterは追加穴数、
cost/owner/donorは費用と利益の変化（手/注文）、sec/end_secは追加段の時間。
新しい段と目次項目はdesign_papers: restoring holes after reassignment。
''')
print(dst)
