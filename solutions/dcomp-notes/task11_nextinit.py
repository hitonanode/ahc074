from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
i=B.index('    __attribute__((target("avx2,popcnt"))) double adaptive_next_cost(');j=B.index('    // Lexicographic permutation rank',i)
a=B[i:j]
def rep(s,x,y):assert s.count(x)==1,(x,s.count(x));return s.replace(x,y)
a=rep(a,'        std::array<int, 64> rank{};','        std::array<int, 64> rank;')
a=rep(a,'        std::array<bool, 128> available{};','        std::array<bool, 128> available;\n        std::fill_n(available.begin(),2*H,false);')
a=rep(a,'        std::fill(first.begin(), first.begin() + 2 * H, -1);\n','')
a=rep(a,'        if (mdp_scan) std::fill(mdp_code.begin(), mdp_code.begin() + H, 1);\n','')
x='        // Checkpoints retain the exact running double after 64/128 terms, together'
a=rep(a,x,'''        if(!start) {
            std::fill_n(rank.begin(),H,0);std::fill_n(first.begin(),2*H,-1);
            if(mdp_scan)std::fill_n(mdp_code.begin(),H,1);
        }
'''+x)
a=rep(a,'        std::array<std::array<double, 2>, 64> covered{};',
'''        std::array<std::array<double,2>,64> covered;
        std::fill_n(covered.begin(),H,std::array<double,2>{0.,0.});''')
s=B[:i]+a+B[j:]
split=rep(s,'    void split_generic(GenericSplit& split) const {\n        int count = 0;',
'''    void split_generic(GenericSplit& split) const {
        // Every consumer only queries below() for a filler. With none, no mask is needed.
        if(fillers.empty())return;
        int count = 0;''')
for name,src,desc in [('dcomp-t11-nextinit',s,'next_costのprefix cacheが戻したrank/first/codeを直前に初期化しない。cache miss時だけ、実際に読むH列・2H色を初期化する。coveredとavailableも読む範囲だけ初期化する。'),('dcomp-t11-nextinit-split',split,'next_costの不要初期化をなくし、fillerが空の時はgeneric境界の走査も省く。split.belowの全利用箇所はfillerの列挙内なので、この時のmaskは読まれない。'),('dcomp-t11-nextinit-check','#define NEXT_PREFIX_CHECK 1\n'+split,'不要初期化とfillerなし境界走査の省略を、元のnext_costによる全double bit照合付きで検証する。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(src)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'計算項と加算順、候補順は同じ。\n\n既存の固定予算、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による分岐は追加しない。\n')
