from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'solver-scan/main.cpp').read_text()
helper='''    static inline bool scan_tops=true;
    using ColumnTops=std::array<std::array<int,kFillerDepth+1>,64>;
    void all_column_tops(ColumnTops&tops,std::array<int,64>&counts)const{
        counts={};
        for(int k:order){int c=col_of[k];if(c<0||counts[c]>kFillerDepth||!in_column(k,c))continue;tops[c][counts[c]++]=k;}
    }
'''
needle='    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {'
s=s.replace(needle,helper+needle)
specs=[('    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {','    // Level for an out-of-place paper','choose_fillers_dp','int u,int d,u64 hh','u,d,hh','std::vector<FillerPick>',' const'),('    void run_joint(int u, const PlanOpt& opt) {','    //','run_joint','int u,const PlanOpt&opt','u,opt','void',''),('    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) {','    //','choose_fillers_prelift','int u,int d,u64 hh','u,d,hh','std::vector<FillerPick>','')]
for begin,ignored,name,args,call,ret,const in specs:
 a=s.index(begin);brace=s.index('{',a);depth=1;b=brace+1
 while depth:
  if s[b]=='{':depth+=1
  if s[b]=='}':depth-=1
  b+=1
 old=s[a:b]
 new=old.replace(name+'(',name+'_scan(')
 new=new.replace('        std::vector<int> top;', '        ColumnTops tops;std::array<int,64> ntop;all_column_tops(tops,ntop);',1)
 new=new.replace('            column_tops(c, kFillerDepth + 1, top);','            const auto&top=tops[c];',1)
 new=new.replace('top.empty()', 'ntop[c]==0').replace('(int)top.size()', 'ntop[c]')
 if name=='choose_fillers_prelift':
  x=new.index('        std::vector<std::array<int, kFillerDepth + 1>> tops(H);')
  y=new.index('        std::vector<PC> pcs;',x)
  new=new[:x]+new[y:]
 wrapper=f'    {ret} {name}({args}){const}{{if(scan_tops)return {name}_scan({call});return {name}_old({call});}}\n'
 s=s[:a]+wrapper+old.replace(name+'(',name+'_old(')+'\n'+new+s[b:]
(p/'main.cpp').write_text(s)
