// Permanent complementary sparse overlay pair added to six comparator sheets.
// Both overlays may occur ANYWHERE in the generic layer. This is different
// from replacing windows by an always-on independent register. Exact legal
// graph on 8! states; cost averaged over fixed sampled initial states.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
#include <array>
#include <limits>

struct Overlay {
    using Order=std::array<uint8_t,8>;
    std::vector<Order> perms;
    std::vector<std::vector<int>> next;
    std::vector<u64> display;
    std::vector<std::vector<uint8_t>> distance;
    std::array<int,256>pc{};
    int M=8;
    int index(const Order&o){int r=0,mask=(1<<M)-1;for(int i=0;i<M;++i){r=r*(M-i)+pc[mask&((1<<o[i])-1)];mask^=1<<o[i];}return r;}
    Overlay(const Data&d,u64 mask,u64 pattern,int samples,const std::string&mode){
        for(int i=0;i<256;++i)pc[i]=std::popcount(unsigned(i));
        std::array<u64,8>op{},bl{};for(int k=0;k<6;++k){op[k]=d.comp.opq[k];bl[k]=d.comp.black[k];}
        op[6]=op[7]=mask;bl[6]=pattern&mask;bl[7]=mask^bl[6];
        if(mode=="clone"||mode=="opposite"){
            M=7;int root=int(mask);assert(root<6);op[6]=op[root];bl[6]=mode=="clone"?bl[root]:op[root]^bl[root];op[7]=bl[7]=0;
        }else if(mode=="fused"){
            M=7;int a=int(mask),b=int(pattern);assert(a<6&&b<6&&a!=b);op[6]=op[a]|op[b];bl[6]=bl[a]|(bl[b]&~op[a]);op[7]=bl[7]=0;
        }
        Order o{0,1,2,3,4,5,6,7};do perms.push_back(o);while(std::next_permutation(o.begin(),o.begin()+M));
        const int n=perms.size();next.resize(n);display.resize(n);
        for(int s=0;s<n;++s){
            u64 cov=0;unsigned visible=0;
            for(int k:perms[s]){u64 e=op[k]&~cov;if(e)visible|=1<<k;display[s]|=bl[k]&e;cov|=op[k];}
            for(int pos=0;pos<M;++pos)if(visible>>perms[s][pos]&1)for(int dest=0;dest<M;++dest)if(dest!=pos){
                Order q=perms[s];int k=q[pos];
                if(pos<dest)for(int i=pos;i<dest;++i)q[i]=q[i+1];
                else for(int i=pos;i>dest;--i)q[i]=q[i-1];
                q[dest]=k;next[s].push_back(index(q));
            }
            std::sort(next[s].begin(),next[s].end());next[s].erase(std::unique(next[s].begin(),next[s].end()),next[s].end());
        }
        std::mt19937 rng(301131);distance.assign(samples,std::vector<uint8_t>(n,255));std::vector<int>queue(n);
        for(int z=0;z<samples;++z){
            auto&ds=distance[z];int source=rng()%n,b=0,e=0;ds[source]=0;queue[e++]=source;
            while(b<e){int s=queue[b++];for(int t:next[s])if(ds[t]==255){ds[t]=ds[s]+1;queue[e++]=t;}}
            assert(e==n);
        }
    }
    std::array<double,2>cost(u64 a,u64 b){
        u64 holes=(a^b)&low_bits(36);std::array<std::vector<int>,2>goals;
        for(int s=0;s<(int)perms.size();++s){if(!((display[s]^a)&holes))goals[0].push_back(s);if(!((display[s]^b)&holes))goals[1].push_back(s);}
        std::array<double,2>cost{};
        for(int side=0;side<2;++side){
            if(goals[side].empty()){cost[side]=-1;continue;}
            for(auto&ds:distance){int mn=255;for(int g:goals[side])if((mn=std::min(mn,int(ds[g])))==0)break;cost[side]+=mn/double(distance.size());}
        }
        return cost;
    }
};
int main(int argc,char**argv){
    int seed=argc>1?std::stoi(argv[1]):0,samples=argc>4?std::stoi(argv[4]):128;
    u64 mask=argc>2?std::stoull(argv[2]):0,pattern=argc>3?std::stoull(argv[3]):0;
    std::string mode=argc>5?argv[5]:"overlay";
    Data d(seed);
    if(!mask&&mode=="overlay"){
        for(int step=0;step<2;++step){double best=1e99;u64 chosen=0;for(int j=0;j<36;++j)if(!(mask>>j&1)&&d.valid_escape(mask|(1ULL<<j))){double val=d.greedy(mask|(1ULL<<j));if(val<best){best=val;chosen=mask|(1ULL<<j);}}mask=chosen;}
    }
    Overlay overlay(d,mask,pattern,samples,mode);
    std::array<std::array<double,256>,256>cost{};for(auto&row:cost)row.fill(-1);
    int oldpairs=0,newpairs=0,oldclose=0,newclose=0;
    for(int u=0;u<256;++u)for(int v=u+1;v<256;++v){
        double old=d.cost(u,v,0);int fd=std::popcount(d.a[u]^d.a[v]);oldpairs+=old>=0;oldclose+=old>=0&&fd<=26;
        if(fd>26&&old<0)continue;
        auto c=overlay.cost(d.a[u],d.a[v]);
        if(c[0]>=0&&c[1]>=0){cost[u][v]=cost[v][u]=(c[0]+c[1])/2;newpairs++;newclose+=fd<=26;}
        else assert(old<0);
    }
    std::cout<<"seed,kind,mask,pattern,samples,compatible,compatible_close,model,retrieval,handles,decoder,novel_selected\n";
    for(int variant=0;variant<2;++variant){
        Design des(d.a,variant?overlay.M:6,36);
        auto index=[&](u64 a){return int(std::find(d.a.begin(),d.a.end(),a)-d.a.begin());};
        auto cc=[&](u64 a,u64 b){return variant?cost[index(a)][index(b)]:d.cost(index(a),index(b),0);};
        if(!des.initialize([&](u64 a,u64 b){return cc(a,b)>=0;},cc,[]{return false;}))return 2;
        des.anneal(1e9,4000000);double ret=0,h=0,g=0;int novel=0;
        for(int c=0;c<28;++c){ret+=des.colcost(c);h+=des.hcost(c);}
        for(auto x:des.unit)if(x.b>=0){g+=des.gc(x);novel+=d.cost(x.a,x.b,0)<0;}
        std::cout<<seed<<','<<(variant?mode:"base")<<','<<mask<<','<<pattern<<','<<samples<<','<<(variant?newpairs:oldpairs)<<','<<(variant?newclose:oldclose)<<','<<std::setprecision(10)<<des.cur/256<<','<<ret/256<<','<<h/256<<','<<g/256<<','<<novel<<'\n'<<std::flush;
    }
}
