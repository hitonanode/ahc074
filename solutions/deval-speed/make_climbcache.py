from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-fast2/main.cpp').read_text()
a=s.index('        auto gain = [&](int t, int y, int c) {',s.index('    void filler_climb('));b=s.index('        std::vector<double> utility(U);',a)
s=s[:a]+'''        std::array<u64,P> target_holes{},donor_cover{},donor_bits{};
        std::array<int,P> target_column{};
        std::array<bool,P> head_eligible{};
        auto cache_unit=[&](int x) {
            const auto& u=unit[x];
            donor_cover[x]=low_bits(u.c+1)&~diffb[x];donor_bits[x]=hb[u.a];
            head_eligible[x]=weight(u)==max_weight[u.c][color(u,u.c)];
            for(int t:{u.a,u.b})if(t>=0) {
                target_column[t]=u.c;target_holes[t]=~low_bits(u.c+1)|diffb[x];
            }
        };
        for(int x=0;x<U;++x)cache_unit(x);
        auto gain=[&](int t,int y,int c) {
            if(target_column[t]==c)return 0.0;
            const u64 range=donor_cover[y]&target_holes[t],mis=(donor_bits[y]^hb[t])&range;
            const int level=mis?64-__builtin_clzll(mis):0;
            if(level>=c)return 0.0;
            return covered_gain(range&low_bits(c)&~low_bits(level),[&](int j){return q[t][j];});
        };
        // Only the two exchanged units change geometry or head eligibility;
        // rollback restores the same cache before the next random proposal.
        auto eligible=[&](int x){return head_eligible[x];};
''' +s[b:]
a=s.index('    void filler_climb(');b=s.index('\n};',a)
part=s[a:b]
part=part.replace('        for (int it = 0;; it++) {','        std::vector<double> old_utility(U);\n        for (int it = 0;; it++) {',1)
part=part.replace('''            std::vector<int> moved;
            for (int t : {ox.a, ox.b, oy.a, oy.b})
                if (t >= 0) moved.push_back(t);
            auto old_utility = utility;''','''            std::array<int,4> moved{ox.a,ox.b,oy.a,oy.b};
            old_utility = utility;''',1)
part=part.replace('for (int t : moved) utility[z]', 'for (int t : moved) if(t>=0) utility[z]')
part=part.replace('            unit[y] = ny;','            unit[y] = ny;\n            cache_unit(x);cache_unit(y);',1)
part=part.replace('                unit[y] = oy;','                unit[y] = oy;\n                cache_unit(x);cache_unit(y);',1)
part=part.replace('utility = std::move(old_utility);','utility = old_utility;',1)
s=s[:a]+part+s[b:]
d=R/'solutions/deval-climbcache';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-climbcache

改良元: solutions/deval-fast2。

filler climbで対象の穴・列と供給紙の被覆・色・先頭適格性を保存し、交換する2ユニットだけ更新する。棄却時には同じ情報を復元する。確率計算・加算順・乱数列は変えない。各提案のutility退避用vectorは確保済み領域へコピーし、最大4対象の列挙は固定配列にする。

設計と注文の探索回数は親と同じ。時間不足による切替えはない。ログ、DesignStore、@paper/@ops、目次・段の目印を維持。
''')
print(len(s.encode()))
