#include "common.hpp"
struct Candidate{unsigned op=0,black=0;int column=0;double value=0,weight=0;};
std::unique_ptr<Design> make_design(const Solver&s,int reserved,int iterations){
 auto a=s.A;for(auto&v:a)v&=kActiveWindows;
 auto d=std::make_unique<Design>(a,6+reserved,s.G);
 auto price=[&](u64 a,u64 b){auto r=s.comparator.closure(a,a^b);u64 key=0;for(int j=0;j<6;j++)key|=u64(r[j])<<(8*j);return PosetSums::get().both_of(key)/1440.;};
 if(!d->initialize([&](u64 a,u64 b){return s.comparator.compatible(a,b);},price,[]{return false;}))return {};
 d->anneal(1e9,iterations);d->filler_climb(1e9,65000);return d;
}
struct Model{
 Solver&s;std::array<unsigned,P>holes{},colors{};std::array<std::array<double,2>,64>bad{};
 explicit Model(Solver&solver):s(solver){
  s.init_adaptive();std::vector<int>nt(s.H);for(int u=0;u<P;u++)nt[s.col_of[s.ded[u]]]++;
  for(int c=0;c<s.H;c++){
   double x=s.adaptive_holes[c][0]*P,y=s.adaptive_holes[c][1]*P,t=2*nt[c],total=x+y+t;int majority=y>x;
   for(int color=0;color<2;color++)bad[c][color]=total?( (color?x:y)+(majority!=color?t:0))/total:.5;
  }
  for(int u=0;u<P;u++){holes[u]=unsigned(low_bits(s.H))&~s.h_opq[s.ded[u]];colors[u]=s.handle_bits(s.A[u]);}
 }
 double value(const Candidate&c)const{
  double sum=0;
  for(int u=0;u<P;u++){
   unsigned shown=c.op&holes[u],wrong=shown&(c.black^colors[u]);
   if(wrong)shown&=~unsigned(low_bits(32-std::countl_zero(wrong)));
   double p0=1,p1=0,expected=0;
   for(unsigned z=shown;z;z&=z-1){int j=std::countr_zero(z);double b=bad[j][colors[u]>>j&1];expected+=b;p1=p1*(1-b)+p0*b;p0*=1-b;}
   sum+=std::max(0.,expected-(1-p0)-.6*(1-p0-p1));
  }
  return sum/P;
 }
 std::vector<Candidate>search(int trials){
  std::mt19937_64 rng(1750930183);std::vector<Candidate>answer;
  for(int col=2;col<s.H;col++)for(int dense=0;dense<2;dense++){
   Candidate c;c.column=col;c.op=unsigned(low_bits(col+1));
   for(int j=0;j<=col;j++)if(bad[j][1]<bad[j][0])c.black|=1U<<j;
   if(!dense)c.op&=unsigned(rng());c.op|=1U<<col;c.black&=c.op;c.value=value(c);auto best=c;
   for(int it=0;it<trials;it++){
    auto next=c;int j=rng()%(col+1),v=rng()%3;if(j==col)v=rng()%2;
    next.op&=~(1U<<j);next.black&=~(1U<<j);if(v<2)next.op|=1U<<j;if(v==1)next.black|=1U<<j;
    if(dense)next.op=unsigned(low_bits(col+1));next.value=value(next);
    double temp=.005*std::pow(.002,double(it)/trials);
    if(next.value>=c.value||std::generate_canonical<double,53>(rng)<std::exp((next.value-c.value)/temp))c=next;
    if(c.value>best.value)best=c;
   }
   answer.push_back(best);
  }
  std::sort(answer.begin(),answer.end(),[](auto&a,auto&b){return a.value>b.value;});return answer;
 }
};
void add(Solver&s,const Candidate&c){
 int k=K-1;s.paper[k]={0,0};
 for(int j=0;j<s.H;j++){if(c.op>>j&1)s.paper[k].opaque|=1ULL<<s.handle[j];if(c.black>>j&1)s.paper[k].black|=1ULL<<s.handle[j];}
 s.col_of[k]=c.column;s.h_opq[k]=c.op;s.h_blk[k]=c.black;
 s.order.erase(std::find(s.order.begin(),s.order.end(),k));
 auto where=s.order.end();for(auto it=s.order.begin();it!=s.order.end();it++)if(s.col_of[*it]>=c.column){where=it;break;}s.order.insert(where,k);
 s.adaptive_initialized=false;s.init_adaptive();s.adaptive_weights[k]=c.weight;
}
double simulate(Solver&s,int sequences,int offset,long long*uses=nullptr){
 auto initial=s.save();long long total=0,wrong=0,active=0;
 for(int q=0;q<sequences;q++){
  s.restore(initial);std::mt19937_64 rng(803171ULL*(q+offset+1));int prev=rng()%P;
  for(int t=0;t<1024;t++){
   int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
   auto st=s.order;auto path=s.process(u);total+=path.size();active+=s.is_filler(K-1);
   u64 shown=0;for(auto[k,d]:path){u64 op=s.paper[k].opaque;for(int x:st){if(x==k)break;op&=~s.paper[x].opaque;}assert(op);auto it=std::find(st.begin(),st.end(),k);assert(it!=st.end()&&d>=0&&d<K);st.erase(it);st.insert(st.begin()+d,k);}
   assert(st==s.order);if(s.display()!=s.A[u]){std::cerr<<"wrong request "<<u<<" q "<<q<<" step "<<t<<" plan_failures "<<s.plan_failures<<" unsafe "<<s.unsafe_plans<<"\n";}wrong+=s.display()!=s.A[u];
  }
 }
 if(wrong||s.plan_failures)std::cerr<<"simulation wrong "<<wrong<<" failures "<<s.plan_failures<<"\n";assert(!wrong);if(uses)*uses=active;s.restore(initial);return double(total)/(1024*sequences);
}
int main(int argc,char**argv){
 if(argc<3)return 2;auto source=head::load(argv[1],argv[2]);if(!source)return 3;
 int tests=argc>3?std::stoi(argv[3]):12,iters=argc>4?std::stoi(argv[4]):20000000,seqs=argc>5?std::stoi(argv[5]):16;
 auto refdesign=make_design(*source,0,iters),design=make_design(*source,1,iters);if(!refdesign||!design)return 4;
 Solver ref=*source,base=*source;materialize(ref,*refdesign);materialize(base,*design);Model model(base);auto choices=model.search(4000);
 double training=simulate(base,2,0);std::cout<<std::setprecision(12)<<"{\"reduced_training\":"<<training<<",\"tests\":[";
 double best=1e100;Candidate chosen;
 int count=std::min(tests,int(choices.size()));
 for(int i=0;i<count;i++)for(double weight:{0.,1.,4.}){
  auto c=choices[i];c.weight=weight;Solver modified=base;add(modified,c);double result=simulate(modified,2,0);
  if(result<best)best=result,chosen=c;
  std::cerr<<"test "<<i<<" column "<<c.column<<" weight "<<weight<<" value "<<c.value<<" difference "<<result-training<<'\n';
  std::cout<<((i||weight!=0.)?",":"")<<"{\"column\":"<<c.column<<",\"op\":"<<c.op<<",\"black\":"<<c.black<<",\"weight\":"<<weight<<",\"proxy\":"<<c.value<<",\"moves\":"<<result<<"}"<<std::flush;
 }
 Solver candidate=base;add(candidate,chosen);long long used=0;
 double original=simulate(ref,seqs,1000),reduced=simulate(base,seqs,1000),value=simulate(candidate,seqs,1000,&used);
 std::cout<<"],\"reference\":"<<original<<",\"reduced\":"<<reduced<<",\"candidate\":"<<value<<",\"difference\":"<<value-original<<",\"helper_gain\":"<<value-reduced<<",\"used\":"<<used<<",\"chosen_column\":"<<chosen.column<<",\"chosen_op\":"<<chosen.op<<",\"chosen_black\":"<<chosen.black<<",\"chosen_weight\":"<<chosen.weight<<",\"seconds\":"<<elapsed_sec()<<"}\n";
}
