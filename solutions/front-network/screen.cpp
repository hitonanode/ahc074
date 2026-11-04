#define main approximate_old_main
#include "approx.hpp"
#undef main
#include <functional>
#include <map>
#include <set>

struct Candidate { double cost; std::vector<int> op; };
static bool less_candidate(const Candidate& a,const Candidate& b) {
    return a.cost!=b.cost?a.cost<b.cost:a.op<b.op;
}
int main(int argc,char**argv) {
    if(argc<2)return 2;
    const long long budget=argc>2?std::stoll(argv[2]):2000000;
    const int train=argc>3?std::stoi(argv[3]):1024;
    Model m(argv[1],8);if(m.W!=3||m.K>10)return 3;
    const auto original=m.op;
    auto start=std::chrono::steady_clock::now();
    auto elapsed=[&]{return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    std::vector<std::vector<int>> masks(m.K),identity(m.K);
    std::vector<int> previous_equal(m.K,-1);
    long long combinations=1;
    for(int k=0;k<m.K;k++) {
        for(int mask=1;mask<=m.full;mask++)if(!(mask&~m.allowed[k]))masks[k].push_back(mask);
        combinations*=masks[k].size();
        identity[k]={m.color[k],m.allowed[k]};
        for(int b=0;b<=m.full;b++) {
            int count=0;for(auto e:m.events)count+=e.paper==k&&e.color==b;
            identity[k].push_back(count);
        }
        for(int j=0;j<k;j++)if(identity[k]==identity[j])previous_equal[k]=j;
    }
    auto staircase=[&](const std::vector<int>& op) {
        std::array<int,3> order{0,1,2};
        do {
            bool all=true;
            for(int k=0;k<m.K;k++) {
                int prefix=0;bool found=false;
                for(int j:order) {prefix|=1<<j;found|=(prefix&m.allowed[k])==op[k];}
                if(!found){all=false;break;}
            }
            if(all)return true;
        }while(std::next_permutation(order.begin(),order.end()));
        return false;
    };
    std::array<std::vector<Candidate>,2> ranked;
    double baseline=m.simulate(train,1000003);
    ranked[1].push_back({baseline,original});
    long long sampled=0,unique=0,valid=0,chain_count=0;
    std::set<std::vector<int>> seen;
    auto consider=[&] {
        sampled++;
        for(int k=0;k<m.K;k++)if(previous_equal[k]>=0&&m.op[k]<m.op[previous_equal[k]])return;
        if(combinations>budget&&!seen.insert(m.op).second)return;
        unique++;if(!m.update())return;valid++;
        bool chain=staircase(m.op);chain_count+=chain;
        double value=m.simulate(train,1000003);auto& rank=ranked[chain];
        if(rank.size()<64||value<rank.back().cost) {
            rank.push_back({value,m.op});std::sort(rank.begin(),rank.end(),less_candidate);
            if(rank.size()>64)rank.pop_back();
        }
        if(valid%10000==0)std::cerr<<"valid "<<valid<<" sampled "<<sampled<<" chain "<<chain_count<<" best "<<(ranked[0].empty()?1e6:ranked[0][0].cost)<<" seconds "<<elapsed()<<'\n';
    };
    if(combinations<=budget) {
        std::function<void(int)> enumerate=[&](int k) {
            if(k==m.K){consider();return;}
            for(int op:masks[k]) {m.op[k]=op;enumerate(k+1);}
        };
        enumerate(0);
    }else {
        std::mt19937_64 rng(563819333);
        for(long long it=0;it<budget;it++) {
            for(int k=0;k<m.K;k++)m.op[k]=masks[k][rng()%masks[k].size()];
            consider();
        }
    }
    std::cerr<<"screened "<<sampled<<" valid "<<valid<<" seconds "<<elapsed()<<'\n';
    m.width=32;m.op=original;m.update();double reference=m.simulate(16384,200000003);
    std::array<std::vector<Candidate>,2> heldout;
    for(int chain=0;chain<2;chain++)for(auto c:ranked[chain]) {
        m.op=c.op;m.update();double score=m.simulate(16384,200000003);
        heldout[chain].push_back({score,c.op});
    }
    for(auto& rank:heldout)std::sort(rank.begin(),rank.end(),less_candidate);
    m.width=64;m.op=original;m.update();double finalbase=m.simulate(262144,81923132);
    std::cout<<std::setprecision(12)<<"{\"combinations\":"<<combinations<<",\"sampled\":"<<sampled<<",\"unique\":"<<unique<<",\"valid\":"<<valid<<",\"chain_count\":"<<chain_count<<",\"baseline_train\":"<<baseline<<",\"baseline_validation\":"<<reference<<",\"baseline\":"<<finalbase<<",\"final\":[";
    int n=0;
    for(int chain=0;chain<2;chain++)for(int k=0;k<std::min(8,int(heldout[chain].size()));k++) {
        const auto& c=heldout[chain][k];m.op=c.op;m.update();double score=m.simulate(262144,81923132);
        std::cout<<(n++?",":"")<<"{\"chain\":"<<chain<<",\"validation\":"<<c.cost<<",\"value\":"<<score<<",\"difference\":"<<score-finalbase<<",\"opaque\":[";
        for(int j=0;j<m.K;j++)std::cout<<(j?",":"")<<m.op[j];
        std::cout<<"]}"<<std::flush;
    }
    std::cout<<"],\"seconds\":"<<elapsed()<<"}\n";
}
