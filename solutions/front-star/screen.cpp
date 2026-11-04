#define main approximate_old_main
#include "approx.hpp"
#undef main
#include <set>
int main(int argc,char**argv){
 if(argc<2)return 2;int iterations=argc>2?std::stoi(argv[2]):1000,train=argc>3?std::stoi(argv[3]):1024;
 Model m(argv[1],8);if(m.W!=3)return 3;auto original=m.op;
 auto start=std::chrono::steady_clock::now();auto elapsed=[&](){return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
 double baseline=m.simulate(train,1000003);std::vector<std::pair<double,std::vector<int>>>ranked{{baseline,original}};
 std::mt19937_64 rng(38170931);std::set<std::vector<int>>seen;int valid=0;
 for(int it=0;it<iterations;it++){
  std::vector<int>root;for(int k=0;k<m.K;k++)if(m.allowed[k]==7)root.push_back(k);std::shuffle(root.begin(),root.end(),rng);int nr=1+rng()%std::min(3,int(root.size()));root.resize(nr);
  m.op.assign(m.K,0);for(int k:root)m.op[k]=7;
  for(int k=0;k<m.K;k++)if(!m.op[k]){
   std::vector<int>bits;for(int j=0;j<3;j++)if(m.allowed[k]>>j&1)bits.push_back(j);
   int j=bits[rng()%bits.size()];if(rng()%2)j=m.column[k];m.op[k]=1<<j;
  }
  if(!seen.insert(m.op).second)continue;if(!m.update())continue;valid++;
  double value=m.simulate(train,1000003);
  if(ranked.size()<24||value<ranked.back().first){ranked.push_back({value,m.op});std::sort(ranked.begin(),ranked.end());if(ranked.size()>24)ranked.pop_back();std::cerr<<"candidate "<<it<<" value "<<value<<" best "<<ranked[0].first<<" seconds "<<elapsed()<<'\n';}
 }
 m.width=64;m.op=original;m.update();double reference=m.simulate(16384,200000003);
 std::cout<<std::setprecision(12)<<"{\"baseline_train\":"<<baseline<<",\"baseline\":"<<reference<<",\"valid\":"<<valid<<",\"candidates\":[";
 std::vector<std::pair<double,std::vector<int>>>heldout;int i=0;for(auto&[v,op]:ranked){m.op=op;m.update();double result=m.simulate(16384,200000003);heldout.push_back({result,op});
  std::cout<<(i++?",":"")<<"{\"train\":"<<v<<",\"validation\":"<<result<<",\"difference\":"<<result-reference<<",\"opaque\":[";for(int k=0;k<m.K;k++)std::cout<<(k?",":"")<<op[k];std::cout<<"]}"<<std::flush;
 }
 std::sort(heldout.begin(),heldout.end());m.op=original;m.update();double finalbase=m.simulate(262144,81923132);
 std::cout<<"],\"final_baseline\":"<<finalbase<<",\"final\":[";
 for(int k=0;k<3&&k<int(heldout.size());k++){m.op=heldout[k].second;m.update();double result=m.simulate(262144,81923132);std::cout<<(k?",":"")<<"{\"value\":"<<result<<",\"difference\":"<<result-finalbase<<",\"opaque\":[";for(int j=0;j<m.K;j++)std::cout<<(j?",":"")<<m.op[j];std::cout<<"]}"<<std::flush;}
 std::cout<<"],\"seconds\":"<<elapsed()<<"}\n";
}
