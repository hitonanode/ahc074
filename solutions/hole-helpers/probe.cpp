#define PATCH_CODE_NO_MAIN
#include "../patch-code/probe.cpp"
#include <unordered_map>
using namespace patch_code;
struct HelperModel {
    Model model;
    struct Donor {int paper,owner,column,count;u64 op,black;};
    std::vector<Donor> donors;std::vector<u64> paper_op,paper_black;std::vector<int> pc,owner,handles,nc;
    struct PairData {int a,b;u64 diff;std::array<u64,2> residual;double original;};std::vector<PairData> pairs;
    std::vector<std::vector<u64>> proposals;
    std::vector<std::unordered_map<u64,std::vector<float>>> cache;
    std::array<bool,256> frozen{};
    std::vector<u64> masks;
    double overhead=1.8;
    u64 residue(u64 target,u64 holes)const{
        std::array<unsigned,6> pred{};for(u64 z=holes&low_bits(model.G);z;z&=z-1){int j=__builtin_ctzll(z);auto[a,b]=model.comp.edge[j];if(int(target>>j&1)!=model.comp.polarity[j])std::swap(a,b);pred[b]|=1U<<a;}
        unsigned remain=63;for(;;){unsigned sources=0;for(int x=0;x<6;x++)if((remain>>x&1)&&!(pred[x]&remain))sources|=1U<<x;if(!sources)break;remain&=~sources;}
        u64 r=0;for(u64 z=holes&low_bits(model.G);z;z&=z-1){int j=__builtin_ctzll(z);auto[a,b]=model.comp.edge[j];if((remain>>a&1)&&(remain>>b&1))r|=1ULL<<j;}return r;
    }
    bool dag(u64 target,u64 holes)const{auto reach=model.comp.closure(target,holes);for(int x=0;x<6;x++)if(reach[x]>>x&1)return false;return true;}
    double mean(u64 target,u64 holes)const{auto r=model.comp.closure(target,holes);u64 key=0;for(int x=0;x<6;x++){if(r[x]>>x&1)return 1e6;key|=u64(r[x])<<(8*x);}auto&t=PosetSums::get();return t.one[t.slot_of(key)]/720.;}
    bool load(const char* in,const char* out,int max_col){
        if(!model.load(in,out))return false;std::ifstream f(out);std::string line;paper_op.resize(192);paper_black.resize(192);pc.assign(192,-1);owner.assign(192,-1);
        auto convert=[&](u64 a){u64 b=0;for(int j=0;j<63;j++)if(a>>model.permutation[j]&1)b|=1ULL<<j;return b;};
        for(int k=0;k<192;k++){f>>line;paper_op[k]=convert(~Model::bits(line,'.'));paper_black[k]=convert(Model::bits(line,'1'));}
        for(int k=7;k<192;k++)for(u64 z=paper_op[k]&~low_bits(model.G);z;z&=z-1){int j=__builtin_ctzll(z);if(std::find(handles.begin(),handles.end(),j)==handles.end())handles.push_back(j);}nc.resize(handles.size());
        for(int k=7;k<192;k++){for(int c=0;c<int(handles.size());c++)if(paper_op[k]>>handles[c]&1)pc[k]=c;nc[pc[k]]++;int count=0;for(int u=0;u<256;u++)if(!((model.A[u]^paper_black[k])&paper_op[k])){owner[k]=u;count++;}if(count==1&&pc[k]<max_col)donors.push_back({k,owner[k],pc[k],0,paper_op[k],paper_black[k]});}
        for(auto& d:donors){d.count=nc[d.column];frozen[d.owner]=true;}
        for(auto p:model.pairs)if(!frozen[p.a]&&!frozen[p.b])pairs.push_back({p.a,p.b,p.diff,{residue(model.A[p.a],p.diff),residue(model.A[p.b],p.diff)},p.old});
        masks.resize(donors.size());proposals.resize(donors.size());cache.resize(donors.size());
        for(int k=0;k<int(donors.size());k++){
            auto&d=donors[k];proposals[k].push_back(0);
            for(auto p:pairs)for(int side=0;side<2;side++){
                int u=side?p.b:p.a;u64 hbad=(d.black^model.A[u])&d.op&p.diff&~low_bits(model.G);if(hbad)continue;
                u64 removed=(d.black^model.A[u])&p.residual[side];if(!removed||!dag(d.black,removed))continue;
                u64 op=d.op&~removed;if(!dag(model.A[u],p.residual[side]&~op))continue;
                proposals[k].push_back(removed);
            }
            std::sort(proposals[k].begin(),proposals[k].end());proposals[k].erase(std::unique(proposals[k].begin(),proposals[k].end()),proposals[k].end());
        }
        return true;
    }
    const std::vector<float>& fees(int k,u64 remove){
        auto&memo=cache[k];auto found=memo.find(remove);if(found!=memo.end())return found->second;
        auto&d=donors[k];u64 op=d.op&~remove;std::vector<float> cost(2*pairs.size(),1e6);
        for(int i=0;i<int(pairs.size());i++){
            auto&p=pairs[i];for(int side=0;side<2;side++){
                int u=side?p.b:p.a;u64 req=p.diff&~low_bits(model.G);if((d.black^model.A[u])&op&(p.residual[side]|req))continue;
                u64 remaining=p.residual[side]&~op;if(!dag(model.A[u],remaining))continue;
                // Optimistic screening: the generic moves needed after the
                // helper covers its correct residual edges. A later exact
                // graph must also enforce the helper insertion position.
                double gen=mean(model.A[u],(p.diff&low_bits(model.G))&~op);
                double retrieval=.5*(d.count-1),credit=.4*__builtin_popcountll(req&op);
                cost[2*i+side]=gen+retrieval+overhead-credit;
            }
        }
        return memo.emplace(remove,std::move(cost)).first->second;
    }
    struct Eval {double value=1e9,own=0;int matched=0,novel=0;};
    Eval evaluate(const std::vector<u64>& remove){
        std::vector<const std::vector<float>*> prices;Eval result;
        for(int k=0;k<int(donors.size());k++){if(!dag(donors[k].black,remove[k]))return result;result.own+=mean(donors[k].black,remove[k]);prices.push_back(&fees(k,remove[k]));}
        std::vector<std::pair<double,int>> ranked;
        for(int i=0;i<int(pairs.size());i++){
            auto&p=pairs[i];double fee=p.original;
            if(p.original<0){double sidefee[2]={1e6,1e6};for(auto v:prices)for(int s=0;s<2;s++)sidefee[s]=std::min(sidefee[s],double((*v)[2*i+s]));fee=sidefee[0]+sidefee[1];}
            if(fee>=1e5)continue;ranked.emplace_back(fee+.65*__builtin_popcountll(p.diff&~low_bits(model.G))+.04*__builtin_popcountll(p.diff),i);
        }
        std::sort(ranked.begin(),ranked.end());std::array<bool,256>used{};double total=0;
        for(auto [cost,i]:ranked){auto&p=pairs[i];if(used[p.a]||used[p.b])continue;used[p.a]=used[p.b]=true;result.matched++;result.novel+=p.original<0;total+=cost;if(result.matched==71)break;}
        result.value=(total+result.own+20*(71-result.matched))/256.;return result;
    }
};
#ifndef HOLE_HELPER_NO_MAIN
int main(int argc,char**argv){if(argc<3)return 2;int columns=argc>3?std::stoi(argv[3]):6,iters=argc>4?std::stoi(argv[4]):10000;double overhead=argc>5?std::stod(argv[5]):1.8;auto start=std::chrono::steady_clock::now();HelperModel m;m.overhead=overhead;if(!m.load(argv[1],argv[2],columns))return 3;
 auto base=m.evaluate(m.masks),current=base,best=base;auto state=m.masks,beststate=state;std::mt19937_64 rng(77934519);int accepted=0;
 for(int it=0;it<iters;it++){
  auto saved=state;int kind=rng()%6;
  if(kind<4){
   int k=rng()%state.size();u64 old=state[k],next=old;
   if(kind<2)next=m.proposals[k][rng()%m.proposals[k].size()];else if(kind==2)next|=m.proposals[k][rng()%m.proposals[k].size()];else next^=1ULL<<(rng()%m.model.G);
   if(next==old||!m.dag(m.donors[k].black,next))continue;state[k]=next;
  }else{
   auto p=m.pairs[rng()%m.pairs.size()];if(p.original>=0)continue;bool valid=true;
   for(int side=0;side<2;side++){
    int u=side?p.b:p.a;std::vector<std::pair<int,u64>> options;
    for(int k=0;k<int(m.donors.size());k++){auto&d=m.donors[k];if((d.black^m.model.A[u])&d.op&p.diff&~low_bits(m.model.G))continue;u64 f=(d.black^m.model.A[u])&p.residual[side];u64 next=state[k]|f;if(!m.dag(d.black,next))continue;u64 op=d.op&~next;if(!m.dag(m.model.A[u],p.residual[side]&~op))continue;options.emplace_back(k,next);}
    if(options.empty()){valid=false;break;}auto[k,next]=options[rng()%options.size()];state[k]=next;
   }
   if(!valid){state=saved;continue;}
  }
  auto e=m.evaluate(state);double temp=.012*std::pow(.01,double(it)/iters);
  if(e.value<=current.value||std::generate_canonical<double,53>(rng)<std::exp((current.value-e.value)/temp)){current=e;accepted++;}else state=saved;
  if(current.value<best.value){best=current;beststate=state;std::cerr<<"best "<<it<<' '<<best.value<<" own "<<best.own/256<<" novel "<<best.novel<<'\n';}
 }
 std::cout<<std::setprecision(12)<<"{\"columns\":"<<columns<<",\"overhead\":"<<overhead<<",\"donors\":"<<m.donors.size()<<",\"baseline\":"<<base.value<<",\"best\":"<<best.value<<",\"difference\":"<<best.value-base.value<<",\"own\":"<<best.own/256<<",\"novel\":"<<best.novel<<",\"matched\":"<<best.matched<<",\"masks\":[";
 for(int k=0;k<int(state.size());k++)std::cout<<(k?",":"")<<beststate[k];std::cout<<"],\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}

#endif
