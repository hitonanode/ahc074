"""Generate alternate perforation/reassignment variants from PR146."""
from pathlib import Path
base=Path('solutions/argon-des-perf-latew105')
s=(base/'main.cpp').read_text()
def change(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)

change('//   Saving and loading the design state (LOCAL_BENCH: DesignStore)',
       '//   design_papers: alternating perforation and reassignment\n//   Saving and loading the design state (LOCAL_BENCH: DesignStore)')
change('''    void run(double weight) {
        AF_SCOPE(perforation, 1);''','''    void run(double weight, bool revisit = false, const std::vector<bool>* focus = nullptr) {
        AF_SCOPE(perforation, 1);''')
change('''            if (k != heads[c][b]) continue;
            for (u64 bits = allowed[k] & low_bits(c); bits; bits &= bits - 1)
                candidates.push_back({k, __builtin_ctzll(bits)});''','''            if (!revisit && k != heads[c][b]) continue;
            u64 bits = allowed[k] & low_bits(c);
            // Restore obsolete holes on any paper; add holes only to eligible heads.
            if (revisit && (k != heads[c][b] || (focus && !(*focus)[k]))) bits &= ~opacity[k];
            for (; bits; bits &= bits - 1) candidates.push_back({k, __builtin_ctzll(bits)});''')
change('''    void install() {
        for (int k = kFirst; k < K; k++) {
            for (int c = 0; c < H; c++)
                if (!(opacity[k] >> c & 1)) s.paper[k].opaque &= ~(1ULL << s.handle[c]);''','''    void install(bool restore = false) {
        for (int k = kFirst; k < K; k++) {
            for (int c = 0; c < H; c++) {
                const u64 bit = 1ULL << s.handle[c];
                if (!(opacity[k] >> c & 1)) s.paper[k].opaque &= ~bit;
                else if (restore) {
                    s.paper[k].opaque |= bit;
                    if (colors[k] >> c & 1) s.paper[k].black |= bit;
                    else s.paper[k].black &= ~bit;
                }
            }''')
change('''    const double perforation_start = elapsed_sec();''','''    std::vector<bool> first_heads(K, false);
    const auto before_late_ded = state.ded;
    const double perforation_start = elapsed_sec();''')
change('''        perforation.run(0.7);''','''        perforation.run(0.7);
        for (const auto& head : perforation.heads) first_heads[head[0]] = first_heads[head[1]] = true;''')
initial=(base/'main.cpp').read_text()
begin=initial.index('        std::vector<u64> extra(des->U);',initial.index('// ==== design_papers: perforation-aware'))
end=initial.index('    return state;',begin)
late=initial[begin:end]
assert late.endswith('    }\n')
late=late[:-6]
late=late.replace('late_iterations, 1.05','1, 1.05').replace('d2_rematch_', 'd2_altmatch_').replace('d2_model_', 'd2_altmodel_').replace('d2_filler_', 'd2_altfiller_').replace('d2_extra_remaining', 'd2_altextra_remaining')
stage='''    // ==== design_papers: alternating perforation and reassignment ====

    const double alt_start = elapsed_sec();
    const int passes = int(env_real("ARGON_D2_ALT_PASSES", 1));
    auto synchronize = [&]() {
        solver.paper = state.papers;
        solver.ded = state.ded;
        for (int k = 0; k < K; ++k) {
            solver.h_opq[k] = solver.handle_bits(state.papers[k].opaque);
            solver.h_blk[k] = solver.handle_bits(state.papers[k].black);
        }
    };
    for (int pass = 0; pass < passes; ++pass) {
        synchronize();
        std::vector<bool> focus(K, false);
        for (int u = 0; u < P; ++u) if (before_late_ded[u] != state.ded[u])
            focus[before_late_ded[u]] = focus[state.ded[u]] = true;
        auto refine = [&]<int Capacity>() {
            Perforation<Capacity> p(solver);
            for (const auto& h : p.heads) for (int k : h) if (!first_heads[k]) focus[k] = true;
            for (const auto& u : des->unit) {
                const int k = state.ded[u.a];
                // A restored color must agree for every target served by this paper.
                p.allowed[k] = low_bits(des->H) & ~des->holes(u);
                p.colors[k] = des->hb[u.a] & p.allowed[k];
            }
            const int before = p.holes();
            const double before_cost = p.hole_cost;
            const auto original = p.opacity;
            p.run(0.7, true, FOCUS_POINTER);
            int added = 0, restored = 0;
            for (int k = Perforation<Capacity>::kFirst; k < K; ++k) {
                added += __builtin_popcountll(original[k] & ~p.opacity[k]);
                restored += __builtin_popcountll(p.opacity[k] & ~original[k]);
            }
            p.install(true);
            state.papers = solver.paper;
            std::cerr << "d2_alt_trials = " << p.trials
                      << "\\nd2_alt_accepts = " << p.accepted
                      << "\\nd2_alt_before = " << before
                      << "\\nd2_alt_after = " << p.holes()
                      << "\\nd2_alt_added = " << added
                      << "\\nd2_alt_restored = " << restored
                      << "\\nd2_alt_cost = " << (p.hole_cost - before_cost) / P
                      << "\\nd2_alt_owner = " << p.accepted_owner_corrected / P
                      << "\\nd2_alt_donor = " << p.accepted_donor / P << '\\n';
        };
        if (solver.H <= 25) refine.template operator()<25>();
        else refine.template operator()<64>();
        if constexpr (FINAL_MATCH) {
            const double late_start = elapsed_sec();
LATE_BODY
        }
    }
    std::cerr << "d2_alt_passes = " << passes
              << "\\nd2_alt_sec = " << elapsed_sec() - alt_start
              << "\\nd2_alt_end_sec = " << elapsed_sec() << '\\n';
'''.replace('LATE_BODY',late)
needle='''    return state;
}

#ifdef LOCAL_BENCH
// ==== Saving and loading'''
change(needle,stage+needle)
for name,focused,rematch in [('alternate',False,False),('altfocus',True,False),('alternate2',False,True)]:
    p=Path('solutions/argon-des-perf-'+name);assert not p.exists();p.mkdir()
    (p/'main.cpp').write_text(s.replace('FOCUS_POINTER','&focus' if focused else 'nullptr').replace('FINAL_MATCH','true' if rematch else 'false'))
    (p/'README.md').write_text(f'''改良元: solutions/argon-des-perf-latew105

穿孔後再割当の後、現在のhead・模様・色確率で穿孔をもう一巡する。
新しい穴の追加と既存穴の復元を許し、自然なペア穴と自身のハンドルは守る。
新しい穴の対象は{'所有目標が移動した紙と新しく選ばれたhead' if focused else '全head'}。
既存穴の復元はhead以外の紙にも許す。穿孔係数0.7、32層化標本・owner条件付き評価を維持。
{'その後、穿孔後再割当を係数1.05でさらに1回行う。' if rematch else '再穿孔の後には再割当を行わない対照。'}

ARGON_D2_ALT_PASSESは追加段の反復数（既定1、0で追加段なし）。
d2_alt_*は試行・受理・追加穴・復元穴・費用と価値の差・時間。
d2_altmatch_*、d2_altmodel_*、d2_altfiller_*は最後の再割当の量と費用・価値。
元のログ・全スイッチ・プロファイラ・DesignStore・段の目印を保持。
新しい段はdesign_papers: alternating perforation and reassignment。
''')
    print(p)
