// Exact finite-state model of three handle windows, six dedicated sheets, and
// a cap representing the data layer / an external target. Unlike astra-probe's
// visibility-only toy, an internal order requires its specific sheet ON TOP,
// all three handle colors correct, and pays later legal recovery of the cap.
// All sheets have distinct opaque 3-bit data tags (the cap tag is 000).
// This is a seven-sheet local model, not a 192-sheet score prediction.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <utility>
#include <vector>

constexpr int N = 7, S = 5040;
using Order = std::array<uint8_t,N>;
std::vector<Order> orders;
std::vector<std::array<std::array<int,N>,N>> next_state;
int rank_order(const Order& p) {
    int rank=0;
    for(int i=0;i<N;++i){int smaller=0;for(int j=i+1;j<N;++j)smaller+=p[j]<p[i];rank=rank*(N-i)+smaller;}
    return rank;
}
void init() {
    Order p{0,1,2,3,4,5,6};
    do orders.push_back(p); while(std::next_permutation(p.begin(),p.end()));
    next_state.resize(S);
    for(int s=0;s<S;++s)for(int i=0;i<N;++i)for(int d=0;d<N;++d){
        auto p=orders[s];int k=p[i];
        if(d<i)for(int j=i;j>d;--j)p[j]=p[j-1];
        else for(int j=i;j<d;++j)p[j]=p[j+1];
        p[d]=k;next_state[s][i][d]=rank_order(p);
    }
}
struct Model {
    std::array<int,6> op,black;
    std::vector<std::vector<int>> rev,goals;
    Model(std::array<int,6> o,std::array<int,6> b):op(o),black(b),rev(S),goals(14){
        for(int s=0;s<S;++s){
            int cov=0,display=0,vis=1<<orders[s][0];
            for(int k:orders[s])if(k<6){int e=op[k]&~cov;if(e)vis|=1<<k;display|=black[k]&e;cov|=op[k];}
            int top=orders[s][0];
            if(top==6)goals[display].push_back(s);
            else if(display==black[top])goals[8+top].push_back(s);
            // The cap represents the external layer and cannot be shifted as
            // if all outside sheets were one movable paper.
            for(int i=0;i<N;++i)if(orders[s][i]!=6&&(vis>>orders[s][i]&1))for(int d=0;d<N;++d)if(i!=d)
                rev[next_state[s][i][d]].push_back(s);
        }
        for(auto& v:rev){std::sort(v.begin(),v.end());v.erase(std::unique(v.begin(),v.end()),v.end());}
    }
    struct Result {double cost=99,span=99;int iters=0;};
    Result solve(const std::array<double,14>& prob,double eps=1e-8,int limit=600) const {
        for(int e=0;e<14;++e)if(prob[e]>0&&goals[e].empty())return {};
        std::vector<double> v(S),nv(S),dist(S);
        using Item=std::pair<double,int>;
        Result res;
        for(int it=0;it<limit;++it){
            std::fill(nv.begin(),nv.end(),0);
            for(int e=0;e<14;++e)if(prob[e]>0){
                std::fill(dist.begin(),dist.end(),1e50);
                std::priority_queue<Item,std::vector<Item>,std::greater<Item>> heap;
                for(int t:goals[e]){dist[t]=v[t];heap.emplace(v[t],t);}
                while(!heap.empty()){
                    auto [d,s]=heap.top();heap.pop();if(d!=dist[s])continue;
                    for(int t:rev[s])if(dist[t]>d+1+1e-12){dist[t]=d+1;heap.emplace(d+1,t);}
                }
                for(int s=0;s<S;++s)nv[s]+=prob[e]*dist[s];
            }
            double mn=1e100,mx=-1e100;
            for(int s=0;s<S;++s){mn=std::min(mn,nv[s]-v[s]);mx=std::max(mx,nv[s]-v[s]);}
            res={(mn+mx)*0.5,mx-mn,it+1};double off=nv[0];
            for(int s=0;s<S;++s)v[s]=nv[s]-off;
            if(res.span<eps)break;
        }
        return res;
    }
};

int main(int argc,char**argv){
    init();
    // mode, access rate, number of random local mutations; fixed PRNG.
    std::string mode=argc>1?argv[1]:"fixed";
    double rho=argc>2?std::stod(argv[2]):0.18;
    int trials=argc>3?std::stoi(argv[3]):0;
    std::array<int,6> colors{0,7,1,6,2,5};
    std::array<double,14> prob{};
    for(int e=0;e<14;++e)prob[e]=e<8?(1-rho)/8:rho/6;
    if(mode=="input"){
        for(int& x:colors)std::cin>>x;
        for(double& x:prob)std::cin>>x;
    }
    std::vector<std::pair<std::string,std::array<int,6>>> cases{
        {"triangular",{1,1,3,3,7,7}},
        {"old_star",{7,1,3,2,7,4}},
        {"old_best_deep",{3,1,7,2,7,7}},
        {"flat",{1,1,2,2,4,4}},
        {"overlap",{3,1,6,2,7,4}}
    };
    std::cout<<"name,access_rate,cost,span,iters,masks,colors\n"<<std::setprecision(12);
    double best=1e100;std::array<int,6> bp{};
    auto eval=[&](std::string name,std::array<int,6> op){
        Model model(op,colors);auto r=model.solve(prob);
        std::cout<<name<<','<<rho<<','<<r.cost<<','<<r.span<<','<<r.iters<<',';
        for(int x:op)std::cout<<x;std::cout<<',';for(int x:colors)std::cout<<x;std::cout<<'\n'<<std::flush;
        if(r.span<1e-7&&r.cost<best){best=r.cost;bp=op;}
    };
    for(auto& [name,op]:cases)eval(name,op);
    std::mt19937 rng(912031);
    for(int t=0;t<trials;++t){
        auto cand=bp;
        for(int j=0;j<1+(t%4==3);++j){int k=rng()%6,w=rng()%3;if(w==k/2)w=(w+1)%3;cand[k]^=1<<w;}
        eval("mutation"+std::to_string(t),cand);
    }
}
