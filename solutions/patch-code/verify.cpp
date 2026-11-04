#define PATCH_CODE_NO_MAIN
#include "probe.cpp"

int main(int argc,char** argv) {
    if(argc!=3)return 2;patch_code::Model m;assert(m.load(argv[1],argv[2]));m.comp.build_tables();XorShift rng(401);
    int checked=0;
    for(int trial=0;trial<12;trial++) {
        u64 mask=0,color=0;for(int j=0;j<m.G;j++){if(rng.mod(2))mask|=1ULL<<j;if(rng.mod(2))color|=1ULL<<j;}
        color&=mask;std::vector<u64> displays;
        // The first of the two equally opaque patches hides the second. Enumerate
        // all six-sheet orders, both patch colors, and its seven insertion sites.
        for(auto& p:m.comp.perms)for(int slot=0;slot<=6;slot++)for(int side=0;side<2;side++) {
            u64 covered=0,black=0;
            for(int pos=0;pos<=6;pos++) {
                if(pos==slot){black|=(side?color^mask:color)&~covered;covered|=mask;}
                if(pos<6){int x=p[pos];black|=m.comp.black[x]&~covered;covered|=m.comp.opq[x];}
            }
            displays.push_back(black);
        }
        for(int k=0;k<300;k++) {
            auto& p=m.pairs[rng.mod(m.pairs.size())];u64 holes=p.diff&low_bits(m.G);bool a=false,b=false;
            for(u64 d:displays){a|=!((d^m.A[p.a])&holes);b|=!((d^m.A[p.b])&holes);if(a&&b)break;}
            assert((a&&b)==m.accepts(p,mask,color));checked++;
        }
    }
    std::cout<<"patch feasibility checked against all orders: "<<checked<<" cases\n";
}
