#include "common.hpp"
#include "perforate.hpp"
int main(int argc,char**argv) {
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);

 Solver observed=*base;std::mt19937_64 training(718000003);int previous=training()%P;
 double sampling_start=elapsed_sec();std::vector<u64> observed_colors;
 for(int t=0;t<4352;t++){
  int u=training()%(P-1);if(u>=previous)u++;previous=u;
  observed.process(u);assert(observed.display()==observed.A[u]);
  if(t<256||(t&15))continue;
  u64 colors=0;
  for(int c=0;c<observed.H;c++){
   int k=observed.column_top(c);
   if(k<0&&observed.top_d>=0&&observed.col_of[observed.top_d]==c)k=observed.top_d;
   if(k<0)for(auto f:observed.fillers)if(observed.col_of[f.paper]==c){k=f.paper;break;}
   assert(k>=0);if(observed.h_blk[k]>>c&1)colors|=1ULL<<c;
  }
  observed_colors.push_back(colors);
 }
 double sampling_seconds=elapsed_sec()-sampling_start;
 Perforation::empirical_colors=observed_colors;
 std::cerr<<"sampling_sec = "<<sampling_seconds<<'\n';
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 std::cout<<std::setprecision(12)<<"[";
 int mode=0;
 for(int setting=0;setting<6;setting++) {
  Solver s=*base;double begin=elapsed_sec();Perforation::overlap_samples=(setting==3||setting==5)?32:8;Perforation::sample_mode=setting<=1?0:setting<=3?1:2;Perforation::screen_weight=1;Perforation design(s);double original=design.hole_cost-design.profit;
  if(setting)design.run(.5,1,false);
  double model=(design.hole_cost-design.profit-original)/P;design.install();double design_seconds=elapsed_sec()-begin;auto initial=s.save();
  long long total=0,wrong=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++) {
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++) {
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
    auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0) {
     for(auto[k,depth]:path) {
      int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;
      for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;
      assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);
     }
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"holes\":"<<design.holes()<<",\"fast_queries\":"<<design.fast_queries<<",\"full_queries\":"<<design.full_queries<<",\"equal_queries\":"<<design.equal_queries<<",\"model\":"<<model<<",\"design_seconds\":"<<design_seconds<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
