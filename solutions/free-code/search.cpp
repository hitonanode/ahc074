// Research model: no request sequence is read, and no contest score is emitted.
#define main inherited_main
#include "main.cpp"
#undef main
#include <fstream>
#include <unordered_map>

namespace free_code {
using Bits = std::array<u64, 12>;
struct Gate { unsigned opaque, black; std::array<unsigned char,720> truth{}; };
struct Pair {
    int a,b,n;
    u64 diff;
    double fixed;
    std::array<unsigned short,40> histogram{};
};
struct Match {
    double value=1e9;
    int errors=0, available=0;
    std::vector<int> selected;
};
struct Search {
    Comparator graph;
    std::vector<Gate> gates;
    std::vector<Pair> pairs;
    std::vector<unsigned char> mismatch;
    std::vector<u64> products;
    std::vector<int> windows, initial, state;
    std::vector<std::vector<int>> affected;
    std::array<double,721> fee{};
    std::vector<std::pair<double,int>> ranked;
    std::vector<double> prices;
    XorShift rng;
    int G=0;

    Search(u64 seed):rng(seed) {}
    static u64 read_bits(const std::string& s,char value) {
        u64 r=0;for(int i=0;i<int(s.size());++i)if(s[i]==value)r|=1ULL<<i;return r;
    }
    bool load(const std::string& in_path,const std::string& saved_path) {
        std::ifstream in(in_path),saved(saved_path);int n,k,p,r;
        in>>n>>k>>p>>r;if(n!=64||k!=192||p!=256)return false;
        std::string s;std::vector<u64> raw(256),op(7),black(7);
        for(auto& a:raw){in>>s;a=read_bits(s,'1');}
        for(int i=0;i<7;i++){saved>>s;op[i]=~read_bits(s,'.');black[i]=read_bits(s,'1');}
        if(!in||!saved)return false;
        u64 gm=0;for(int i=1;i<7;i++)gm|=op[i];
        for(int j=0;j<64;j++)if(gm>>j&1)windows.push_back(j);
        G=windows.size();if(G!=38)return false;
        products.resize(256);
        for(int a=0;a<256;a++)for(int j=0;j<G;j++)if(raw[a]>>windows[j]&1)products[a]|=1ULL<<j;
        graph.M=6;graph.G=G;graph.build_tables();
        for(unsigned o=1;o<64;o++)for(unsigned b=(o-1)&o;b;b=(b-1)&o) {
            Gate g{o,b,{}};
            for(int t=0;t<720;t++)for(int x:graph.perms[t])if(o>>x&1){g.truth[t]=b>>x&1;break;}
            gates.push_back(g);
        }
        for(int j:windows) {
            unsigned o=0,b=0;
            for(int x=0;x<6;x++){o|=unsigned(op[x+1]>>j&1)<<x;b|=unsigned(black[x+1]>>j&1)<<x;}
            int id=-1;for(int g=0;g<int(gates.size());g++)if(gates[g].opaque==o&&gates[g].black==b)id=g;
            if(id<0)return false;initial.push_back(id);
        }
        const u64 hm=~(gm|op[0]);affected.resize(G);
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++) {
            u64 full=(raw[a]^raw[b])&~op[0];
            if(__builtin_popcountll(full)>30)continue;
            u64 d=products[a]^products[b];int id=pairs.size();
            pairs.push_back({a,b,__builtin_popcountll(d),d,
                .50*__builtin_popcountll(full&hm)+.04*__builtin_popcountll(full),{}});
            for(u64 z=d;z;z&=z-1)affected[__builtin_ctzll(z)].push_back(id);
        }
        mismatch.resize(pairs.size()*720);prices.resize(pairs.size());ranked.reserve(pairs.size());
        // The count of satisfying orders is only a cheap surrogate during search.
        // Calibrate it against all exact six-element poset classes. Final prices
        // below use the actual visibility graph of the freely printed sheets.
        std::array<double,721> sum{};std::array<int,721> count{};
        for(auto pc:kPosetClasses) {
            int goals=0;
            for(int t=0;t<720;t++) {
                bool ok=true;
                for(int x=0;x<6;x++)if(((pc.relation>>(8*x))&63)&~graph.below[t][x]){ok=false;break;}
                goals+=ok;
            }
            if(goals){sum[goals]+=double(pc.sum)/720;count[goals]++;}
        }
        for(int c=1;c<=720;c++)if(count[c])fee[c]=sum[c]/count[c];
        for(int c=1;c<=720;c++)if(!count[c]) {
            int a=c,b=c;while(a>1&&!count[a])--a;while(b<720&&!count[b])++b;
            if(a==b)fee[c]=fee[a];else {
                double w=std::log(double(c)/a)/std::log(double(b)/a);
                fee[c]=fee[a]*(1-w)+fee[b]*w;
            }
        }
        reset(initial);return true;
    }
    void reset(const std::vector<int>& design) {
        state=design;std::array<u64,720> display{};
        for(int j=0;j<G;j++)for(int s=0;s<720;s++)if(gates[state[j]].truth[s])display[s]|=1ULL<<j;
        for(int i=0;i<int(pairs.size());i++) {
            auto& p=pairs[i];p.histogram.fill(0);
            for(int s=0;s<720;s++) {
                int z=__builtin_popcountll((products[p.a]^display[s])&p.diff);
                mismatch[i*720+s]=z;p.histogram[z]++;
            }
        }
    }
    void change(int j,int ng) {
        int old=state[j];if(old==ng)return;
        std::array<int,720> plus{},minus{};int np=0,nm=0;
        for(int s=0;s<720;s++)if(gates[old].truth[s]!=gates[ng].truth[s]) {
            if(gates[ng].truth[s])plus[np++]=s;else minus[nm++]=s;
        }
        for(int i:affected[j]) {
            auto& p=pairs[i];auto* d=&mismatch[i*720];
            int step=(products[p.a]>>j&1)?-1:1;
            for(int z=0;z<np;z++){int s=plus[z],v=d[s];p.histogram[v]--;p.histogram[v+step]++;d[s]=v+step;}
            for(int z=0;z<nm;z++){int s=minus[z],v=d[s];p.histogram[v]--;p.histogram[v-step]++;d[s]=v-step;}
        }
        state[j]=ng;
    }
    Match matching(double lambda,bool hard) {
        ranked.clear();Match result;
        for(int i=0;i<int(pairs.size());i++) {
            auto& p=pairs[i];int lo=0,hi=p.n;
            if(hard && (!p.histogram[0]||!p.histogram[p.n])){prices[i]=1e9;continue;}
            while(!p.histogram[lo])++lo;while(!p.histogram[hi])--hi;
            double price=p.fixed+fee[p.histogram[lo]]+fee[p.histogram[hi]]+lambda*(lo+p.n-hi);
            prices[i]=price;ranked.emplace_back(price,i);
        }
        std::sort(ranked.begin(),ranked.end());result.available=ranked.size();
        std::array<bool,256> used{};double total=0;
        for(auto [price,i]:ranked) {
            auto& p=pairs[i];if(used[p.a]||used[p.b])continue;
            used[p.a]=used[p.b]=true;total+=price;result.selected.push_back(i);
            if(result.selected.size()==71)break;
        }
        if(result.selected.size()<71) {
            std::array<std::vector<std::pair<int,int>>,256> neighbours;
            for(auto [price,i]:ranked) {
                auto& p=pairs[i];neighbours[p.a].emplace_back(p.b,i);neighbours[p.b].emplace_back(p.a,i);
            }
            while(result.selected.size()<71) {
                double best=1e9;int bx=-1,bi=-1,bj=-1,bu=-1,bv=-1;
                for(int x=0;x<int(result.selected.size());x++) {
                    int old=result.selected[x];auto& p=pairs[old];
                    for(auto [u,i]:neighbours[p.a])if(!used[u])for(auto [v,j]:neighbours[p.b])if(!used[v]&&u!=v) {
                        double add=prices[i]+prices[j]-prices[old];
                        if(add<best){best=add;bx=x;bi=i;bj=j;bu=u;bv=v;}
                    }
                }
                if(bx<0){result.value=total/71+10*(71-result.selected.size());return result;}
                used[bu]=used[bv]=true;total+=best;result.selected[bx]=bi;result.selected.push_back(bj);
            }
        }
        result.value=total/71;
        for(int i:result.selected) {
            auto& p=pairs[i];int lo=0,hi=p.n;while(!p.histogram[lo])lo++;while(!p.histogram[hi])hi--;
            result.errors+=lo+p.n-hi;
        }
        return result;
    }
    struct Exact { double value; int available,matched; double visible; };
    Exact exact() {
        std::array<u64,6> op{},bl{};
        for(int j=0;j<G;j++)for(int x=0;x<6;x++) {
            if(gates[state[j]].opaque>>x&1)op[x]|=1ULL<<j;
            if(gates[state[j]].black>>x&1)bl[x]|=1ULL<<j;
        }
        std::vector<std::vector<int>> reverse(720);double visible=0;
        for(int s=0;s<720;s++) {
            u64 covered=0;
            for(int pos=0;pos<6;pos++) {
                int x=graph.perms[s][pos];bool seen=(op[x]&~covered)!=0;covered|=op[x];
                if(!seen)continue;++visible;
                for(int d=0;d<6;d++)if(d!=pos) {
                    auto order=graph.perms[s];order.erase(order.begin()+pos);order.insert(order.begin()+d,x);
                    reverse[graph.order_index(order)].push_back(s);
                }
            }
        }
        std::unordered_map<std::string,double> cache;
        auto price=[&](int id,int which) {
            Bits bits{};auto& p=pairs[id];
            for(int s=0;s<720;s++)if(mismatch[id*720+s]==(which?p.n:0))bits[s>>6]|=1ULL<<(s&63);
            std::string key(reinterpret_cast<const char*>(bits.data()),sizeof(bits));
            auto it=cache.find(key);if(it!=cache.end())return it->second;
            std::array<int,720> dist{},queue{};dist.fill(100000);int qh=0,qt=0;
            for(int s=0;s<720;s++)if(bits[s>>6]>>(s&63)&1){dist[s]=0;queue[qt++]=s;}
            while(qh<qt){int s=queue[qh++];for(int t:reverse[s])if(dist[t]>dist[s]+1){dist[t]=dist[s]+1;queue[qt++]=t;}}
            double value=std::accumulate(dist.begin(),dist.end(),0.0)/720;
            cache.emplace(key,value);return value;
        };
        // Use the same matching operation as the proxy, but temporarily replace
        // each pair's fixed part so its complete price is exact.
        std::vector<double> original(pairs.size());
        for(int i=0;i<int(pairs.size());i++) {
            auto& p=pairs[i];original[i]=p.fixed;
            if(p.histogram[0]&&p.histogram[p.n])p.fixed+=price(i,0)+price(i,1)-fee[p.histogram[0]]-fee[p.histogram[p.n]];
        }
        auto m=matching(0,true);
        for(int i=0;i<int(pairs.size());i++)pairs[i].fixed=original[i];
        return {m.value,m.available,int(m.selected.size()),visible/720};
    }
};
}

#ifndef FREE_CODE_NO_MAIN
int main(int argc,char** argv) {
    using namespace free_code;
    using Clock=std::chrono::steady_clock;
    if(argc<3)return 2;
    int iterations=30000;double seconds=300,temperature=.12,penalty=2;u64 seed=1;std::string start="base";
    for(int i=3;i<argc;i++) {
        std::string s=argv[i];auto j=s.find('=');if(j==s.npos)continue;
        std::string a=s.substr(0,j),b=s.substr(j+1);
        if(a=="iters")iterations=std::stoi(b);else if(a=="seconds")seconds=std::stod(b);
        else if(a=="seed")seed=std::stoull(b);else if(a=="start")start=b;
        else if(a=="temp")temperature=std::stod(b);else if(a=="penalty")penalty=std::stod(b);
    }
    auto t0=Clock::now();Search q(seed);if(!q.load(argv[1],argv[2]))return 3;
    auto baseline=q.matching(0,true);auto baseline_exact=q.exact();
    if(start!="base") {
        std::vector<int> allowed;
        for(int g=0;g<int(q.gates.size());g++)if(start!="balanced"||__builtin_popcount(q.gates[g].opaque)==2*__builtin_popcount(q.gates[g].black))allowed.push_back(g);
        auto s=q.state;for(auto& g:s)g=allowed[q.rng.mod(allowed.size())];q.reset(s);
    }
    auto hard=q.matching(0,true);double best=hard.value;auto best_state=q.state;
    int accepted=0,completed=0;double current=0;int errors=0;
    for(int t=0;t<iterations;t++) {
        double elapsed=std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE;
        if(elapsed>=seconds)break;
        double progress=std::max(double(t)/iterations,elapsed/seconds);
        double lambda=penalty*std::pow(4.0,progress),temp=temperature*std::pow(.025,progress);
        auto before=q.matching(lambda,false);int j=q.rng.mod(q.G),old=q.state[j],ng=old;
        if(q.rng.mod(2)==0)ng=q.rng.mod(q.gates.size());
        else {
            auto g=q.gates[old];int x=q.rng.mod(6),value=q.rng.mod(3);
            g.opaque=(g.opaque&~(1U<<x))|((value<2?1U:0U)<<x);g.black=(g.black&~(1U<<x))|((value==1?1U:0U)<<x);
            for(int y=0;y<int(q.gates.size());y++)if(q.gates[y].opaque==g.opaque&&q.gates[y].black==g.black){ng=y;break;}
        }
        q.change(j,ng);auto after=q.matching(lambda,false);
        if(after.value<=before.value||q.rng.real()<std::exp((before.value-after.value)/temp)){accepted++;current=after.value;errors=after.errors;}
        else {q.change(j,old);current=before.value;errors=before.errors;}
        if(t%32==0||!errors) {
            auto h=q.matching(0,true);
            if(h.value<best){best=h.value;best_state=q.state;std::cerr<<"best "<<t<<' '<<best<<" edges "<<h.available<<'\n';}
        }
        completed=t+1;
        if(t%1000==0)std::cerr<<"step "<<t<<" sec "<<elapsed<<" value "<<current<<" errors "<<errors<<" best "<<best<<'\n';
    }
    q.reset(best_state);auto result=q.exact();int nonlinear=0;
    for(int g:q.state)nonlinear+=__builtin_popcount(q.gates[g].opaque)>2;
    std::cout<<"{\"baseline_proxy\":"<<baseline.value<<",\"baseline_exact\":"<<baseline_exact.value
        <<",\"best_proxy\":"<<best<<",\"best_exact\":"<<result.value<<",\"available\":"<<result.available
        <<",\"matched\":"<<result.matched<<",\"mean_visible\":"<<result.visible<<",\"nonlinear\":"<<nonlinear<<",\"iterations\":"<<completed
        <<",\"accepted\":"<<accepted<<",\"last_errors\":"<<errors<<",\"elapsed\":"
        <<std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE<<",\"windows\":[";
    for(int j=0;j<q.G;j++)std::cout<<(j?",":"")<<q.windows[j];
    std::cout<<"],\"gates\":[";
    for(int j=0;j<q.G;j++){auto& g=q.gates[q.state[j]];std::cout<<(j?",":"")<<'['<<g.opaque<<','<<g.black<<']';}
    std::cout<<"]}\n";
}
#endif
