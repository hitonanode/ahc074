// Synthesize opacity for a local module against the FREE-order baseline.
// A mask still contains its original own-column bit. The colors are fixed.
// The actual workload is a relaxation (six representatives, exposure only).
#define main module3_original_main
#include "module3_toy.cpp"
#undef main
#include <fstream>
#include <map>
#include <random>

struct Event{int mask,bits;double weight;};
int main(int argc,char**argv){
    int block=argc>1?std::stoi(argv[1]):8,limit=argc>2?std::stoi(argv[2]):128;
    Order p{0,1,2,3,4,5};do orders.push_back(p);while(std::next_permutation(p.begin(),p.end()));
    std::ifstream in("solutions/astra-probe/module_events.txt");std::vector<Event>events;
    for(int b,n;in>>b>>n;)for(int i=0;i<n;++i){Event e{};in>>e.mask>>e.bits>>e.weight;if(b==block)events.push_back(e);}
    double rate=0;for(auto e:events)rate+=e.weight;
    std::map<std::array<int,6>,double>cache;
    auto evaluate=[&](std::array<int,6>op){
        if(auto it=cache.find(op);it!=cache.end())return it->second;
        Model m(op,false);std::vector<std::vector<int>>goals;
        for(auto e:events){goals.emplace_back();if(!e.mask)goals.back()=m.goals[8+e.bits];else for(int a=0;a<8;++a)if((a&e.mask)==e.bits)goals.back().insert(goals.back().end(),m.goals[a].begin(),m.goals[a].end());if(goals.back().empty())return cache[op]=99;}
        std::array<double,720>v{},next{};double mean=0,span=0;
        for(int it=0;it<500;++it){double mn=1e99,mx=-1e99;
            for(int s=0;s<720;++s){next[s]=0;auto*d=m.dist.data()+s*720;
                for(int e=0;e<(int)events.size();++e){double best=1e99;for(int t:goals[e])best=std::min(best,d[t]+v[t]);next[s]+=best*events[e].weight/rate;}
                mn=std::min(mn,next[s]-v[s]);mx=std::max(mx,next[s]-v[s]);
            }
            mean=(mn+mx)/2;span=mx-mn;double off=next[0];for(int s=0;s<720;++s)v[s]=next[s]-off;if(span<1e-7)break;
        }
        if(span>1e-6)return cache[op]=99;
        return cache[op]=mean*rate;
    };
    std::array<int,6>start{1,1,3,3,7,7},cur=start,best=start;
    double base=evaluate(start),cv=base,bv=base;std::mt19937 rng(71265+block);
    auto report=[&]{std::cout<<block<<','<<cache.size()<<','<<std::setprecision(12)<<base<<','<<bv<<','<<bv-base<<',';for(int a:best)std::cout<<a;std::cout<<'\n'<<std::flush;};
    std::cout<<"block,evaluated,free_baseline,best,delta,opacity\n";report();
    while((int)cache.size()<limit){
        double nv=cv;auto next=cur;
        for(int k=0;k<6&&int(cache.size())<limit;++k)for(int j=0;j<3&&int(cache.size())<limit;++j)if(j!=k/2){auto cand=cur;cand[k]^=1<<j;double v=evaluate(cand);if(v<nv-1e-8){nv=v;next=cand;}}
        if(nv<cv-1e-8){cur=next;cv=nv;if(cv<bv){bv=cv;best=cur;report();}}
        else {cur=best;for(int t=0;t<3;++t){int k=rng()%6,j=rng()%3;if(j!=k/2)cur[k]^=1<<j;}cv=evaluate(cur);}
    }
    report();
}
