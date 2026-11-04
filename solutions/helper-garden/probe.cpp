#include "common.hpp"
#include "garden.hpp"
int main(int argc,char**argv){
    if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
    auto original=recover(*base);materialize(*base,*original);
    int sequences=argc>3?std::stoi(argv[3]):16;
    int variants=argc>4?std::stoi(argv[4]):2;
    double reference=0;std::cout<<std::setprecision(12)<<"[";
    for(int mode=0;mode<=variants;mode++){
        Solver s=*base;auto d=*original;double start=elapsed_sec();int added=0;
        if(mode){Garden garden(s,d);garden.select(mode-1+(argc>5?std::stoi(argv[5]):0));garden.build();added=garden.new_pairs;}
        d.anneal(1e9,20000000);d.refresh_reset();
        int special=0;for(auto&u:d.unit)if(u.b>=0&&!s.comparator.compatible(s.A[u.a],s.A[u.b]))special++;
        for(int c=0;c<d.H;c++)assert(d.n1[c]>0&&d.n1[c]<d.nc[c]);
        materialize(s,d);double seconds=elapsed_sec()-start;auto initial=s.save();long long moves=0,wrong=0,needed=0;
        for(int u=0;u<P;u++)if(s.helper_required[u]){
            bool found=false;for(auto&h:s.interleave->helpers[u])if(s.garden_helper[h.paper])found=true;assert(found);
        }
        for(int q=0;q<sequences;q++){
            s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){
                int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
                auto before=s.order;auto path=s.process(u);moves+=path.size();wrong+=s.display()!=s.A[u];needed+=s.helper_required[u];
                if(q==0){
                    for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 covered=0;for(int j=0;j<at;j++)covered|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~covered);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
                    assert(before==s.order);
                }
            }
        }
        assert(!wrong);assert(!s.plan_failures);double average=double(moves)/(1024*sequences);if(!mode)reference=average;
        std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<average<<",\"difference\":"<<average-reference<<",\"model\":"<<d.cur/P<<",\"new_pairs\":"<<added<<",\"special\":"<<special<<",\"required\":"<<needed<<",\"wrong\":"<<wrong<<",\"design_seconds\":"<<seconds<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
