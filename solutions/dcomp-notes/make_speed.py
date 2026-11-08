"""Output-identical experiments chosen from the current design profile."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=(ROOT/'solutions/legal-tie-fast/main.cpp').read_text()
def sub(s,a,b):
    assert s.count(a)==1,(s.count(a),a[:80])
    return s.replace(a,b)
def write(name,s,desc):
    p=ROOT/'solutions'/name;p.mkdir(exist_ok=True)
    (p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: solutions/legal-tie-fast\n\n'+desc+'\n\n注文処理はlegal-tie-fastのまま。本文に記した変更以外の探索規則と既存のログ・実験スイッチを保つ。探索予算は固定回数で、時間不足の切替なし。標準runnerの24並列で比較する。\n')

cache=sub(BASE,'''struct WindowRelations {
    const PosetSums& sums;''','''struct WindowRelations {
    const PosetSums& sums;
    // Exact memoization of the raw relation's cost. Transposition preserves
    // the sum of both target directions; full keys detect every collision.
    static constexpr unsigned kCostSlots=1U<<16;
    mutable std::vector<uint32_t> cached_key=std::vector<uint32_t>(kCostSlots,~0U);
    mutable std::vector<uint16_t> cached_value=std::vector<uint16_t>(kCostSlots);
    mutable long long cache_queries=0,cache_hits=0;
    static uint32_t cost_key(uint32_t r){return std::min(r,(r>>16)|(r<<16));}
    static unsigned cost_slot(uint32_t k){return (k*0x9e3779b1U)>>(32-16);}
    int cached_cost(uint32_t r) const {
        const uint32_t key=cost_key(r);const unsigned i=cost_slot(key);
        return cached_key[i]==key ? int(cached_value[i]) : -1;
    }
    void remember_cost(uint32_t r,int v) const {
        const uint32_t key=cost_key(r);const unsigned i=cost_slot(key);
        cached_key[i]=key;cached_value[i]=uint16_t(v);
    }''')
cache=sub(cache,'''    // the closures first, without a branch on their cycles (pending[] is compacted to the''','''    // A relation's cost depends only on its raw arcs, not on the window map
    // that produced them. Keep unknown pairs in their original order for the
    // existing SIMD closure path. Cached cyclic pairs retain the same witness update.
    const int old_pending=npending;int unknown=0;
    for(int j=0;j<old_pending;++j) {
        const int p=pending[j],cost=relations.cached_cost(ndir[p]);
        if(cost<0)pending[unknown++]=p;
        else {
            nrel[p]=cost;
            if(!cost){const uint32_t t=relations.triangle(pdir[p]&ndir[p]);if(t)pwit[p]=t;}
        }
    }
    relations.cache_queries+=old_pending;relations.cache_hits+=old_pending-unknown;
    npending=unknown;
    // the closures first, without a branch on their cycles (pending[] is compacted to the''')
cache=sub(cache,'''        const int p = valid[k];
        const uint32_t t = relations.triangle(pdir[p] & ndir[p]);''','''        const int p = valid[k];
        relations.remember_cost(ndir[p],0);
        const uint32_t t = relations.triangle(pdir[p] & ndir[p]);''')
cache=sub(cache,'''    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);''','''    for (int k = 0; k < nacyclic; ++k) {
        const int p=pending[k],cost=1+relations.sums.both_of(closures[k]);
        nrel[p]=cost;relations.remember_cost(ndir[p],cost);
    }''')
cache=sub(cache,'''    stats.gobj_after = cur;''','''    std::cerr<<"dc_relation_queries = "<<relations.cache_queries
             <<"\\ndc_relation_hits = "<<relations.cache_hits<<'\\n';
    stats.gobj_after = cur;''')
write('dcomp-relcache',cache,'窓探索の未確定な関係の計算結果を、向きを反転しても不変な raw relation の整数キーで記憶する。65536スロットの直接参照キャッシュで、完全なキーを照合する。ヒット時も循環の witness 更新を保ち、ミスだけ従来の4並列閉包と費用表を使う。dc_relation_queries/hits は参照/ヒット数。')

for bits in [14,16,18]:
    packed=sub(cache,'''    static constexpr unsigned kCostSlots=1U<<16;
    mutable std::vector<uint32_t> cached_key=std::vector<uint32_t>(kCostSlots,~0U);
    mutable std::vector<uint16_t> cached_value=std::vector<uint16_t>(kCostSlots);''',f'''    static constexpr unsigned kCostBits={bits}, kCostSlots=1U<<kCostBits;
    // One load checks the exact tag and returns its value.
    mutable std::vector<u64> cost_entries=std::vector<u64>(kCostSlots,~u64(0));''')
    packed=sub(packed,'''    static unsigned cost_slot(uint32_t k){return (k*0x9e3779b1U)>>(32-16);}''','''    static unsigned cost_slot(uint32_t k){return (k*0x9e3779b1U)>>(32-kCostBits);}''')
    packed=sub(packed,'''        return cached_key[i]==key ? int(cached_value[i]) : -1;''','''        const u64 entry=cost_entries[i];
        return uint32_t(entry>>32)==key ? int(entry&65535) : -1;''')
    packed=sub(packed,'''        cached_key[i]=key;cached_value[i]=uint16_t(v);''','''        cost_entries[i]=(u64(key)<<32)|unsigned(v);''')
    write(f'dcomp-cache{bits}',packed,f'窓関係の完全キーと整数費用を1個の64bitエントリにまとめ、ヒット時の2段階ロードを省く。2^{bits}スロット。他の処理は dcomp-relcache と同じ。')

start='''        const __m128i rs = _mm_set_epi32(int(r3),int(r2),int(r1),int(r0));'''
end='''        const __m256i ones = _mm256_set1_epi8(1);'''
i=BASE.index(start);j=BASE.index(end,i)
expand=BASE[:i]+'''        // Independent scalar loads avoid AVX2 gather setup for four tiny tables.
        // The resulting four matrices and every subsequent pivot are bit-identical.
        auto expanded=[&](uint32_t r) {
            return expand[0][r&255]|expand[1][(r>>8)&255]
                 | expand[2][(r>>16)&255]|expand[3][r>>24];
        };
        __m256i c=_mm256_set_epi64x(expanded(r3),expanded(r2),expanded(r1),expanded(r0));
'''+BASE[j:]
write('dcomp-expand',expand,'窓探索で4個の関係を閉包に変換する際、4回のAVX2 gatherを独立な通常ロードに置き換える。展開するビット行列と、その後の6 pivotのSIMD演算は同じ。')

climb=sub(BASE,'''        std::vector<double> utility(U);
        for (int y = 0; y < U; y++)
            if (eligible(y))
                for (int t = 0; t < 256; t++) utility[y] += gain(t, y, unit[y].c);''','''        std::vector<double> utility(U), gain_cache(U*256);
        for (int y = 0; y < U; y++)
            if (eligible(y))
                for (int t = 0; t < 256; t++) utility[y] += (gain_cache[y*256+t]=gain(t, y, unit[y].c));
        // The head probabilities stay frozen during this climb. Cache the exact
        // current target/donor contribution; a trial changes four targets and two
        // donors. Commit those entries only when the original objective accepts.
        std::array<std::array<double,256>,2> next_donor{};
        std::array<std::array<double,4>,P> next_target{};''')
climb=sub(climb,'''                    for (int t : moved) if(t>=0) utility[z] -= gain(t, z, unit[z].c);''','''                    for (int t : moved) if(t>=0) utility[z] -= gain_cache[z*256+t];''')
climb=sub(climb,'''                for (int t = 0; t < 256; t++) utility[x] += gain(t, x, b);''','''                for (int t = 0; t < 256; t++) utility[x] += (next_donor[0][t]=gain(t, x, b));''')
climb=sub(climb,'''                for (int t = 0; t < 256; t++) utility[y] += gain(t, y, a);''','''                for (int t = 0; t < 256; t++) utility[y] += (next_donor[1][t]=gain(t, y, a));''')
climb=sub(climb,'''                    for (int t : moved) if(t>=0) utility[z] += gain(t, z, unit[z].c);''','''                    for (int j=0;j<4;++j) if(moved[j]>=0)
                        utility[z] += (next_target[z][j]=gain(moved[j], z, unit[z].c));''')
climb=sub(climb,'''            if (cur - old - kClimbProxyWeight * (next - proxy) < -1e-9) {
                proxy = next;
                climb_accepted++;''','''            if (cur - old - kClimbProxyWeight * (next - proxy) < -1e-9) {
                for(int z=0;z<U;++z) if(z!=x&&z!=y&&eligible(z))
                    for(int j=0;j<4;++j) if(moved[j]>=0)gain_cache[z*256+moved[j]]=next_target[z][j];
                if(eligible(x))std::copy(next_donor[0].begin(),next_donor[0].end(),gain_cache.begin()+x*256);
                if(eligible(y))std::copy(next_donor[1].begin(),next_donor[1].end(),gain_cache.begin()+y*256);
                proxy = next;
                climb_accepted++;''')
write('dcomp-climb-cache',climb,'filler climb 内で確率が固定されることを使い、現在の各 target/donor の寄与を保存する。交換候補で古い寄与を引くときの再計算を省き、動く2 donorと最大4 targetの新しい寄与だけ計算する。受理時だけ保存値を更新し、元の加減算順序を保つ。')

mask_cache=sub(climb,'''        auto gain=[&](int t,int y,int c) {''','''        struct GainMemo { u64 key=~u64(0);double value=0; };
        std::vector<GainMemo> gain_memo(1U<<14);
        auto gain=[&](int t,int y,int c) {''')
mask_cache=sub(mask_cache,'''            return covered_gain(range&low_bits(c)&~low_bits(level),[&](int j){return q[t][j];});''','''            const u64 covered=range&low_bits(c)&~low_bits(level);
            if(!covered)return 0.0;
            // Prefix subtraction makes q target-specific even for equal colours.
            // Retain the full target ID and covered mask, with exact-key validation.
            const u64 key=(covered<<8)|unsigned(t);
            auto& memo=gain_memo[(key*0x9E3779B97F4A7C15ULL)>>(64-14)];
            if(memo.key==key)return memo.value;
            const double result=covered_gain(covered,[&](int j){return q[t][j];});
            memo.key=key;memo.value=result;return result;''')
write('dcomp-climb-mask',mask_cache,'dcomp-climb-cache に加え、確率計算の寄与を (target ID, covered mask) の完全キーで記憶する。列移動後も同じ範囲を覆う場合に再利用する。q の丸めがtargetごとに異なりうるため、色だけの共有はしない。16384スロット、climbごとに初期化。')

bound=sub(climb,'''        // Only the two exchanged units change geometry or head eligibility;''','''        auto gain_upper=[&](int t,int y,int c) {
            if(target_column[t]==c)return 0;
            const u64 range=donor_cover[y]&target_holes[t],mis=(donor_bits[y]^hb[t])&range;
            const int level=mis?64-__builtin_clzll(mis):0;
            if(level>=c)return 0;
            return __builtin_popcountll(range&low_bits(c)&~low_bits(level));
        };
        // Only the two exchanged units change geometry or head eligibility;''')
bound=sub(bound,'''            for (int z = 0; z < U; z++)
                if (z != x && z != y && eligible(z))
                    for (int j=0;j<4;++j) if(moved[j]>=0)
                        utility[z] += (next_target[z][j]=gain(moved[j], z, unit[z].c));
            auto ix = std::find(members[a].begin(), members[a].end(), x);
            auto iy = std::find(members[b].begin(), members[b].end(), y);
            *ix = y;
            *iy = x;
            double next = 0;
            for (int c = 0; c < H; c++) next += column_value(c);''','''            auto ix = std::find(members[a].begin(), members[a].end(), x);
            auto iy = std::find(members[b].begin(), members[b].end(), y);
            *ix = y;
            *iy = x;
            std::array<bool,P> resolved{};resolved[x]=resolved[y]=true;
            auto resolve=[&](int z) {
                if(resolved[z])return;
                for(int j=0;j<4;++j)if(moved[j]>=0)
                    utility[z]+=(next_target[z][j]=gain(moved[j],z,unit[z].c));
                resolved[z]=true;
            };
            double next = 0;
            for(int c=0;c<H;++c) {
                std::array<double,2> best{};
                std::array<int,2> count{},first{-1,-1};
                for(int z:members[c]) {
                    const int b=color(unit[z],c);++count[b];
                    if(eligible(z)&&(first[b]<0||old_utility[z]>old_utility[first[b]]))first[b]=z;
                }
                for(int b=0;b<2;++b)if(first[b]>=0){resolve(first[b]);best[b]=std::max(0.,utility[first[b]]);}
                for(int z:members[c])if(eligible(z)) {
                    const int b=color(unit[z],c);
                    if(!resolved[z]) {
                        double upper=utility[z];
                        for(int t:moved)if(t>=0)upper+=gain_upper(t,z,c);
                        // A contribution is <= its number of covered holes. The
                        // margin exceeds all possible rounding error in these sums.
                        if(upper<best[b]-1e-7)continue;
                        resolve(z);
                    }
                    best[b]=std::max(best[b],utility[z]);
                }
                double value=0;
                for(int b=0;b<2;++b)if(count[b])value+=color_probability[c][b]*best[b];
                next+=value;
            }''')
bound=sub(bound,'''                for(int z=0;z<U;++z) if(z!=x&&z!=y&&eligible(z))
                    for(int j=0;j<4;++j) if(moved[j]>=0)gain_cache[z*256+moved[j]]=next_target[z][j];''','''                // Rejected trials need only the maxima. Accepted trials finish
                // every deferred update in its original per-donor arithmetic order.
                for(int z=0;z<U;++z)if(eligible(z))resolve(z);
                for(int z=0;z<U;++z) if(z!=x&&z!=y&&eligible(z))
                    for(int j=0;j<4;++j) if(moved[j]>=0)gain_cache[z*256+moved[j]]=next_target[z][j];''')
write('dcomp-climb-bound',bound,'dcomp-climb-cache に加え、列先頭になれないdonorの寄与の再計算を受理まで遅延する。寄与は覆う穴の数以下なので、既に計算した同色の最大値に届かないdonorを安全に判定できる。丸め誤差より十分大きい1e-7の余白を置く。受理する場合は全donorを元の加算順で更新し、探索候補・評価値・乱数列は変えない。')

table=sub(BASE,'''    template <int NR>
    struct Annealer {''','''    // n0,n1 and reset/2 are integers. The numerator is at most 49152,
    // hence its products and sums are exact in float. Table entries perform the
    // same rounded division as eval_holes; no reciprocal approximation is used.
    struct HoleTable {
        static constexpr int Stride=257*129;
        std::vector<float> value;
        std::array<bool,257> ready{};
        void prepare(int nt) {
            if(ready[nt])return;
            for(int sum=0;sum<=256;++sum)for(int minority=0;minority<=128;++minority) {
                const float a=float(minority),b=float(sum-minority),reset=float(2*nt);
                value[nt*Stride+sum*129+minority]=(a*b+.5f*reset*a)/std::max(1.f,a+b+reset);
            }
            ready[nt]=true;
        }
    };
    static HoleTable& hole_table(){static HoleTable table;return table;}
    template <int NR>
    struct Annealer {''')
table=sub(table,'''        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {}, reset[L] = {};''','''        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {}, reset[L] = {};
        alignas(32) int hole_base[L]{};
        const float* hole_value=nullptr;''')
table=sub(table,'''            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            for (int j = 0; j < H; j++) {''','''            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            auto& table=hole_table();int largest=0;
            for(int j=0;j<H;++j)largest=std::max(largest,int(D.reset_targets[j]/2));
            if(table.value.size()<size_t((largest+1)*HoleTable::Stride))table.value.resize((largest+1)*HoleTable::Stride);
            for(int j=0;j<L;++j) {
                const int nt=j<H?int(D.reset_targets[j]/2):0;
                table.prepare(nt);hole_base[j]=nt*HoleTable::Stride;
            }
            hole_value=table.value.data();
            for (int j = 0; j < H; j++) {''')
table=sub(table,'''                const __m256 reset_count = _mm256_load_ps(reset + 8 * r);
                const __m256 s = _mm256_max_ps(_mm256_add_ps(_mm256_add_ps(N0[r], N1[r]), reset_count), one);
                const __m256 numerator = _mm256_fmadd_ps(_mm256_mul_ps(_mm256_set1_ps(.5f), reset_count),
                                                         _mm256_min_ps(N0[r], N1[r]), _mm256_mul_ps(N0[r], N1[r]));
                Q[r] = _mm256_div_ps(numerator, s);''','''                const __m256i sum=_mm256_cvttps_epi32(_mm256_add_ps(N0[r],N1[r]));
                const __m256i minority=_mm256_cvttps_epi32(_mm256_min_ps(N0[r],N1[r]));
                const __m256i index=_mm256_add_epi32(_mm256_load_si256((const __m256i*)(hole_base+8*r)),
                    _mm256_add_epi32(_mm256_add_epi32(_mm256_slli_epi32(sum,7),sum),minority));
                Q[r]=_mm256_i32gather_ps(hole_value,index,4);''')
write('dcomp-hole-table',table,'anneal の取っ手費用を (reset/2, n0+n1, min(n0,n1)) で表引きする。各値は元と同じ float 除算で事前計算する。整数の分子は49152以下なので積・和がfloatで正確で、近似逆数やfast-mathを使わない。必要になったreset値だけ作り、全区間で共有する。')

for name,ma,gp in [('dcomp-map470',470000,133000),('dcomp-gopt165',450000,165000)]:
    s=sub(climb,'kMapIters = int(450000 * ITER_SCALE)',f'kMapIters = int({ma} * ITER_SCALE)') if ma!=450000 else climb
    if gp!=133000:s=sub(s,'kGoptSteps = int(133000 * ITER_SCALE)',f'kGoptSteps = int({gp} * ITER_SCALE)')
    write(name,s,f'dcomp-climb-cache の短縮時間を窓探索へ使う。map={ma}、最後のclimb={gp}反復。それ以外の反復数・候補数・注文処理は元のまま。')

nine=sub(climb,'''    for(int j=0;j<4;++j) {''','''    for(int j=0;j<5;++j) {''')
nine=sub(nine,'''        const bool warm=j%2==1;''','''        const bool warm=j%2==1 || j==4;''')
write('dcomp-nine',nine,'dcomp-climb-cache の短縮時間で、最良の完成割当から穴を引き継ぐ仕上げを1回追加する。既存の8候補を保持したまま9候補からVで選ぶ。追加候補はfiller climb/最初のrematchを省き、穿孔＋後段rematchを通常どおり行う。反復数はすべて固定。')

late=sub(nine,'''    for(int j=0;j<5;++j) {''','''    for(int j=0;j<6;++j) {''')
late=sub(late,'''        const bool warm=j%2==1 || j==4;''','''        const bool warm=j%2==1 || j>=4;''')
late=sub(late,'''        complete(id,warm?2:1);''','''        complete(id,j==5?3:warm?2:1);''')
late=sub(late,'''    if(!raw && extra!=2) {''','''    if(!raw && extra<2) {''')
late=sub(late,'''    if(extra==2 && !warm_state.papers.empty()) {''','''    if(extra>=2 && !warm_state.papers.empty()) {''')
late=sub(late,'''    if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();''','''    if(extra==3) {
        // One additional native reassignment on the best finished holes. Install
        // exactly the warm opacity, without running another perforation search.
        int holes=0;
        for(int k=0;k<K;++k)if(state.columns[k]>=0) {
            for(int c=0;c<solver.H;++c)if(!(solver.h_opq[k]>>c&1))solver.paper[k].opaque&=~(u64(1)<<solver.handle[c]);
            solver.paper[k].black&=solver.paper[k].opaque;
            solver.h_opq[k]=solver.handle_bits(solver.paper[k].opaque);
            solver.h_blk[k]=solver.handle_bits(solver.paper[k].black);
            holes+=__builtin_popcountll(natural_opacity[k]&~solver.h_opq[k]);
        }
        state.papers=solver.paper;
        std::cerr<<"perf_owner_bound_checks = 0\\nperf_owner_bound_skips = 0\\nperf_owner_raw = 0\\nperf_owner_conditioned = 0\\nperf_donor_gain = 0\\nperf_cache_rows = 0\\nperf_cache_skips = 0\\nperforation_trials = 0\\nperforation_accepts = 0"
                 <<"\\nperforation_holes = "<<holes<<"\\nperforation_sec = "<<elapsed_sec()-perforation_start
                 <<"\\nperforation_end_sec = "<<elapsed_sec()<<'\\n';
    } else if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();''')
write('dcomp-ten-late',late,'dcomp-nine に加え、最良完成設計の穴を保持したまま後段rematchだけを1回行う安い候補を追加する。10候補からVで選ぶ。10番目は穿孔探索を行わず、保持した穴を物理紙へ反映してから従来のHungarianを行う。既存9候補は保持する。')
