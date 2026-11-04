#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using U=std::uint64_t;
struct Paper {U op=0,black=0;};
U bits(const std::string& s,char c){U a=0;for(int j=0;j<int(s.size());j++)if(s[j]==c)a|=U(1)<<j;return a;}
struct Graph {
    using Order=std::array<unsigned char,8>;
    int M,S;std::array<int,256> count{};
    std::vector<Order> perm;
    std::vector<U> display;
    std::vector<int> begin,back,forward_begin,forward;
    int rank(const Order& p)const{int r=0,unused=(1<<M)-1;for(int i=0;i<M;i++){r=r*(M-i)+count[unused&((1<<p[i])-1)];unused^=1<<p[i];}return r;}
    Graph(const std::vector<Paper>& paper,int m):M(m){
        for(int i=0;i<256;i++)count[i]=std::popcount(unsigned(i));
        Order p{};std::iota(p.begin(),p.begin()+M,0);
        do{perm.push_back(p);}while(std::next_permutation(p.begin(),p.begin()+M));
        S=perm.size();display.resize(S);std::vector<std::vector<int>> rev(S),next(S);
        for(int s=0;s<S;s++){
            U covered=0;unsigned visible=0;
            for(int j=0;j<M;j++){int x=perm[s][j];U seen=paper[x+1].op&~covered;if(seen)visible|=1<<x;display[s]|=paper[x+1].black&seen;covered|=paper[x+1].op;}
            for(int a=0;a<M;a++)if(visible>>perm[s][a]&1)for(int d=0;d<M;d++)if(a!=d){
                Order q=perm[s];int x=q[a];if(a<d)for(int j=a;j<d;j++)q[j]=q[j+1];else for(int j=a;j>d;j--)q[j]=q[j-1];q[d]=x;
                int t=rank(q);next[s].push_back(t);
            }
            std::sort(next[s].begin(),next[s].end());next[s].erase(std::unique(next[s].begin(),next[s].end()),next[s].end());
            for(int t:next[s])rev[t].push_back(s);
        }
        begin.resize(S+1);forward_begin.resize(S+1);
        for(int s=0;s<S;s++){begin[s+1]=begin[s]+rev[s].size();forward_begin[s+1]=forward_begin[s]+next[s].size();}
        back.resize(begin[S]);forward.resize(forward_begin[S]);
        for(int s=0;s<S;s++){std::copy(rev[s].begin(),rev[s].end(),back.begin()+begin[s]);std::copy(next[s].begin(),next[s].end(),forward.begin()+forward_begin[s]);}
    }
};
struct Target {int product;std::vector<int> goal,order;std::vector<unsigned char> distance;std::vector<int> policy;};

int main(int argc,char** argv){
    if(argc<4)return 2;auto started=std::chrono::steady_clock::now();
    auto elapsed=[&]{return std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()*CLOCK_SCALE;};
    std::ifstream in(argv[1]),out(argv[2]);int N,K,P,R;in>>N>>K>>P>>R;int M=std::stoi(argv[3]);if(M<2||M>8)return 3;
    std::string line;std::vector<U>A(P);for(auto& a:A){in>>line;a=bits(line,'1');}
    std::vector<Paper> papers(K);for(auto& p:papers){out>>line;p={~bits(line,'.'),bits(line,'1')};}
    if(!in||!out||N!=64)return 4;
    U cap=papers[0].op,gm=0;for(int x=1;x<=M;x++)gm|=papers[x].op;
    std::vector<int> owner(P,-1);for(int x=M+1;x<K;x++)for(int a=0;a<P;a++)if(!((A[a]^papers[x].black)&papers[x].op&~cap)){if(owner[a]>=0)return 5;owner[a]=x;}
    if(std::find(owner.begin(),owner.end(),-1)!=owner.end())return 6;
    Graph graph(papers,M);int S=graph.S;
    std::vector<Target> targets;
    for(int a=0;a<P;a++){
        U holes=gm&~papers[owner[a]].op;if(!holes)continue;
        Target t;t.product=a;t.distance.assign(S,255);t.policy.resize(S);
        for(int s=0;s<S;s++)if(!((graph.display[s]^A[a])&holes)){t.goal.push_back(s);t.order.push_back(s);t.distance[s]=0;}
        if(t.goal.empty())return 7;
        for(int front=0;front<int(t.order.size());front++){int s=t.order[front];for(int j=graph.begin[s];j<graph.begin[s+1];j++){int b=graph.back[j];if(t.distance[b]!=255)continue;t.distance[b]=t.distance[s]+1;t.order.push_back(b);}}
        if(int(t.order.size())!=S)return 8;
        targets.push_back(std::move(t));
    }
    int Q=targets.size(),threads=argc>4?std::stoi(argv[4]):4;
    std::vector<double> future(S);double uniform=0;
    for(const auto& t:targets)for(int s=0;s<S;s++)future[s]+=double(t.distance[s])/Q;
    uniform=std::accumulate(future.begin(),future.end(),0.0)/S;
    // At each distance level the best root is the goal with minimum terminal
    // value among all shortest paths. Goal choices may be reached by many paths.
    auto transform=[&](Target& t,const std::vector<double>& h,std::vector<double>& d,std::vector<int>& root,bool exact){
        if(!exact){
            for(int s:t.order){
                if(t.distance[s]==0){d[s]=h[s];root[s]=s;continue;}
                double v=1e100;int r=-1;
                for(int j=graph.forward_begin[s];j<graph.forward_begin[s+1];j++){
                    int b=graph.forward[j];if(t.distance[b]+1!=t.distance[s])continue;
                    if(d[b]<v){v=d[b];r=root[b];}
                }
                d[s]=v;root[s]=r;
            }
            for(int s=0;s<S;s++)d[s]+=t.distance[s];
        }else{
            using Item=std::pair<double,int>;
            std::priority_queue<Item,std::vector<Item>,std::greater<Item>> heap;
            std::fill(d.begin(),d.end(),1e100);
            for(int s:t.goal){d[s]=h[s];root[s]=s;heap.emplace(d[s],s);}
            while(!heap.empty()){
                auto[value,s]=heap.top();heap.pop();if(value!=d[s])continue;
                for(int j=graph.begin[s];j<graph.begin[s+1];j++){
                    int b=graph.back[j];if(d[b]<=value+1)continue;
                    d[b]=value+1;root[b]=root[s];heap.emplace(d[b],b);
                }
            }
        }
    };
    // Fix the current look-ahead policy first, then evaluate its steady state.
    std::vector<double> work(S);std::vector<int> root(S);
    {
        // Independently compare the distance-level transform with unrestricted
        // shortest paths, using a bounded deterministic terminal value.
        std::vector<double> h(S),check(S);std::vector<int> roots(S);
        for(int s=0;s<S;s++)h[s]=0.7*double((s*173+19)%997)/997;
        for(int a=0;a<std::min(Q,4);a++){
            transform(targets[a],h,work,root,false);transform(targets[a],h,check,roots,true);
            for(int s=0;s<S;s++)if(std::abs(work[s]-check[s])>1e-10)return 9;
        }
    }
    for(auto& t:targets){transform(t,future,work,root,false);t.policy=root;}
    auto iterate=[&](bool optimize){
        std::vector<double> h(S),nh(S);double lo=0,hi=1e10;int it=0;
        for(;it<200&&hi-lo>1e-8;it++){
            std::fill(nh.begin(),nh.end(),0.0);
            if(!optimize){for(const auto& t:targets)for(int s=0;s<S;s++)nh[s]+=(t.distance[s]+h[t.policy[s]])/Q;}
            else{
                const double span=*std::max_element(h.begin(),h.end())-*std::min_element(h.begin(),h.end());
                // With value span below one, an extra move cannot compensate
                // its cost. Otherwise use the unrestricted Dijkstra transform.
                bool exact=span>=1.0;
                std::atomic<int> next{0};std::vector<std::vector<double>> partial(threads,std::vector<double>(S));std::vector<std::thread> workers;
                for(int worker=0;worker<threads;worker++)workers.emplace_back([&,worker]{std::vector<double>d(S);std::vector<int>r(S);while(true){int a=next.fetch_add(1);if(a>=Q)break;transform(targets[a],h,d,r,exact);for(int s=0;s<S;s++)partial[worker][s]+=d[s]/Q;}});
                for(auto& w:workers)w.join();for(auto& v:partial)for(int s=0;s<S;s++)nh[s]+=v[s];
            }
            lo=1e100;hi=-1e100;for(int s=0;s<S;s++){lo=std::min(lo,nh[s]-h[s]);hi=std::max(hi,nh[s]-h[s]);}
            double offset=nh[0];for(auto& v:nh)v-=offset;h.swap(nh);
            if(optimize&&it%10==0)std::cerr<<"iteration "<<it<<" bounds "<<lo<<' '<<hi<<" time "<<elapsed()<<'\n';
        }
        double span=*std::max_element(h.begin(),h.end())-*std::min_element(h.begin(),h.end());
        return std::array<double,4>{lo,hi,double(it),span};
    };
    auto policy=iterate(false),optimal=iterate(true);
    std::cout<<std::setprecision(12)<<"{\"M\":"<<M<<",\"states\":"<<S<<",\"targets\":"<<Q<<",\"uniform\":"<<uniform<<",\"policy_lo\":"<<policy[0]<<",\"policy_hi\":"<<policy[1]<<",\"optimal_lo\":"<<optimal[0]<<",\"optimal_hi\":"<<optimal[1]<<",\"iterations\":"<<optimal[2]<<",\"value_span\":"<<optimal[3]<<",\"global_gain\":"<<(optimal[0]-policy[0])*Q/P<<",\"elapsed\":"<<elapsed()<<"}\n";
}
