#define PATCH_CODE_NO_MAIN
#include "../patch-code/probe.cpp"
#include <stdexcept>

struct Auxiliary {
    std::array<u64,2> mask{},color{};
};
struct Search {
    patch_code::Model m;
    std::array<u64,8> op{},black{};
    std::vector<int> sorted;
    double price=3,cap_fee=1;
    Search(const char* input,const char* output,double p,double cf):price(p),cap_fee(cf){
        if(!m.load(input,output))throw std::runtime_error("load");
        std::ifstream in(input);int n,k,pn,r;std::string s;in>>n>>k>>pn>>r;
        for(int a=0;a<256;a++){in>>s;if(s[63]=='1')m.A[a]|=kCapBit;}
        for(int x=0;x<6;x++){op[x]=m.comp.opq[x];black[x]=m.comp.black[x];}
        sorted.resize(m.pairs.size());std::iota(sorted.begin(),sorted.end(),0);
        std::sort(sorted.begin(),sorted.end(),[&](int i,int j){return cost(i)<cost(j);});
    }
    double cost(int i)const{
        auto p=m.pairs[i];return p.fixed+(p.old>=0?p.old+cap_fee*bool((m.A[p.a]^m.A[p.b])&kCapBit):2*price);
    }
    bool can(u64 target,u64 holes)const{
        // Placing any paper which has no wrong cell on the remaining holes is
        // safe: it only removes requirements. Repeating this is an exact
        // existence test for an ordering, even for freely printed papers.
        unsigned left=255;
        while(holes){
            bool progress=false;
            for(int x=0;x<8;x++)if(left>>x&1){
                if((black[x]^target)&op[x]&holes)continue;
                holes&=~op[x];left^=1U<<x;progress=true;
            }
            if(!progress)return false;
        }
        return true;
    }
    patch_code::Evaluation evaluate(const Auxiliary& aux){
        for(int x=0;x<2;x++){op[6+x]=aux.mask[x]|kCapBit;black[6+x]=(aux.color[x]&aux.mask[x])|(x?kCapBit:0);}
        std::array<bool,256> used{};patch_code::Evaluation answer;double sum=0;
        for(int i:sorted){
            auto p=m.pairs[i];if(used[p.a]||used[p.b])continue;
            if(p.old<0){u64 holes=(m.A[p.a]^m.A[p.b])&(low_bits(m.G)|kCapBit);if(!can(m.A[p.a],holes)||!can(m.A[p.b],holes))continue;}
            used[p.a]=used[p.b]=true;sum+=cost(i);answer.selected++;answer.novel+=p.old<0;
            if(answer.selected==72)break;
        }
        answer.value=sum/72+10*(72-answer.selected);return answer;
    }
};
#ifndef ACCESS_NO_MAIN
int main(int argc,char** argv){
    if(argc<3)return 2;double seconds=180,price=3,capfee=1;int iterations=500000,maxbits=20;u64 seed=1;
    for(int i=3;i<argc;i++){std::string s=argv[i];auto j=s.find('=');if(j==s.npos)continue;auto k=s.substr(0,j),v=s.substr(j+1);
        if(k=="seconds")seconds=std::stod(v);else if(k=="price")price=std::stod(v);else if(k=="capfee")capfee=std::stod(v);else if(k=="iters")iterations=std::stoi(v);else if(k=="seed")seed=std::stoull(v);else if(k=="maxbits")maxbits=std::stoi(v);
    }
    Search model(argv[1],argv[2],price,capfee);XorShift rng{seed};Auxiliary current,best;
    auto value=model.evaluate(current),best_value=value;
    double start=elapsed_sec();int done=0;
    for(int it=0;it<iterations;it++){
        double sec=elapsed_sec()-start;if(sec>seconds)break;double progress=std::max(double(it)/iterations,sec/seconds);
        Auxiliary next=current;int x=rng.mod(2),j=rng.mod(model.m.G),kind=rng.mod(8);
        if(kind<5){int state=rng.mod(3);next.mask[x]&=~(1ULL<<j);next.color[x]&=~(1ULL<<j);if(state<2)next.mask[x]|=1ULL<<j;if(state==1)next.color[x]|=1ULL<<j;}
        else if(kind==5){int k=rng.mod(model.m.G);if(((next.mask[x]>>j)^(next.mask[x]>>k))&1)next.mask[x]^=(1ULL<<j)|(1ULL<<k);if(((next.color[x]>>j)^(next.color[x]>>k))&1)next.color[x]^=(1ULL<<j)|(1ULL<<k);}
        else if(kind==6){auto p=model.m.pairs[rng.mod(model.m.pairs.size())];if(p.old>=0)continue;int a=(model.m.A[p.a]&kCapBit)?p.b:p.a;next.mask[0]|=p.residual;next.mask[1]|=p.residual;next.color[0]=(next.color[0]&~p.residual)|(model.m.A[a]&p.residual);next.color[1]=(next.color[1]&~p.residual)|(~model.m.A[a]&p.residual);}
        else{next.mask[1-x]=next.mask[x];next.color[1-x]=next.mask[x]^next.color[x];}
        if(__builtin_popcountll(next.mask[0])>maxbits||__builtin_popcountll(next.mask[1])>maxbits)continue;
        for(int x=0;x<2;x++)next.color[x]&=next.mask[x];auto nv=model.evaluate(next);
        double temp=.09*std::pow(.015,progress);
        if(nv.value<=value.value||rng.real()<std::exp((value.value-nv.value)/temp)){current=next;value=nv;}
        if(value.value<best_value.value){best=current;best_value=value;std::cerr<<"best "<<it<<' '<<value.value<<" novel "<<value.novel<<" bits "<<__builtin_popcountll(best.mask[0])<<' '<<__builtin_popcountll(best.mask[1])<<" sec "<<sec<<'\n';}
        done=it+1;
    }
    auto baseline=model.m.evaluate(0,0,price,71);
    std::cout<<std::setprecision(12)<<"{\"base\":"<<baseline.value<<",\"best\":"<<best_value.value<<",\"novel\":"<<best_value.novel<<",\"selected\":"<<best_value.selected<<",\"mask0\":"<<best.mask[0]<<",\"color0\":"<<best.color[0]<<",\"mask1\":"<<best.mask[1]<<",\"color1\":"<<best.color[1]<<",\"price\":"<<price<<",\"capfee\":"<<capfee<<",\"maxbits\":"<<maxbits<<",\"iterations\":"<<done<<",\"elapsed\":"<<elapsed_sec()-start<<"}\n";
}
#endif
