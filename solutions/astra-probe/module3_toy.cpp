// Exact 3-window / 6-paper local-module MDP, with the same exposure relaxation
// as module_toy.cpp. Independent color requests plus occasional paper access.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <queue>
#include <string>
#include <vector>
using Order=std::array<int,6>;
std::vector<Order> orders;
struct Model{
    std::array<int,6>op;
    std::vector<uint8_t>dist;
    std::array<std::vector<int>,14>goals;
    Model(std::array<int,6>o,bool canonical):op(o),dist(720*720,255){
        constexpr std::array<int,6>black{0,7,1,6,2,5};
        std::vector<std::vector<int>>edges(720);
        for(int s=0;s<720;++s){
            int cov=0,visible=0,display=0;
            for(int k:orders[s]){int e=op[k]&~cov;if(e)visible|=1<<k;display|=black[k]&e;cov|=op[k];}
            bool term=true;if(canonical)for(int i=0;i<6;++i)term&=orders[s][i]/2==i/2;
            if(term){goals[display].push_back(s);for(int k=0;k<6;++k)if(visible>>k&1)goals[8+k].push_back(s);}
            for(int pos=0;pos<6;++pos)if(visible>>orders[s][pos]&1)for(int dest=0;dest<6;++dest)if(dest!=pos){
                std::vector<int>v(orders[s].begin(),orders[s].end());int k=v[pos];v.erase(v.begin()+pos);v.insert(v.begin()+dest,k);
                Order q{};std::copy(v.begin(),v.end(),q.begin());edges[s].push_back(std::lower_bound(orders.begin(),orders.end(),q)-orders.begin());
            }
        }
        for(int source=0;source<720;++source){
            uint8_t*d=dist.data()+source*720;d[source]=0;int queue[720],b=0,e=0;queue[e++]=source;
            while(b<e){int x=queue[b++];for(int y:edges[x])if(d[y]==255){d[y]=d[x]+1;queue[e++]=y;}}
        }
    }
    std::pair<double,double>solve(double rho){
        for(auto&g:goals)if(g.empty())return {99,99};
        std::array<double,720>v{},next{};double mean=0,span=0;
        for(int it=0;it<2000;++it){
            double mn=1e99,mx=-1e99;
            for(int s=0;s<720;++s){
                next[s]=0;const uint8_t*d=dist.data()+s*720;
                for(int event=0;event<14;++event){double best=1e99;for(int t:goals[event])best=std::min(best,d[t]+v[t]);next[s]+=best*(event<8?(1-rho)/8:rho/6);}
                mn=std::min(mn,next[s]-v[s]);mx=std::max(mx,next[s]-v[s]);
            }
            mean=(mn+mx)/2;span=mx-mn;double offset=next[0];for(int s=0;s<720;++s)v[s]=next[s]-offset;
            if(span<1e-10)break;
        }
        return {mean,span};
    }
};
int main(){
    Order p{0,1,2,3,4,5};do orders.push_back(p);while(std::next_permutation(p.begin(),p.end()));
    std::cout<<"variant,access_probability,mean,span,opacity\n";
    struct Case{std::string name;std::array<int,6>op;bool canonical;};
    for(auto c:std::vector<Case>{{"triangular_canonical",{1,1,3,3,7,7},true},{"triangular_free",{1,1,3,3,7,7},false},{"star",{7,1,1,2,2,4},false},{"star_patches",{7,1,3,2,7,4},false}}){
        Model m(c.op,c.canonical);
        for(double rho:{0.0,.02,.05,.1,.2,.4}){auto [mean,span]=m.solve(rho);std::cout<<c.name<<','<<rho<<','<<std::setprecision(12)<<mean<<','<<span<<',';for(int op:c.op)std::cout<<op;std::cout<<'\n'<<std::flush;}
    }
    return 0;
}
