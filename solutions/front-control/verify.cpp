#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#include "module.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <queue>
#include <random>
#include <utility>

int main(int argc,char**argv){
 std::ifstream in(argv[1]);int k,p,n;in>>k>>p>>n;assert(n==2);
 std::vector<int>op(k),ink(k);for(int i=0;i<k;i++){int id,col,color,allowed;in>>id>>col>>op[i]>>color>>allowed;ink[i]=color&op[i];}
 std::vector<FrontModel::Event>events;
 for(int u=0;u<p;u++){int paper,mask,color;in>>paper>>mask>>color;if(paper>=0||mask)events.push_back({paper,mask,color,1});}
 FrontModel model(op,ink,events);model.solve(1000,2e-7);long long checks=0;
 for(int index=0;index<=k;index++){
  const auto&v=model.variants[index];
  for(int open=0;open<4;open++)for(int goal=0;goal<9;goal++)if(!(FrontModel::need_mask(goal)&~open)){
   // Build a reverse graph independently from physical visibility and permutation search.
   std::vector<std::vector<int>> reverse(v.states);
   for(int s=0;s<v.states;s++){
    int cov=0;
    for(int from=0;from<v.n;from++){
     int paper=v.permutations[s][from];bool visible=op[paper]&open&~cov;cov|=op[paper];if(!visible)continue;
     for(int to=0;to<v.n;to++)if(from!=to){auto seq=v.permutations[s];seq.erase(seq.begin()+from);seq.insert(seq.begin()+to,paper);auto it=std::lower_bound(v.permutations.begin(),v.permutations.end(),seq);assert(it!=v.permutations.end()&&*it==seq);reverse[it-v.permutations.begin()].push_back(s);}
    }
   }
   std::vector<double>d(v.states,1e30);std::priority_queue<std::pair<double,int>,std::vector<std::pair<double,int>>,std::greater<std::pair<double,int>>>q;
   for(int s=0;s<v.states;s++){
    int seen=0,black=0;for(int paper:v.permutations[s]){black|=ink[paper]&~seen;seen|=op[paper];}
    if(!((black^FrontModel::need_color(goal))&FrontModel::need_mask(goal))){d[s]=v.bias[s];q.push({d[s],s});}
   }
   while(!q.empty()){auto[c,s]=q.top();q.pop();if(c!=d[s])continue;for(int old:reverse[s])if(d[old]>c+1){d[old]=c+1;q.push({d[old],old});}}
   const auto&path=v.fix[open][goal];
   for(int s=0;s<v.states;s++){
    if(d[s]>1e20){assert(path.value[s]>1e20);continue;}
    assert(std::abs(d[s]-path.value[s])<2e-6);int state=s,moves=0;
    while(path.action[state]>=0){int a=path.action[state],from=a/v.n,to=a%v.n;int seen=0;for(int i=0;i<from;i++)seen|=op[v.permutations[state][i]];assert(op[v.permutations[state][from]]&open&~seen);state=v.next[(size_t(state)*v.n+from)*v.n+to];assert(++moves<100);}
    assert(!((v.shown[state]^FrontModel::need_color(goal))&FrontModel::need_mask(goal)));assert(std::abs(moves+v.bias[state]-d[s])<2e-6);checks++;
   }
  }
 }
 std::cout<<"verified "<<checks<<" state / goal paths\n";
}
