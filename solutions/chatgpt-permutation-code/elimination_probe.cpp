#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>

// Exact column synthesis without enumerating 3^m printings. If a paper is
// currently first in rows requiring both colors, it must be a hole. Delete all
// such papers until reaching a fixed point. At a nonempty fixed point, coloring
// each paper by the common label of rows where it is first gives a solution.
bool synth(const std::vector<std::vector<int>>& orders, std::uint64_t labels,
           std::vector<int>* pattern = nullptr) {
    int q=orders.size(), m=orders[0].size();
    std::vector<int> removed(m), at(q), seen(m);
    while(true){
        std::fill(seen.begin(),seen.end(),0);
        for(int u=0;u<q;++u){while(at[u]<m && removed[orders[u][at[u]]])++at[u];
            if(at[u]==m)return false;
            seen[orders[u][at[u]]] |= 1+((labels>>u)&1);
        }
        bool changed=false;
        for(int k=0;k<m;++k)if(seen[k]==3){removed[k]=1;changed=true;}
        if(!changed){if(pattern){pattern->resize(m);for(int k=0;k<m;++k)
                (*pattern)[k]=removed[k]||seen[k]==0?2:seen[k]-1;}
            return true;}
    }
}
int main(int argc,char**argv){
    int m=argc>1?std::atoi(argv[1]):24,q=argc>2?std::atoi(argv[2]):32;
    int samples=argc>3?std::atoi(argv[3]):100, front=argc>4?std::atoi(argv[4]):0;
    assert(q<=64);
    std::mt19937_64 rng(740062); int fails=0,full=0;double opaque=0;
    for(int g=0;g<samples;++g){
        std::vector<std::vector<int>>o(q,std::vector<int>(m));
        for(auto&p:o){std::iota(p.begin(),p.end(),0);std::shuffle(p.begin(),p.end(),rng);
            if(front){std::sort(p.begin()+front,p.end());}}
        int f=0;
        for(int j=0;j<64;++j){std::uint64_t x=rng();std::vector<int>p;
            if(!synth(o,x,&p)){++f;continue;}
            for(int c:p)opaque+=c!=2;
        }
        fails+=f;full+=f==0;
    }
    std::cout<<"m="<<m<<" q="<<q<<" front="<<front<<" samples="<<samples
             <<" mean_missing="<<double(fails)/samples<<" solved="<<full
             <<" mean_opaque_per_column="<<opaque/(samples*64-fails)<<"\n";
}
