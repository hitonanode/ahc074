#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"

double potential(const Solver& s){
    double value=.6*s.fillers.size()+s.adaptive_next_cost();
    if(s.interleave&&!s.future.empty())value+=(142./P)*s.future[s.interleave->state(s.order)];
    return value;
}

int main(int argc,char**argv){
    if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
    auto initial=recover(*base);int sequences=argc>3?std::stoi(argv[3]):16;
    std::cout<<std::setprecision(12)<<"[";int index=0;
    for(int count:{1,2,4})for(int k=0;k<count;k++){
        auto d=*initial;d.rng.x^=0x7c317d9b51ULL*k;double start=elapsed_sec();
        d.anneal(1e9,20000000/count);d.refresh_reset();double raw=d.cur/P;
        d.filler_climb(1e9,65000);rematch_probability(d,4,1,2,true,true);d.refresh_reset();
        ProbabilityHead head(d,2,true);double merit=(d.cur-head.rebuild())/P;
        Solver s=*base;materialize(s,d);auto state=s.save();double design_seconds=elapsed_sec()-start;
        std::cout<<(index?",":"")<<"{\"id\":"<<index++<<",\"count\":"<<count<<",\"raw\":"<<raw<<",\"merit\":"<<merit<<",\"design_seconds\":"<<design_seconds<<",\"training\":[";
        for(int kind=0;kind<3;kind++){
            Solver::sampling_mode=kind==1?2:1;s.restore(state);double initial_value=potential(s);
            start=elapsed_sec();std::mt19937_64 random(0xc9103a57ULL);std::vector<int> sequence;
            int prev=random()%P;
            if(kind<2)for(int round=0;round<16;round++){
                std::vector<int> order(P);std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),random);
                if(!sequence.empty()&&sequence.back()==order[0])std::swap(order[0],order[1]);
                sequence.insert(sequence.end(),order.begin(),order.end());
            }else for(int i=0;i<4096;i++){int u=random()%(P-1);if(u>=prev)u++;sequence.push_back(u);prev=u;}
            long long total=0;bool first=true;
            std::cout<<(kind?",":"")<<"[";
            for(int t=1;t<=4096;t++){
                int u=sequence[t-1];auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
                if(t>=256&&!(t&(t-1))){
                    std::cout<<(first?"":",")<<"{\"n\":"<<t<<",\"moves\":"<<double(total)/t<<",\"adjusted\":"<<(total+potential(s)-initial_value)/t<<",\"seconds\":"<<elapsed_sec()-start<<"}";first=false;
                }
            }
            std::cout<<"]";
        }
        Solver::sampling_mode=0;long long total=0,wrong=0;start=elapsed_sec();
        for(int q=0;q<sequences;q++){
            s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){
                int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
                auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
                if(q==0){
                    for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
                    assert(before==s.order);
                }
            }
        }
        assert(!wrong);assert(!s.plan_failures);
        std::cout<<"],\"moves\":"<<double(total)/(sequences*1024)<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<",\"wrong\":"<<wrong<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
