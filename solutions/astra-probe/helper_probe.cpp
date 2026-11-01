// Fixed shallow anchor dictionary: feasibility and decoder costs for pairs
// forbidden by the original comparator. This is a model on saved snapshots,
// not a full redesign. All anchors and their original target assignments must
// remain frozen in any implementation using these witnesses.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
struct Snapshot {int generic;std::array<int,192> depth{};std::array<std::array<int,2>,28> fix{};};
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8,limit=argc>3?std::stoi(argv[3]):300;
    bool engineered=argc>4&&std::string(argv[4])=="sparse";
    std::cout<<"seed,u,v,handle_diff,total_diff,helpers_u,helpers_v,decoder,decoder_without_handle_credit,rate_below_3_4,mean_generic,mean_access,mean_credit,helper_mask_u,helper_mask_v\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);auto ptr=make_solver(d,false);auto&s=*ptr;
        Interleave table;table.init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);
        std::vector<Snapshot> snapshots;std::vector<int> trace(192);std::iota(trace.begin(),trace.end(),0);
        for(int r=0;r<1024;++r){
            if(r%32==0){
                s.order=trace;s.fillers.clear();s.canonicalize();s.ops.clear();s.invalid=false;s.check_vis=true;
                if(s.top_d>=0)s.return_paper(s.top_d,-1,1);
                auto old=s.fillers;s.return_visible_fillers(old,-1,1);assert(!s.invalid);
                Snapshot z;z.generic=table.state(s.order);
                std::array<int,28> ranks{};
                for(int k:s.order)if(k>=6)z.depth[k]=ranks[s.col_of[k]]++;
                for(int c=0;c<28;++c)for(int b=0;b<2;++b)z.fix[c][b]=s.handle_fix_cost(c,b);
                snapshots.push_back(z);
            }
            for(auto[k,depth]:d.queries[r]){auto it=std::find(trace.begin(),trace.end(),k);trace.erase(it);trace.insert(trace.begin()+depth,k);}
        }
        std::vector<int> anchors;std::array<bool,256>locked{};
        for(int k=6;k<192;++k)if(d.cols[k]<8)anchors.push_back(k);
        for(int u=0;u<256;++u)locked[u]=d.cols[d.ded[u]]<8;
        if(engineered){
            std::ofstream costfile("solutions/astra-probe/anchor_costs_"+std::to_string(seed)+".csv");
            costfile<<"paper,targets,removed_G,removed_H,generic_cost_increment,handle_cost_increment\n";
            auto mean=[&](int u,u64 holes){auto cl=s.comparator.closure(d.a[u],holes);u64 rel=0;for(int a=0;a<6;++a){assert(!(cl[a]>>a&1));rel|=u64(cl[a])<<(8*a);}const auto&t=PosetSums::get();return t.one[t.slot_of(rel)]/720.0;};
            for(int k:anchors){
                std::vector<int> own;for(int u=0;u<256;++u)if(d.ded[u]==k)own.push_back(u);
                std::vector<std::vector<int>> goals;
                u64 oldop=s.paper[k].opaque,oldgh=~oldop&s.gmask,bestmask=oldop&s.gmask;int bestsize=65;
                for(int u:own){goals.emplace_back();for(int z=0;z<720;++z)if(!((table.display[z]^d.a[u])&oldgh))goals.back().push_back(z);}
                if(own.size()==1){for(int z:goals[0]){u64 m=(table.display[z]^d.a[own[0]])&s.gmask;int size=std::popcount(m);if(size<bestsize){bestsize=size;bestmask=m;}}}
                else for(int x:goals[0])for(int y:goals[1]){u64 m=((table.display[x]^d.a[own[0]])|(table.display[y]^d.a[own[1]]))&oldop&s.gmask;int size=std::popcount(m);if(size<bestsize){bestsize=size;bestmask=m;}}
                s.paper[k].opaque=bestmask|(1ULL<<(36+d.cols[k]));s.paper[k].black=d.a[own[0]]&s.paper[k].opaque;
                double gc=0;for(int u:own)gc+=mean(u,~s.paper[k].opaque&s.gmask)-mean(u,oldgh);
                int hg=std::popcount((oldop&~s.paper[k].opaque)&s.gmask),hh=std::popcount((oldop&~s.paper[k].opaque)&s.hmask);
                costfile<<k<<','<<own.size()<<','<<hg<<','<<hh<<','<<gc/256<<','<<.4*hh*own.size()/256<<'\n';
            }
        }
        struct E{int u,v,hd,fd;};std::vector<E> edges;
        for(int u=0;u<256;++u)if(!locked[u])for(int v=u+1;v<256;++v)if(!locked[v]&&d.cost(u,v,0)<0){
            const auto delta=d.a[u]^d.a[v];int fd=std::popcount(delta),hd=std::popcount(delta>>36);
            if(fd<=26)edges.push_back({u,v,hd,fd});
        }
        std::sort(edges.begin(),edges.end(),[](E a,E b){return std::tuple(a.hd,a.fd,a.u,a.v)<std::tuple(b.hd,b.fd,b.u,b.v);});
        if((int)edges.size()>limit)edges.resize(limit);
        for(auto e:edges){
            const u64 delta=d.a[e.u]^d.a[e.v],gh=delta&low_bits(36),hh=delta&~low_bits(36);
            std::array<int,2> counts{};std::array<u64,2> masks{};
            double total=0,uncredited=0,rate=0,gen=0,access=0,credit=0;
            bool feasible=true;
            for(int side=0;side<2;++side){
                int u=side?e.v:e.u;std::vector<double> best(snapshots.size(),1e9),bestnc(snapshots.size(),1e9);
                std::vector<int> bg(snapshots.size()),ba(snapshots.size()),bc(snapshots.size());
                for(int ki=0;ki<(int)anchors.size();++ki){int k=anchors[ki];
                    auto pp=s.paper[k];if((pp.black^d.a[u])&pp.opaque&hh)continue;
                    std::vector<int> goals;
                    for(int state=0;state<720;++state)for(int t=6;t>=0;--t){
                        u64 y=(table.display[state]&(table.prefix[state][t]|~pp.opaque))|(pp.black&~table.prefix[state][t]);
                        if(!((y^d.a[u])&gh)){goals.push_back(state);break;}
                    }
                    if(goals.empty())continue;++counts[side];masks[side]|=1ULL<<ki;
                    for(int q=0;q<(int)snapshots.size();++q){
                        const auto&z=snapshots[q];int dist=6;
                        for(int g:goals)if((dist=std::min(dist,s.comparator.distance(z.generic,g)))==0)break;
                        int saved=0;
                        for(int c=0;c<8;++c)if((hh&pp.opaque)>>(36+c)&1)saved+=z.fix[c][d.a[u]>>(36+c)&1];
                        const double raw=dist+z.depth[k]+1.6,val=raw-saved;
                        bestnc[q]=std::min(bestnc[q],raw);
                        if(val<best[q]){best[q]=val;bg[q]=dist;ba[q]=z.depth[k];bc[q]=saved;}
                    }
                }
                if(!counts[side]){feasible=false;continue;}
                for(int q=0;q<(int)snapshots.size();++q){
                    total+=best[q]/(2*snapshots.size());uncredited+=bestnc[q]/(2*snapshots.size());rate+=(best[q]<=3.4)/(2.0*snapshots.size());
                    gen+=bg[q]/(2.0*snapshots.size());access+=ba[q]/(2.0*snapshots.size());credit+=bc[q]/(2.0*snapshots.size());
                }
            }
            std::cout<<seed<<','<<e.u<<','<<e.v<<','<<e.hd<<','<<e.fd<<','<<counts[0]<<','<<counts[1]<<',';
            if(feasible)std::cout<<total<<','<<uncredited<<','<<rate<<','<<gen<<','<<access<<','<<credit;
            else std::cout<<"nan,nan,nan,nan,nan,nan";
            std::cout<<','<<masks[0]<<','<<masks[1]<<'\n';
        }
        std::cout<<std::flush;
    }
}
