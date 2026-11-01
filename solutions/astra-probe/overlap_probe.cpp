// Research-only selective overlapping pair representation. Convert a single's
// existing paper X into a pair (single u, already-paired v); v may choose X or
// its original paper. K is unchanged. Select edges on common saved snapshots,
// then validate on fresh independent synthetic requests (not tester scores).
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
#include <tuple>

struct Edge {int x,u,v,old;double gain,du,dv;};
void weight_overlap(Solver&s,const Data&d,const std::vector<Edge>&es){
    s.adaptive_initialized=false;s.init_adaptive();
    for(auto e:es){
        s.adaptive_weights[e.x]+=.5;s.adaptive_weights[e.old]-=.5;
        for(int c=0;c<28;++c){
            int bit=d.a[e.v]>>(36+c)&1;
            int before=!(s.paper[e.old].opaque>>(36+c)&1),after=!(s.paper[e.x].opaque>>(36+c)&1);
            s.adaptive_holes[c][bit]+=.5*(after-before)/256;
        }
    }
}
double score_plan(Solver&s,int u,const Solver::State&state){
    s.restore(state);double start=s.adaptive_next_cost()+.6*s.fillers.size();
    auto ops=s.process(u);assert(s.display()==s.A[u]);
    return ops.size()+s.adaptive_next_cost()+.6*s.fillers.size()-start;
}
std::vector<Edge> select(Data&d,int samples){
    auto base=make_solver(d,false);std::vector<Solver::State> states;
    std::vector<int> trace(192);std::iota(trace.begin(),trace.end(),0);
    for(int r=0;r<1024;++r){
        if(r%(1024/samples)==0){base->order=trace;base->fillers.clear();base->canonicalize();states.push_back(base->save());}
        for(auto[k,z]:d.queries[r]){trace.erase(std::find(trace.begin(),trace.end(),k));trace.insert(trace.begin()+z,k);}
    }
    std::array<int,192> degree{};for(int k:d.ded)degree[k]++;
    std::vector<Edge> edges;
    for(int u=0;u<256;++u)if(degree[d.ded[u]]==1)for(int v=0;v<256;++v)if(degree[d.ded[v]]==2){
        int x=d.ded[u];if((d.a[u]^d.a[v])>>(36+d.cols[x])&1)continue;
        if(d.cost(u,v,0)<0)continue;
        edges.push_back({x,u,v,d.ded[v],0,0,0});
    }
    std::vector<std::vector<double>> costs(256,std::vector<double>(states.size(),-999));
    for(auto&e:edges){
        Data cd=d;cd.papers[e.x].opaque&=~(d.a[e.u]^d.a[e.v]);cd.papers[e.x].black&=cd.papers[e.x].opaque;
        auto cand=make_solver(cd,false);weight_overlap(*cand,d,{e});
        for(int i=0;i<(int)states.size();++i){
            for(int u:{e.u,e.v})if(costs[u][i]<-100)costs[u][i]=score_plan(*base,u,states[i]);
            cand->ded[e.v]=e.old;
            double cu=score_plan(*cand,e.u,states[i]);
            double cv=score_plan(*cand,e.v,states[i]);
            cand->ded[e.v]=e.x;cv=std::min(cv,score_plan(*cand,e.v,states[i]));
            e.du+=(cu-costs[e.u][i])/states.size();e.dv+=(cv-costs[e.v][i])/states.size();
        }
        e.gain=-(e.du+e.dv)/256;
    }
    std::sort(edges.begin(),edges.end(),[](const Edge&a,const Edge&b){return a.gain>b.gain;});
    return edges;
}
std::tuple<double,long long,double> simulate(Data&d,const std::vector<Edge>&es,int seqs){
    Data cd=d;std::array<int,256> alternate{};alternate.fill(-1);
    for(auto e:es){cd.papers[e.x].opaque&=~(d.a[e.u]^d.a[e.v]);cd.papers[e.x].black&=cd.papers[e.x].opaque;alternate[e.v]=e.x;}
    auto original=make_solver(cd,true);weight_overlap(*original,d,es);
    std::vector<std::vector<Interleave::Helper>> alternatives(256);
    for(auto e:es){
        auto ded=original->ded;ded[e.v]=e.x;Interleave tab;
        tab.init(original->comparator,original->paper,original->A,ded,original->col_of,original->gmask,original->hmask,1e9);
        alternatives[e.v]=std::move(tab.helpers[e.v]);
    }
    double moves=0,chosen=0,eligible=0;long long wrong=0;
    for(int q=0;q<seqs;++q){
        Solver sim=*original;sim.interleave=std::make_shared<Interleave>(*original->interleave);
        std::mt19937_64 rng(9100003ULL+q*100003ULL);int prev=-1;
        for(int r=0;r<1024;++r){
            int u=r?int(rng()%255):int(rng()%256);if(r&&u>=prev)++u;prev=u;
            auto before=sim.save();auto op=sim.process(u);auto best=sim.save();int size=op.size();
            double value=size+.6*sim.fillers.size()+sim.adaptive_next_cost();
            if(alternate[u]>=0){
                eligible++;sim.restore(before);sim.ded[u]=alternate[u];
                sim.interleave->helpers[u]=alternatives[u];auto op2=sim.process(u);
                double v2=op2.size()+.6*sim.fillers.size()+sim.adaptive_next_cost();
                if(v2<value){best=sim.save();size=op2.size();chosen++;}
                sim.ded[u]=d.ded[u];sim.interleave->helpers[u]=original->interleave->helpers[u];
            }
            sim.restore(best);moves+=size;wrong+=sim.display()!=sim.A[u];
        }
    }
    return {moves/(1024*seqs),wrong,eligible?chosen/eligible:0};
}
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):4,seqs=argc>3?std::stoi(argv[3]):4,samples=argc>4?std::stoi(argv[4]):32;
    std::cout<<"seed,duplicates,screen_gain,moves,wrong,alternate_rate\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);auto edges=select(d,samples);
        std::ofstream eo("solutions/astra-probe/overlap_edges_"+std::to_string(seed)+".csv");eo<<"paper,u,v,gain,delta_u,delta_v\n";
        for(auto e:edges)eo<<e.x<<','<<e.u<<','<<e.v<<','<<e.gain<<','<<e.du<<','<<e.dv<<'\n';
        std::vector<Edge>chosen;std::array<bool,192>used{};
        for(auto e:edges)if(e.gain>0 && !used[e.x]&&!used[e.old]){used[e.x]=used[e.old]=true;chosen.push_back(e);if(chosen.size()==16)break;}
        for(int cap:{0,4,8,16}){
            std::vector<Edge> es(chosen.begin(),chosen.begin()+std::min(cap,int(chosen.size())));double gain=0;for(auto e:es)gain+=e.gain;
            auto [moves,wrong,rate]=simulate(d,es,seqs);
            std::cout<<seed<<','<<es.size()<<','<<gain<<','<<std::setprecision(10)<<moves<<','<<wrong<<','<<rate<<'\n'<<std::flush;
            if(cap>=int(chosen.size()))break;
        }
    }
}
