#define main inherited_main
#include "main.cpp"
#undef main
#include <fstream>
#include <iomanip>

namespace coat {
u64 parse(const std::string& s,char c){u64 a=0;for(int j=0;j<64;j++)if(s[j]==c)a|=1ULL<<j;return a;}
std::unique_ptr<Solver> load(const std::string& input,const std::string& output){
    std::ifstream in(input),out(output);int n,k,p,r;in>>n>>k>>p>>r;if(n!=64||k!=192||p!=256)return {};
    std::vector<u64> raw(P);std::string line;for(auto& a:raw){in>>line;a=parse(line,'1');}
    std::vector<Paper> raw_p(K);for(auto& q:raw_p){out>>line;q={~parse(line,'.'),parse(line,'1')};}if(!in||!out)return {};
    u64 gm=0;for(int x=1;x<=6;x++)gm|=raw_p[x].opaque;
    if(raw_p[0].opaque!=kCapBit)return {};
    std::vector<int> windows;for(int j=0;j<63;j++)if(gm>>j&1)windows.push_back(j);int G=windows.size();
    for(int j=0;j<63;j++)if(!(gm>>j&1))windows.push_back(j);windows.push_back(63);
    auto convert=[&](u64 a){u64 b=0;for(int j=0;j<64;j++)if(a>>windows[j]&1)b|=1ULL<<j;return b;};
    std::vector<u64>A(P);for(int u=0;u<P;u++)A[u]=convert(raw[u]);
    auto s=std::make_unique<Solver>(A);s->G=G;s->H=63-G;s->gmask=low_bits(G);s->hmask=kActiveWindows&~s->gmask;s->paper.resize(K);
    for(int x=0;x<K;x++){int old=x==6?0:x<6?x+1:x;s->paper[x]={convert(raw_p[old].opaque),convert(raw_p[old].black)};}
    s->comparator.M=6;s->comparator.G=G;
    for(int j=0;j<G;j++){int a=-1,b=-1;for(int x=0;x<6;x++)if(s->paper[x].opaque>>j&1){if(a<0)a=x;else b=x;}if(a<0||b<0)return {};s->comparator.edge.emplace_back(a,b);s->comparator.polarity.push_back(s->paper[a].black>>j&1);}
    s->comparator.rebuild();s->hidx.assign(64,-1);
    for(int x=7;x<K;x++)for(u64 z=s->paper[x].opaque&s->hmask;z;z&=z-1){int j=__builtin_ctzll(z);if(s->hidx[j]<0){s->hidx[j]=s->handle.size();s->handle.push_back(j);}}
    if(int(s->handle.size())!=s->H)return {};
    s->col_of.assign(K,-1);s->ded.assign(P,-1);
    for(int x=7;x<K;x++){
        for(int c=0;c<s->H;c++)if(s->paper[x].opaque>>s->handle[c]&1)s->col_of[x]=c;
        for(int u=0;u<P;u++)if(!((A[u]^s->paper[x].black)&s->paper[x].opaque&~kCapBit)){
            if(s->ded[u]>=0)return {};s->ded[u]=x;
        }
    }
    if(std::find(s->ded.begin(),s->ded.end(),-1)!=s->ded.end())return {};
    s->h_opq.resize(K);s->h_blk.resize(K);for(int x=0;x<K;x++){s->h_opq[x]=s->handle_bits(s->paper[x].opaque);s->h_blk[x]=s->handle_bits(s->paper[x].black);}
    s->order.push_back(6);for(int x=0;x<K;x++)if(x!=6)s->order.push_back(x);
    return s;
}
}
