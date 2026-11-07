from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
for name,table in [('deval-coltable',True),('deval-colscalar',False)]:
    s=base
    if table:
        needle='        static const float* bit_lanes(unsigned v)'
        i=s.index(needle)
        s=s[:i]+'''        static constexpr auto small_colcost=[] {
            std::array<int,32*32*2> result{};
            for(int nc=0;nc<32;++nc)for(int np=0;np<32;++np)for(int same=0;same<2;++same)
                result[(nc*32+np)*2+same]=20*(nc*(nc-1)+np*(np-1)+2*std::max(0,np-1)*same);
            return result;
        }();
        __attribute__((always_inline)) static int fast_colcost(int nc,int nt,int n1,int p1) {
            const int np=nt-nc;
            if((unsigned(nc)|unsigned(np))>=32)return Design::colcost40(nc,nt,n1,p1);
            return small_colcost[(nc*32+np)*2+int((p1==0)|(p1==np))]+4000000*int((n1==0)|(n1==nc));
        }
'''+s[i:]
    fn='fast_colcost' if table else 'Design::colcost40'
    a=s.index('            const __m128i costs = colcost_pair(',s.index('ANNEAL_TARGET void column_move'))
    b=s.index('            const int delta_col40',a)
    s=s[:a]+f'''            const int cvP={fn}(cnc[P]+dnc[0],cnt[P]+dnt[0],cn1[P]+dn1[0],cp1[P]+dp1[0]);
            const int cvQ={fn}(cnc[Q]+dnc[1],cnt[Q]+dnt[1],cn1[Q]+dn1[1],cp1[Q]+dp1[1]);
'''+s[b:]
    a=s.index('            const __m128i costs = colcost_pair(',s.index('ANNEAL_TARGET void target_move'))
    b=s.index('            __m256 N0[NR]',a)
    s=s[:a]+f'''            const int cvx={fn}(cnc[cx],cnt[cx]+dnt[0],cn1[cx]+dn1[0],cp1[cx]+dp1[0]);
            const int cvy=iy?{fn}(cnc[cy],cnt[cy]+dnt[1],cn1[cy]+dn1[1],cp1[cy]+dp1[1]):0;
'''+s[b:]
    a=s.index('            const __m128i costs =',s.index('ANNEAL_TARGET void handle_swap'))
    b=s.index('            const double delta =',a)
    s=s[:a]+f'''            const int cva={fn}(cnc[a],cnt[a],n1a,pa), cvb={fn}(cnc[b],cnt[b],n1b,pb);
'''+s[b:]
    d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-vbranch-o3。

焼きなましの列費用を{'小さな整数の完全表引き' if table else '従来の整数式をスカラーで2列分計算する方式'}にする。色が欠けた列の罰金と同点処理は変えない。{'列の紙数や対数が32以上なら元の正確な式を使う。' if table else ''} 穴費用・乱数・探索予算・時間ガードは同じ。
''')
    print(name,len(s.encode()))
