#define main inherited_main
#include "main.cpp"
#undef main
#include <fstream>
#include <iomanip>

namespace cover {
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
    s->col_of.assign(K,-1);s->ded.assign(P,-1);s->choices.resize(P);
    for(int x=7;x<K;x++){
        for(int c=0;c<s->H;c++)if(s->paper[x].opaque>>s->handle[c]&1)s->col_of[x]=c;
        for(int u=0;u<P;u++)if(!((A[u]^s->paper[x].black)&s->paper[x].opaque&~kCapBit)){
            if(s->ded[u]>=0)return {};s->ded[u]=x;s->choices[u]={x};
        }
    }
    if(std::find(s->ded.begin(),s->ded.end(),-1)!=s->ded.end())return {};
    s->h_opq.resize(K);s->h_blk.resize(K);for(int x=0;x<K;x++){s->h_opq[x]=s->handle_bits(s->paper[x].opaque);s->h_blk[x]=s->handle_bits(s->paper[x].black);}
    s->order.push_back(6);for(int x=0;x<K;x++)if(x!=6)s->order.push_back(x);
    return s;
}
void share(Solver& s,int a,int b){
    int x=s.choices[b][0];u64 diff=s.A[a]^s.A[b];
    assert(s.choices[a].size()==1&&s.choices[b].size()==1);
    assert(!(diff>>s.handle[s.col_of[x]]&1));assert(s.comparator.compatible(s.A[a],s.A[b]));
    s.paper[x].opaque&=~(diff&~kCapBit);s.paper[x].black&=s.paper[x].opaque;
    if(diff&kCapBit)s.paper[x].black&=~kCapBit;
    s.h_opq[x]=s.handle_bits(s.paper[x].opaque);s.h_blk[x]=s.handle_bits(s.paper[x].black);
    s.choices[a].push_back(x);
}
double simulate(Solver& s,int sequences,std::vector<double>* per_product=nullptr,int sequence_offset=0){
    double sum=0;std::vector<double> total(P),count(P);int wrong=0;
    s.init_choices();auto initial=s.save();
    for(int q=0;q<sequences;q++){
        s.restore(initial);std::mt19937_64 rng(1000003ULL*(q+1+sequence_offset));int prev=rng()%P;
        for(int t=0;t<1024;t++){
            int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
            auto path=s.process(u);sum+=path.size();total[u]+=path.size();count[u]++;wrong+=s.display()!=s.A[u];
        }
    }
    if(wrong){std::cerr<<"wrong = "<<wrong<<'\n';return 1e9;}
    if(per_product){per_product->resize(P);for(int u=0;u<P;u++)(*per_product)[u]=total[u]/count[u];}
    return sum/(1024*sequences);
}

std::unique_ptr<Solver> redesign(const Solver& source,int reserve,int iterations=20000000){
    std::vector<u64> a=source.A;for(auto& x:a)x&=kActiveWindows;
    Design d(a,6+reserve,source.G);
    auto estimate=[&](u64 a,u64 b){auto reach=source.comparator.closure(a,a^b);u64 key=0;for(int x=0;x<6;x++)key|=u64(reach[x])<<(8*x);return PosetSums::get().both_of(key)/1440.0;};
    if(!d.initialize([&](u64 a,u64 b){return source.comparator.compatible(a,b);},estimate,[]{return false;}))return {};
    d.anneal(1e9,iterations);d.filler_climb(1e9,60000);
    auto s=std::make_unique<Solver>(source.A);s->G=source.G;s->H=d.H;s->gmask=source.gmask;s->hmask=source.hmask;s->comparator=source.comparator;
    s->paper.resize(K);s->col_of.assign(K,-1);s->ded.assign(P,-1);s->choices.resize(P);s->handle=d.handle;s->hidx.assign(64,-1);
    for(int c=0;c<s->H;c++)s->hidx[s->handle[c]]=c;
    for(int x=0;x<=6;x++)s->paper[x]=source.paper[x];
    std::vector<std::array<int,2>> demand(s->H);
    for(auto u:d.unit)for(int c=u.c+1;c<s->H;c++){demand[c][d.hb[u.a]>>c&1]++;if(u.b>=0)demand[c][d.hb[u.b]>>c&1]++;}
    u64 opaque=s->gmask|kCapBit;int next=7;
    for(int c=0;c<s->H;c++){
        opaque|=1ULL<<s->handle[c];std::array<std::vector<int>,2> members;
        for(int x=0;x<d.U;x++)if(d.unit[x].c==c)members[d.color(d.unit[x],c)].push_back(x);
        for(auto& v:members)std::stable_sort(v.begin(),v.end(),[&](int x,int y){return d.weight(d.unit[x])<d.weight(d.unit[y]);});
        int majority=demand[c][1]>demand[c][0];
        for(int step=0;!members[0].empty()||!members[1].empty();step++){
            int color=members[1].size()>members[0].size();if(step<2&&!members[majority^step].empty())color=majority^step;
            int x=members[color].back();members[color].pop_back();auto u=d.unit[x];u64 mask=opaque,diff=u.b<0?0:s->A[u.a]^s->A[u.b];mask&=~(diff&~kCapBit);
            u64 black=s->A[u.a]&mask;if(diff&kCapBit)black&=~kCapBit;
            s->paper[next]={mask,black};s->col_of[next]=c;s->ded[u.a]=next;s->choices[u.a]={next};if(u.b>=0){s->ded[u.b]=next;s->choices[u.b]={next};}next++;
        }
    }
    assert(next==K-reserve);
    s->h_opq.resize(K);s->h_blk.resize(K);for(int x=0;x<K;x++){s->h_opq[x]=s->handle_bits(s->paper[x].opaque);s->h_blk[x]=s->handle_bits(s->paper[x].black);}
    s->order.push_back(6);for(int x=0;x<K;x++)if(x!=6)s->order.push_back(x);return s;
}
std::vector<int> copy_to(Solver& s,int original,int column,int spare){
    std::vector<int> owners;for(int u=0;u<P;u++)if(s.choices[u][0]==original)owners.push_back(u);
    assert(!owners.empty()&&owners.size()<=2&&s.col_of[original]!=column&&s.col_of[spare]<0);
    u64 diff=owners.size()==2?s.A[owners[0]]^s.A[owners[1]]:0;
    assert(!(diff>>s.handle[column]&1));
    u64 op=s.gmask|kCapBit;for(int c=0;c<=column;c++)op|=1ULL<<s.handle[c];op&=~(diff&~kCapBit);
    u64 black=s.A[owners[0]]&op;if(diff&kCapBit)black&=~kCapBit;
    s.paper[spare]={op,black};s.col_of[spare]=column;s.h_opq[spare]=s.handle_bits(op);s.h_blk[spare]=s.handle_bits(black);
    for(int u:owners){assert(s.choices[u].size()==1);s.choices[u].push_back(spare);}
    s.order.erase(std::find(s.order.begin(),s.order.end(),spare));
    auto it=s.order.end();for(auto j=s.order.begin();j!=s.order.end();j++)if(s.col_of[*j]>=column&&*j>=7){it=j;break;}
    s.order.insert(it,spare);return owners;
}
}
