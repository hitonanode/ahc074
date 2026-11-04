#include "saved.hpp"
int main(int argc,char**argv){
 auto solver=head::load(argv[1],argv[2]);if(!solver)return 2;auto&s=*solver;std::vector<int>ids;for(int k=0;k<6;k++)ids.push_back(k);
 for(int color=0;color<2;color++){int chosen=-1,w=-1;for(int k=7;k<K;k++)if(s.col_of[k]==0&&int(s.h_blk[k]&1)==color){int n=std::count(s.ded.begin(),s.ded.end(),k);if(n>w){chosen=k;w=n;}}if(chosen<0)return 3;ids.push_back(chosen);}
 u64 mask=s.gmask|(1ULL<<s.handle[0]);auto feasible=[&](u64 target,u64 required){unsigned used=0;for(;;){bool progress=false;for(int i=0;i<8;i++)if(!(used>>i&1)&&!((s.paper[ids[i]].black^target)&s.paper[ids[i]].opaque&required)){required&=~s.paper[ids[i]].opaque;used|=1U<<i;progress=true;}if(!required)return true;if(!progress)return false;}};
 int near=0,base=0,mixed=0;std::vector<std::pair<int,int>>rescued;
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
  if(s.ded[a]==ids[6]||s.ded[a]==ids[7]||s.ded[b]==ids[6]||s.ded[b]==ids[7])continue;
  if(__builtin_popcountll((s.A[a]^s.A[b])&kActiveWindows)>26)continue;
  near++;bool old=s.comparator.compatible(s.A[a],s.A[b]);base+=old;
  u64 need=(s.A[a]^s.A[b])&mask;bool now=feasible(s.A[a],need)&&feasible(s.A[b],need);mixed+=now;if(now&&!old)rescued.push_back({a,b});
 }
 std::cout<<"{\"near\":"<<near<<",\"base\":"<<base<<",\"mixed\":"<<mixed<<",\"rescued\":[";for(int i=0;i<int(rescued.size());i++)std::cout<<(i?",":"")<<"["<<rescued[i].first<<","<<rescued[i].second<<"]";std::cout<<"]}\n";
}
