#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>

// Exhaust every injection of four distinct target states into the six orders
// of three papers, and every ternary printing of one physical window.
int main(int argc, char** argv) {
    std::array<int,3> p{0,1,2};
    std::vector<std::array<int,3>> perms;
    do {perms.push_back(p);}while(std::next_permutation(p.begin(),p.end()));
    int out[6][27]{};
    for(int s=0;s<6;++s)for(int t=0;t<27;++t){
        int v=t;std::array<int,3> colors{};
        for(int&c:colors){c=v%3;v/=3;}
        for(int k:perms[s])if(colors[k]!=2){out[s][t]=colors[k];break;}
    }
    std::set<unsigned> families;
    std::map<int,int> histogram;
    for(int a=0;a<6;++a)for(int b=0;b<6;++b)if(a!=b)
    for(int c=0;c<6;++c)if(c!=a&&c!=b)
    for(int d=0;d<6;++d)if(d!=a&&d!=b&&d!=c){
        unsigned mask=0;
        for(int t=0;t<27;++t){int v=out[a][t]|out[b][t]<<1|out[c][t]<<2|out[d][t]<<3;mask|=1U<<v;}
        ++histogram[std::popcount(mask)];families.insert(mask);
    }
    int maximal=0;
    for(unsigned a:families){bool dominated=false;
        for(unsigned b:families)if(a!=b&&(a&b)==a)dominated=true;
        maximal+=!dominated;
    }
    assert(histogram[8]==72 && histogram[10]==288 && histogram.size()==2);
    std::cout<<"state_injections=360 unique_families="<<families.size()
             <<" maximal_families="<<maximal<<" max_patterns="<<histogram.rbegin()->first<<"\n";
    for(auto [n,count]:histogram)std::cout<<"patterns="<<n<<" injections="<<count<<"\n";
    if(argc>1){
        std::ifstream f(argv[1]);int n,k,q,r;f>>n>>k>>q>>r;
        assert(f && n==64);std::vector<std::uint64_t> target(q);
        for(auto&x:target){std::string s;f>>s;for(int j=0;j<64;++j)if(s[j]=='1')x|=1ULL<<j;}
        std::uint64_t tested=0,feasible=0,small=0;
        for(int a=0;a<q;++a)for(int b=a+1;b<q;++b)for(int c=b+1;c<q;++c){
            std::uint64_t buckets[8];int nb=0;
            for(int v=0;v<8;++v){buckets[v]=(v&1?target[a]:~target[a])&
                (v&2?target[b]:~target[b])&(v&4?target[c]:~target[c]);nb+=buckets[v]!=0;}
            for(int d=c+1;d<q;++d){++tested;int count=nb;unsigned mask=0;
                for(int v=0;v<8;++v){bool lo=(buckets[v]&~target[d])!=0,hi=(buckets[v]&target[d])!=0;
                    count+=lo&&hi;mask|=(unsigned(lo)<<v)|(unsigned(hi)<<(v+8));if(count>10)break;}
                if(count>10)continue;++small;
                for(unsigned fam:families)if((mask&fam)==mask){++feasible;break;}
            }
        }
        std::cout<<"file="<<argv[1]<<" tested_quadruples="<<tested<<" at_most_10_patterns="<<small
                 <<" representable_quadruples="<<feasible<<"\n";
    }
}
