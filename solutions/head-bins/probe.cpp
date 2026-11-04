#include "saved.hpp"
std::unique_ptr<Design> recover(const Solver&s){
 auto a=s.A;for(auto&v:a)v&=kActiveWindows;auto d=std::make_unique<Design>(a,6,s.G);d->handle=s.handle;for(int u=0;u<P;u++)d->hb[u]=s.handle_bits(a[u]);
 for(int k=7;k<K;k++){std::vector<int>owners;for(int u=0;u<P;u++)if(s.ded[u]==k)owners.push_back(u);assert(owners.size()==1||owners.size()==2);Design::Unit x{owners[0],owners.size()==2?owners[1]:-1,s.col_of[k]};d->unit.push_back(x);if(x.b>=0){auto r=s.comparator.closure(a[x.a],a[x.a]^a[x.b]);u64 key=0;for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);d->gcost[x.a][x.b]=d->gcost[x.b][x.a]=PosetSums::get().both_of(key)/1440.;}}
 d->rebuild();return d;
}
void materialize(Solver&s,const Design&d){
 s.handle=d.handle;s.hidx.assign(64,-1);for(int c=0;c<s.H;c++)s.hidx[s.handle[c]]=c;
 std::vector<u64>prefix(s.H);u64 p=0;for(int c=0;c<s.H;c++)prefix[c]=p|=1ULL<<s.handle[c];
 for(int x=0;x<d.U;x++){auto u=d.unit[x];int k=7+x;u64 hm=prefix[u.c];if(u.b>=0)hm&=~(s.A[u.a]^s.A[u.b]);s.paper[k].opaque=(s.paper[k].opaque&~s.hmask)|hm;s.paper[k].black=(s.paper[k].black&~s.hmask)|(s.A[u.a]&hm);s.col_of[k]=u.c;}
 s.order.clear();s.order.push_back(6);for(int k=0;k<6;k++)s.order.push_back(k);
 for(int c=0;c<s.H;c++){
  std::array<std::vector<int>,2>members;for(int x=0;x<d.U;x++)if(d.unit[x].c==c)members[d.color(d.unit[x],c)].push_back(x);
  for(auto&g:members)std::stable_sort(g.begin(),g.end(),[&](int a,int b){return d.weight(d.unit[a])<d.weight(d.unit[b]);});int majority=d.hn[c][1]>d.hn[c][0];
  for(int step=0;!members[0].empty()||!members[1].empty();step++){int color=members[1].size()>members[0].size();if(step<2&&!members[majority^step].empty())color=majority^step;int x=members[color].back();members[color].pop_back();s.order.push_back(7+x);}
 }
 for(int k=0;k<K;k++)s.h_opq[k]=s.handle_bits(s.paper[k].opaque),s.h_blk[k]=s.handle_bits(s.paper[k].black);s.adaptive_initialized=false;s.init_adaptive();
 s.comparator.build_tables();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;int seqs=argc>3?std::stoi(argv[3]):8;
 auto design=recover(*base);double reference=0;std::cout<<std::setprecision(12)<<"[";
 std::vector<std::pair<int,int>> settings{{0,65000},{1,65000},{2,65000},{3,65000},{0,130000},{1,130000},{2,130000},{3,130000}};
 for(int index=0;index<int(settings.size());index++){
  auto d=*design;auto[mode,iters]=settings[index];Design::probability_model=mode;
  auto start=std::chrono::steady_clock::now();d.filler_climb(1e9,iters);double seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  Solver s=*base;materialize(s,d);auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(initial);std::mt19937_64 rng(230000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double average=double(total)/(seqs*1024);if(!index)reference=average;
  std::cout<<(index?",":"")<<"{\"mode\":"<<mode<<",\"iterations\":"<<iters<<",\"moves\":"<<average<<",\"difference\":"<<average-reference<<",\"wrong\":"<<wrong<<",\"accepted\":"<<d.climb_accepted<<",\"seconds\":"<<seconds<<"}"<<std::flush;
 }std::cout<<"]\n";
}
