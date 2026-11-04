#include "model.hpp"
int main(int argc,char**argv){
 if(argc<2)return 2;Model m(argv[1],32);assert(m.W==2);assert(m.update());
 auto initial=m.op;int train=argc>2?std::stoi(argv[2]):16384,validation=argc>3?std::stoi(argv[3]):131072;
 double begin=std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count()*CLOCK_SCALE;
 double baseline=m.simulate(train,718000003),best=baseline;int selected=-1;std::vector<double>scores;
 for(int k=0;k<m.K;k++)if(m.column[k]==0&&(m.allowed[k]&2)&&!(m.op[k]&2)){
  m.op[k]|=2;assert(m.update());double score=m.simulate(train,718000003);scores.push_back(score);
  if(score<best){best=score;selected=k;}m.op=initial;assert(m.update());
 }
 std::cout<<std::setprecision(12)<<"{\"papers\":"<<m.K<<",\"candidates\":"<<scores.size()<<",\"selected\":"<<selected<<",\"baseline_train\":"<<baseline<<",\"train\":"<<best<<",\"validation\":[";
 for(int mode=0;mode<2;mode++){
  m.width=mode?64:32;m.op=initial;m.update();double reference=m.simulate(validation,331000003);long long reference_fallback=m.fallback_calls;
  if(selected>=0)m.op[selected]|=2;m.update();double value=m.simulate(validation,331000003);
  std::cout<<(mode?",":"")<<"{\"width\":"<<m.width<<",\"baseline\":"<<reference<<",\"value\":"<<value<<",\"difference\":"<<value-reference<<",\"fallback\":"<<m.fallback_calls<<",\"baseline_fallback\":"<<reference_fallback<<"}"<<std::flush;
 }
 double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count()*CLOCK_SCALE-begin;
 std::cout<<"],\"seconds\":"<<seconds<<"}\n";
}
