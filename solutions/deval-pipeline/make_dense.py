from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-flex8/main.cpp').read_text()
s=s.replace('#include <sstream>','#include <sstream>\n#include <span>',1)
code='''// Dense scratch rows retain the runtime width and allocate their storage once.
struct FinishRows {
    std::vector<double> values;int count,width;
    FinishRows(int n,int m,double value=0):values(n*m,value),count(n),width(m) {}
    int size() const {return count;}
    std::span<double> operator[](int i) {return {values.data()+i*width,size_t(width)};}
    std::span<const double> operator[](int i) const {return {values.data()+i*width,size_t(width)};}
};
'''
needle='// The assignment of least total cost of a square cost matrix (the Hungarian algorithm with'
assert s.count(needle)==1;s=s.replace(needle,code+needle,1)
s=s.replace('hungarian(const std::vector<std::vector<double>>& cost)','hungarian(const FinishRows& cost)',1)
s=s.replace('std::vector<std::vector<double>> q;  // q[t][j]: as in filler_climb','FinishRows q;  // q[t][j]: as in filler_climb',1)
s=s.replace('q(P, std::vector<double>(d.H + 1))','q(P, d.H + 1)',1)
old='''        std::vector<std::vector<double>> tail(P, std::vector<double>(d.H + 1)),
            single_target(P, std::vector<double>(d.H, -1)), single_donor(P, std::vector<double>(d.H, -1));'''
new='''        FinishRows tail(P,d.H+1),single_target(P,d.H,-1),single_donor(P,d.H,-1);'''
assert old in s;s=s.replace(old,new,1)
s=s.replace('std::vector<std::vector<double>> cost(d.U, std::vector<double>(d.U, 1e9));','FinishRows cost(d.U,d.U,1e9);',1)
a=s.index('inline constexpr std::array<ModelTerm,142> kTerms{{');z=s.index('}};',a)
s=s[:a]+s[a:z].replace('\n    {','\n{')+s[z:]
p=R/'solutions/deval-flex8-dense';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-flex8`。\n\n仕上げのProbabilityHead、再割当ての一時表、Hungarianの費用行列を、それぞれ1つの連続したdouble領域へ置く。実際のHとUの幅を保ち、spanで元と同じ行アクセスをする。行ごとのheap確保をなくし、式・初期値・浮動小数点の更新順・乱数・候補順は保つ。生成係数表の行頭空白だけを削る。全予算固定、時間不足による切り替えなし。\n')
print(len(s.encode()))
