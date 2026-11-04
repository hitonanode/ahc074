#include "saved.hpp"
struct HeadPool {
 Solver&s;int S,H;struct Sample{int target;u64 holes,bad,head;};std::vector<Sample>samples;
 std::vector<std::array<std::vector<int>,2>> choices;std::vector<std::array<int,2>> chosen;
 // For each sample and paper, gain[lo] is the corrected number of windows
 // minus placement/return, before charging the extra extraction of color 2.
 std::vector<std::array<float,26>>gain;
 double before=0,after=0;int changed=0;double seconds=0;
 HeadPool(Solver&source,int copies,u64 seed):s(source),S(P*copies),H(source.H){
  choices.resize(H);chosen.resize(H);std::vector<int>direct(K);for(int d:s.ded)direct[d]++;
  for(int c=0;c<H;c++)for(int color=0;color<2;color++){
   int high=0;for(int k=7;k<K;k++)if(s.col_of[k]==c&&int(s.h_blk[k]>>c&1)==color)high=std::max(high,direct[k]);
   for(int k=7;k<K;k++)if(s.col_of[k]==c&&int(s.h_blk[k]>>c&1)==color&&direct[k]==high)choices[c][color].push_back(k);
   assert(!choices[c][color].empty());chosen[c][color]=*std::max_element(choices[c][color].begin(),choices[c][color].end(),[&](int a,int b){return s.adaptive_weights[a]<s.adaptive_weights[b];});
  }
  std::mt19937_64 rng(seed);
  for(int u=0;u<P;u++)for(int q=0;q<copies;q++){
   u64 head=0;for(int c=0;c<H;c++){double sum=s.adaptive_holes[c][0]+s.adaptive_holes[c][1];double p=sum?s.adaptive_holes[c][1]/sum:.5;if((rng()>>11)*(1.0/9007199254740992.0)<p)head|=1ULL<<c;}
   u64 holes=low_bits(H)&~s.h_opq[s.ded[u]];samples.push_back({u,holes,(s.handle_bits(s.A[u])^head)&holes,head});
  }
  gain.resize(S*K);
  for(int z=0;z<S;z++)for(int k=7;k<K;k++){
   auto&g=gain[z*K+k];g.fill(-100);int c=s.col_of[k];if(c<0||k==s.ded[samples[z].target])continue;
   u64 mismatch=(s.h_blk[k]^s.handle_bits(s.A[samples[z].target]))&s.h_opq[k]&samples[z].holes;
   int lo=mismatch?64-__builtin_clzll(mismatch):0;if(lo>c)continue;
   for(int i=lo;i<=c;i++)g[i]=__builtin_popcountll(samples[z].bad&s.h_opq[k]&~low_bits(i))-1.6f;
  }
 }
 using Edges=std::array<std::array<float,26>,26>;
 void edges(int z,Edges&e)const{
  for(auto&r:e)r.fill(-100);
  for(int c=0;c<H;c++)for(int color=0;color<2;color++){
   int k=chosen[c][color],depth=color!=int(samples[z].head>>c&1);auto&g=gain[z*K+k];for(int i=0;i<=c;i++)e[c+1][i]=std::max(e[c+1][i],g[i]-depth);
  }
 }
 static float forward(const Edges&e,int H,int skip,std::array<float,26>&f){f.fill(0);for(int end=1;end<=H;end++){f[end]=f[end-1];if(end==skip)continue;for(int i=0;i<end;i++)f[end]=std::max(f[end],f[i]+e[end][i]);}return f[H];}
 double value()const{double total=0;for(int z=0;z<S;z++){Edges e;edges(z,e);std::array<float,26>f;total+=__builtin_popcountll(samples[z].bad)-forward(e,H,-1,f);}return total/S;}
 void optimize(int rounds){
  auto start=std::chrono::steady_clock::now();auto original=chosen;before=value();
  std::vector<float>without(S);std::array<std::vector<std::vector<float>>,2>candidate;
  for(int round=0;round<rounds;round++)for(int order=0;order<H;order++){
   int c=round%2?order:H-1-order;
   for(int color=0;color<2;color++)candidate[color].assign(choices[c][color].size(),std::vector<float>(S));
   for(int z=0;z<S;z++){
    Edges e;edges(z,e);std::array<float,26>f,b{},omitted;forward(e,H,-1,f);without[z]=forward(e,H,c+1,omitted);
    for(int i=H-1;i>=0;i--){b[i]=b[i+1];for(int end=i+1;end<=H;end++)b[i]=std::max(b[i],e[end][i]+b[end]);}
    for(int color=0;color<2;color++)for(int x=0;x<int(choices[c][color].size());x++){
     int k=choices[c][color][x],depth=color!=int(samples[z].head>>c&1);float v=-100;for(int i=0;i<=c;i++)v=std::max(v,f[i]+gain[z*K+k][i]-depth+b[c+1]);candidate[color][x][z]=v;
    }
   }
   double best=-1e100;int bx=0,by=0;
   for(int x=0;x<int(choices[c][0].size());x++)for(int y=0;y<int(choices[c][1].size());y++){
    double sum=0;for(int z=0;z<S;z++)sum+=std::max(without[z],std::max(candidate[0][x][z],candidate[1][y][z]));
    // Keep the prior champion on ties to avoid changing irrelevant ranks.
    if(sum>best+1e-6||(std::abs(sum-best)<=1e-6&&choices[c][0][x]==chosen[c][0]&&choices[c][1][y]==chosen[c][1]))best=sum,bx=x,by=y;
   }
   chosen[c][0]=choices[c][0][bx];chosen[c][1]=choices[c][1][by];
  }
  after=value();for(int c=0;c<H;c++)for(int color=0;color<2;color++)if(chosen[c][color]!=original[c][color]){changed++;std::swap(s.adaptive_weights[chosen[c][color]],s.adaptive_weights[original[c][color]]);}
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
int main(int argc,char**argv){if(argc<3)return 2;int seqs=argc>3?std::stoi(argv[3]):8;int samples=argc>4?std::stoi(argv[4]):4;int rounds=argc>5?std::stoi(argv[5]):2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 base->init_adaptive();base->comparator.build_tables();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<2;mode++){Solver s=*base;HeadPool model(s,samples,730000003);if(mode)model.optimize(rounds);auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(initial);std::mt19937_64 rng(140000007ULL*(q+1));int previous=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):previous;if(t&&u>=previous)u++;previous=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double avg=double(total)/(seqs*1024);if(mode==0)reference=avg;std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"model_before\":"<<model.before<<",\"model_after\":"<<model.after<<",\"changed\":"<<model.changed<<",\"samples\":"<<samples<<",\"rounds\":"<<rounds<<",\"seconds\":"<<model.seconds<<"}"<<std::flush;
 }std::cout<<"]\n";
}
