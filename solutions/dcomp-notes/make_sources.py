"""Reproducible Task8 variants; all requests remain legal-tie-fast's code."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
BASE = (ROOT / 'solutions/legal-tie-fast/main.cpp').read_text()

def replace(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:100])
    return s.replace(old, new)

def write(name, source, description):
    d = ROOT / 'solutions' / name
    d.mkdir(exist_ok=True)
    (d / 'main.cpp').write_text(source)
    (d / 'README.md').write_text('改良元: solutions/legal-tie-fast\n\n' + description + '\n\n注文処理は改良元と同一。固定反復回数で動作し、時間による省略はしない。\n')

audit = replace(BASE, '    long long forced_steps = 0, tabu_skips = 0;', '''    long long forced_steps = 0, tabu_skips = 0;
    long long dc_stall_iters[2]{}, dc_stall_events[2]{}, dc_stall_resets[2]{};
    int dc_max_gap[2]{};
    bool dc_was_stalled = false;
    const bool dc_fix_stall = false;''')
audit = replace(audit, '''    auto propose_candidate = [&](int it, int stall, double& candidate) {
        const bool path_move''', '''    auto propose_candidate = [&](int it, int stall, double& candidate) {
        const int phase = stall == kClimbStall;
        dc_max_gap[phase] = std::max(dc_max_gap[phase], it - last_accept_it);
        const bool stalled = it - last_accept_it >= 4 * stall && !escape_valid;
        dc_stall_iters[phase] += stalled;
        dc_stall_events[phase] += stalled && !dc_was_stalled;
        dc_was_stalled = stalled;
        // No eligible escape can age the accepted-state tabu. Advance its generation
        // only after four ordinary stall intervals; this uses no additional RNG draws.
        if (dc_fix_stall && stalled) {
            epoch += kTabuAccepted + 1;
            last_accept_it = it;
            screen_dirty = true;
            path_active = false;
            escape_floor = 1e30;
            escape_valid = false;
            ++dc_stall_resets[phase];
        }
        const bool path_move''')
audit = replace(audit, '    long long climb_forced_steps = 0;', '''    long long climb_forced_steps = 0;
    dc_was_stalled = false;''')
audit = replace(audit, '    stats.gobj_after = cur;', '''    for (int phase=0; phase<2; ++phase) {
        std::cerr << "dc_stall_iters_" << phase << " = " << dc_stall_iters[phase]
                  << "\\ndc_stall_events_" << phase << " = " << dc_stall_events[phase]
                  << "\\ndc_stall_resets_" << phase << " = " << dc_stall_resets[phase]
                  << "\\ndc_max_gap_" << phase << " = " << dc_max_gap[phase] << '\\n';
    }
    stats.gobj_after = cur;''')
write('dcomp-audit', audit, '窓探索の tabu 停滞を計測するだけの版。提案・受理・乱数列を変えない。dc_stall_iters_0/1 は焼きなまし/最後の climb で、4 倍の停滞間隔を超え、退避可能な候補がない反復数。dc_stall_events は連続区間数、dc_max_gap は最後の受理からの最大反復数。')
unstall = replace(audit, 'const bool dc_fix_stall = false;', 'const bool dc_fix_stall = true;')
write('dcomp-unstall', unstall, '窓探索が受理世代を進められない場合、tabu の世代を 5 だけ進める。条件は最後の受理から 4×stall 以上経過し、利用できる退避候補がないこと。反復数・探索温度は元のまま。dc_stall_resets_0/1 は発動回数。他の診断は dcomp-audit と同じ。')

profile = '#define DESIGN_PROFILE 1\n#define AS_PROFILE 1\n#define AF_PROFILE 1\n' + audit
profile = replace(profile, '''    if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);
    std::cerr''', '''    const double dc_climb_start = elapsed_sec();
    if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);
    std::cerr << "dc_climb_sec = " << elapsed_sec()-dc_climb_start << '\\n';
    std::cerr''')
profile = replace(profile, '''        finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
        if(candidate.emergency)''', '''        const double dc_finish_sec=elapsed_sec()-begin;
        finish_sec+=dc_finish_sec;std::cerr.rdbuf(old);
        std::istringstream dc_log(log.str());std::string dc_line;
        while(std::getline(dc_log,dc_line))std::cerr<<"@dcomp_finish "<<id<<' '<<extra<<' '<<dc_line<<'\\n';
        std::cerr<<"dc_finish_"<<id<<"_sec = "<<dc_finish_sec<<'\\n';
        if(candidate.emergency)''')
write('dcomp-profile', profile, '出力を変えずに設計段を測定する研究版。既存 DESIGN_PROFILE/AS_PROFILE/AF_PROFILE を有効化し、8 候補それぞれの finishing ログを @dcomp_finish に保存する。dc_climb_sec は filler climb の時間。プロファイラのオーバーヘッドがあるため、時間制限を超える研究実行は --no-record とする。')

two = replace(BASE, '''    const double prefix_begin=elapsed_sec();
    des->anneal(1e300,anneal_iters,0,shared);
    anneal_sec+=elapsed_sec()-prefix_begin;
    total_iters+=des->anneal_iters;
    const auto prefix=std::make_unique<Design>(*des);''', '''    const auto initial=std::make_unique<Design>(*des);''')
old_branches = '''    for(int i=0;i<candidates;++i) {
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        complete(i,0);
    }'''
two = replace(two, old_branches, '''    // Two independently salted half-length prefixes; two last-half branches
    // per prefix. The sum of anneal iterations and four native finishes is unchanged.
    for(int root=0;root<2;++root) {
        des=std::make_unique<Design>(*initial);
        if(root)des->rng.x^=0x1d42ac9b531ULL;
        double begin=elapsed_sec();des->anneal(1e300,anneal_iters/2,0,shared);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        const auto prefix=std::make_unique<Design>(*des);
        for(int i=0;i<2;++i) {
            const int id=2*root+i;deval_salt=first_salt+id;
            des=std::make_unique<Design>(*prefix);
            if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
            begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
            des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
            anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
            complete(id,0);
        }
    }''')
write('dcomp-two-anneals', two, '窓探索は共有し、前半 2 区間の anneal を独立な乱数で 2 本行う。それぞれ前半の反復回数を半分とし、後半は各 2 枝。総 anneal 反復数・4 枝の finishing・4 回の refinish は元と同じ。V で全候補から選ぶ。')

maps = replace(BASE, '''u64 deval_salt=0;''', '''u64 deval_salt=0;
u64 dc_window_salt=0;''')
maps = replace(maps, '''    XorShift rng{0x71eb2566be932e31ULL};''', '''    XorShift rng{0x71eb2566be932e31ULL ^ dc_window_salt};''')
maps = replace(maps, '''DesignState design_papers(const std::vector<u64>& originalA) {''', '''DesignState design_papers_half(const std::vector<u64>& originalA, u64 salt) {''')
maps = replace(maps, '''    deval_salt=std::max(0,env_int("DEVAL_SALT"));''', '''    deval_salt=u64(std::max(0,env_int("DEVAL_SALT")))+salt;
    dc_window_salt=salt;''')
maps = replace(maps, '''    const int candidates=4;''', '''    const int candidates=2;''')
maps = replace(maps, '''    const double branch_scale=0.25;''', '''    const double branch_scale=0.5;''')
maps = replace(maps, '''    const int anneal_iters = anneal_env ? anneal_env : kAnnealIters;''', '''    const int anneal_iters = (anneal_env ? anneal_env : kAnnealIters)/2;''')
maps = replace(maps, '''    std::mt19937_64 rng(779879);''', '''    std::mt19937_64 rng(779879 ^ salt);''')
maps = replace(maps, '''            const int map_iters = map_env ? map_env : attempt == 0 ? kMapIters : kMapRetryIters;''', '''            const int map_iters = (map_env ? map_env : attempt == 0 ? kMapIters : kMapRetryIters)/2;''')
maps = replace(maps, '''            const int gsteps = attempt ? 0 : gopt_env ? std::max(0, gopt_env) : kGoptSteps;''', '''            const int gsteps = (attempt ? 0 : gopt_env ? std::max(0, gopt_env) : kGoptSteps)/2;''')
maps = replace(maps, '''    for(int j=0;j<4;++j) {''', '''    for(int j=0;j<2;++j) {''')
maps = replace(maps, '''    if(finished)improve_initial_columns(state);''', '''    // The winner of both pipelines receives the initial-order optimization once.''')
end = '''    return state;
}

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options'''
maps = replace(maps, end, '''    return state;
}

DesignState design_papers(const std::vector<u64>& originalA) {
    deval::DesignValue value;
    DesignState state;
    double best=1e100;
    std::string best_log;
    int chosen=-1;
    const double start=elapsed_sec();
    for(int root=0;root<2;++root) {
        std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
        auto candidate=design_papers_half(originalA,u64(root)*0x1d42ac9b531ULL);
        std::cerr.rdbuf(old);
        if(candidate.emergency)continue;
        const double v=value.from_design(candidate);
        std::cerr<<"dc_map_"<<root<<"_v = "<<v<<'\\n';
        if(v<best){best=v;state=std::move(candidate);best_log=log.str();chosen=root;}
    }
    if(chosen<0)state.emergency=true;
    else improve_initial_columns(state);
    std::cerr<<best_log<<"dc_map_chosen = "<<chosen
             <<"\\ndc_total_design_sec = "<<elapsed_sec()-start<<'\\n';
    return state;
}

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options''')
write('dcomp-two-maps', maps, '窓探索から独立な 2 系統を実行し、V で完成設計を選ぶ。各系統は map と gopt と総 anneal を半分にし、2 枝＋2 refinish。合計の反復数、通常 finishing 4 回と refinish 4 回は元と同じ。初期列順の DP は最終候補だけに適用。dc_map_chosen は選ばれた系統、dc_total_design_sec は両系統の合計時間。')

print('base SHA256', hashlib.sha256(BASE.encode()).hexdigest())
