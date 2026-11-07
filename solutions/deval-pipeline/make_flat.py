"""Remove repeated row allocations from the finishing model, with identical arithmetic."""
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-flex8/main.cpp').read_text()
b=b.replace('std::vector<std::vector<double>> q;  // q[t][j]: as in filler_climb','std::array<std::array<double,65>,P> q;  // Live entries 0..H are rebuilt before use.',1)
b=b.replace('          q(P, std::vector<double>(d.H + 1)),\n','',1)
old='''        std::vector<std::vector<double>> tail(P, std::vector<double>(d.H + 1)),
            single_target(P, std::vector<double>(d.H, -1)), single_donor(P, std::vector<double>(d.H, -1));
        for (int a = 0; a < P; a++) {'''
new='''        std::array<std::array<double,65>,P> tail,single_target,single_donor;
        // Only 0..H is ever read. Avoid hundreds of heap rows and initialize
        // exactly the live cache entries; the tail recurrence overwrites the rest.
        for (int a = 0; a < P; a++) {
            tail[a][d.H]=0;
            std::fill_n(single_target[a].begin(),d.H,-1.);
            std::fill_n(single_donor[a].begin(),d.H,-1.);'''
assert old in b;b=b.replace(old,new,1)
# The generated table's indentation can be removed without changing tokens.
a=b.index('inline constexpr std::array<ModelTerm,142> kTerms{{');z=b.index('}};',a)
b=b[:a]+b[a:z].replace('\n    {','\n{')+b[z:]
for name,matrix in [('deval-flex8-arrays',False),('deval-flex8-matrix',True)]:
    s=b
    if matrix:
        s=s.replace('#include <sstream>','#include <sstream>\n#include <span>',1)
        old='__attribute__((target("avx2"))) std::vector<int> hungarian(const std::vector<std::vector<double>>& cost)'
        new='template<class Matrix>\n__attribute__((target("avx2"))) std::vector<int> hungarian(const Matrix& cost)'
        assert old in s;s=s.replace(old,new,1)
        old='''        std::vector<std::vector<double>> cost(d.U, std::vector<double>(d.U, 1e9));'''
        new='''        std::vector<double> entries(d.U*d.U,1e9);
        std::vector<std::span<double>> cost;
        for(int i=0;i<d.U;++i)cost.emplace_back(entries.data()+i*d.U,d.U);'''
        assert old in s;s=s.replace(old,new,1)
    p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/deval-flex8`。\n\n仕上げのProbabilityHeadとHungarian提案用の一時表を、固定サイズの行配列へ替える。実際に読むH列だけを初期化し、ターゲットごとのheap確保と不要な初期化を省く。'+('Hungarianの費用行列も1つの連続領域に置き、spanで元と同じ行アクセスをする。' if matrix else '')+'式・浮動小数点の更新順・乱数・候補順は同じ。容量はP=256、H≤63に対応。係数表の行頭空白だけ削って容量を確保する。全予算固定、時間不足による切り替えなし。\n')
    print(name,len(s.encode()))
