#define ANCHOR_RESEARCH
#define main inherited_main
#include "main.cpp"
#undef main
#undef ANCHOR_RESEARCH
#include <fstream>
#include <iomanip>

namespace patch_code {
struct Pair {int a,b;u64 diff,residual;double fixed,old;};
struct Evaluation {double value=1e9;int selected=0,novel=0,eligible=0;};
struct Model {
    Comparator comp;
    std::vector<u64> A;
    std::array<int,256> cap{};
    std::vector<int> permutation;
    std::vector<Pair> pairs;
    int G=38;
    static u64 bits(const std::string& s,char color){u64 a=0;for(int j=0;j<64;j++)if(s[j]==color)a|=1ULL<<j;return a;}
    bool load(const std::string& input,const std::string& output) {
        std::ifstream in(input),out(output);int n,k,p,r;in>>n>>k>>p>>r;if(n!=64||k!=192||p!=256)return false;
        std::vector<u64> raw(256),op(7),black(7);std::string s;
        for(auto& a:raw){in>>s;a=bits(s,'1');}
        for(int a=0;a<256;a++)cap[a]=raw[a]>>63&1;
        for(int i=0;i<7;i++){out>>s;op[i]=~bits(s,'.');black[i]=bits(s,'1');}
        if(!in||!out)return false;
        u64 gm=0;for(int i=1;i<7;i++)gm|=op[i];G=__builtin_popcountll(gm);if(G!=38)return false;
        for(int j=0;j<64;j++)if(gm>>j&1)permutation.push_back(j);
        for(int j=0;j<63;j++)if(!(gm>>j&1))permutation.push_back(j);
        permutation.push_back(63);A.resize(256);
        for(int a=0;a<256;a++)for(int j=0;j<63;j++)if(raw[a]>>permutation[j]&1)A[a]|=1ULL<<j;
        comp.M=6;comp.G=G;
        for(int j=0;j<G;j++) {
            int x=-1,y=-1;for(int i=0;i<6;i++)if(op[i+1]>>permutation[j]&1){if(x<0)x=i;else y=i;}
            if(x<0||y<0)return false;comp.edge.emplace_back(x,y);comp.polarity.push_back(black[x+1]>>permutation[j]&1);
        }
        comp.rebuild();
        auto residual=[&](u64 a,u64 d) {
            std::array<unsigned,6> incoming{};
            for(u64 z=d&low_bits(G);z;z&=z-1){int j=__builtin_ctzll(z);auto[x,y]=comp.edge[j];if(int(a>>j&1)!=comp.polarity[j])std::swap(x,y);incoming[y]|=1U<<x;}
            unsigned left=63;
            while(true){unsigned rem=0;for(int x=0;x<6;x++)if((left>>x&1)&&!(incoming[x]&left))rem|=1U<<x;if(!rem)break;left&=~rem;}
            u64 r=0;for(u64 z=d&low_bits(G);z;z&=z-1){int j=__builtin_ctzll(z);auto[x,y]=comp.edge[j];if((left>>x&1)&&(left>>y&1))r|=1ULL<<j;}return r;
        };
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++) {
            u64 d=A[a]^A[b];if(__builtin_popcountll(d)>26)continue;
            auto reach=comp.closure(A[a],d);bool ok=true;u64 key=0;
            for(int x=0;x<6;x++){ok&=!(reach[x]>>x&1);key|=u64(reach[x])<<(8*x);}
            double old=ok?PosetSums::get().both_of(key)/720.0:-1;
            pairs.push_back({a,b,d,residual(A[a],d)|residual(A[b],d),
                .5*__builtin_popcountll(d>>G)+.04*__builtin_popcountll(d),old});
        }
        return true;
    }
    bool accepts(const Pair& p,u64 mask,u64 color) const {
        if(p.old>=0)return true;
        u64 q=p.residual&mask,mismatch=(A[p.a]^color)&q;
        if(mismatch && mismatch!=q)return false;
        auto reach=comp.closure(A[p.a],p.diff&~mask);
        for(int x=0;x<6;x++)if(reach[x]>>x&1)return false;
        return true;
    }
    Evaluation evaluate(u64 mask,u64 color,double price,int need) const {
        std::vector<std::pair<double,int>> ranked;ranked.reserve(pairs.size());
        for(int i=0;i<int(pairs.size());i++) {
            auto& p=pairs[i];if(!accepts(p,mask,color))continue;
            ranked.emplace_back(p.fixed+(p.old<0?2*price:p.old),i);
        }
        std::sort(ranked.begin(),ranked.end());std::array<bool,256> used{};double sum=0;Evaluation result;
        for(auto [v,i]:ranked){auto& p=pairs[i];if(used[p.a]||used[p.b])continue;used[p.a]=used[p.b]=true;sum+=v;result.selected++;result.novel+=p.old<0;if(result.selected==need)break;}
        result.value=sum/need+10*(need-result.selected);result.eligible=ranked.size();return result;
    }
};
}

#ifndef PATCH_CODE_NO_MAIN
int main(int argc,char** argv) {
    using namespace patch_code;using Clock=std::chrono::steady_clock;
    if(argc<3)return 2;int iterations=100000;double seconds=120,price=3.0;u64 seed=1;
    for(int i=3;i<argc;i++){std::string s=argv[i];auto j=s.find('=');if(j==s.npos)continue;auto a=s.substr(0,j),b=s.substr(j+1);if(a=="iters")iterations=std::stoi(b);else if(a=="seconds")seconds=std::stod(b);else if(a=="price")price=std::stod(b);else if(a=="seed")seed=std::stoull(b);}
    auto t0=Clock::now();Model m;if(!m.load(argv[1],argv[2]))return 3;XorShift rng(seed);
    auto base=m.evaluate(0,0,price,71);u64 mask=0,color=0,bmask=0,bcolor=0;auto current=m.evaluate(mask,color,price,73),best=current;int done=0;
    for(int t=0;t<iterations;t++) {
        double sec=std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE;if(sec>seconds)break;
        double progress=std::max(double(t)/iterations,sec/seconds),temp=.08*std::pow(.02,progress);
        u64 nm=mask,nc=color;int j=rng.mod(m.G),kind=rng.mod(6);
        if(kind<3){nm^=1ULL<<j;if(rng.mod(2))nc^=1ULL<<j;}
        else if(kind==3){nc^=1ULL<<j;}
        else if(kind==4){int k=rng.mod(m.G);if(((nm>>j)^(nm>>k))&1)nm^=(1ULL<<j)|(1ULL<<k);if(((nc>>j)^(nc>>k))&1)nc^=(1ULL<<j)|(1ULL<<k);}
        else {auto& p=m.pairs[rng.mod(m.pairs.size())];if(p.old>=0)continue;nm|=p.residual;nc=(nc&~p.residual)|(m.A[p.a]&p.residual);}
        nc&=nm;auto candidate=m.evaluate(nm,nc,price,73);
        if(candidate.value<=current.value||rng.real()<std::exp((current.value-candidate.value)/temp)){mask=nm;color=nc;current=candidate;}
        if(current.value<best.value){best=current;bmask=mask;bcolor=color;std::cerr<<"best "<<t<<' '<<best.value<<" bits "<<__builtin_popcountll(mask)<<" novel "<<best.novel<<'\n';}
        if(t%10000==0)std::cerr<<"step "<<t<<" sec "<<sec<<" best "<<best.value<<'\n';done=t+1;
    }
    std::cout<<std::setprecision(10)<<"{\"base\":"<<base.value<<",\"best\":"<<best.value<<",\"selected\":"<<best.selected<<",\"novel\":"<<best.novel<<",\"eligible\":"<<best.eligible<<",\"mask\":"<<bmask<<",\"color\":"<<bcolor<<",\"bits\":"<<__builtin_popcountll(bmask)<<",\"iterations\":"<<done<<",\"price\":"<<price<<",\"elapsed\":"<<std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE<<"}\n";
}
#endif
