#include "common.hpp"

// A cheap counterfactual model. All starting generic permutations have equal
// weight; the held-out controller measures whether these savings survive.
struct GenericHoles {
    static constexpr int S=720,W=12;
    using Bits=std::array<u64,W>;
    using Dist=std::array<uint8_t,S>;
    Solver& s;
    std::vector<int> donors;
    std::vector<std::vector<int>> owners;
    std::vector<double> depth;
    std::vector<std::array<Bits,6>> balls;
    std::array<u64,S> display{};
    std::array<std::array<u64,7>,S> prefix{};
    std::vector<Dist> direct,helper;
    std::vector<std::vector<float>> charge;
    std::vector<std::array<float,S>> best,second;
    std::vector<std::array<int16_t,S>> winner;
    int accepted=0,trials=0,invalid=0;
    double predicted=0;

    explicit GenericHoles(Solver& solver):s(solver),owners(K),balls(S),direct(P),best(P),second(P),winner(P){
        Perforation p(s);
        auto heads=p.choose_heads();
        for(int c=0;c<s.H;c++)for(int b=0;b<2;b++){
            donors.push_back(heads[c][b]);depth.push_back(1-p.probability[c][b]);
        }
        for(int u=0;u<P;u++)owners[s.ded[u]].push_back(u);
        charge.assign(P,std::vector<float>(donors.size(),1e6));
        helper.resize(P*donors.size());
        for(int a=0;a<S;a++){
            u64 covered=0;
            for(int i=0;i<6;i++){
                int k=s.comparator.perms[a][i];display[a]|=s.paper[k].black&~covered;
                covered|=s.paper[k].opaque;prefix[a][i+1]=covered;
            }
            for(int b=0;b<S;b++){
                int d=s.comparator.distance(a,b);
                for(int j=d;j<6;j++)balls[a][j][b>>6]|=1ULL<<(b&63);
            }
        }
        for(int u=0;u<P;u++)for(int id=0;id<int(donors.size());id++){
            int k=donors[id],own=s.ded[u];u64 hh=s.hmask&~s.paper[own].opaque;
            if(s.col_of[k]==s.col_of[own]||((s.paper[k].black^s.A[u])&s.paper[k].opaque&hh))continue;
            double cover=0;
            for(int c=0;c<s.H;c++)if((s.paper[k].opaque&hh)>>s.handle[c]&1)
                cover+=p.probability[c][((s.A[u]>>s.handle[c])&1)^1];
            charge[u][id]=1.6+depth[id]-cover;
        }
        rebuild();
    }
    Dist distances(const Bits& goals)const{
        Dist result;result.fill(255);
        int n=0;for(u64 b:goals)n+=__builtin_popcountll(b);
        if(!n)return result;
        if(n==S){result.fill(0);return result;}
        for(int a=0;a<S;a++){
            if(goals[a>>6]>>(a&63)&1){result[a]=0;continue;}
            for(int d=1;d<6;d++){
                bool found=false;
                for(int w=0;w<W;w++)if(balls[a][d][w]&goals[w]){found=true;break;}
                if(found){result[a]=d;break;}
            }
            assert(result[a]<6);
        }
        return result;
    }
    Dist calculate(int u,int id=-1)const{
        Bits goals{};u64 holes=s.gmask&~s.paper[s.ded[u]].opaque;
        if(id<0){
            for(int a=0;a<S;a++)if(!((display[a]^s.A[u])&holes))goals[a>>6]|=1ULL<<(a&63);
        }else{
            if(charge[u][id]>1e5){Dist r;r.fill(255);return r;}
            const auto& p=s.paper[donors[id]];
            for(int a=0;a<S;a++)for(int t=6;t>=0;t--){
                u64 shown=(display[a]&(prefix[a][t]|~p.opaque))|(p.black&~prefix[a][t]);
                if(!((shown^s.A[u])&holes)){goals[a>>6]|=1ULL<<(a&63);break;}
            }
        }
        return distances(goals);
    }
    void rebuild(){
        int D=donors.size();
        for(int u=0;u<P;u++){
            direct[u]=calculate(u);assert(direct[u][0]<255);
            for(int id=0;id<D;id++)helper[u*D+id]=calculate(u,id);
            for(int a=0;a<S;a++){
                best[u][a]=direct[u][a];second[u][a]=1e6;winner[u][a]=-1;
                for(int id=0;id<D;id++){
                    float v=helper[u*D+id][a]+charge[u][id];
                    if(v<best[u][a])second[u][a]=best[u][a],best[u][a]=v,winner[u][a]=id;
                    else if(v<second[u][a])second[u][a]=v;
                }
            }
        }
    }
    void run(double weight){
        std::vector<std::pair<int,int>> candidates;
        for(int id=0;id<int(donors.size());id++)for(u64 z=s.paper[donors[id]].opaque&s.gmask;z;z&=z-1)
            candidates.push_back({id,__builtin_ctzll(z)});
        std::mt19937_64 random(439001003);std::shuffle(candidates.begin(),candidates.end(),random);
        for(auto[id,j]:candidates){
            int k=donors[id];auto old=s.paper[k];s.paper[k].opaque&=~(1ULL<<j);s.paper[k].black&=s.paper[k].opaque;trials++;
            bool valid=true;double base_change=0,combined_change=0;
            for(int u:owners[k]){
                auto own=calculate(u);if(own[0]==255){valid=false;break;}
                std::array<float,S> cost;for(int a=0;a<S;a++){cost[a]=own[a];base_change+=int(own[a])-direct[u][a];}
                for(int y=0;y<int(donors.size());y++)if(charge[u][y]<1e5){
                    auto d=calculate(u,y);for(int a=0;a<S;a++)cost[a]=std::min(cost[a],d[a]+charge[u][y]);
                }
                for(int a=0;a<S;a++)combined_change+=cost[a]-best[u][a];
            }
            if(!valid){s.paper[k]=old;invalid++;continue;}
            for(int u=0;u<P;u++)if(s.ded[u]!=k&&charge[u][id]<1e5){
                auto d=calculate(u,id);
                for(int a=0;a<S;a++){
                    float without=winner[u][a]==id?second[u][a]:best[u][a];
                    combined_change+=std::min(without,d[a]+charge[u][id])-best[u][a];
                }
            }
            double change=(1-weight)*base_change+weight*combined_change;
            if(change<-1e-5){accepted++;predicted+=change/(S*P);rebuild();}
            else s.paper[k]=old;
        }
    }
};

int main(int argc,char**argv){
    if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
    auto d=recover(*base);materialize(*base,*d);Perforation p(*base);p.run(.5,1,false);p.install();
    base->init_handle_cache();base->adaptive_initialized=false;base->init_adaptive();
    int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
    std::cout<<std::setprecision(12)<<"[";
    for(int mode=0;mode<4;mode++){
        Solver s=*base;int holes=0,trials=0,invalid=0;double start=elapsed_sec(),prediction=0;
        if(mode){GenericHoles model(s);model.run(mode==1?.25:mode==2?.5:1);holes=model.accepted;trials=model.trials;invalid=model.invalid;prediction=model.predicted;}
        double design_seconds=elapsed_sec()-start;
        s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
        auto initial=s.save();long long total=0;start=elapsed_sec();
        for(int q=0;q<sequences;q++){
            s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){
                int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
                auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
                if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
            }
        }
        assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
        std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"holes\":"<<holes<<",\"trials\":"<<trials<<",\"invalid\":"<<invalid<<",\"prediction\":"<<prediction<<",\"design_seconds\":"<<design_seconds<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
