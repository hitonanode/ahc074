#include "saved.hpp"
std::unique_ptr<Design> recover(const Solver&s){
 auto a=s.A;for(auto&v:a)v&=kActiveWindows;auto d=std::make_unique<Design>(a,6,s.G);d->handle=s.handle;for(int u=0;u<P;u++)d->hb[u]=s.handle_bits(a[u]);
 for(int k=7;k<K;k++){std::vector<int>owners;for(int u=0;u<P;u++)if(s.ded[u]==k)owners.push_back(u);assert(owners.size()==1||owners.size()==2);Design::Unit x{owners[0],owners.size()==2?owners[1]:-1,s.col_of[k]};d->unit.push_back(x);if(x.b>=0){auto r=s.comparator.closure(a[x.a],a[x.a]^a[x.b]);u64 key=0;for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);d->gcost[x.a][x.b]=d->gcost[x.b][x.a]=PosetSums::get().both_of(key)/1440.;}}
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(s.comparator.compatible(d->A[a],d->A[b])){d->ok[a][b]=d->ok[b][a]=1;d->partners[a].push_back(b);d->partners[b].push_back(a);auto r=s.comparator.closure(d->A[a],d->A[a]^d->A[b]);u64 key=0;for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);d->gcost[a][b]=d->gcost[b][a]=PosetSums::get().both_of(key)/1440.;}
 d->rebuild();return d;
}
void materialize(Solver&s,const Design&d){
 for(int k=7;k<K;k++){s.paper[k]={0,0};s.col_of[k]=-1;}s.ded.assign(P,-1);s.handle=d.handle;s.hidx.assign(64,-1);for(int c=0;c<s.H;c++)s.hidx[s.handle[c]]=c;
 std::vector<u64>prefix(s.H);u64 p=0;for(int c=0;c<s.H;c++)prefix[c]=p|=1ULL<<s.handle[c];
 for(int x=0;x<d.U;x++){auto u=d.unit[x];int k=7+x;u64 hm=prefix[u.c];if(u.b>=0)hm&=~(s.A[u.a]^s.A[u.b]);u64 gm=s.gmask;if(u.b>=0)gm&=~(s.A[u.a]^s.A[u.b]);s.paper[k].opaque=gm|hm|kCapBit;s.paper[k].black=s.A[u.a]&(gm|hm|kCapBit);if(u.b>=0&&((s.A[u.a]^s.A[u.b])&kCapBit))s.paper[k].black&=~kCapBit;s.col_of[k]=u.c;s.ded[u.a]=k;if(u.b>=0)s.ded[u.b]=k;}
 s.order.clear();s.order.push_back(6);for(int k=0;k<6;k++)s.order.push_back(k);
 for(int c=0;c<s.H;c++){
  std::array<std::vector<int>,2>members;for(int x=0;x<d.U;x++)if(d.unit[x].c==c)members[d.color(d.unit[x],c)].push_back(x);
  for(auto&g:members)std::stable_sort(g.begin(),g.end(),[&](int a,int b){return d.weight(d.unit[a])<d.weight(d.unit[b]);});int majority=d.hn[c][1]>d.hn[c][0];
  for(int step=0;!members[0].empty()||!members[1].empty();step++){int color=members[1].size()>members[0].size();if(step<2&&!members[majority^step].empty())color=majority^step;int x=members[color].back();members[color].pop_back();s.order.push_back(7+x);}
 }
 for(int k=7+d.U;k<K;k++)s.order.push_back(k);
 for(int k=0;k<K;k++)s.h_opq[k]=s.handle_bits(s.paper[k].opaque),s.h_blk[k]=s.handle_bits(s.paper[k].black);s.adaptive_initialized=false;s.init_adaptive();
 s.comparator.build_tables();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
}
