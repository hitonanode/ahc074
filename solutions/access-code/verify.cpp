#define ACCESS_NO_MAIN
#include "search.cpp"
int main(int argc,char**argv){
    if(argc<3)return 2;Search m(argv[1],argv[2],3,1);XorShift rng{9812347};int tested=0;
    for(int trial=0;trial<16;trial++){
        Auxiliary aux;for(int x=0;x<2;x++){aux.mask[x]=rng.next()&low_bits(m.m.G);aux.color[x]=rng.next()&aux.mask[x];}
        m.evaluate(aux);std::vector<u64> displays;std::array<int,8> order{0,1,2,3,4,5,6,7};
        do{u64 covered=0,display=0;for(int x:order){display|=m.black[x]&~covered;covered|=m.op[x];}displays.push_back(display);}while(std::next_permutation(order.begin(),order.end()));
        for(int sample=0;sample<64;sample++){
            auto p=m.m.pairs[rng.mod(m.m.pairs.size())];u64 holes=(m.m.A[p.a]^m.m.A[p.b])&(low_bits(m.m.G)|kCapBit),target=m.m.A[(sample&1)?p.a:p.b];
            bool expected=false;for(u64 display:displays)if(!((display^target)&holes)){expected=true;break;}
            if(m.can(target,holes)!=expected){std::cerr<<"mismatch "<<trial<<' '<<p.a<<' '<<p.b<<'\n';return 3;}tested++;
        }
    }
    std::cout<<"greedy_order_checks = "<<tested<<'\n';
}
