from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text();a=s.index('__attribute__((target("popcnt"))) inline CoverResult expectation(');b=s.index('\n} // namespace deval',a);part=s[a:b]
part='template<int Capacity>\n'+part.replace('CoverResult expectation(','CoverResult expectation_impl(',1).replace('MaxH+1','Capacity+1').replace('std::array<std::uint32_t,MaxH> threshold','std::array<std::uint32_t,Capacity> threshold').replace('std::vector<std::array<std::uint32_t,MaxH>> draws','std::vector<std::array<std::uint32_t,Capacity>> draws')
wrapper='''
__attribute__((target("popcnt"))) inline CoverResult expectation(const State& s,const Donors& d,
        const std::array<double,MaxH>& prob,const double* samples,int nSample,double price) {
    if(s.H<=25)return expectation_impl<25>(s,d,prob,samples,nSample,price);
    return expectation_impl<MaxH>(s,d,prob,samples,nSample,price);
}
'''
s=s[:a]+part+wrapper+s[b:]
p=r/'solutions/deval-vcapacity';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\nVの区間DPと色サンプルの作業配列を、通常の25ハンドルに合わせて特殊化する。参照しない末尾の初期化を省く。大きな配置も元の63ハンドル容量で扱い、演算と同点処理は変えない。固定予算で、時間不足による分岐はない。\n');print(len(s.encode()))
