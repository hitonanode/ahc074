from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
marker=''' double rebuild(){
  if(dynamic)update_probability();'''
addition=''' static inline int fast_single_tables=0;
 // A single's holes are a suffix. For a fixed donor, all target columns
 // before its last mismatch share exactly the same covered suffix.
 void all_single_targets(std::vector<std::vector<double>>&table)const{
  for(auto&r:table)std::fill(r.begin(),r.end(),0.);
  for(int y=0;y<d.U;y++)if(beta[y]){
   const auto v=d.unit[y];int c=v.c;u64 mask=low_bits(c+1)&~diff[y];
   for(int t=0;t<P;t++){
    u64 wrong=(d.hb[t]^d.hb[v.a])&mask;int lo=wrong?64-__builtin_clzll(wrong):0;
    if(lo>=c)continue;
    double full=lo?Design::filler_gain(d.hb[t],-1,0,d.hb[v.a],diff[y],c,q[t].data()):0;
    for(int l=0;l<c;l++){
     double value=l<lo?full:Design::filler_gain(d.hb[t],l,0,d.hb[v.a],diff[y],c,q[t].data());
     table[t][l]+=beta[y]*value;
    }
   }
  }
 }
 // Extend a prospective single donor one handle at a time. A wrong exposed
 // color resets the useful suffix; the donor's own handle is excluded from
 // the saving, so its probability is incorporated after recording the value.
 void all_single_donors(std::vector<std::vector<double>>&table)const{
  for(auto&r:table)std::fill(r.begin(),r.end(),0.);
  std::vector<std::vector<double>>chance(P,std::vector<double>(d.H));
  for(int t=0;t<P;t++)for(int c=0;c<d.H;c++)chance[t][c]=.5*(q[t][c+1]-q[t][c]);
  for(int a=0;a<P;a++)for(int t=0;t<P;t++){
   auto u=d.unit[d.owner[t]];u64 holes=d.holes(u),wrong=holes&(d.hb[t]^d.hb[a]);
   double p0=1,p1=0,expected=0;
   for(int c=0;c<d.H;c++){
    if(wrong>>c&1){p0=1;p1=0;expected=0;continue;}
    if(c!=u.c)table[a][c]+=std::max(0.,expected-(1-p0)-.6*(1-p0-p1));
    if(holes>>c&1){double p=chance[t][c];expected+=p;p1=p1*(1-p)+p0*p;p0*=1-p;}
   }
  }
 }
'''
assert s.count(marker)==1;s=s.replace(marker,addition+marker)
old='''   for(int c=0;c<d.H;c++)single_target[a][c]=head.target(a,{a,-1,c});
  }
  std::vector<std::vector<double>>cost'''
new='''   if(!(ProbabilityHead::fast_single_tables&1))for(int c=0;c<d.H;c++)single_target[a][c]=head.target(a,{a,-1,c});
  }
  if(ProbabilityHead::fast_single_tables&1)head.all_single_targets(single_target);
  if(ProbabilityHead::fast_single_tables&2)head.all_single_donors(single_donor);
  std::vector<std::vector<double>>cost'''
assert s.count(old)==1;s=s.replace(old,new)
(p/'main.cpp').write_text(s)
