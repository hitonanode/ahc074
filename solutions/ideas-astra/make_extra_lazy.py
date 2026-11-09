from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-combo-dual30/main.cpp').read_text()
a=s.index('    __attribute__((target("avx2,popcnt"))) double adaptive_next_cost(');b=s.index('    // Lexicographic permutation rank',a)
f=s[a:b]
old='''        std::array<bool, K> extra{};  // the lifted paper and the fillers (out of their columns)
        if (top_d >= 0) extra[top_d] = true;
        for (auto f : fillers) extra[f.paper] = true;
'''
assert f.count(old)==1;f=f.replace(old,'')
old='        } else for(int k:order)if(col_of[k]>=0 && !extra[k])key[key_size++]=k;'
new='''        } else {
            // Ordinary role maps already exclude extras in the SIMD comparison.
            // Build the scalar membership array only for the exceptional role map.
            std::array<bool, K> extra{};
            if (top_d >= 0) extra[top_d] = true;
            for (auto q : fillers) extra[q.paper] = true;
            for(int k:order)if(col_of[k]>=0 && !extra[k])key[key_size++]=k;
        }'''
assert f.count(old)==1;f=f.replace(old,new)
f=f.replace('colmdp_next_partial(key.data(),in_place,extra,available,first,rank,covered)','colmdp_next_partial(key.data(),in_place,available,first,rank,covered)')
s=s[:a]+f+s[b:]
a=s.index('    double colmdp_next_partial(');b=s.index('    // The same when some column',a);f=s[a:b]
old='                            const std::array<bool,K>& extra,\n'
assert old in f;f=f.replace(old,'')
f=f.replace('#ifdef PARTIAL_MDP_CHECK\n', '''#ifdef PARTIAL_MDP_CHECK
        std::array<bool, K> extra{};
        if (top_d >= 0) extra[top_d] = true;
        for (auto q : fillers) extra[q.paper] = true;
''')
f=f.replace('#else\n        (void)extra;\n','#else\n')
s=s[:a]+f+s[b:]
p=r/'solutions/ia-extra-lazy';p.mkdir(exist_ok=False);(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-combo-dual30。

adaptive_next_costの列外紙のbool配列extraは、通常の紙役割ではSIMDの比較で代用済みで、partial MDPも本番経路では読まない。この配列の0初期化と記入を例外のscalar key経路へ移し、partial MDPへの未使用引数を外す。PARTIAL_MDP_CHECKでは元配列を作って検査を保つ。

費用、cache key、浮動小数点の演算順、候補、乱数は不変。Clangの自動0初期化でも不要配列を初期化しないよう、配列の宣言自体を例外分岐へ移す。DesignStore、時計、属性出力、段の目印を維持する。小さな速度probe用の試作。
''')
