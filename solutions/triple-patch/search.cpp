#include "comparison.hpp"
struct Aux{std::array<U,2>op{},black{};};
struct Candidate{std::array<int,3>a{};std::array<U,3>residual{};U diff=0;int n=0;double fee=0,rank=0;};
struct Result{double cost=1e9;int triples=0,merges=0,catalog=0;};
struct Patch{
 Problem base;int added;double tripleprice,discount;
 std::array<U,8>op{},black{};std::vector<Candidate>candidates;
 std::mt19937_64 rng{185171173};
 explicit Patch(const char*path,int n,double price,double disc):base(path),added(n),tripleprice(price),discount(disc){
  assert(base.M==6);
  for(int j=0;j<base.G;j++){auto[a,b]=base.edge[j];op[a]|=1ULL<<j;op[b]|=1ULL<<j;black[a]|=1ULL<<j;}
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(base.compatible[a][b]){
   Candidate c;c.a={a,b,-1};c.n=2;c.diff=base.A[a]^base.A[b];
   for(int t:{a,b}){Rows rows{};assert(base.extend(rows,base.A[t],c.diff&base.gm));c.fee+=base.lower_cost(rows);}
   c.fee+=.4*c.n*std::popcount(c.diff&~base.gm)+.04*c.n*std::popcount(c.diff);c.rank=c.fee;candidates.push_back(c);
  }
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)for(int c=b+1;c<256;c++){
   U diff=(base.A[a]^base.A[b])|(base.A[a]^base.A[c]);if(std::popcount(diff)>38)continue;
   Candidate x;x.a={a,b,c};x.n=3;x.diff=diff;
   for(int t=0;t<3;t++)x.residual[t]=peel(base.A[x.a[t]],diff&base.gm,6);
   x.fee=3*price+.4*3*std::popcount(diff&~base.gm)+.04*3*std::popcount(diff);
   x.rank=(x.fee-discount)/2;candidates.push_back(x);
  }
  std::sort(candidates.begin(),candidates.end(),[](const auto&a,const auto&b){return a.rank<b.rank;});
 }
 U peel(U target,U holes,int count)const{
  for(int iteration=0;iteration<count&&holes;iteration++){
   U before=holes;
   for(int k=0;k<count;k++)if(!((target^black[k])&op[k]&holes))holes&=~op[k];
   if(before==holes)break;
  }
  return holes;
 }
 Result evaluate(const Aux&aux,bool full=false){
  for(int k=0;k<added;k++){op[6+k]=aux.op[k];black[6+k]=aux.black[k];}
  std::array<bool,256>used{};double sum=0;Result r;r.cost=0;
  for(auto&c:candidates){
   bool occupied=false;for(int t=0;t<c.n;t++)occupied|=used[c.a[t]];
   if(occupied&&!full)continue;
   bool valid=true;if(c.n==3)for(int t=0;t<3;t++)if(peel(base.A[c.a[t]],c.residual[t],6+added)){valid=false;break;}
   if(!valid)continue;r.catalog+=c.n==3;
   if(occupied||r.merges+c.n-1>71+added)continue;
   for(int t=0;t<c.n;t++)used[c.a[t]]=true;
   sum+=c.rank*(c.n-1);r.merges+=c.n-1;r.triples+=c.n==3;
   if(r.merges==71+added&&!full)break;
  }
  r.cost=sum+100*(71+added-r.merges);return r;
 }
 Aux mutation(Aux next){
  int p=rng()%added,j=rng()%base.G,kind=rng()%10;
  if(kind<6){unsigned v=rng()%3;next.op[p]&=~(1ULL<<j);next.black[p]&=~(1ULL<<j);if(v<2)next.op[p]|=1ULL<<j;if(v==1)next.black[p]|=1ULL<<j;}
  else if(kind<8){int k=rng()%base.G;for(U*bits:{&next.op[p],&next.black[p]})if(((*bits>>j)^(*bits>>k))&1)*bits^=(1ULL<<j)|(1ULL<<k);}
  else if(kind==8&&added==2){next.op[1-p]=next.op[p];next.black[1-p]=next.op[p]^next.black[p];}
  else{
   auto&c=candidates[rng()%candidates.size()];if(c.n==3){int t=rng()%3;U q=c.residual[t];if(q){unsigned k=std::countr_zero(q);next.op[p]|=1ULL<<k;next.black[p]=(next.black[p]&~(1ULL<<k))|(base.A[c.a[t]]&(1ULL<<k));}}
  }
  return next;
 }
};
int main(int argc,char**argv){
 if(argc<2)return 2;int n=argc>2?std::stoi(argv[2]):2;double price=argc>3?std::stod(argv[3]):3.5,seconds=argc>4?std::stod(argv[4]):120;int maxbits=argc>5?std::stoi(argv[5]):20;
 auto start=std::chrono::steady_clock::now();auto elapsed=[&](){return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
 double discount=argc>6?std::stod(argv[6]):8;Patch p(argv[1],n,price,discount);Aux current,best;auto cr=p.evaluate(current),br=cr;double initial=cr.cost;int iterations=0;
 while(elapsed()<seconds){
  Aux next=p.mutation(current);if(std::popcount(next.op[0])>maxbits||std::popcount(next.op[1])>maxbits)continue;
  auto r=p.evaluate(next);double temperature=2*std::pow(.015,elapsed()/seconds);
  if(r.cost<=cr.cost||std::generate_canonical<double,53>(p.rng)<std::exp((cr.cost-r.cost)/temperature)){current=next;cr=r;}
  if(cr.cost<br.cost){best=current;br=cr;std::cerr<<"best "<<iterations<<" cost "<<br.cost<<" triples "<<br.triples<<" bits "<<std::popcount(best.op[0])<<' '<<std::popcount(best.op[1])<<" seconds "<<elapsed()<<'\n';}
  iterations++;
 }
 br=p.evaluate(best,true);
 std::cout<<std::setprecision(12)<<"{\"M\":"<<6+n<<",\"G\":"<<p.base.G<<",\"discount\":"<<discount<<",\"price\":"<<price<<",\"initial\":"<<initial<<",\"best\":"<<br.cost<<",\"selected_triples\":"<<br.triples<<",\"catalog\":"<<br.catalog<<",\"merges\":"<<br.merges<<",\"iterations\":"<<iterations<<",\"seconds\":"<<elapsed()<<",\"patterns\":[";
 for(int j=0;j<63;j++){if(j)std::cout<<',';if(j>=p.base.G){std::cout<<"null";continue;}unsigned white=0,black=0;for(int k=0;k<6+n;k++)if(p.op[k]>>j&1){if(p.black[k]>>j&1)black|=1U<<k;else white|=1U<<k;}std::cout<<'['<<white<<','<<black<<']';}
 std::cout<<"]}\n";
}
