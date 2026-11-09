"""単色列の費用と、存在しない頭色の扱いを dual30 にまとめて実装する。"""
from make_small import BASE, replace, write

s=BASE
s=replace(s,'    static constexpr double kHoleWeight = 0.38;', '''    static constexpr double kHoleWeight = 0.38;
#ifdef LOCAL_BENCH
    inline static const bool kMono = env_real("D30A_MONO", 1) != 0;
    inline static const double kMonoFill = env_real("D30A_MONO_FILL", 1.7);
#else
    static constexpr bool kMono = true;
    static constexpr double kMonoFill = 1.7;
#endif
    bool mono_allowed(int c) const { return kMono && c < H - 2; }
    bool monochrome(int c, int count, int ones) const {
        return mono_allowed(c) && count > 0 && (ones == 0 || ones == count);
    }
    double mono_cost(int c, double x, double y) const {
        return monochrome(c,nc[c],n1[c]) ? 4*kHoleWeight*kMonoFill*std::min(x,y) : 0.;
    }
    std::array<double,2> column_probability(int c,double x,double y,double reset) const {
        if (nc[c] && n1[c] == 0) return {1.,0.};
        if (nc[c] && n1[c] == nc[c]) return {0.,1.};
        return head_probability(x,y,reset);
    }''')
s=replace(s,'static double colcost_of(int nc, int nt, int n1, int p1)',
          'static double colcost_of(int nc, int nt, int n1, int p1, bool allow_mono = false)')
s=replace(s,'100000.0 * int((n1 == 0) | (n1 == nc))',
          '100000.0 * int(nc == 0 || (!allow_mono && ((n1 == 0) | (n1 == nc))))')
s=replace(s,'colcost_of(nc[c], nt[c], n1[c], pairOne[c])',
          'colcost_of(nc[c], nt[c], n1[c], pairOne[c], mono_allowed(c))')
s=replace(s,'static int colcost40(int nc, int nt, int n1, int p1)',
          'static int colcost40(int nc, int nt, int n1, int p1, bool allow_mono = false)')
s=replace(s,'4000000 * int((n1 == 0) | (n1 == nc))',
          '4000000 * int(nc == 0 || (!allow_mono && ((n1 == 0) | (n1 == nc))))')
s=replace(s,'return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]);',
          'return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]) + mono_cost(j,hn[j][0],hn[j][1]);')
s=replace(s,'        cur -= cval[u.c];','''        // The soft missing-color charge is grouped with hcost. A count change
        // can enable it even though the unit has no hole at its own handle.
        cur -= hcost(u.c);
        cur -= cval[u.c];''')
s=replace(s,'        cur += cval[u.c] = colcost(u.c);',
          '        cur += cval[u.c] = colcost(u.c);\n        cur += hcost(u.c);')
s=replace(s,'                if (!take(c, v, false)) return false;',
          '                if ((v == 0 || !mono_allowed(c)) && !take(c, v, false)) return false;')
s=replace(s,'    // W, plus 1e5 if either handle color is absent.', '''    // W, plus 1e5 for an empty column or a missing color in the deepest two.
    // The soft charge of an allowed monochrome column is included in hcost.''')

# The integer retrieval term stays SIMD. The extra soft term uses hole counts
# already computed by each proposal, including changes of monochrome status.
s=replace(s,'        std::array<int, 64> cv{};  // colcost40', '''        std::array<int, 64> cv{};  // colcost40
        alignas(32) std::array<float,L> mono{};  // current monochrome indicators''')
s=replace(s,'static __m128i colcost_pair(__m128i nc, __m128i nt, __m128i n1, __m128i p1)',
          'static __m128i colcost_pair(__m128i nc, __m128i nt, __m128i n1, __m128i p1, __m128i allow)')
s=replace(s,'_mm_and_si128(_mm_set1_epi32(4000000), _mm_or_si128(_mm_cmpeq_epi32(n1, z), _mm_cmpeq_epi32(n1, nc)));',
          '''_mm_and_si128(_mm_set1_epi32(4000000), _mm_or_si128(_mm_cmpeq_epi32(nc,z),
                    _mm_andnot_si128(allow,_mm_or_si128(_mm_cmpeq_epi32(n1,z),_mm_cmpeq_epi32(n1,nc)))));''')
s=replace(s,'        static const float* bit_lanes(unsigned v)', '''        ANNEAL_TARGET __m128i mono_allow(int a,int b) const {
            return _mm_setr_epi32(D.mono_allowed(a)?-1:0,D.mono_allowed(b)?-1:0,0,0);
        }
        ANNEAL_TARGET static float lane(const __m256* x,int c) {
            return std::bit_cast<std::array<float,8>>(x[c/8])[c%8];
        }
        ANNEAL_TARGET double mono_hole_delta(const __m256* x,const __m256* y) const {
            __m256 sum=_mm256_setzero_ps();
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                const auto old=_mm256_min_ps(_mm256_load_ps(n0+8*r),_mm256_load_ps(n1+8*r));
                const auto change=_mm256_sub_ps(_mm256_min_ps(x[r],y[r]),old);
                sum=_mm256_add_ps(sum,_mm256_mul_ps(change,_mm256_load_ps(mono.data()+8*r)));
            }
            return hsum(sum);
        }
        ANNEAL_TARGET double mono_flag_delta(int c,int count,int ones,const __m256* x,const __m256* y) const {
            return (int(D.monochrome(c,count,ones))-mono[c])*std::min(lane(x,c),lane(y,c));
        }
        void refresh_mono(int c) { mono[c]=float(D.monochrome(c,cnc[c],cn1[c])); }
        static const float* bit_lanes(unsigned v)''')
s=replace(s,'cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c]);',
          'cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c], D.mono_allowed(c));\n            for (int c = 0; c < H; c++) refresh_mono(c);')
s=replace(s,'_mm_setr_epi32(cp1[P] + dp1[0], cp1[Q] + dp1[1], 0, 0));',
          '_mm_setr_epi32(cp1[P] + dp1[0], cp1[Q] + dp1[1], 0, 0), mono_allow(P,Q));')
s=replace(s,'const double delta = delta_col40 * (1.0 / 40) + kHoleScale * dq;', '''const double dm = mono_hole_delta(N0,N1)
                + mono_flag_delta(P,cnc[P]+dnc[0],cn1[P]+dn1[0],N0,N1)
                + mono_flag_delta(Q,cnc[Q]+dnc[1],cn1[Q]+dn1[1],N0,N1);
            const double delta = delta_col40 * (1.0 / 40) + kHoleScale * (dq+kMonoFill*dm);''')
s=replace(s,'            column_rows(ox, oy, P, Q, sy);',
          '            refresh_mono(P); refresh_mono(Q);\n            column_rows(ox, oy, P, Q, sy);')
s=replace(s,'_mm_setr_epi32(cp1[cx] + dp1[0], cp1[cy] + dp1[1], 0, 0));',
          '_mm_setr_epi32(cp1[cx] + dp1[0], cp1[cy] + dp1[1], 0, 0), mono_allow(cx,cy));')
s=replace(s,'const double delta = dcol + kHoleScale * dq + ((D.gc(nx) + D.gc(ny)) - (D.gc(ox) + D.gc(oy)));',
          '''const double dm = mono_hole_delta(N0,N1) + mono_flag_delta(cx,cnc[cx],cn1[cx]+dn1[0],N0,N1)
                + (iy ? mono_flag_delta(cy,cnc[cy],cn1[cy]+dn1[1],N0,N1) : 0.);
            const double delta = dcol + kHoleScale * (dq+kMonoFill*dm) + ((D.gc(nx) + D.gc(ny)) - (D.gc(ox) + D.gc(oy)));''')
s=replace(s,'            unit_rows(ox, -1.0f);',
          '            refresh_mono(cx); refresh_mono(cy);\n            unit_rows(ox, -1.0f);')
s=replace(s,'_mm_setr_epi32(n1a, n1b, 0, 0), _mm_setr_epi32(pa, pb, 0, 0));',
          '_mm_setr_epi32(n1a, n1b, 0, 0), _mm_setr_epi32(pa, pb, 0, 0), mono_allow(a,b));')
s=replace(s,'kHoleScale * ((qa - hq[a]) + (qb - hq[b])) + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);',
          '''kHoleScale * ((qa - hq[a]) + (qb - hq[b]) + kMonoFill *
                    (int(D.monochrome(a,cnc[a],n1a))*std::min(na0,na1)-mono[a]*std::min(n0[a],n1[a])
                    +int(D.monochrome(b,cnc[b],n1b))*std::min(nb0,nb1)-mono[b]*std::min(n0[b],n1[b])))
                    + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);''')
s=replace(s,'            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);\n        }\n        // Exchange the columns',
          '            refresh_mono(a); refresh_mono(b);\n            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);\n        }\n        // Exchange the columns')
s=replace(s,'            const double delta = kHoleScale * dq;', '''            const int cva=colcost40(cnc[b],cnt[b],cn1[b],cp1[b],D.mono_allowed(a));
            const int cvb=colcost40(cnc[a],cnt[a],cn1[a],cp1[a],D.mono_allowed(b));
            const double dm=mono_hole_delta(N0,N1)+mono_flag_delta(a,cnc[b],cn1[b],N0,N1)
                +mono_flag_delta(b,cnc[a],cn1[a],N0,N1);
            const double delta = kHoleScale * (dq+kMonoFill*dm)+(cva+cvb-cv[a]-cv[b])*(1./40);''')
s=replace(s,'            std::swap(cp1[a], cp1[b]), std::swap(cv[a], cv[b]);',
          '            std::swap(cp1[a], cp1[b]); cv[a]=cva; cv[b]=cvb;\n            refresh_mono(a); refresh_mono(b);')
s=replace(s,'cp1[c] + dp1[i]);','cp1[c] + dp1[i], D.mono_allowed(c));')
s=replace(s,'            const double delta = dcol * (1.0 / 40) + kHoleScale * dq + dg;', '''            double dm=mono_hole_delta(N0,N1);
            for(int i=0;i<ncols;++i)dm+=mono_flag_delta(cols[i],cnc[cols[i]]+dnc[i],cn1[cols[i]]+dn1[i],N0,N1);
            const double delta = dcol * (1.0 / 40) + kHoleScale * (dq+kMonoFill*dm) + dg;''')
s=replace(s,'cn1[c] += dn1[i], cp1[c] += dp1[i], cv[c] = ncv[i];',
          'cn1[c] += dn1[i], cp1[c] += dp1[i], cv[c] = ncv[i];\n                refresh_mono(c);')

# Finishing: absent heads have probability zero and must never index a vector.
s=replace(s,'color_probability[c] = head_probability(hn[c][0], hn[c][1], 2.0 * nt[c]);',
          'color_probability[c] = column_probability(c,hn[c][0],hn[c][1],2.0*nt[c]);')
s=replace(s,'Design::hole_cost_of(extended_counts[c][0], extended_counts[c][1], d.reset_targets[c]) - d.hcost(c)',
          'Design::hole_cost_of(extended_counts[c][0], extended_counts[c][1], d.reset_targets[c]) + d.mono_cost(c,extended_counts[c][0],extended_counts[c][1]) - d.hcost(c)')
s=replace(s,'prob[c] = Design::head_probability(counts[c][0], counts[c][1], strength * d.nt[c]);',
          'prob[c] = d.column_probability(c,counts[c][0],counts[c][1],strength*d.nt[c]);')
s=replace(s,'for (int c = 0; c < d.H; c++) gradient[c] = utility[selected[c][1]] - utility[selected[c][0]];',
          '''for (int c = 0; c < d.H; c++) gradient[c] =
            (selected[c][1]>=0 ? utility[selected[c][1]] : 0.) - (selected[c][0]>=0 ? utility[selected[c][0]] : 0.);''')
s=replace(s,'                assert(y >= 0);\n                beta[y]',
          '                if (y < 0) continue;\n                beta[y]')
s=replace(s,'                           k * ((x + .5 * t * (y < x)) * den - n) / (den * den)};',
          '''                           k * ((x + .5 * t * (y < x)) * den - n) / (den * den)};
            if (d.monochrome(j,d.nc[j],d.n1[j]))
                gradient[j][x<=y?0:1] += k*Design::kMonoFill;''')
s=replace(s,'                double den = std::max(1., counts[j][0]',
          '                if (d.monochrome(j,d.nc[j],d.n1[j])) continue;\n                double den = std::max(1., counts[j][0]')
s=replace(s,'valid&=d.n1[c]>0 && d.n1[c]<d.nc[c];',
          'valid&=d.nc[c]>0 && (d.mono_allowed(c) || (d.n1[c]>0 && d.n1[c]<d.nc[c]));')

# The same missing-color guards in the perforation surrogate.
s=replace(s,'sum += probability[c][b] * utility[heads[c][b]];',
          'if (heads[c][b]>=0) sum += probability[c][b] * utility[heads[c][b]];')
s=replace(s,'            const int k=heads[c][b];\n            const u64 mask',
          '            const int k=heads[c][b];\n            if(k<0){g.lo[b]=H+1;continue;}\n            const u64 mask')
s=replace(s,'                u64 mask = opq[x] & holes, wrong',
          '                if(x<0)return std::pair<u64,int>{0,0};\n                u64 mask = opq[x] & holes, wrong')
s=replace(s,'            probability[c] = Design::head_probability(counts[c][0], counts[c][1], 2 * demands[c]);',
          '''            probability[c] = Design::head_probability(counts[c][0], counts[c][1], 2 * demands[c]);
            if(!max_frequency[c][0])probability[c]={0.,1.};
            if(!max_frequency[c][1])probability[c]={1.,0.};''')

# The request planner's interval DP must give mandatory covers a large benefit.
s=replace(s,'    int handle_fix_cost(int l, int c) const {',
          '    static constexpr int kMissingHandleCost = 10000;\n    int handle_fix_cost(int l, int c) const {')
s=replace(s,'        return 0;\n    }\n    // handle_fix_cost of A_u',
          '        return kMissingHandleCost;\n    }\n    // handle_fix_cost of A_u')
s=replace(s,'fix[c] = 0;  // no paper of the right color: as handle_fix_cost',
          'fix[c] = kMissingHandleCost;  // mandatory filler: there is no legal dig')
s=replace(s,'fix[b][g] = d < L ? H[offset[r[d]] + suffix[d]] : F[g];',
          'fix[b][g] = !present[b] ? 10000.f : d < L ? H[offset[r[d]] + suffix[d]] : F[g];')
s=replace(s,'            if (need && barrier < 0) value += fc[desired];',
          '            if (need && barrier < 0) value += (first[desired]==n && cx!=desired ? kMissingHandleCost : fc[desired]);')

# V: actual head colors and no access through head == -1. The fitted coefficients stay.
s=replace(s,'            p[c]=(y+r*(y>x))/std::max(1.,x+y+r);',
          '''            p[c]=(y+r*(y>x))/std::max(1.,x+y+r);
            if(nc[c]>0 && n1[c]==0)p[c]=0;
            else if(nc[c]>0 && n1[c]==nc[c])p[c]=1;''')
s=replace(s,'for(int c=0;c<s.H;++c)v+=(1-p[c])*utility[head[c][0]]+p[c]*utility[head[c][1]];',
          '''for(int c=0;c<s.H;++c) {
            if(head[c][0]>=0)v+=(1-p[c])*utility[head[c][0]];
            if(head[c][1]>=0)v+=p[c]*utility[head[c][1]];
        }''')
s=replace(s,'    if(finished)improve_initial_columns(state);', '''    if(finished)improve_initial_columns(state);
    if(finished) {
        std::array<int,64> count{},ones{};
        for(int k=0;k<K;++k)if(state.columns[k]>=0) {
            const int c=state.columns[k];++count[c];ones[c]+=int(state.papers[k].black>>state.handle[c]&1);
        }
        int monochrome=0;for(int c=0;c<state.H;++c)monochrome+=count[c] && (ones[c]==0 || ones[c]==count[c]);
        std::cerr<<"mono_columns = "<<monochrome<<'\\n';
    }''')

write('mono',s,'''深い 2 列以外で「自列のハンドルに両色の紙が必要」という制約を緩める。空の列と深い 2 列の色欠けには元の大きな罰を残す。その他の単色列には、少数色の穴需要 × 1.7 × 4 × kHoleWeight の費用を置く。これは合計目的関数では列費用だが、穴需要の変化を正しく差分更新するため hcost と一緒に計算する。焼きなましの全移動で列の色欠け・穴需要の変化を計算し、初期化は浅い列で両色を強制しない。

存在しない頭色は仕上げ・穴あけ・V で確率 0 とし、その紙番号を参照しない。再割り当ては浅い列の単色化を許す。V の学習係数は変えない。

注文側はその色への掘りを費用 10000 の「不可能」として扱い、区間 DP が深い列の穴埋め紙を優先する。set_handle は元からある不正計画の判定で止まる。ColumnMdp の存在しない色の fix 値も 10000 とする。将来費用の先頭深さは元から列長に丸められており、初期列順序の DP は空の色群を扱える。

LOCAL_BENCH の D30A_MONO=0 は単色列の許可を止める。D30A_MONO_FILL は軟らかい罰の係数（既定 1.7）。新しい stderr 指標 mono_columns は最終設計の単色列数。plan_failures と E は既存指標で確認する。''')
