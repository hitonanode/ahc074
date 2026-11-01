// Same exact legal six-card graph as module3_toy.cpp, but includes actual
// distributions of partially exposed handle masks. This remains a relaxation.
#define main module3_original_main
#include "module3_toy.cpp"
#undef main
int main(){
    Order p{0,1,2,3,4,5};do orders.push_back(p);while(std::next_permutation(p.begin(),p.end()));
    struct Event{int mask,bits;double weight;};
    std::array<std::vector<Event>,9>events;
    for(int b,n;std::cin>>b>>n;)for(int i=0;i<n;++i){Event e{};std::cin>>e.mask>>e.bits>>e.weight;events[b].push_back(e);}
    struct Case{std::string name;std::array<int,6>op;bool canonical;int max_fillers=6;};
    std::cout<<"variant,block,event_rate,mean_per_event,cost_per_global_query,residual_span\n";
    for(auto c:std::vector<Case>{{"triangular_canonical",{1,1,3,3,7,7},true},{"triangular_filler1",{1,1,3,3,7,7},false,1},{"triangular_filler2",{1,1,3,3,7,7},false,2},{"triangular_free",{1,1,3,3,7,7},false},{"star_patches",{7,1,3,2,7,4},false}}){
        Model m(c.op,c.canonical);
        // Same greedy in-place subsequence as imp-910::canonicalize, without
        // a generic layer or top dedicated paper in this local relaxation.
        if(c.max_fillers<6)for(auto& goal:m.goals)std::erase_if(goal,[&](int s){
            int cur=3,fillers=0;for(int i=5;i>=0;--i){int col=orders[s][i]/2;if(col<=cur)cur=col;else ++fillers;}
            return fillers>c.max_fillers;
        });
        for(int b=0;b<9;++b){
            double rate=0;std::vector<std::vector<int>> goals;
            for(auto e:events[b]){rate+=e.weight;goals.emplace_back();if(!e.mask)goals.back()=m.goals[8+e.bits];else for(int a=0;a<8;++a)if((a&e.mask)==e.bits)goals.back().insert(goals.back().end(),m.goals[a].begin(),m.goals[a].end());}
            std::array<double,720>v{},next{};double mean=0,span=0;
            for(int it=0;it<2000;++it){
                double mn=1e99,mx=-1e99;
                for(int s=0;s<720;++s){
                    next[s]=0;auto*d=m.dist.data()+s*720;
                    for(int e=0;e<(int)events[b].size();++e){double best=1e99;for(int t:goals[e])best=std::min(best,d[t]+v[t]);next[s]+=best*events[b][e].weight/rate;}
                    mn=std::min(mn,next[s]-v[s]);mx=std::max(mx,next[s]-v[s]);
                }
                mean=(mn+mx)/2;span=mx-mn;double off=next[0];for(int s=0;s<720;++s)v[s]=next[s]-off;
                if(span<1e-9)break;
            }
            std::cout<<c.name<<','<<b<<','<<rate<<','<<std::setprecision(12)<<mean<<','<<rate*mean<<','<<span<<'\n'<<std::flush;
        }
    }
}
