from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/triple-bound/design.hpp').read_text()
a=s.index('struct Problem {');b=s.index('\nstruct Group',a)
s=s[:a]+'''struct Problem {
    int M=6,G;U gm;std::vector<U>A;Comparator comp;
    std::array<std::array<unsigned char,256>,256> compatible{};
    std::array<std::array<float,256>,256> gcost{};
    double triple_price;
    Problem(const Design&d,const Comparator&c,bool triples):G(d.G),gm(low_bits(d.G)),A(d.A),comp(c),gcost(d.gcost),triple_price(triples?0:-1){
        for(int a=0;a<256;a++)for(int b=0;b<256;b++)compatible[a][b]=d.ok[a][b];
    }
    double fee(U target,U holes)const{
        auto relation=comp.closure(target,holes);u64 key=0;
        for(int k=0;k<6;k++){if(relation[k]>>k&1)return -1;key|=u64(relation[k])<<(8*k);}
        const auto& table=PosetSums::get();return table.one[table.slot_of(key)]/720.;
    }
};'''+s[b:]
s=s.replace(',27>',',64>').replace('assert(H<=27);','assert(H<=63);')
s=s.replace('if(n==3)g.fee=3*p.triple_price;', '''if(n==3)for(int t=0;t<3;t++){double value=p.fee(p.A[a[t]],g.diff);if(value<0)return;g.fee+=value;}''')
s=s.replace('if(p.triple_price>=0)for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)for(int c=b+1;c<256;c++){','if(p.triple_price>=0)for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p.compatible[a][b])for(int c=b+1;c<256;c++)if(p.compatible[a][c]&&p.compatible[b][c]){')
(p/'design.hpp').write_text(s)
(p/'README.md').write_text('''# 少ない汎用窓で3商品を共有する\n\n改良元: solutions/triple-bound。比較の制御は solutions/post-repair。\n\n汎用紙は6枚のまま、汎用窓を18〜38個へ減らし、残りを取り出し用の列にする。3商品の共通色だけを印刷した紙が、3商品の全てで比較制約を満たす場合に限って共有を許す。各商品の汎用操作費用は、6枚の全720順序からの合法な距離の平均を使う。\n\n窓割当は通常の2商品共有の目的で25万候補・貪欲5万候補を探索。その後、単独・2商品・3商品と列・ハンドル順を一般化した探索で選ぶ。各列の両色・全256商品の担当・計192枚を守る。取り出しと穴の費用は元の近似模型で測るため、全体の値は正式スコアではない。全比較辺が残ることも検査する。\n\n研究用。main.cpp単独は基準のコピーで、probe.cppが模型を検査する。実際の注文列は読まない。全時計にCLOCK_SCALEを適用する。\n''')
