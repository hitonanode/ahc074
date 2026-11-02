#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

// Feasibility experiment, not a reactive solver. A ternary column is evaluated
// in each selected permutation, so all 3^m possible printings are considered.
int main(int argc, char** argv) {
    int m = argc > 1 ? std::atoi(argv[1]) : 6;
    int q = argc > 2 ? std::atoi(argv[2]) : 8;
    int iters = argc > 3 ? std::atoi(argv[3]) : 100000;
    int groups = argc > 4 ? std::atoi(argv[4]) : 16;
    assert(2 <= m && m <= 8 && q <= 12);
    std::mt19937 rng(740062);
    std::vector<std::uint64_t> targets;
    if (argc > 5) {
        std::ifstream f(argv[5]); int n,k,p,r; f>>n>>k>>p>>r;
        for (int u=0;u<p;++u) { std::string s; f>>s; std::uint64_t a=0;
            for (int j=0;j<n;++j) if(s[j]=='1') a|=1ULL<<j;
            targets.push_back(a);
        }
    } else {
        for(int u=0;u<q*groups;++u) {
            std::vector<int> order(64); std::iota(order.begin(),order.end(),0);
            std::shuffle(order.begin(),order.end(),rng); std::uint64_t a=0;
            for(int j=0;j<32;++j) a|=1ULL<<order[j]; targets.push_back(a);
        }
    }
    std::vector<std::vector<int>> perms; std::vector<int> ord(m);
    std::iota(ord.begin(),ord.end(),0);
    do {perms.push_back(ord);}while(std::next_permutation(ord.begin(),ord.end()));
    int nt=1;for(int i=0;i<m;++i)nt*=3;
    std::vector<unsigned char> out(perms.size()*nt);
    std::vector<std::vector<int>> print(nt,std::vector<int>(m));
    for(int t=0;t<nt;++t){int v=t;for(int i=0;i<m;++i){print[t][i]=v%3;v/=3;}}
    for(int s=0;s<(int)perms.size();++s) for(int t=0;t<nt;++t)
        for(int k:perms[s]) if(print[t][k]!=2){out[s*nt+t]=print[t][k];break;}
    std::cout<<"m="<<m<<" q="<<q<<" permutations="<<perms.size()<<" columns="<<nt<<"\n";
    int solved=0;double mean_missing=0;
    for(int g=0;g<groups;++g) {
        std::vector<int> weight(1<<q), state(q), cv(nt), count(1<<q);
        for(int j=0;j<64;++j){int v=0;for(int u=0;u<q;++u)v|=((targets[(g*q+u)%targets.size()]>>j)&1)<<u;++weight[v];}
        for(int u=0;u<q;++u)state[u]=rng()%perms.size();
        for(int t=0;t<nt;++t){int v=0;for(int u=0;u<q;++u)v|=out[state[u]*nt+t]<<u;cv[t]=v;++count[v];}
        int loss=0;for(int v=0;v<(1<<q);++v)if(!count[v])loss+=weight[v];
        int best=loss;std::vector<int> beststate=state;
        for(int it=0;it<iters && best;++it){
            int u=rng()%q,old=state[u], neu;
            if((rng()&3)==0)neu=rng()%perms.size();
            else{auto p=perms[old];int a=rng()%m,b=rng()%m;std::swap(p[a],p[b]);neu=std::lower_bound(perms.begin(),perms.end(),p)-perms.begin();}
            int diff=0;
            for(int t=0;t<nt;++t){int a=cv[t];int b=(a&~(1<<u))|(out[neu*nt+t]<<u);if(a==b)continue;
                if(--count[a]==0)diff+=weight[a];if(count[b]++==0)diff-=weight[b];cv[t]=b;
            }
            double temp=0.08+1.8*std::pow(1.0-double(it%20000)/20000,2);
            bool accept=diff<=0 || std::generate_canonical<double,32>(rng)<std::exp(-diff/temp);
            if(accept){state[u]=neu;loss+=diff;if(loss<best){best=loss;beststate=state;}}
            else for(int t=0;t<nt;++t){int a=cv[t];int b=(a&~(1<<u))|(out[old*nt+t]<<u);if(a!=b){--count[a];++count[b];cv[t]=b;}}
        }
        solved+=best==0;mean_missing+=best;
        std::cout<<"group="<<g<<" missing="<<best<<" orders=";
        for(int s:beststate){for(int k:perms[s])std::cout<<k;std::cout<<',';}std::cout<<"\n";
    }
    std::cout<<"solved="<<solved<<'/'<<groups<<" mean_missing="<<mean_missing/groups<<"\n";
}
