#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){
    if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
    int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
    std::cout<<std::setprecision(12)<<"[";
    for(int mode=0;mode<4;mode++){
        group_rate=mode==0?0:mode==3?16:64;group_loss=mode==1?3:6;
        auto a=base->A;for(auto&v:a)v&=kActiveWindows;auto comp=base->comparator;
        std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
        double start=elapsed_sec();
        auto stats=assign_windows(a,6,base->G,comp.edge,comp.polarity,permutation,1e9,250000,50000,0);
        double map_seconds=elapsed_sec()-start;comp.rebuild();
        auto d=std::make_unique<Design>(a,6,base->G);
        auto estimate=[&](u64 x,u64 y){auto relation=comp.closure(x,x^y);u64 r=0;for(int j=0;j<6;j++)r|=u64(relation[j])<<(8*j);return PosetSums::get().both_of(r)/1440.;};
        bool valid=d->initialize([&](u64 x,u64 y){return comp.compatible(x,y);},estimate,[]{return false;});assert(valid);
        d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);d->refresh_reset();
        Solver s=*base;s.comparator=comp;
        for(int u=0;u<P;u++)a[u]|=base->A[u]&kCapBit;s.A=a;
        for(int k=0;k<6;k++)s.paper[k]={comp.opq[k],comp.black[k]};
        materialize(s,*d);auto initial=s.save();double design_seconds=elapsed_sec()-start;
        long long total=0,wrong=0;
        for(int q=0;q<sequences;q++){
            s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){
                int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
                auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
                if(q==0){
                    for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
                    assert(before==s.order);
                }
            }
        }
        assert(!wrong);assert(!s.plan_failures);double value=double(total)/(sequences*1024);if(!mode)reference=value;
        std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<d->cur/P<<",\"gobj\":"<<stats.gobj_after<<",\"group_trials\":"<<stats.group_trials<<",\"group_evals\":"<<stats.group_evals<<",\"group_accepts\":"<<stats.group_accepts<<",\"map_seconds\":"<<map_seconds<<",\"seconds\":"<<design_seconds<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
