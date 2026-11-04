#include "common.hpp"
void reorder(Solver&s,int mode){
 s.init_adaptive();std::vector<int>order{6,0,1,2,3,4,5};
 for(int c=0;c<s.H;c++){
  std::array<std::vector<int>,2>v;
  for(int k:s.order)if(s.col_of[k]==c)v[s.paper[k].black>>s.handle[c]&1].push_back(k);
  for(auto&g:v)std::stable_sort(g.begin(),g.end(),[&](int a,int b){return s.adaptive_weights[a]>s.adaptive_weights[b];});
  int majority=s.adaptive_holes[c][1]>s.adaptive_holes[c][0];
  auto make=[&](int first){
   auto rows=v;std::vector<int>result;for(int b:{first,1-first}){assert(!rows[b].empty());result.push_back(rows[b][0]);rows[b].erase(rows[b].begin());}
   if(mode==1){while(!rows[0].empty()||!rows[1].empty()){int b=rows[1].size()>rows[0].size();result.push_back(rows[b][0]);rows[b].erase(rows[b].begin());}}
   else{std::vector<int>tail=rows[0];tail.insert(tail.end(),rows[1].begin(),rows[1].end());std::stable_sort(tail.begin(),tail.end(),[&](int a,int b){return s.adaptive_weights[a]>s.adaptive_weights[b];});result.insert(result.end(),tail.begin(),tail.end());}
   return result;
  };
  auto chosen=make(majority);
  if(mode==3){auto opposite=make(1-majority);auto value=[&](auto&row){double total=0;std::array<int,2>first{-1,-1};for(int i=0;i<int(row.size());i++){int b=s.paper[row[i]].black>>s.handle[c]&1;if(first[b]<0)first[b]=i;total+=i*s.adaptive_weights[row[i]]/P;}return total+s.adaptive_holes[c][0]*first[0]+s.adaptive_holes[c][1]*first[1];};if(value(opposite)<value(chosen))chosen=opposite;}
  order.insert(order.end(),chosen.begin(),chosen.end());
 }
 assert(int(order.size())==K);s.order=order;
}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto d=recover(*base);materialize(*base,*d);
 int seqs=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  Solver s=*base;if(mode)reorder(s,mode);auto initial=s.save();long long total=0,early=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto path=s.process(u);total+=path.size();if(t<100)early+=path.size();wrong+=s.display()!=s.A[u];}}
  double average=double(total)/(seqs*1024);if(!mode)reference=average;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<average<<",\"difference\":"<<average-reference<<",\"early_moves\":"<<double(early)/seqs<<",\"wrong\":"<<wrong<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
