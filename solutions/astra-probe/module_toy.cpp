// Exact 2-window, 4-paper average-cost toy. A request either sets both local
// colors or exposes a specified paper. Exposure is a relaxation of extraction
// and reinsertion: this toy must not be interpreted as a full-solver score.
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <queue>
#include <vector>
using Order=std::array<int,4>;
std::vector<Order> orders;
struct Result{double mean,span;std::array<int,4> opacity;int canonical;};
Result solve(std::array<int,4>op,double rho,bool canonical){
    // Full local colors of four primary records, top-to-bottom by old column:
    // column 0: 00,11; column 1: 01,10. Each has both handle colors.
    constexpr std::array<int,4>black={0,3,1,2};
    const int n=24;int display[24]{},visible[24]{};bool term[24]{};
    std::array<std::array<int,24>,24>d{};
    for(int s=0;s<n;++s){
        d[s].fill(99);d[s][s]=0;int covered=0;
        for(int k:orders[s]){int e=op[k]&~covered;if(e)visible[s]|=1<<k;display[s]|=black[k]&e;covered|=op[k];}
        term[s]=!canonical||(orders[s][0]<2&&orders[s][1]<2&&orders[s][2]>=2&&orders[s][3]>=2);
        for(int pos=0;pos<4;++pos)if(visible[s]>>orders[s][pos]&1)for(int dest=0;dest<4;++dest)if(dest!=pos){
            std::vector<int>v(orders[s].begin(),orders[s].end());int k=v[pos];v.erase(v.begin()+pos);v.insert(v.begin()+dest,k);
            Order q{};std::copy(v.begin(),v.end(),q.begin());int t=std::lower_bound(orders.begin(),orders.end(),q)-orders.begin();d[s][t]=1;
        }
    }
    for(int k=0;k<n;++k)for(int s=0;s<n;++s)for(int t=0;t<n;++t)d[s][t]=std::min(d[s][t],d[s][k]+d[k][t]);
    std::array<std::vector<int>,8>goals;
    for(int s=0;s<n;++s)if(term[s]){goals[display[s]].push_back(s);for(int k=0;k<4;++k)if(visible[s]>>k&1)goals[4+k].push_back(s);}
    for(auto&g:goals)if(g.empty())return {99,99,op,canonical};
    std::array<double,24>v{},next{};double mean=0,span=0;
    for(int it=0;it<10000;++it){
        double mn=1e99,mx=-1e99;
        for(int s=0;s<n;++s){
            next[s]=0;
            for(int event=0;event<8;++event){double best=1e99;for(int t:goals[event])best=std::min(best,d[s][t]+v[t]);next[s]+=best*(event<4?1-rho:rho)/4;}
            mn=std::min(mn,next[s]-v[s]);mx=std::max(mx,next[s]-v[s]);
        }
        mean=(mn+mx)/2;span=mx-mn;double offset=next[0];for(int s=0;s<n;++s)v[s]=next[s]-offset;
        if(span<1e-11)break;
    }
    return {mean,span,op,canonical};
}
int main(){
    Order p{0,1,2,3};do orders.push_back(p);while(std::next_permutation(p.begin(),p.end()));
    std::cout<<"access_probability,variant,mean,span,opacity0,opacity1,opacity2,opacity3\n";
    for(double rho:{0.0,.02,.05,.1,.2,.4,.6}){
        auto output=[&](const char*name,Result r){std::cout<<rho<<','<<name<<','<<std::setprecision(12)<<r.mean<<','<<r.span;for(int x:r.opacity)std::cout<<','<<x;std::cout<<'\n';};
        auto original=solve({1,1,3,3},rho,true),free=solve({1,1,3,3},rho,false),best=free;
        for(int code=0;code<81;++code){int z=code;std::array<int,4>op{};for(int&i:op){i=z%3+1;z/=3;}auto r=solve(op,rho,false);if(r.mean<best.mean)best=r;}
        output("triangular_canonical",original);output("triangular_free",free);output("synthesized",best);
    }
}
