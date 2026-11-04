#define OVERPATCH_NO_MAIN
#include "probe.cpp"
int main(int argc,char**argv){
 if(argc<3)return 2;Search s;if(!s.load(argv[1],argv[2]))return 3;
 s.need=71;s.charge=0;auto base=s.eval(0,0,38,0);Search::Eval best;u64 bm=0,bc=0;int tested=0,feasible=0;
 auto inspect=[&](const std::vector<int>&bits){u64 mask=0;for(int j:bits)mask|=1ULL<<j;
  for(unsigned pattern=0;pattern<(1U<<bits.size());pattern++){u64 color=0;for(int j=0;j<int(bits.size());j++)if(pattern>>j&1)color|=1ULL<<bits[j];auto e=s.eval(mask,color,38,0);tested++;feasible+=e.selected==71;if(e.value<best.value){best=e;bm=mask;bc=color;}}
 };
 for(int a=0;a<s.G;a++){inspect({a});for(int b=a+1;b<s.G;b++){inspect({a,b});for(int c=b+1;c<s.G;c++)inspect({a,b,c});}}
 std::cout<<std::setprecision(12)<<"{\"base\":"<<base.value<<",\"best_nonempty\":"<<best.value<<",\"difference\":"<<best.value-base.value<<",\"selected\":"<<best.selected<<",\"novel\":"<<best.novel<<",\"special\":"<<best.special<<",\"mask\":"<<bm<<",\"color\":"<<bc<<",\"tested\":"<<tested<<",\"feasible\":"<<feasible<<"}\n";
}
