// Legal full-order simulation of an actual long three-handle module plus a cap.
// All n dedicated sheets remain individually present; no representative stands
// for a whole queue. Cap/data tags make the requested sheet uniquely the top.
// A bounded beam is an approximate online policy, not an optimality certificate.
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
constexpr int MAXN=192;
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using Order=std::array<uint8_t,MAXN>;
struct Paper {int op,black;double weight;int paired=0;};
struct Event {int top,bits;};
struct Node {Order order{};double score=0,potential=0;int parent=-1,k=-1,d=-1;};
struct Engine {
    int n,cap,width,max_depth,handles;
    double lambda;
    std::vector<Paper> paper;
    uint64_t expanded=0,constructive_used=0;
    Engine(int count,int w,double l,int h):n(count+1),cap(count),width(w),max_depth(90),handles(h),lambda(l),paper(n){}
    int display(const Order& p) const {int cov=0,black=0;for(int i=0;i<n;++i){int k=p[i];black|=paper[k].black&~cov;cov|=paper[k].op;}return black;}
    bool goal(const Order& p,Event e) const {
        return p[0]==e.top&&display(p)==e.bits&&(!paper[e.top].paired||p[1]==cap);
    }
    std::array<bool,MAXN> visible(const Order& p) const {
        std::array<bool,MAXN> vis{};vis[p[0]]=true;int cov=0;
        for(int i=0;i<n;++i){int k=p[i];if(paper[k].op&~cov)vis[k]=true;cov|=paper[k].op;}return vis;
    }
    // The access lower bound counts the cheapest witness's blockers, or removes
    // every sheet above the goal. All sheets are opaque in the data-tag windows.
    std::pair<double,double> evaluate(const Order& p,Event e) const {
        int count[28]{},access=0;double potential=0;bool cap_above=false;
        for(int i=0;i<n;++i){
            int k=p[i],best=(cap_above&&k!=cap)?100000:i;
            for(int w=0;w<handles;++w)if(paper[k].op>>w&1)best=std::min(best,1+count[w]);
            if(k==e.top)access=best;
            potential+=paper[k].weight*best;
            for(int w=0;w<handles;++w)count[w]+=paper[k].op>>w&1;
            cap_above|=k==cap;
        }
        int cov=paper[e.top].op,black=paper[e.top].black;
        for(int i=0;i<n;++i){int k=p[i];if(k==e.top)continue;black|=paper[k].black&~cov;cov|=paper[k].op;}
        // Additional guidance after a hypothetical free lift. It can overlap
        // access moves and is NOT an admissible lower bound; this is beam search.
        double guidance=access+0.8*__builtin_popcount(unsigned(black^e.bits));
        double pair_probability=0;for(int k=0;k<n;++k)if(paper[k].paired)pair_probability+=paper[k].weight;
        potential+=pair_probability*(std::find(p.begin(),p.begin()+n,cap)-p.begin());
        return {guidance,potential};
    }
    static uint64_t hash(const Order& p,int n){uint64_t h=1469598103934665603ULL;for(int i=0;i<n;++i){h^=p[i]+1;h*=1099511628211ULL;}return h;}
    Order moved(Order p,int i,int d) const {int k=p[i];if(d<i)for(int j=i;j>d;--j)p[j]=p[j-1];else for(int j=i;j<d;++j)p[j]=p[j+1];p[d]=k;return p;}
    bool feasible(Event e) const {
        int cov=paper[e.top].op,black=paper[e.top].black;
        if((black^e.bits)&cov)return false;
        std::array<bool,MAXN> rem{};for(int k=0;k<n;++k)rem[k]=k!=e.top;int nr=n-1;
        while(nr){bool progress=false;
            for(int k=0;k<n;++k)if(rem[k]){
                int exposed=paper[k].op&~cov;
                if(((paper[k].black^e.bits)&exposed)==0){black|=paper[k].black&~cov;cov|=paper[k].op;rem[k]=false;--nr;progress=true;}
            }
            if(!progress)return false;
        }
        return black==e.bits;
    }
    // A generic top-down construction. A previously selected provider is never
    // disturbed: the next extraction witness is an as-yet-uncovered window.
    // Blockers are inserted below the requested paper, with their future access
    // cost charged by the same potential as the beam. This works for arbitrary
    // masks and includes all physical moves and later recovery.
    std::pair<Order,std::vector<std::pair<int,int>>> construct(Order p,Event e,int mode) const {
        std::vector<std::pair<int,int>> path;
        auto act=[&](int k,int d){int i=std::find(p.begin(),p.begin()+n,k)-p.begin();if(i==d)return;assert(visible(p)[k]);p=moved(p,i,d);path.emplace_back(k,d);};
        auto access=[&](int k,int allowed,bool data){
            int at=std::find(p.begin(),p.begin()+n,k)-p.begin();
            int cp=std::find(p.begin(),p.begin()+n,cap)-p.begin();
            int best=(data&&(k==cap||at<cp))?at:100000,bw=-1;
            for(int w=0;w<handles;++w)if((allowed&paper[k].op)>>w&1){int b=0;for(int i=0;i<at;++i)b+=paper[p[i]].op>>w&1;if(b<best){best=b;bw=w;}}
            return std::pair<int,int>(best,bw);
        };
        auto expose=[&](int k,int allowed,bool data){
            auto [unused,w]=access(k,allowed,data);(void)unused;
            while(true){int at=std::find(p.begin(),p.begin()+n,k)-p.begin(),i=0;
                while(i<at&&w>=0&&!(paper[p[i]].op>>w&1))++i;
                if(i==at)break;
                int x=p[i],bestd=n-1;assert(x!=cap);double best=1e100;
                // After deletion k is at at-1, hence d>=at is below k.
                for(int d=at;d<n;++d){auto q=moved(p,i,d);double value=evaluate(q,e).second;
                    if(value<best-1e-12){best=value;bestd=d;}}
                act(x,bestd);
            }
        };
        expose(e.top,(1<<handles)-1,true);act(e.top,0);
        int cov=paper[e.top].op;
        std::array<bool,MAXN> protected_paper{};protected_paper[e.top]=true;
        for(int stage=0;stage<handles&&display(p)!=e.bits;++stage){
            int remaining=((1<<handles)-1)&~cov,bestk=-1;double best=1e100;
            for(int k=0;k<n;++k)if(!protected_paper[k]){
                int ex=paper[k].op&remaining;
                if(!ex||((paper[k].black^e.bits)&ex))continue;
                auto [dig,w]=access(k,remaining,false);(void)w;
                double key=(dig+1.0)/(mode?1.0:__builtin_popcount(unsigned(ex)));
                key+=paper[k].weight*0.01;
                if(key<best){best=key;bestk=k;}
            }
            if(bestk<0)return {p,{{-1,-1}}};
            expose(bestk,remaining,false);
            int last=0;
            for(int i=0;i<n;++i)if(protected_paper[p[i]])last=i;
            int at=std::find(p.begin(),p.begin()+n,bestk)-p.begin();
            int dest=last+1;
            if(dest<n&&p[dest]==cap&&bestk!=cap)++dest;
            if(at<dest)--dest;
            act(bestk,dest);protected_paper[bestk]=true;cov|=paper[bestk].op;
        }
        if(!goal(p,e))return {p,{{-1,-1}}};
        return {p,path};
    }
    std::vector<std::pair<int,int>> solve(Order& state,Event e){
        std::vector<std::pair<int,int>> prefix;
        // A pair has generic holes. Clear the region above the immobile generic
        // layer before it is reordered; no old dedicated sheet may silently
        // overwrite those holes. During this order only D may be above the cap.
        if(paper[e.top].paired)while(state[0]!=cap){
            int cp=std::find(state.begin(),state.begin()+n,cap)-state.begin();
            int k=state[0],bestd=n-1;double best=1e100;
            for(int d=cp;d<n;++d){auto q=moved(state,0,d);auto [h,pot]=evaluate(q,e);double score=h+lambda*pot;
                if(score<best){best=score;bestd=d;}}
            prefix.emplace_back(k,bestd);state=moved(state,0,bestd);
        }
        // A legal initial upper bound, using the SAME mask design and graph.
        // Build a feasible target permutation, then insertion-sort the actual
        // sheets below the IMMOBILE cap. At most 2n moves including recovery. This
        // is not a switch to the triangular solver; no failed event is dropped.
        Order target{};target[0]=e.top;int fill=1,cov=paper[e.top].op;
        std::array<bool,MAXN> used{};used[e.top]=true;
        while(fill<n){bool progress=false;
            for(int i=0;i<n;++i){int k=state[i];if(used[k])continue;
                if(((paper[k].black^e.bits)&paper[k].op&~cov)==0){target[fill++]=k;used[k]=true;cov|=paper[k].op;progress=true;}
            }
            if(!progress)return {{-1,-1}};
        }
        std::array<int,MAXN> ranks{};for(int i=0;i<n;++i)ranks[target[i]]=i;
        Order sorted=state;std::vector<std::pair<int,int>> initial;
        if(!goal(state,e)){
            while(sorted[0]!=cap){int k=sorted[0];initial.emplace_back(k,n-1);sorted=moved(sorted,0,n-1);}
            for(int t=0;t<n-1;++t){
                int k=sorted[1],less=0;assert(paper[k].op!=0);
                for(int i=n-t;i<n;++i)less+=ranks[sorted[i]]<ranks[k];
                int dest=n-t-1+less;
                if(dest!=1){initial.emplace_back(k,dest);sorted=moved(sorted,1,dest);}
            }
            if(e.top!=cap){assert(sorted[1]==e.top);initial.emplace_back(e.top,0);sorted=moved(sorted,1,0);}
        }
        assert(goal(sorted,e));
        double initial_score=initial.size()+lambda*evaluate(sorted,e).second;
        for(int mode=0;mode<2;++mode){
            auto [q,path]=construct(state,e,mode);
            if(!path.empty()&&path[0].first<0)continue;
            double score=path.size()+lambda*evaluate(q,e).second;
            if(score<initial_score-1e-10){sorted=q;initial=path;initial_score=score;}
        }
        std::vector<Node> arena(1);arena[0].order=state;
        std::vector<int> frontier{0};
        std::unordered_map<uint64_t,int> visited;visited.reserve(100000);
        visited.emplace(hash(state,n),0);
        int best=-2,bestdepth=int(initial.size());double bestscore=bestdepth+lambda*evaluate(sorted,e).second;
        for(int depth=0;depth<=max_depth&&!frontier.empty();++depth){
            for(int id:frontier){auto& nd=arena[id];if(goal(nd.order,e)){
                double sc=depth+lambda*evaluate(nd.order,e).second;
                if(sc<bestscore-1e-10){bestscore=sc;best=id;bestdepth=depth;}
            }}
            if(depth>=max_depth||depth>=std::min(bestdepth+2,int(bestscore)))break;
            std::vector<Node> candidates;candidates.reserve(frontier.size()*n*4);
            for(int id:frontier){const Order p=arena[id].order;auto vis=visible(p);
                for(int i=0;i<n;++i)if(p[i]!=cap&&vis[p[i]])for(int d=0;d<n;++d)if(d!=i){
                    auto q=moved(p,i,d);
                    if(paper[e.top].paired){int cp=std::find(q.begin(),q.begin()+n,cap)-q.begin();
                        if(cp>1||(cp==1&&q[0]!=e.top))continue;
                    }
                    auto h=hash(q,n);
                    auto it=visited.find(h);if(it!=visited.end()&&it->second<depth+1)continue;
                    auto [lb,pot]=evaluate(q,e);++expanded;
                    double sc=depth+1+lb+lambda*pot;
                    if(depth+1>bestscore+1e-9)continue;
                    candidates.push_back({q,sc,pot,id,int(p[i]),d});
                }
            }
            auto less=[](const Node& a,const Node& b){
                if(std::abs(a.score-b.score)>1e-10)return a.score<b.score;
                if(a.potential!=b.potential)return a.potential<b.potential;
                return a.order<b.order;
            };
            std::sort(candidates.begin(),candidates.end(),less);
            frontier.clear();
            for(auto& x:candidates){
                uint64_t h=hash(x.order,n);auto it=visited.find(h);
                if(it!=visited.end()&&it->second<=depth+1)continue;
                visited[h]=depth+1;
                frontier.push_back(arena.size());arena.push_back(x);
                if(int(frontier.size())==width)break;
            }
        }
        std::vector<std::pair<int,int>> path;
        if(best==-2){path=initial;++constructive_used;}
        else {
            for(int id=best;arena[id].parent>=0;id=arena[id].parent)path.emplace_back(arena[id].k,arena[id].d);
            std::reverse(path.begin(),path.end());
        }
        for(auto [k,d]:path){assert(k!=cap&&visible(state)[k]);int at=std::find(state.begin(),state.begin()+n,k)-state.begin();state=moved(state,at,d);}
        assert(goal(state,e));
        prefix.insert(prefix.end(),path.begin(),path.end());
        return prefix;
    }
};
int main(int argc,char**argv){
    auto start=std::chrono::steady_clock::now();
    int width=argc>1?std::stoi(argv[1]):32;
    double lambda=argc>2?std::stod(argv[2]):1.0;
    int handles=argc>3?std::stoi(argv[3]):3;
    int n,r,checks;std::cin>>n>>r>>checks;assert(n<MAXN);
    Engine eng(n,width,lambda,handles);
    for(int k=0;k<=n;++k)std::cin>>eng.paper[k].op>>eng.paper[k].black>>eng.paper[k].weight>>eng.paper[k].paired;
    for(int k=0;k<n;++k)if(!eng.paper[k].op){std::cout<<"no_local_access,"<<k<<'\n';return 0;}
    // Check every public product, including products absent from the test order
    // sequence. These constraints are supplied from the initial barcode list.
    for(int q=0;q<checks;++q){Event e;std::cin>>e.top>>e.bits;
        if(!eng.feasible(e)){std::cout<<"infeasible,"<<e.top<<','<<e.bits<<'\n';return 0;}}
    std::vector<Event> events(r);for(auto& e:events)std::cin>>e.top>>e.bits;
    std::ofstream trace;
    if(argc>4){trace.open(argv[4]);trace<<n<<' '<<r<<' '<<handles<<'\n';
        for(auto p:eng.paper)trace<<p.op<<' '<<p.black<<' '<<p.paired<<'\n';
        for(auto e:events)trace<<e.top<<' '<<e.bits<<'\n';
    }
    Order state{};state[0]=n;for(int i=0;i<n;++i)state[i+1]=i;
    long long moves=0,external=0,internal=0,countint=0,returns=0;
    std::array<long long,8> batch{};
    for(int t=0;t<r;++t){
        auto path=eng.solve(state,events[t]);
        if(!path.empty()&&path[0]==std::make_pair(-1,-1)){std::cout<<"search_failed,"<<t<<','<<moves<<'\n';return 0;}
        if(trace){trace<<path.size()<<'\n';for(auto [k,d]:path)trace<<k<<' '<<d<<'\n';}
        moves+=path.size();batch[std::min(7,t*8/r)]+=path.size();
        if(events[t].top==n)external+=path.size();else {internal+=path.size();++countint;}
        for(auto [k,d]:path)returns+=(k<n&&d>0);
    }
    double sec=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::cout<<"ok,n,requests,moves,per_request,internal_moves,external_moves,internal_requests,non_top_moves,expanded,seconds,batches,constructive_used\n";
    std::cout<<"ok,"<<n<<','<<r<<','<<moves<<','<<std::setprecision(10)<<double(moves)/r<<','<<internal<<','<<external<<','<<countint<<','<<returns<<','<<eng.expanded<<','<<sec;
    for(auto x:batch)std::cout<<','<<x;std::cout<<','<<eng.constructive_used<<'\n';
}
