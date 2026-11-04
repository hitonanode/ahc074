#include "common.hpp"
#include <unordered_set>
struct Choice {u64 mask=0,black=0;int handle=0,count=0;double gain=0;};
int main(int argc,char**argv){auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto dp=recover(*base);auto&d=*dp;d.refresh_reset();
 std::vector<int>pairs;for(int x=0;x<d.U;x++)if(d.unit[x].b>=0)pairs.push_back(x);
 std::array<double,3>charges{1,1.6,2};std::array<Choice,3>best{};std::unordered_set<u64>seen;long long tested=0;
 auto hcost=[&](int j,int x,int y){double t=d.reset_targets[j];return 1.6*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);};
 std::vector<double>marginal(d.H);for(int j=0;j<d.H;j++)if(d.hn[j][0]&&d.hn[j][1])marginal[j]=d.hcost(j)-hcost(j,d.hn[j][0]-1,d.hn[j][1]-1);
 for(int h=1;h<d.H;h++)for(int x:pairs){auto u=d.unit[x];if(u.c>=h)continue;u64 difference=(d.hb[u.a]^d.hb[u.b])&low_bits(u.c+1);
  for(u64 mask=difference;mask;mask=(mask-1)&difference){if(__builtin_popcountll(mask)<2)continue;
   for(int a:{u.a,u.b}){u64 op=mask|(1ULL<<h),black=d.hb[a]&op,key=op|(black<<25)|(u64(h)<<50);if(!seen.insert(key).second)continue;tested++;
    struct Candidate{u64 bits;double value;};std::vector<Candidate>candidate;
    int deepest=63-__builtin_clzll(mask);
    for(int y:pairs){auto v=d.unit[y];if(v.c<deepest||v.c>=h)continue;if(((d.hb[v.a]^black)&op)&&((d.hb[v.b]^black)&op))continue;u64 bits=(d.hb[v.a]^d.hb[v.b])&mask;double val=0;for(u64 z=bits;z;z&=z-1)val+=marginal[__builtin_ctzll(z)];if(val>0)candidate.push_back({bits,val});}
    for(int mode=0;mode<3;mode++){
     std::vector<int>removed(d.H);int count=0;for(auto v:candidate)if(v.value>charges[mode]){count++;for(u64 z=v.bits;z;z&=z-1)removed[__builtin_ctzll(z)]++;}
     double gain=-charges[mode]*count;for(int j=0;j<d.H;j++)if(removed[j])gain+=d.hcost(j)-hcost(j,d.hn[j][0]-removed[j],d.hn[j][1]-removed[j]);
     if(gain>best[mode].gain)best[mode]={mask,black,h,count,gain};
    }
   }
  }
 }
 std::cout<<std::setprecision(12)<<"{\"tested\":"<<tested<<",\"conditions\":[";for(int mode=0;mode<3;mode++){auto v=best[mode];std::cout<<(mode?",":"")<<"{\"charge\":"<<charges[mode]<<",\"difference\":"<<-v.gain/P<<",\"mask\":"<<v.mask<<",\"black\":"<<v.black<<",\"handle\":"<<v.handle<<",\"selected\":"<<v.count<<"}";}std::cout<<"],\"seconds\":"<<elapsed_sec()<<"}\n";
}
