#define main inherited_main
#include "main.cpp"
#undef main
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    const auto& sums = PosetSums::get();
    WindowRelations relations(sums);
    std::vector<std::pair<int,int>> edges;
    for(int a=0;a<5;a++) for(int b=a+1;b<5;b++) edges.emplace_back(a,b);
    for(int code=0;code<59049;code++) {
        int v=code; uint32_t packed=0; u64 relation=0;
        for(int e=0;e<10;e++,v/=3) {
            auto [a,b]=edges[e];
            if(v%3==1){packed|=1U<<e;relation|=1ULL<<(8*a+b);}
            if(v%3==2){packed|=1U<<(16+e);relation|=1ULL<<(8*b+a);}
        }
        for(int k=0;k<5;k++)for(int a=0;a<5;a++)
            if(relation>>(8*a+k)&1)relation|=((relation>>(8*k))&31)<<(8*a);
        int expected=(relation&kDiagonal)?0:1+sums.both_of(relation);
        assert(relations.cost(packed)==expected);
    }
    for(int i=1;i<argc;i++) {
        std::ifstream in(argv[i]); int n,k,p,r; in>>n>>k>>p>>r;
        assert(n==64&&k==192&&p==256);
        std::vector<u64> original(P); std::string line;
        for(auto& a:original){in>>line;for(int j=0;j<63;j++)if(line[j]=='1')a|=1ULL<<j;}
        for(int g:{32,34,36}) {
            auto A=original; std::mt19937_64 rng(779879); Comparator comp;comp.init(5,g,rng);
            std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
            auto stats=assign_windows(A,5,g,comp.edge,comp.polarity,permutation,1e9,10000,1000,0);
            comp.rebuild();
            assert(comp.complete); assert(permutation[63]==63);
            for(int u=0;u<P;u++)for(int j=0;j<63;j++)assert((A[u]>>j&1)==(original[u]>>permutation[j]&1));
            std::cout<<"input = "<<argv[i]<<" G = "<<g<<" iterations = "<<stats.iterations<<'\n';
        }
    }
    std::cout<<"raw_relations = 59049\n";
}
