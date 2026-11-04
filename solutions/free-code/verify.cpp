#define FREE_CODE_NO_MAIN
#include "search.cpp"

int main(int argc,char** argv) {
    if(argc!=3)return 2;
    free_code::Search q(7);assert(q.load(argv[1],argv[2]));
    auto original=q.state;
    for(int t=0;t<200;t++) {
        int j=q.rng.mod(q.G),g=q.rng.mod(q.gates.size());q.change(j,g);
        if(t%19==0) {
            auto counts=q.mismatch;auto before=q.pairs;auto design=q.state;q.reset(design);
            assert(counts==q.mismatch);
            for(int i=0;i<int(before.size());i++)assert(before[i].histogram==q.pairs[i].histogram);
        }
    }
    q.reset(original);
    for(auto& p:q.pairs)if(p.histogram[0]&&p.histogram[p.n]) {
        std::array<unsigned,12> reach{};
        for(int j=0;j<q.G;j++)if(p.diff>>j&1) {
            auto& g=q.gates[q.state[j]];unsigned want=q.products[p.a]>>j&1;
            int a=-1,b=-1;for(int x=0;x<6;x++)if(g.opaque>>x&1){if((g.black>>x&1)==want)a=x;else b=x;}
            assert(a>=0&&b>=0);reach[a]|=1U<<b;
        }
        for(int k=0;k<6;k++)for(int a=0;a<6;a++)if(reach[a]>>k&1)reach[a]|=reach[k];
        u64 key=0;for(int a=0;a<6;a++){assert(!(reach[a]>>a&1));key|=u64(reach[a])<<(8*a);}
        int count=0;for(auto& below:q.graph.below){bool ok=true;for(int a=0;a<6;a++)ok&=!(reach[a]&~below[a]);count+=ok;}
        assert(count==p.histogram[0]);
    }
    std::cout<<"incremental updates 200, histogram rebuilds 11, all compatible pairs checked\n";
}
