"""Generate same/target from the measured profile; request policy stays byte-identical."""
from pathlib import Path
import json,hashlib,sys
N=Path(__file__).resolve().parent;R=N.parents[1]
shares=json.loads((N/'t13-shares.json').read_text())
source=(R/'solutions/dcomp-time-profile/main.cpp').read_text()
def replace(a,b,count=1):
 global source
 assert source.count(a)==count,(a[:90],source.count(a),count)
 source=source.replace(a,b)
replace('// Defaults use fixed random seeds and iteration counts; no future order is read during design.',
        '// Design search uses cumulative absolute deadlines and fixed random seeds; no future orders are read.')
replace('// Time-shortage fallback is intentionally absent (PR #117); restore it before the final submission\n// (solutions/deval-vbranch-o3 has the light request modes and the design caps).',
        '// The request policy is unchanged here. A separate submission patch supplies its pacer.')
replace('// design iterations; MAP_ITERS / GOPT_STEPS / ANNEAL_ITERS override individual stages; filler climbs are fixed.',
        '// legacy design iterations when LOCAL_BENCH DESIGN_FIXED_ITERS=1. DESIGN_SECONDS overrides the local time budget.')
replace('//   Design phase timing','//   Design phase timing\n//   Design absolute deadlines')
replace('    std::vector<Row> rows;',
'''    std::vector<Row> rows;
    std::vector<std::pair<std::string,long long>> counts;
    void count(const std::string& phase,long long iterations) {
        counts.push_back({name(phase),iterations});
    }''')
table='\n'.join('        {"'+q['name']+'", '+format(q['cumulative'],'.15f')+'},' for q in shares['schedule'])
new=r'''// ==== Design absolute deadlines ====
// Common weights for both compilers, measured on 200 cases each. Finite work
// (matching, one perforation pass, V, initial order and helper tables) keeps its
// full algorithm and is charged before the next absolute search deadline.
struct DesignTimePlan {
    struct Boundary { const char* name; double fraction; };
    static constexpr Boundary boundaries[] = {
@TABLE@
    };
    static constexpr double kDefaultSeconds = @BUDGET@;
    // Coarse polling keeps clock reads below 0.1% of the measured phase cost.
    static constexpr int kMapPoll = 512, kGoptPoll = 512;
    static constexpr int kAnnealPoll = 2048, kFillerPoll = 2048;
    bool active=false;
    double start=0,seconds=kDefaultSeconds;
    long long reads=0;
    void begin(double origin) {
        start=origin;seconds=kDefaultSeconds;active=true;reads=0;
#ifdef LOCAL_BENCH
        if(const char* s=std::getenv("DESIGN_SECONDS")) seconds=std::max(0.01,std::atof(s));
        if(const char* s=std::getenv("DESIGN_FIXED_ITERS")) active=std::atoi(s)==0;
#endif
    }
    double now() { ++reads;return elapsed_sec(); }
    double deadline(const std::string& phase) const {
        const auto name=design_trace.name(phase);
        for(const auto& b:boundaries)if(name==b.name)return start+seconds*b.fraction;
        std::cerr<<"unknown design deadline "<<name<<'\n';std::abort();
    }
    void report() const {
        std::cerr<<"design_time_enabled = "<<active<<"\ndesign_time_budget_sec = "<<seconds
                 <<"\ndesign_time_start_sec = "<<start<<"\ndesign_time_end_sec = "<<start+seconds
                 <<"\ndesign_clock_reads = "<<reads<<'\n';
    }
};
DesignTimePlan design_time;

'''.replace('@TABLE@',table)
replace('// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====',
        new+'// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====')
replace('    const double dt_design_begin=elapsed_sec();',
        '    const double dt_design_begin=elapsed_sec();\n    design_time.begin(dt_design_begin);')
replace('    design_trace.note("map_search",dt_search_begin);',
        '    design_trace.note("map_search",dt_search_begin);\n    design_trace.count("map_search",stats.iterations);')
replace('    design_trace.note("gopt",dt_gopt_begin);',
        '    design_trace.note("gopt",dt_gopt_begin);\n    design_trace.count("gopt",stats.climb_steps);')
replace('            total += anneal_iters;',
        '            design_trace.count("anneal_s"+std::to_string(s),anneal_iters);\n            total += anneal_iters;')
replace('      if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters); }',
'''      if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);
      design_trace.count("filler",des->climb_iters); }''')
replace('''    const double dt_search_begin=elapsed_sec();
    for (int it = 0;; it++) {
        if ((it & 15) == 0) {
            elapsed = scaled_since(start);
            if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;
        }
        stats.iterations++;
#if AS_PROFILE
        as_phase = fixed_iters ? std::min(3, 4 * it / fixed_iters) : 0;
#endif
        double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;''',
'''    const double dt_search_begin=elapsed_sec();
    const bool timed=design_time.active;
    const double search_end=timed?design_time.deadline("map_search"):0;
    const double gopt_end=timed?design_time.deadline("gopt"):0;
    const int clock_mask=timed?DesignTimePlan::kMapPoll-1:15;
    for (int it = 0;; it++) {
        if ((it & clock_mask) == 0) {
            if(timed) { elapsed=design_time.now();if(elapsed>=search_end)break; }
            else {
                elapsed = scaled_since(start);
                if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;
            }
        }
        stats.iterations++;
        const double progress = timed ? std::clamp((elapsed-dt_search_begin)/std::max(1e-9,search_end-dt_search_begin),0.,1.)
                                      : fixed_iters ? double(it) / fixed_iters : elapsed / seconds;
#if AS_PROFILE
        as_phase = timed ? std::min(3,int(4*progress)) : fixed_iters ? std::min(3,4*it/fixed_iters) : 0;
#endif''')
replace('    if (climb_steps > 0 || climb_seconds > 0) {',
        '    if (timed || climb_steps > 0 || climb_seconds > 0) {')
replace('''            if (climb_steps > 0 ? it >= climb_steps : (it & 15) == 0 && scaled_since(climb_start) >= climb_seconds)
                break;''',
'''            if (timed ? (it & (DesignTimePlan::kGoptPoll-1))==0 && design_time.now()>=gopt_end
                      : climb_steps > 0 ? it >= climb_steps : (it & 15) == 0 && scaled_since(climb_start) >= climb_seconds)
                break;''')
replace('            const int fi = fixedIterations ? fixedIterations / kAnnealSegments : 0;',
'''            const int fi = design_time.active ? 0 : fixedIterations ? fixedIterations / kAnnealSegments : 0;
            const double deadline=design_time.active?design_time.deadline("anneal_s"+std::to_string(s)):-1.;''')
replace('Annealer<4>(*this).run(sec, fi, p0, p1);','Annealer<4>(*this).run(sec, fi, p0, p1, deadline);')
replace('Annealer<5>(*this).run(sec, fi, p0, p1);','Annealer<5>(*this).run(sec, fi, p0, p1, deadline);')
replace('        ANNEAL_TARGET void run(double seconds, int fixedIterations, double p0 = 0, double p1 = 1) {',
        '        ANNEAL_TARGET void run(double seconds, int fixedIterations, double p0 = 0, double p1 = 1, double deadline=-1) {')
replace('''            double bestCost = cur;
            for (int it = 0;; it++) {
                D.anneal_iters = it;
                if ((it & 255) == 0) {
                    const double elapsed = scaled_since(start);
                    progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                    if (progress >= 1 || elapsed >= seconds) break;''',
'''            double bestCost = cur;
            const bool timed=deadline>=0;
            const double phase_begin=timed?elapsed_sec():0;
            const int clock_mask=timed?DesignTimePlan::kAnnealPoll-1:255;
            for (int it = 0;; it++) {
                D.anneal_iters = it;
                if ((it & clock_mask) == 0) {
                    if(timed) {
                        const double now=design_time.now();
                        if(now>=deadline)break;
                        progress=std::clamp((now-phase_begin)/std::max(1e-9,deadline-phase_begin),0.,1.);
                    } else {
                        const double elapsed = scaled_since(start);
                        progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                        if (progress >= 1 || elapsed >= seconds) break;
                    }''')
replace('''        proxy_before = proxy;
        std::vector<double> old_utility(U);
        for (int it = 0;; it++) {
            if (fixedIterations > 0 ? it >= fixedIterations : ((it & 63) == 0 && scaled_since(start) >= seconds)) break;''',
'''        proxy_before = proxy;
        std::vector<double> old_utility(U);
        const bool timed=design_time.active;
        const double deadline=timed?design_time.deadline("filler"):-1.;
        if(timed)climb_iters=0;
        for (int it = 0;; it++) {
            if (timed ? (it & (DesignTimePlan::kFillerPoll-1))==0 && design_time.now()>=deadline
                      : fixedIterations > 0 ? it >= fixedIterations : ((it & 63) == 0 && scaled_since(start) >= seconds)) break;''')
# Only the profile has the clock calibration microbenchmark. No request code is changed.
replace(r'''    {
        const double begin=elapsed_sec();
        volatile double sample=begin;
        for(int i=0;i<32768;++i)sample=elapsed_sec();
        const double cost=elapsed_sec()-begin;
        std::cerr<<"dt_clock_ns = "<<1e9*cost/32768<<'\n';
        (void)sample;
    }
''','')
# Emit trace in one write, so stderr's unitbuf does not add a write per field.
replace('''    void report() const {
        for(const auto& row:rows)
            std::cerr << "dt_" << row.name << "_sec = " << row.end-row.begin
                      << "\\ndt_" << row.name << "_begin = " << row.begin
                      << "\\ndt_" << row.name << "_end = " << row.end << '\\n';
    }''',
'''    void report() const {
        std::ostringstream out;
        for(const auto& row:rows)
            out << "dt_" << row.name << "_sec = " << row.end-row.begin
                << "\\ndt_" << row.name << "_begin = " << row.begin
                << "\\ndt_" << row.name << "_end = " << row.end << '\\n';
        for(const auto& [name,count]:counts)out<<"dt_"<<name<<"_iters = "<<count<<'\\n';
        std::cerr<<out.str();
    }''')
# Save design-stage diagnostics inside DesignStore's capture; do not overwrite
# them with an inactive schedule when loading a saved design.
replace('''              << "\\ndv_eval_sec = " << eval_sec << '\\n';
    return state;''',
'''              << "\\ndv_eval_sec = " << eval_sec << '\\n';
    design_trace.report();design_time.report();
    design_trace.rows.clear();design_trace.counts.clear();
    return state;''')
replace('''#ifdef LOCAL_BENCH
    store.design_end(state, solver.interleave && solver.interleave->ready);
#endif
    design_trace.note("helpers",dt_helpers_begin);
    design_trace.report();''',
'''    design_trace.note("helpers",dt_helpers_begin);
    design_trace.report();
#ifdef LOCAL_BENCH
    store.design_end(state, solver.interleave && solver.interleave->ready);
#endif''')
replace('    // Use fixedIterations when positive, otherwise the time budget; retain the 256-step checkpoints.',
'''    // The active design schedule supplies an absolute deadline for each segment.
    // Fixed-iteration experiments keep the old 256-step temperature checkpoints.''')
replace('// ITER_SCALE scales the four iteration budgets below; stage environment overrides take precedence.',
'''// Legacy fixed-iteration experiments: LOCAL_BENCH DESIGN_FIXED_ITERS=1.
// The default design schedule below supersedes these counts with absolute deadlines.''')
request_begin='// ==== Solver: papers, handles and the generic look-ahead ===='
request_end='// ==== Emergency design ===='
base=(R/'solutions/dcomp-combo-dual30/main.cpp').read_text()
assert source.split(request_begin)[1].split(request_end)[0]==base.split(request_begin)[1].split(request_end)[0]
assert source.split('    // ==== main: requests ====')[1]==base.split('    // ==== main: requests ====')[1]
for name,budget in [('same',1.05),('target',1.22)]:
 d=R/f'solutions/dcomp-time-{name}'
 assert '--update' in sys.argv or not d.exists()
 d.mkdir(exist_ok='--update' in sys.argv)
 code=source.replace('@BUDGET@',str(budget));(d/'main.cpp').write_text(code)
 (d/'README.md').write_text(f'''改良元: solutions/dcomp-combo-dual30

設計の探索回数を、設計開始からの絶対期限で決める。全設計の予算は{budget:.2f}秒（CLOCK_SCALE適用済み）。窓探索、窓の最終climb(gopt)、共有2区間と4分岐の各anneal区間、6回のfiller climbが対象。期限はGCC/Clang各200件で測った段の時間比率の等重み平均を用い、両コンパイラで共通とする。

Hungarianと後段再割当、穴あけの一巡、V、初期列順DP、helper表は同じ固定作業を完了する。その時間を含めた累積期限を次の可変段が使う。途中が遅くても後の段の期限を後ろへ延ばさない。9候補を全て仕上げてVで選び、候補の時間切れ除外は行わない。anneal温度は各区間の残り時間に沿って進める。

時計確認は窓/gopt512回、anneal/filler2048回ごと。全てscaled_since経由で倍率を適用する。dt_<段>_sec/begin/endは段別の実測、dt_<段>_itersは実行した反復数、design_time_budget_sec/end_secは予算と最終予定時刻、design_clock_readsは探索中の確認回数。c0–c8は候補番号。段の診断はDesignStoreにも保存する。

LOCAL_BENCHだけでDESIGN_SECONDSにより予算を上書きできる。DESIGN_FIXED_ITERS=1なら旧固定反復へ戻して同一性を検査でき、その時は既存のMAP_ITERS/GOPT_STEPS/ANNEAL_ITERS等も有効。通常は時間が優先される。

要求の計画・修復・予算・操作は変更しない。この版単独には要求pacerを含めず、別のpatchと統合する。helperの旧cutoffは現在1e300で無効のまま、表を全て構築する。DesignStore、ログ、@paper/@ops、profiler、目次と段の目印は保持する。
''')
 print(name,budget,hashlib.sha256(code.encode()).hexdigest())
