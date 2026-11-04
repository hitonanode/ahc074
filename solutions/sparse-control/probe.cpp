#include "common.hpp"
int main(int argc,char**argv){
 if(argc<4)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int sequences=argc>4?std::stoi(argv[4]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<3;mode++){
  std::ifstream in(std::string(argv[3])+"-"+std::to_string(mode)+".txt");int G,U;in>>G>>U;assert(G==38&&U==185);
  Solver s=*base;for(auto&v:s.A)in>>v;
  auto a=s.A;for(auto&v:a)v&=kActiveWindows;Design d(a,6,G);
  for(auto&h:d.handle)in>>h;for(int u=0;u<P;u++){d.hb[u]=0;for(int c=0;c<d.H;c++)d.hb[u]|=((a[u]>>d.handle[c])&1)<<c;}
  Comparator comp;comp.M=6;comp.G=G;comp.edge.resize(G);comp.polarity.resize(G);
  for(int j=0;j<G;j++)in>>comp.edge[j].first>>comp.edge[j].second>>comp.polarity[j];comp.rebuild();
  d.unit.resize(U);for(auto&u:d.unit)in>>u.a>>u.b>>u.c;assert(in);d.rebuild();d.refresh_reset();
  s.comparator=comp;for(int k=0;k<6;k++)s.paper[k]={comp.opq[k],comp.black[k]};materialize(s,d);
  Perforation perforation(s);perforation.run(.5,1,false);perforation.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();long long total=0,wrong=0,generic=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];for(auto[k,z]:path)generic+=k<6;
    if(q==0){
     for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(sequences*1024);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"generic\":"<<double(generic)/(sequences*1024)<<",\"complete\":"<<comp.complete<<",\"wrong\":"<<wrong<<",\"unsafe\":"<<s.unsafe_plans<<",\"holes\":"<<perforation.holes()<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
