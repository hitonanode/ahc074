#include "model.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto solver=head::load(argv[1],argv[2]);if(!solver)return 3;auto&s=*solver;
 std::vector<int>ids;for(int k=0;k<6;k++)ids.push_back(k);
 int column_size=0;for(int k=7;k<K;k++)column_size+=s.col_of[k]==0;
 for(int color=0;color<2;color++){
  int chosen=-1,weight=-1;for(int k=7;k<K;k++)if(s.col_of[k]==0&&int(s.h_blk[k]&1)==color){int w=std::count(s.ded.begin(),s.ded.end(),k);if(w>weight){weight=w;chosen=k;}}
  assert(chosen>=0);ids.push_back(chosen);
 }
 u64 bit=1ULL<<s.handle[0],mask=s.gmask|bit;std::vector<u64>op,black;for(int k:ids){op.push_back(s.paper[k].opaque&mask);black.push_back(s.paper[k].black&mask);}
 std::map<std::tuple<int,u64,u64>,int>count;
 for(int u=0;u<P;u++){int d=s.ded[u],own=d==ids[6]?0:d==ids[7]?1:-1;u64 need=mask&~(own>=0?op[own+6]:s.paper[d].opaque);u64 color=s.A[u]&need;if(own>=0||need)count[{own,need,color}]++;}
 std::vector<Mixed::Event>events;for(auto[key,n]:count){auto[k,m,c]=key;events.push_back({k,m,c,n});}
 std::cout<<std::setprecision(12)<<"{\"column_size\":"<<column_size<<",\"papers\":["<<ids[6]<<","<<ids[7]<<"],\"variants\":[";
 Mixed original(op,black,events,mask,false);assert(original.feasible);original.solve(200,1e-6);double best=original.upper;int best_code=0;
 std::cout<<"{\"code\":0,\"lower\":"<<original.lower<<",\"upper\":"<<original.upper<<",\"iterations\":"<<original.iterations<<",\"seconds\":"<<original.seconds<<"}"<<std::flush;
 int infeasible=0;std::vector<int>codes;for(int code=1;code<729;code++)codes.push_back(code);
 std::stable_sort(codes.begin(),codes.end(),[](int a,int b){auto count=[](int x){int n=0;for(int k=0;k<6;k++){n+=x%3!=0;x/=3;}return n;};return count(a)<count(b);});
 for(int code:codes){
  auto o=op,b=black;int v=code;for(int k=0;k<6;k++){int color=v%3;v/=3;if(color)o[k]|=bit;if(color==2)b[k]|=bit;}
  Mixed model(o,b,events,mask,false);if(!model.feasible){infeasible++;continue;}
  model.h=original.h;model.solve(200,1e-6,best-1e-7);
  if(model.upper<best){best=model.upper;best_code=code;}
  std::cout<<",{\"code\":"<<code<<",\"lower\":"<<model.lower<<",\"upper\":"<<model.upper<<",\"iterations\":"<<model.iterations<<",\"seconds\":"<<model.seconds<<"}"<<std::flush;
 }
 std::cout<<"],\"best\":"<<best<<",\"best_code\":"<<best_code<<",\"infeasible\":"<<infeasible<<"}\n";
}
