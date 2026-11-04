#define main count_only_main
#include "probe.cpp"
#undef main
#include <cassert>
int main(int argc,char**argv){if(argc<2)return 2;auto p=std::make_unique<Problem>(argv[1],6,38,0);std::mt19937_64 rng(734644);
for(int test=0;test<1000;test++){
 Rows r{};std::array<int,20> order{};std::iota(order.begin(),order.begin()+6,0);std::shuffle(order.begin(),order.begin()+6,rng);
 for(int i=5;i>=0;i--)for(int j=i+1;j<6;j++)if(rng()&1)r[order[i]]|=(1U<<order[j])|r[order[j]];
 double total=0;for(int sample=0;sample<8;sample++){
  std::array<int,6> seq;for(int x=0;x<6;x++)seq[std::popcount(p->prefixes[sample][x])]=x;
  int best=6;for(unsigned keep=0;keep<64;keep++){bool ok=true;for(int i=0;i<6;i++)if(keep>>i&1)for(int j=i+1;j<6;j++)if((keep>>j&1)&&(r[seq[j]]>>seq[i]&1))ok=false;if(ok)best=std::min(best,6-std::popcount(keep));}total+=best;
 }assert(std::abs(total/8-p->lower_cost(r))<1e-10);
}std::cout<<"1000 partial orders x 8 starting orders: subset and matching costs agree\n";return 0;}
