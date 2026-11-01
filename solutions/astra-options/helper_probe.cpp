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
struct Best { int helper=-1, goals=0, depth=-1, total=0, punched=0, shallow=0; double generic=1e9, rank=0, cost=1e9; };

int main(int argc,char** argv) {
    if(argc<3) { std::cerr<<"Usage: helper_probe INPUT SAVED_OUTPUT [all-columns] [punch|punch-single]\n"; return 1; }
    bool allcols=false,punch=false,single_helpers=false;
    for(int i=3;i<argc;i++){std::string flag=argv[i];allcols|=flag=="all-columns";punch|=flag=="punch"||flag=="punch-single";single_helpers|=flag=="punch-single";}
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
    auto id=[&](const std::array<int,M>&q){return int(std::lower_bound(perms.begin(),perms.end(),q)-perms.begin());};
    std::vector<std::vector<int>>reverse(S);
    for(int s=0;s<S;s++)for(int at=0;at<M-1;at++)for(int to=0;to<M;to++)if(at!=to){
        auto v=perms[s];int x=v[at];
        if(at<to)std::rotate(v.begin()+at,v.begin()+at+1,v.begin()+to+1);
        else std::rotate(v.begin()+to,v.begin()+at,v.begin()+at+1);
        (void)x;reverse[id(v)].push_back(s);
    }
    std::vector<U64>generic(S),catalog(k*S*7);
    for(int s=0;s<S;s++){
        U64 shown=0,covered=0;std::array<U64,7>pre{};
        for(int t=0;t<M;t++){int x=perms[s][t];shown|=paper[x].black&~covered;covered|=paper[x].opq;pre[t+1]=covered;}
        generic[s]=shown;
        for(int x=M;x<k;x++)for(int t=0;t<=M;t++)
            catalog[(x*S+s)*7+t]=(shown&(pre[t]|~paper[x].opq))|(paper[x].black&gm&~pre[t]);
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
    // Generic feasibility depends on the pair and helper, not its proposed handle column.
    struct GenericInfo { int goals=-1,depth=-1; double mean=0; };
    std::array<std::array<GenericInfo,192>,2> cache{};
    int cache_u=-1,cache_v=-1;
    auto evaluate=[&](int u,int v,int c){
        if(cache_u!=std::min(u,v)||cache_v!=std::max(u,v)){
            cache_u=std::min(u,v);cache_v=std::max(u,v);
            for(auto& row:cache)for(auto& info:row)info=GenericInfo{};
        }
        Best best;const U64 diff=A[u]^A[v],gh=diff&gm,hh=~gm&(~prefixH[c]|diff);
        for(int x=M;x<k;x++){
            if(x==ded[u]||x==ded[v]||col[x]==c)continue;
            if(single_helpers&&uses[x]!=1)continue;
            const U64 bad=(paper[x].black^A[u])&paper[x].opq&hh;
            if(bad&&(!punch||(bad>>handles[col[x]]&1)))continue;
            const int npunch=__builtin_popcountll(bad);
            auto& info=cache[u==cache_u?0:1][x];
            if(info.goals<0){
                std::array<int,S>distance;distance.fill(-1);
                std::array<int,S>queue{};int tail=0,mindep=7;
                for(int s=0;s<S;s++){
                    int td=-1;
                    for(int t=0;t<M;t++)if(!((catalog[(x*S+s)*7+t]^A[u])&gh)){td=t;break;}
                    if(td>=0){distance[s]=0;queue[tail++]=s;mindep=std::min(mindep,td);}
                }
                info.goals=tail;info.depth=mindep;
                if(tail){
                    for(int at=0;at<tail;at++)for(int z:reverse[queue[at]])if(distance[z]<0){distance[z]=distance[queue[at]]+1;queue[tail++]=z;}
                    info.mean=std::accumulate(distance.begin(),distance.end(),0.0)/S;
                }
            }
            if(!info.goals)continue;
            best.total++;
            best.shallow+=meanrank[x]<=1.0;
            const int ng=info.goals,mindep=info.depth;
            double avg=info.mean;
            const double cost=avg+meanrank[x]+1.8+0.4*uses[x]*npunch;
            if(cost<best.cost){best.helper=x;best.goals=ng;best.depth=mindep;best.generic=avg;best.rank=meanrank[x];best.cost=cost;best.punched=npunch;}
        }
        return best;
    };
    int close=0,incompatible=0,rescued=0,assignments=0;
    std::cout<<"u,v,c,du,dv,hdiff,gdiff,uholes,helpers_u,helpers_v,best_u,best_v,generic_u,generic_v,rank_u,rank_v,proxy_u,proxy_v,insert_u,insert_v,punch_u,punch_v,shallow_u,shallow_v\n";
    for(int u=0;u<p;u++)if(ded[u]>=0&&uses[ded[u]]==1)for(int v=u+1;v<p;v++)if(ded[v]>=0&&uses[ded[v]]==1){
        const U64 diff=A[u]^A[v];if(__builtin_popcountll(diff)>26)continue;close++;
        bool compat=false;for(U64 g:generic)if(!((g^A[u])&diff&gm)){compat=true;break;}
        if(compat)continue;incompatible++;
        std::vector<int>cs;
        if(allcols){for(int c=0;c<H;c++)cs.push_back(c);}
        else{cs.push_back(col[ded[u]]);cs.push_back(col[ded[v]]);std::sort(cs.begin(),cs.end());cs.erase(std::unique(cs.begin(),cs.end()),cs.end());}
        bool any=false;
        for(int c:cs){
            if(diff>>handles[c]&1)continue;
            Best a=evaluate(u,v,c),b=evaluate(v,u,c);
            if(a.helper<0||b.helper<0)continue;any=true;assignments++;
            std::cout<<u<<','<<v<<','<<c<<','<<ded[u]<<','<<ded[v]<<','<<__builtin_popcountll(diff&~gm)<<','<<__builtin_popcountll(diff&gm)<<','
                <<__builtin_popcountll((~prefixH[c]|diff)&~gm)<<','<<a.total<<','<<b.total<<','<<a.helper<<','<<b.helper<<','
                <<a.generic<<','<<b.generic<<','<<a.rank<<','<<b.rank<<','<<a.cost<<','<<b.cost<<','<<a.depth<<','<<b.depth<<','<<a.punched<<','<<b.punched<<','<<a.shallow<<','<<b.shallow<<'\n';
        }
        rescued+=any;
    }
    std::cerr<<"close_single_pairs = "<<close<<"\nincompatible_single_pairs = "<<incompatible<<"\nrescued_pairs = "<<rescued
        <<"\nrescued_column_assignments = "<<assignments<<"\ntrace_states = "<<seen<<'\n';
}
