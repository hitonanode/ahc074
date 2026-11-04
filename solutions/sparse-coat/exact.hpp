#include <unordered_map>

// Reverse BFS prices only legal visible-sheet moves. The target is a partial
// order, so every satisfying permutation is an initial zero-distance state.
struct ExactGraph {
 std::vector<std::array<int,6>> permutations;
 std::vector<std::array<unsigned,6>> below;
 std::vector<std::vector<int>> reverse;
 std::unordered_map<u64,double> cache;
 explicit ExactGraph(const Comparator&comp){
  std::array<int,6>p{0,1,2,3,4,5};
  do{permutations.push_back(p);}while(std::next_permutation(p.begin(),p.end()));
  below.resize(720);reverse.resize(720);
  for(int state=0;state<720;state++){
   auto order=permutations[state];unsigned mask=0;u64 covered=0;
   for(int i=5;i>=0;i--){below[state][order[i]]=mask;mask|=1U<<order[i];}
   for(int pos=0;pos<6;pos++){
    int paper=order[pos];bool visible=bool(comp.opq[paper]&~covered);covered|=comp.opq[paper];
    if(!visible)continue;
    for(int depth=0;depth<6;depth++)if(depth!=pos){
     auto next=order;int x=next[pos];
     if(pos<depth)for(int i=pos;i<depth;i++)next[i]=next[i+1];
     else for(int i=pos;i>depth;i--)next[i]=next[i-1];
     next[depth]=x;
     int to=std::lower_bound(permutations.begin(),permutations.end(),next)-permutations.begin();
     assert(to<720&&permutations[to]==next);reverse[to].push_back(state);
    }
   }
  }
 }
 double one(const std::array<unsigned,12>&relations){
  u64 key=0;for(int k=0;k<6;k++){if(relations[k]>>k&1)return -1;key|=u64(relations[k])<<(8*k);}
  if(auto it=cache.find(key);it!=cache.end())return it->second;
  std::array<int,720>dist,queue;dist.fill(-1);int begin=0,end=0;
  for(int s=0;s<720;s++){
   bool valid=true;for(int k=0;k<6;k++)if(relations[k]&~below[s][k]){valid=false;break;}
   if(valid)dist[s]=0,queue[end++]=s;
  }
  if(!end)return cache[key]=-1;
  while(begin<end){int s=queue[begin++];for(int old:reverse[s])if(dist[old]<0){dist[old]=dist[s]+1;queue[end++]=old;}}
  if(end<720)return cache[key]=-1;
  double result=std::accumulate(dist.begin(),dist.end(),0)/720.;cache[key]=result;return result;
 }
};
