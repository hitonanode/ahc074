#define main inherited_module_main
#include "module.hpp"
#undef main
#include <iomanip>
#include <functional>
#include <tuple>
struct Event {int paper,mask,color,count;};
struct Exact:Evaluator {
 std::vector<Event>events;std::vector<std::vector<int>>goals;double active=0;int iterations=0;
 Exact(const Model&m):Evaluator(m,1000){}
 void prepare_actual(const Design&d){
  rest.assign((1<<M.N)+M.K,{});goals.assign(events.size(),{});const int Q=1<<M.N;
  u64 all=0;for(auto o:d.op)all|=o;infeasible=all!=unsigned(Q-1);if(infeasible)return;
  for(int s=0;s<M.S;s++){
   const auto*p=&M.perm[s*M.K];u64 cov=0,display=0;unsigned visible=0;
   for(int i=0;i<M.K;i++){int k=p[i];u64 shown=d.op[k]&~cov;if(shown)visible|=1U<<i,rest[Q+k].push_back(s);display|=d.bk[k]&shown;cov|=d.op[k];}
   vis[s]=visible;tgt[s]=display;rest[display].push_back(s);
   for(int e=0;e<int(events.size());e++){auto q=events[e];if(q.paper<0){if(!((int(display)^q.color)&q.mask))goals[e].push_back(s);}else if(p[0]==q.paper&&int(display)==q.color)goals[e].push_back(s);}
  }
  for(auto&g:goals)infeasible+=g.empty();if(infeasible)return;
  pstart.assign(M.S+1,0);
  for(int y=0;y<M.S;y++){const auto*r=&M.succ[size_t(y)*M.K*M.K];for(unsigned v=vis[y];v;v&=v-1){int p=__builtin_ctz(v);for(int q=0;q<M.K;q++)if(p!=q)pstart[r[p*M.K+q]+1]++;}}
  for(int s=0;s<M.S;s++)pstart[s+1]+=pstart[s];pred.resize(pstart.back());fillp.assign(pstart.begin(),pstart.end()-1);
  for(int y=0;y<M.S;y++){const auto*r=&M.succ[size_t(y)*M.K*M.K];for(unsigned v=vis[y];v;v&=v-1){int p=__builtin_ctz(v);for(int q=0;q<M.K;q++)if(p!=q)pred[fillp[r[p*M.K+q]]++]=y;}}
 }
 void event_cost(int e){
  terminal=h;const int paper=events[e].paper;
  if(paper<0){propagate(goals[e]);return;}
  for(int s:goals[e])for(int depth=0;depth<M.K;depth++)terminal[s]=std::min(terminal[s],h[M.succ[size_t(s)*M.K*M.K+depth]]);
  propagate(goals[e],paper);const auto after=dist;
  for(int s:rest[(1<<M.N)+paper]){const auto*p=&M.perm[s*M.K];int pos=0;while(p[pos]!=paper)pos++;terminal[s]=after[M.succ[(size_t(s)*M.K+pos)*M.K]];}
  propagate(rest[(1<<M.N)+paper]);
 }
 double solve_actual(int limit=500,double tol=1e-7,double cutoff=1e100){
  if(infeasible)return 1e9;
  int count=0;for(auto e:events)count+=e.count;active=double(count)/256;
  for(int it=0;it<limit;it++){
   Th.assign(M.S,0);for(int e=0;e<int(events.size());e++){event_cost(e);double p=double(events[e].count)/count;for(int s=0;s<M.S;s++)Th[s]+=p*dist[s];}
   double lo=1e100,hi=-1e100,mean=0;for(int s=0;s<M.S;s++){double d=Th[s]-h[s];lo=std::min(lo,d);hi=std::max(hi,d);mean+=Th[s];}mean/=M.S;
   g_lo=lo*active;g_hi=hi*active;for(int s=0;s<M.S;s++)h[s]=.4*h[s]+.6*(Th[s]-mean);iterations=it+1;
   if((hi-lo)*active<tol||g_lo>=cutoff)break;
  }return (g_lo+g_hi)/2;
 }
};
int main(int argc,char**argv){
 if(argc<2)return 2;std::ifstream in(argv[1]);int K=0,P=0,N=0;in>>K>>P>>N;if(!in)return 4;if(K>9||N>3||P!=256)return 3;
 int rounds=argc>2?std::stoi(argv[2]):1;bool doubles=argc>3?std::stoi(argv[3]):false;auto start=std::chrono::steady_clock::now();
 Model model;model.build(N,K);Design original;original.op.resize(K);original.bk.resize(K);std::vector<int>color(K),allowed(K),weights(K),id(K),col(K);
 for(int k=0;k<K;k++){in>>id[k]>>col[k]>>original.op[k]>>color[k]>>allowed[k];original.bk[k]=color[k]&original.op[k];}
 std::map<std::tuple<int,int,int>,int>counts;for(int u=0;u<P;u++){int k,m,c;in>>k>>m>>c;if(k>=0)weights[k]++,counts[{k,(1<<N)-1,c}]++;else if(m)counts[{k,m,c&m}]++;}if(!in)return 4;
 Exact e(model);for(auto[key,n]:counts){auto[k,m,c]=key;e.events.push_back({k,m,c,n});}
 e.prepare_actual(original);double baseline=e.solve_actual(1500,2e-6);double base_gap=e.g_hi-e.g_lo;
 std::cerr<<"baseline "<<baseline<<" gap "<<base_gap<<" iters "<<e.iterations<<" seconds "<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<'\n';
 Design best=original,chain=original;double bv=baseline,cv=baseline;int tested=0,valid=0,pruned=0,total_iterations=0;
 auto best_bias=e.h;
 std::vector<std::vector<int>>identity(K);
 for(int k=0;k<K;k++){
  identity[k]={color[k],allowed[k]};
  for(int c=0;c<(1<<N);c++){int n=0;for(auto[key,count]:counts){auto[p,m,b]=key;if(p==k&&b==c)n+=count;}identity[k].push_back(n);}
 }
 std::map<u64,bool>seen;
 // Shared papers may omit differing bits inside a prefix. Testing raw masks
 // for subset nesting would incorrectly classify those ordinary columns.
 auto staircase=[&](const Design&d){
  std::vector<int>windows(N);std::iota(windows.begin(),windows.end(),0);
  do{
   bool all=true;
   for(int k=0;k<K;k++){
    unsigned prefix=0;bool found=false;
    for(int w:windows){prefix|=1U<<w;if((prefix&unsigned(allowed[k]))==d.op[k])found=true;}
    if(!found){all=false;break;}
   }
   if(all)return true;
  }while(std::next_permutation(windows.begin(),windows.end()));
  return false;
 };
 auto signature=[&](const Design&d){
  auto masks=d.op;
  for(int k=0;k<K;k++){
   bool first=true;for(int j=0;j<k;j++)if(identity[j]==identity[k])first=false;
   if(!first)continue;std::vector<int>positions;std::vector<u64>values;
   for(int j=k;j<K;j++)if(identity[j]==identity[k])positions.push_back(j),values.push_back(masks[j]);
   std::sort(values.begin(),values.end());for(int i=0;i<int(positions.size());i++)masks[positions[i]]=values[i];
  }
  u64 key=0;for(int k=0;k<K;k++)key|=masks[k]<<(3*k);return key;
 };
 for(int round=0;round<rounds;round++){
  auto before=best;double old=bv;
  auto consider=[&](Design candidate){
   u64 key=signature(candidate);if(seen.contains(key))return;seen[key]=true;
   tested++;e.prepare_actual(candidate);if(e.infeasible)return;valid++;e.h=best_bias;
   double value=e.solve_actual(3000,2e-6,bv-1e-5);total_iterations+=e.iterations;
   bool cut=e.g_lo>=bv-1e-5;pruned+=cut;
   std::cerr<<"candidate "<<tested<<" lower "<<e.g_lo<<" upper "<<e.g_hi<<" iters "<<e.iterations<<" pruned "<<cut<<'\n';
   if(cut)return;
   bool nested=staircase(candidate);
   if(nested&&value<cv-1e-5)cv=value,chain=candidate;
   if(e.g_hi<bv-1e-5){bv=value;best=candidate;best_bias=e.h;std::cerr<<"best "<<round<<' '<<tested<<" value "<<bv<<" gap "<<e.g_hi-e.g_lo<<" nested "<<nested<<'\n';}
  };
  for(int k=0;k<K;k++)for(unsigned mask=1;mask<unsigned(1<<N);mask++)if(!(mask&~allowed[k])&&mask!=before.op[k]){
   Design candidate=before;candidate.op[k]=mask;candidate.bk[k]=color[k]&mask;consider(candidate);
  }
  if(doubles)for(int k=0;k<K;k++)for(int j=k+1;j<K;j++)
   for(unsigned a=1;a<unsigned(1<<N);a++)if(!(a&~allowed[k])&&a!=before.op[k])
    for(unsigned b=1;b<unsigned(1<<N);b++)if(!(b&~allowed[j])&&b!=before.op[j]){
     Design candidate=before;candidate.op[k]=a;candidate.bk[k]=color[k]&a;candidate.op[j]=b;candidate.bk[j]=color[j]&b;consider(candidate);
    }
  if(bv>=old-1e-5)break;
 }
 double best_gap=base_gap;if(signature(best)!=signature(original)){e.prepare_actual(best);std::fill(e.h.begin(),e.h.end(),0);bv=e.solve_actual(3000,2e-6);best_gap=e.g_hi-e.g_lo;}
 std::cout<<std::setprecision(12)<<"{\"K\":"<<K<<",\"N\":"<<N<<",\"baseline\":"<<baseline<<",\"baseline_gap\":"<<base_gap<<",\"best\":"<<bv<<",\"best_gap\":"<<best_gap<<",\"chain\":"<<cv<<",\"difference\":"<<bv-baseline<<",\"difference_chain\":"<<bv-cv<<",\"staircase\":"<<staircase(best)<<",\"active\":"<<e.active<<",\"tested\":"<<tested<<",\"valid\":"<<valid<<",\"pruned\":"<<pruned<<",\"iterations\":"<<total_iterations<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"opaque\":[";
 for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best.op[k];std::cout<<"]}\n";
}
