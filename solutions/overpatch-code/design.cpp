#define OVERPATCH_NO_MAIN
#include "probe.cpp"
int main(int argc,char**argv){if(argc<8)return 2;auto s=std::make_unique<Search>();if(!s->load(argv[1],argv[2]))return 3;u64 mask=std::stoull(argv[3]),color=std::stoull(argv[4]);int h=std::stoi(argv[5]),hc=std::stoi(argv[6]);double charge=std::stod(argv[7]);int steps=argc>8?std::stoi(argv[8]):20000000;
 auto cost=[&](u64 a,u64 b,bool special){
  auto price=[&](u64 holes){auto r=s->comp.closure(a,holes);u64 key=0;for(int x=0;x<6;x++){if(r[x]>>x&1)return -1.;key|=u64(r[x])<<(8*x);}return PosetSums::get().both_of(key)/720.;};
  double old=price(a^b);if(special&&mask&&((a^b)&mask)&&((!((a^color)&mask)&&int(a>>h&1)==hc)||(!((b^color)&mask)&&int(b>>h&1)==hc))){double v=price((a^b)&~mask);if(v>=0&&(old<0||v+charge<old))return v+charge;}return old;
 };
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int kind=0;kind<2;kind++){
  auto d=std::make_unique<Design>(s->A,6,s->G);if(kind)d->U=184,d->need=72;
  if(!d->initialize([&](u64 a,u64 b){return cost(a,b,kind)>=0;},[&](u64 a,u64 b){return cost(a,b,kind)/2;},[]{return false;}))return 4;
  d->anneal(1e9,steps);d->filler_climb(1e9,65000);double val=d->cur/256;if(!kind)reference=val;int special=0,novel=0;for(auto u:d->unit)if(u.b>=0){double c0=cost(s->A[u.a],s->A[u.b],false),c1=cost(s->A[u.a],s->A[u.b],kind);special+=c0<0||c1<c0-1e-6;novel+=c0<0;}
  int access_col=std::find(d->handle.begin(),d->handle.end(),h)-d->handle.begin();double col=0,hole=0,generic=0;for(int c=0;c<d->H;c++)col+=d->colcost(c)/256,hole+=d->hcost(c)/256;for(auto u:d->unit)generic+=d->gc(u)/256;
  std::cout<<(kind?",":"")<<"{\"kind\":"<<kind<<",\"model\":"<<val<<",\"difference\":"<<val-reference<<",\"special\":"<<special<<",\"novel\":"<<novel<<",\"access_col\":"<<access_col<<",\"access_size\":"<<d->nc[access_col]<<",\"columns\":"<<col<<",\"holes\":"<<hole<<",\"generic\":"<<generic<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
