// Exact feasibility of an otherwise incompatible pair, using one existing helper.
// Costs are explicitly a frozen-state proxy, not an attainable contest-score claim.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <string>
#include <vector>

using U64=std::uint64_t;
struct Paper { U64 opq=0,black=0; };
struct Plan { int paper=-1,g=99,h=0,prefix=-1; U64 gmask=0; double proxy=1e9; };

int main(int argc,char** argv) {
    if(argc<3) { std::cerr<<"Usage: helper_punch_g_probe INPUT SAVED_OUTPUT [single-helpers]\n"; return 1; }
    bool single_helpers=false;
    for(int i=3;i<argc;i++){
        if(std::string(argv[i])!="single-helpers")return 1;
        single_helpers=true;
    }
    std::ifstream in(argv[1]),out(argv[2]);
    int n,k,p,r;in>>n>>k>>p>>r;
    if(!in||n!=64||k!=192||p!=256)return 2;
    std::vector<U64>A(p);std::vector<int>requests(r);
    for(auto& a:A){std::string s;in>>s;for(int j=0;j<n;j++)if(s[j]=='1')a|=U64(1)<<j;}
    for(auto& q:requests)in>>q;
    std::vector<Paper>paper(k);
    for(auto& a:paper){std::string s;out>>s;if(s.size()!=64)return 3;
        for(int j=0;j<n;j++){if(s[j]!='.')a.opq|=U64(1)<<j;if(s[j]=='1')a.black|=U64(1)<<j;}}
    constexpr int M=6,S=720;
    U64 gm=0;for(int x=0;x<M;x++)gm|=paper[x].opq;
    U64 known=gm;std::vector<int>handles,col(k,-1);
    for(int x=M;x<k;x++){
        U64 fresh=paper[x].opq&~known;
        while(fresh){int j=__builtin_ctzll(fresh);fresh&=fresh-1;handles.push_back(j);}
        known|=paper[x].opq;
        for(int c=0;c<int(handles.size());c++)if(paper[x].opq>>handles[c]&1)col[x]=c;
    }
    const int H=handles.size();
    if(H+__builtin_popcountll(gm)!=64)return 4;
    std::vector<U64>prefixH(H);U64 mask=0;
    for(int c=0;c<H;c++){mask|=U64(1)<<handles[c];prefixH[c]=mask;}
    std::array<int,M>perm;std::iota(perm.begin(),perm.end(),0);
    std::vector<std::array<int,M>>perms;
    do{perms.push_back(perm);}while(std::next_permutation(perm.begin(),perm.end()));
    std::vector<U64>generic(S);
    for(int s=0;s<S;s++){
        U64 shown=0,covered=0;
        for(int t=0;t<M;t++){int x=perms[s][t];shown|=paper[x].black&~covered;covered|=paper[x].opq;}
        generic[s]=shown;
    }
    std::vector<int>ded(p,-1),uses(k,0);
    for(int u=0;u<p;u++)for(int x=M;x<k;x++){
        if((A[u]^paper[x].black)&paper[x].opq)continue;
        U64 holes=gm&~paper[x].opq;bool possible=false;
        for(U64 g:generic)if(!((g^A[u])&holes)){possible=true;break;}
        if(possible){if(ded[u]>=0){std::cerr<<"nonunique primary\n";return 5;}ded[u]=x;uses[x]++;}
    }
    std::vector<double>meanrank(k,0),meanexpose(k,0);
    std::vector<int>order(k);std::iota(order.begin(),order.end(),0);
    int seen=0;
    for(int q=0;q<r;q++){
        std::vector<int>rank(H,0);std::array<int,64>blocked{};
        for(int x:order){
            if(col[x]>=0)meanrank[x]+=rank[col[x]]++;
            int ex=k;U64 bits=paper[x].opq;
            while(bits){int j=__builtin_ctzll(bits);bits&=bits-1;ex=std::min(ex,blocked[j]);blocked[j]++;}
            meanexpose[x]+=ex;
        }
        int count;out>>count;if(!out)break;
        for(int t=0;t<count;t++){int x,d;out>>x>>d;auto it=std::find(order.begin(),order.end(),x);order.erase(it);order.insert(order.begin()+d,x);}
        seen++;
    }
    for(int x=0;x<k;x++)meanrank[x]/=seen,meanexpose[x]/=seen;
    constexpr U64 ROWS=0x010101010101ULL,DIAG=0x201008040201ULL;
    auto closure=[](U64 rel){
        for(int j=0;j<6;j++)rel|=((rel>>j)&ROWS)*((rel>>(8*j))&63);
        return rel;
    };
    std::array<std::array<U64,64>,256> relation{};
    for(int j=0;j<64;j++)if(gm>>j&1){
        int zero=-1,one=-1;
        for(int x=0;x<M;x++)if(paper[x].opq>>j&1){if(paper[x].black>>j&1)one=x;else zero=x;}
        if(zero<0||one<0)return 6;
        for(int u=0;u<p;u++){
            int a=(A[u]>>j&1)?one:zero,b=(A[u]>>j&1)?zero:one;
            relation[u][j]=U64(1)<<(8*a+b);
        }
    }
    auto rel_for=[&](int u,U64 holes){U64 rel=0;while(holes){int j=__builtin_ctzll(holes);holes&=holes-1;rel|=relation[u][j];}return rel;};
    std::array<U64,64> prefix_opq{},prefix_rel{};
    for(int s=0;s<64;s++)for(int a=0;a<6;a++)if(s>>a&1){
        prefix_opq[s]|=paper[a].opq;
        for(int b=0;b<6;b++)if(!(s>>b&1))prefix_rel[s]|=U64(1)<<(8*a+b);
    }
    std::vector<std::vector<int>>owners(k);
    std::vector<U64>owner_closure(p);
    for(int u=0;u<p;u++){
        owners[ded[u]].push_back(u);
        owner_closure[u]=closure(rel_for(u,gm&~paper[ded[u]].opq));
    }
    // These 64 choices describe every possible position of the helper among the six generic
    // sheets. Relative orders within the prefix and suffix are determined by the DAG conditions.
    auto plans_for=[&](int u,int v){
        std::vector<Plan> plans;
        const U64 gh=(A[u]^A[v])&gm;
        for(int x=M;x<k;x++){
            if(x==ded[u]||x==ded[v]||(single_helpers&&uses[x]!=1))continue;
            Plan best;best.paper=x;
            for(int s=0;s<64;s++){
                const U64 bad=(paper[x].black^A[u])&paper[x].opq&gh&~prefix_opq[s];
                const int ng=__builtin_popcountll(bad);
                if(ng>=best.g)continue;
                const U64 need=gh&(prefix_opq[s]|~paper[x].opq|bad);
                if(closure(prefix_rel[s]|rel_for(u,need))&DIAG)continue;
                // A changed helper must still serve every original owner using only the core.
                bool valid=true;
                for(int w:owners[x])if(closure(owner_closure[w]|rel_for(w,bad))&DIAG){valid=false;break;}
                if(!valid)continue;
                best.g=ng;best.gmask=bad;best.prefix=s;
                if(ng==0)break;
            }
            if(best.g<99)plans.push_back(best);
        }
        return plans;
    };
    int close=0,incompatible=0,rescued=0,assignments=0,shallow_rescued=0;
    std::cout<<"u,v,c,hdiff,gdiff,helpers_u,helpers_v,helper_u,helper_v,g_punch_u,g_punch_v,h_punch_u,h_punch_v,rank_u,rank_v,prefix_u,prefix_v,g_mask_u,g_mask_v,shallow_both\n";
    for(int u=0;u<p;u++)if(uses[ded[u]]==1)for(int v=u+1;v<p;v++)if(uses[ded[v]]==1){
        const U64 diff=A[u]^A[v];if(__builtin_popcountll(diff)>26)continue;close++;
        if(!(closure(rel_for(u,diff&gm))&DIAG))continue;
        incompatible++;
        auto pu=plans_for(u,v),pv=plans_for(v,u);
        bool any=false,shallow_any=false;
        for(int c=0;c<H;c++)if(!(diff>>handles[c]&1)){
            const U64 hh=~gm&(~prefixH[c]|diff);
            auto usable=[&](int target,const std::vector<Plan>&source){
                std::vector<Plan>ans;
                for(auto a:source){
                    int x=a.paper;if(col[x]==c)continue;
                    const U64 bad=(paper[x].black^A[target])&paper[x].opq&hh;
                    if(bad>>handles[col[x]]&1)continue;
                    a.h=__builtin_popcountll(bad);
                    // This ordering is only to pick one concise witness. It is not a score model:
                    // each new generic hole is charged 1, each handle hole 0.4, plus recorded rank.
                    a.proxy=meanrank[x]+uses[x]*(a.g+0.4*a.h);
                    ans.push_back(a);
                }
                return ans;
            };
            auto a=usable(u,pu),b=usable(v,pv);
            if(a.empty()||b.empty())continue;
            Plan ba,bb;double best=1e9;bool shallow=false;
            for(auto x:a)for(auto y:b)if(x.paper!=y.paper){
                shallow|=meanrank[x.paper]<=1.0&&meanrank[y.paper]<=1.0;
                if(x.proxy+y.proxy<best){best=x.proxy+y.proxy;ba=x;bb=y;}
            }
            if(ba.paper<0)continue;
            any=true;shallow_any|=shallow;assignments++;
            std::cout<<u<<','<<v<<','<<c<<','<<__builtin_popcountll(diff&~gm)<<','<<__builtin_popcountll(diff&gm)<<','<<a.size()<<','<<b.size()<<','
                <<ba.paper<<','<<bb.paper<<','<<ba.g<<','<<bb.g<<','<<ba.h<<','<<bb.h<<','<<meanrank[ba.paper]<<','<<meanrank[bb.paper]<<','
                <<ba.prefix<<','<<bb.prefix<<','<<ba.gmask<<','<<bb.gmask<<','<<shallow<<'\n';
        }
        rescued+=any;shallow_rescued+=shallow_any;
    }
    std::cerr<<"close_single_pairs = "<<close<<"\nincompatible_single_pairs = "<<incompatible<<"\nrescued_pairs = "<<rescued
        <<"\nrescued_column_assignments = "<<assignments<<"\nshallow_both_pairs = "<<shallow_rescued<<"\ntrace_states = "<<seen<<'\n';
}
