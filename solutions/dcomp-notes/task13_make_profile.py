"""Add boundary-only design timing to dual30. No solver executions here."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
source=(R/'solutions/dcomp-combo-dual30/main.cpp').read_text()
def replace(a,b,count=1):
 global source
 assert source.count(a)==count,(a[:80],source.count(a),count)
 source=source.replace(a,b)
replace('//   Request profiling (COLFAST_PROFILE): inclusive and exclusive times',
        '//   Design phase timing\n//   Request profiling (COLFAST_PROFILE): inclusive and exclusive times')
replace('// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====',r'''// ==== Design phase timing ====
// Boundary-only accounting; all times use the program's scaled clock.
struct DesignPhaseTrace {
    struct Row { std::string name; double begin, end; };
    int candidate = -1;
    std::vector<Row> rows;
    std::string name(const std::string& phase) const {
        return candidate < 0 ? phase : "c" + std::to_string(candidate) + "_" + phase;
    }
    void note(const std::string& phase, double begin) {
        rows.push_back({name(phase),begin,elapsed_sec()});
    }
    void report() const {
        for(const auto& row:rows)
            std::cerr << "dt_" << row.name << "_sec = " << row.end-row.begin
                      << "\ndt_" << row.name << "_begin = " << row.begin
                      << "\ndt_" << row.name << "_end = " << row.end << '\n';
    }
};
DesignPhaseTrace design_trace;
struct DesignPhaseScope {
    std::string name; double begin;
    explicit DesignPhaseScope(std::string label): name(std::move(label)),begin(elapsed_sec()) {}
    ~DesignPhaseScope() { design_trace.note(name,begin); }
};

// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====''')
replace('    constexpr int kCutoff = 26;','    const double dt_map_begin=elapsed_sec();\n    constexpr int kCutoff = 26;')
replace('    for (int it = 0;; it++) {\n        if ((it & 15) == 0) {',
'''    design_trace.note("map_setup",dt_map_begin);
    const double dt_search_begin=elapsed_sec();
    for (int it = 0;; it++) {
        if ((it & 15) == 0) {''')
replace('    // Search from the annealing best for the original final time interval.',
'''    design_trace.note("map_search",dt_search_begin);
    const double dt_reset_begin=elapsed_sec();
    // Search from the annealing best for the original final time interval.''')
replace('    if (climb_steps > 0 || climb_seconds > 0) {',
'''    design_trace.note("map_reset",dt_reset_begin);
    const double dt_gopt_begin=elapsed_sec();
    if (climb_steps > 0 || climb_seconds > 0) {''')
replace('    // The returned assignment is the best visited state, not the last uphill escape.',
'''    design_trace.note("gopt",dt_gopt_begin);
    const double dt_map_return=elapsed_sec();
    // The returned assignment is the best visited state, not the last uphill escape.''')
replace('    return stats;\n}\n\n// ==== Design: units, columns and the cost model ====',
'''    design_trace.note("map_return",dt_map_return);
    return stats;
}

// ==== Design: units, columns and the cost model ====''')
replace('        for (int s = firstSegment; s < endSegment; s++) {',
'''        for (int s = firstSegment; s < endSegment; s++) {
            DesignPhaseScope dt("anneal_s"+std::to_string(s));''')
replace('    // ==== design_papers: window assignment and the initial design ====\n',
'''    // ==== design_papers: window assignment and the initial design ====
    const double dt_design_begin=elapsed_sec();
''')
replace('        comp.rebuild();\n        des =',
'''        const double dt_initialize_begin=elapsed_sec();
        comp.rebuild();
        des =''')
replace('        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate, []() { return false; }))\n            break;',
'''        const bool initialized=des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate, []() { return false; });
        design_trace.note("initialize",dt_initialize_begin);
        if(initialized) break;''')
replace('    if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);',
'''    { DesignPhaseScope dt("filler");
      if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters); }''')
replace('    const auto match = rematch_probability(*des, extra?1:2, 1.0, 2.0);',
'''    const double dt_match_begin=elapsed_sec();
    const auto match = rematch_probability(*des, extra?1:2, 1.0, 2.0);
    design_trace.note("match",dt_match_begin);''')
replace('    // Restore the cap bit only for the physical papers and online targets.',
'''    const double dt_print_begin=elapsed_sec();
    // Restore the cap bit only for the physical papers and online targets.''')
replace('    const double perforation_start = elapsed_sec();',
'''    design_trace.note("print",dt_print_begin);
    const double perforation_start = elapsed_sec();''')
replace('    else perforate.template operator()<64>();',
'''    else perforate.template operator()<64>();
    design_trace.note("perforation",perforation_start);''')
replace('                  << "\\nd2_rematch_end_sec = " << elapsed_sec() << \'\\n\';',
'''                  << "\\nd2_rematch_end_sec = " << elapsed_sec() << '\\n';
        design_trace.note("late_match",late_start);''')
replace('    auto complete=[&](int id,int extra) {',
'''    auto complete=[&](int id,int extra) {
        design_trace.candidate=id;''')
replace('        begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;',
'''        begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
        design_trace.note("value",begin);''')
replace('    for(int i=0;i<candidates;++i) {\n        deval_salt=',
'''    for(int i=0;i<candidates;++i) {
        design_trace.candidate=i;
        deval_salt=''')
replace('    if(finished)improve_initial_columns(state);',
'''    design_trace.candidate=-1;
    { DesignPhaseScope dt("initial_order"); if(finished)improve_initial_columns(state); }
    design_trace.note("design_total",dt_design_begin);''')
replace('    Solver solver = make_solver(state);\n    const int M = state.M, G = state.G;',
'''    const double dt_helpers_begin=elapsed_sec();
    Solver solver = make_solver(state);
    const int M = state.M, G = state.G;''')
replace('    std::cerr << "helper_end_sec = " << elapsed_sec() << \'\\n\';',
'''    design_trace.note("helpers",dt_helpers_begin);
    design_trace.report();
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\\n';''')
replace('    design_trace.report();\n    std::cerr << "helper_end_sec = " << elapsed_sec() << \'\\n\';',
r'''    design_trace.report();
    {
        const double begin=elapsed_sec();
        volatile double sample=begin;
        for(int i=0;i<32768;++i)sample=elapsed_sec();
        const double cost=elapsed_sec()-begin;
        std::cerr<<"dt_clock_ns = "<<1e9*cost/32768<<'\n';
        (void)sample;
    }
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\n';''')
d=R/'solutions/dcomp-time-profile';assert not d.exists();d.mkdir()
(d/'main.cpp').write_text(source)
(d/'README.md').write_text('''改良元: solutions/dcomp-combo-dual30

設計の段の境界だけで時刻を読み、窓探索・gopt・初期マッチング・共有annealと4分岐の各区間・候補ごとのfiller/Hungarian/穴あけ/後段再割当/V・初期列順・helper準備を計測する。探索の回数、乱数、採用規則、要求処理は変更しない。

`dt_<段>_sec`は所要時間、`_begin`/`_end`は倍率込みプログラム時刻。`c0`から`c8`は設計候補の番号。`design_total`は設計全体で、個別の段と重なる集計値。境界時計以外の追加計測はない。全てscaled_since経由でCLOCK_SCALEを適用する。

設計計測後に32768回の時計読みを測り、`dt_clock_ns`へ1回あたりの平均費用を出す。この校正分は設計の個別段には含まれず、helper_endには含まれる。
''')
print(d)
