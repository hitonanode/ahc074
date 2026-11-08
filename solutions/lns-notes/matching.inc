// ==== Window assignment: regional matching ====

// Edmonds cardinality augmentation, with a greedy matching as a starting point.
struct LnsMatching {
    int n=256;
    std::array<std::vector<int>,256> g;
    std::array<int,256> mate,p,base,q;
    std::array<bool,256> used,blossom;
    LnsMatching(){mate.fill(-1);}
    int lca(int a,int b){
        std::array<bool,256> seen{};
        for(;;){a=base[a];seen[a]=true;if(mate[a]<0)break;a=p[mate[a]];}
        for(;;){b=base[b];if(seen[b])return b;b=p[mate[b]];}
    }
    void mark(int v,int b,int child){
        while(base[v]!=b){blossom[base[v]]=blossom[base[mate[v]]]=true;p[v]=child;child=mate[v];v=p[mate[v]];}
    }
    bool augment(int root){
        used.fill(false);p.fill(-1);std::iota(base.begin(),base.end(),0);
        int h=0,t=0;q[t++]=root;used[root]=true;
        while(h<t){int v=q[h++];for(int u:g[v]){
            if(base[v]==base[u]||mate[v]==u)continue;
            if(u==root||(mate[u]>=0&&p[mate[u]]>=0)){
                int b=lca(v,u);blossom.fill(false);mark(v,b,u);mark(u,b,v);
                for(int i=0;i<n;++i)if(blossom[base[i]]){base[i]=b;if(!used[i]){used[i]=true;q[t++]=i;}}
            }else if(p[u]<0){
                p[u]=v;
                if(mate[u]<0){for(int x=u;x>=0;){int y=p[x],z=y<0?-1:mate[y];mate[x]=y;if(y>=0)mate[y]=x;x=z;}return true;}
                u=mate[u];used[u]=true;q[t++]=u;
            }
        }}return false;
    }
};
#ifdef LOCAL_BENCH
// Exact subset DP checks the augmenting-path implementation on small random
// graphs, including odd cycles and arbitrary valid greedy starting matchings.
void lns_verify_matching() {
    XorShift rng{0x3a6c8d1e51ULL};
    for(int trial=0;trial<512;++trial){
        LnsMatching m;m.n=2+rng.below(11);std::vector<int> mask(m.n);
        for(int a=0;a<m.n;++a)for(int b=a+1;b<m.n;++b)if(rng.below(10)<2+trial%7){
            m.g[a].push_back(b);m.g[b].push_back(a);mask[a]|=1<<b;mask[b]|=1<<a;
            if(m.mate[a]<0&&m.mate[b]<0&&(rng.next()&1)){m.mate[a]=b;m.mate[b]=a;}
        }
        for(int a=0;a<m.n;++a)if(m.mate[a]<0)m.augment(a);
        int count=0;for(int a=0;a<m.n;++a)count+=m.mate[a]>a;
        std::vector<int> memo(1<<m.n,-1);memo[0]=0;
        std::function<int(int)> solve=[&](int bits){
            int& best=memo[bits];if(best>=0)return best;
            int a=__builtin_ctz(unsigned(bits)),rest=bits^(1<<a);best=solve(rest);
            for(unsigned b=unsigned(rest&mask[a]);b;b&=b-1)best=std::max(best,1+solve(rest^(b&-b)));
            return best;
        };
        assert(count==solve((1<<m.n)-1));
    }
    std::cerr<<"lns_matching_verified = 512\n";
}
#endif
