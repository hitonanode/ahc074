#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <set>
#include <string>
#include <thread>
#include <vector>

using U=std::uint64_t;
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
const auto start_time=std::chrono::steady_clock::now();
double elapsed(){return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start_time).count();}

U closure(U r,int n){
    for(int k=0;k<n;++k)r|=((r>>k)&0x0101010101010101ULL)*((r>>(8*k))&255);
    return r;
}

// In/out degree is invariant under relabeling. Enumerate only equal-degree
// cells; vertices with identical predecessors and successors are interchangeable.
U canonical(U r,int n){
    unsigned out[8]{},in[8]{};int key[8]{},order[8]{};
    for(int a=0;a<n;++a){
        out[a]=(r>>(8*a))&255;
        for(int b=0;b<n;++b)if(out[a]>>b&1)in[b]|=1u<<a;
    }
    for(int a=0;a<n;++a)key[a]=std::popcount(out[a])*9+std::popcount(in[a]);
    U best=~U(0);
    auto dfs=[&](auto&&self,int depth,unsigned used)->void{
        if(depth==n){
            U x=0;
            for(int i=0;i<n;++i)for(int j=0;j<n;++j)if(out[order[i]]>>order[j]&1)x|=U(1)<<(8*i+j);
            best=std::min(best,x);return;
        }
        int minimum=1000;
        for(int a=0;a<n;++a)if(!(used>>a&1))minimum=std::min(minimum,key[a]);
        unsigned tried=0;
        for(int a=0;a<n;++a)if(!(used>>a&1)&&key[a]==minimum){
            bool twin=false;
            for(int b=0;b<a;++b)if(tried>>b&1)twin|=out[a]==out[b]&&in[a]==in[b];
            if(twin)continue;
            tried|=1u<<a;order[depth]=a;self(self,depth+1,used|(1u<<a));
        }
    };
    dfs(dfs,0,0);return best;
}

struct Graph{
    int n,S;
    std::vector<std::array<unsigned char,8>> perms;
    std::vector<U> wrong;
    std::vector<int> begin,pred;
    static int rank(const std::array<unsigned char,8>& p,int n){
        int r=0;unsigned used=0;
        for(int i=0;i<n;++i){r=r*(n-i)+std::popcount(((1u<<p[i])-1)&~used);used|=1u<<p[i];}
        return r;
    }
    explicit Graph(int size):n(size){
        std::array<unsigned char,8> p{};std::iota(p.begin(),p.begin()+n,0);
        do{perms.push_back(p);}while(std::next_permutation(p.begin(),p.begin()+n));
        S=perms.size();wrong.resize(S);begin.resize(S+1);
        std::vector<std::pair<int,int>> links;links.reserve((size_t)S*(n-1)*(n-1));
        for(int s=0;s<S;++s){
            const auto& o=perms[s];
            for(int i=0;i<n;++i)for(int j=0;j<i;++j)wrong[s]|=U(1)<<(8*o[i]+o[j]);
            // In the complete comparison graph, exactly the bottom sheet is
            // invisible. The moved sheet may subsequently go below that sheet.
            for(int i=0;i<n-1;++i)for(int depth=0;depth<n;++depth)if(i!=depth){
                auto next=o;int x=o[i],at=0;
                for(int j=0;j<n;++j)if(j!=i)next[at++]=o[j];
                for(int j=n-1;j>depth;--j)next[j]=next[j-1];next[depth]=x;
                int t=rank(next,n);links.emplace_back(t,s);++begin[t+1];
            }
        }
        std::partial_sum(begin.begin(),begin.end(),begin.begin());
        pred.resize(links.size());auto cursor=begin;
        for(auto[t,s]:links)pred[cursor[t]++]=s;
    }
    int sum(U relation)const{
        std::vector<unsigned char> d(S,255);std::vector<int> queue(S);
        int head=0,tail=0;
        for(int s=0;s<S;++s)if(!(relation&wrong[s])){d[s]=0;queue[tail++]=s;}
        assert(tail);
        while(head<tail){
            int x=queue[head++],nd=d[x]+1;
            for(int j=begin[x];j<begin[x+1];++j){int y=pred[j];if(d[y]==255){d[y]=nd;queue[tail++]=y;}}
        }
        assert(tail==S);
        return std::accumulate(d.begin(),d.end(),0);
    }
};

int main(int argc,char**argv){
    if(argc!=3)return 2;
    std::ifstream input(argv[1]);
    int n;input>>n;
    std::vector<U> old;std::vector<int> expected;
    U relation;int sum;
    while(input>>std::hex>>relation>>std::dec>>sum){old.push_back(relation);expected.push_back(sum);}
    Graph previous(n);
    // Verify all supplied lower-order costs against the independent legal graph.
    for(int i=0;i<int(old.size());++i){
        const int actual=previous.sum(old[i]);
        if(actual!=expected[i]){std::cerr<<"mismatch "<<i<<' '<<actual<<' '<<expected[i]<<'\n';return 3;}
    }
    std::cerr<<"verified = "<<old.size()<<"\nverified_sec = "<<elapsed()<<'\n';
    std::set<U> unique;
    for(U r:old)for(unsigned mask=0;mask<(1u<<n);++mask){
        U x=r;
        // Add a maximal element below any predecessor set, then take closure.
        // Every (n+1)-poset can be obtained by deleting one maximal element.
        for(int a=0;a<n;++a)if(mask>>a&1)x|=U(1)<<(8*a+n);
        unique.insert(canonical(closure(x,n+1),n+1));
    }
    std::vector<U> reps(unique.begin(),unique.end());std::vector<int> costs(reps.size());
    std::cerr<<"classes = "<<reps.size()<<"\nclasses_sec = "<<elapsed()<<'\n';
    Graph graph(n+1);std::atomic<int> next{0},completed{0};
    std::vector<std::thread> workers;
    for(int worker=0;worker<4;++worker)workers.emplace_back([&]{
        for(;;){int i=next.fetch_add(1);if(i>=int(reps.size()))break;costs[i]=graph.sum(reps[i]);
            int done=completed.fetch_add(1)+1;if(done%2000==0)std::cerr<<"done "<<done<<" elapsed "<<elapsed()<<'\n';}
    });
    for(auto& thread:workers)thread.join();
    std::ofstream output(argv[2]);output<<n+1<<'\n';
    for(int i=0;i<int(reps.size());++i)output<<std::hex<<reps[i]<<std::dec<<' '<<costs[i]<<'\n';
    std::cerr<<"end_sec = "<<elapsed()<<'\n';
}
