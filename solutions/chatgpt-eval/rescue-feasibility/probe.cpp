// Static representability probe only. It never runs or scores a contestant.
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using U = std::uint64_t;
constexpr U DATA = (U(1) << 35) - 1, GUARD = U(1) << 35;
struct Book { std::array<U,6> op{}, black{}; };
struct Pair { int a,b,d; U diff; };

std::vector<U> patterns(const Book& b) {
    std::array<int,6> p{0,1,2,3,4,5};
    std::vector<U> v;
    do {
        U covered=0, black=0;
        for (int i:p) { black |= b.black[i] & ~covered; covered |= b.op[i]; }
        v.push_back(black);
    } while (std::next_permutation(p.begin(),p.end()));
    std::sort(v.begin(),v.end()); v.erase(std::unique(v.begin(),v.end()),v.end());
    return v;
}

std::vector<U> rescued(const Book& b, U y, U support=DATA) {
    std::array<int,6> p{0,1,2,3,4,5};
    std::vector<U> v;
    do {
        U allcover=0, base=0;
        for (int i:p) { base |= b.black[i] & ~allcover; allcover |= b.op[i]; }
        base &= DATA;
        U covered=0;
        for (int cut=0;cut<=6;++cut) {
            U overwrite=support & ~covered;
            v.push_back((base & ~overwrite) | (y & overwrite));
            v.push_back((base & ~overwrite) | ((y ^ support) & overwrite) | GUARD);
            if (cut<6) covered |= b.op[p[cut]] & DATA;
        }
    } while (std::next_permutation(p.begin(),p.end()));
    std::sort(v.begin(),v.end()); v.erase(std::unique(v.begin(),v.end()),v.end());
    return v;
}

bool has(const std::vector<U>& code, U target, U mask) {
    target &= mask;
    for (U s:code) if ((s & mask)==target) return true;
    return false;
}
bool feasible(const std::vector<U>& code,U a,U b,U mask) {
    bool x=false,y=false;
    a &= mask; b &= mask;
    for (U s:code) {
        U t=s&mask; x |= t==a; y |= t==b;
        if(x&&y) return true;
    }
    return false;
}

int main(int argc,char** argv) {
    if(argc<4) { std::cerr<<"rescue_probe INPUT BASELINE_OUTPUT SEED [triples=1]\n"; return 1; }
    int seed=std::stoi(argv[3]); bool triples=argc<5||std::stoi(argv[4]);
    std::ifstream in(argv[1]), out(argv[2]);
    int n,k,p,r; in>>n>>k>>p>>r;
    std::vector<U> original(p), a(p);
    for(U& x:original){std::string s;in>>s;x=0;for(int j=0;j<64;++j)if(s[j]=='1')x|=U(1)<<j;}
    std::array<std::string,6> paper;
    for(auto& s:paper)out>>s;
    std::vector<int> positions;
    std::array<int,64> e0{},e1{};
    int freq[6][6]{};
    for(int j=0;j<64;++j){
        std::vector<int> opaque;
        for(int i=0;i<6;++i)if(paper[i][j]!='.')opaque.push_back(i);
        if(!opaque.empty()){
            if(opaque.size()!=2){std::cerr<<"Not a six-comparator design\n";return 1;}
            e0[j]=opaque[0]; e1[j]=opaque[1]; ++freq[e0[j]][e1[j]]; positions.push_back(j);
        }
    }
    if(positions.size()!=36){std::cerr<<"Expected G=36\n";return 1;}
    // Remove one duplicated edge's window so all 15 comparator pairs remain.
    int gi=0;
    for(int j=1;j<36;++j) if(freq[e0[positions[j]]][e1[positions[j]]]>freq[e0[positions[gi]]][e1[positions[gi]]])gi=j;
    std::swap(positions[gi],positions[35]);
    Book actual;
    for(int j=0;j<36;++j)for(int i=0;i<6;++i){
        if(paper[i][positions[j]]!='.')actual.op[i]|=U(1)<<j;
        if(paper[i][positions[j]]=='1')actual.black[i]|=U(1)<<j;
    }
    for(int i=0;i<p;++i)for(int j=0;j<36;++j)if(original[i]>>positions[j]&1)a[i]|=U(1)<<j;
    std::vector<Pair> pairs;
    int close=0;
    for(int u=0;u<p;++u)for(int v=u+1;v<p;++v){
        int d=std::popcount(original[u]^original[v]);
        pairs.push_back({u,v,d,a[u]^a[v]}); close+=d<=26;
    }
    std::mt19937_64 rng(0x735a0c93ULL);
    Book random;
    std::vector<std::pair<int,int>> edges;
    for(int u=0;u<6;++u)for(int v=u+1;v<6;++v)edges.emplace_back(u,v);
    std::shuffle(edges.begin(),edges.end(),rng);
    for(int j=0;j<36;++j){auto[u,v]=edges[j%15];random.op[u]|=U(1)<<j;random.op[v]|=U(1)<<j;random.black[(rng()&1)?u:v]|=U(1)<<j;}

    std::cout<<"seed,book,mode,guard_physical,distinct_codes,close_pairs,base_close,guard_close,compatible_close,added_over_base,added_over_guard,compatible_all,pair_triangles,feasible_triples,first_triple,support_size,support_hex,y_hex\n";
    for(int bi=0;bi<2;++bi){
        Book b=bi?random:actual;
        auto base=patterns(b), guard=rescued(b,0,0);
        std::vector<bool> baseok(pairs.size()), guardok(pairs.size());
        int bclose=0,gclose=0;
        for(std::size_t i=0;i<pairs.size();++i){auto q=pairs[i];baseok[i]=feasible(base,a[q.a],a[q.b],q.diff);guardok[i]=feasible(guard,a[q.a],a[q.b],q.diff);if(q.d<=26){bclose+=baseok[i];gclose+=guardok[i];}}
        U mixed=0;
        int seen[6][6]{};
        for(int j=0;j<35;++j){
            int x=-1,y=-1;for(int t=0;t<6;++t)if(b.op[t]>>j&1){if(x<0)x=t;else y=t;}
            const bool bit=bool(b.black[x]>>j&1) ^ bool(seen[x][y]++&1);
            if(bit)mixed|=U(1)<<j;
        }
        std::mt19937_64 patch_rng(0xA074526573637565ULL);
        struct Mode{std::string name;U y,support;};
        std::vector<Mode> modes={{"zero",0,DATA},{"copy_comparator",base.front()&DATA,DATA},{"mixed_edges",mixed,DATA},{"copy_target0",a[0]&DATA,DATA}};
        for(int t=0;t<4;++t)modes.push_back({"random"+std::to_string(t),patch_rng()&DATA,DATA});
        std::vector<int> support_order(35);std::iota(support_order.begin(),support_order.end(),0);
        std::shuffle(support_order.begin(),support_order.end(),patch_rng);
        for(int count:{4,8,12,18,24}){
            U support=0;for(int i=0;i<count;++i)support|=U(1)<<support_order[i];
            modes.push_back({"sparse"+std::to_string(count)+"_mixed",mixed,support});
            modes.push_back({"sparse"+std::to_string(count)+"_random",modes[4].y,support});
        }
        std::vector<U> group;
        for(int x=0;x<6;++x)for(int y=x+1;y<6;++y)group.push_back(b.op[x]&b.op[y]&DATA);
        std::stable_sort(group.begin(),group.end(),[](U a,U b){return std::popcount(a)>std::popcount(b);});
        for(int count:{1,2,4}){
            U support=0;for(int i=0;i<count;++i)support|=group[i];
            modes.push_back({"groups"+std::to_string(count)+"_mixed",mixed,support});
        }
        U one_per_edge=0;
        for(U mask:group) if(mask)one_per_edge|=mask&-mask;
        modes.push_back({"one_per_edge_random",modes[4].y,one_per_edge});
        modes.push_back({"one_per_edge_mixed",mixed,one_per_edge});
        for(auto[name,y,support]:modes){
            if(argc>5 && name.rfind(argv[5],0)!=0)continue;
            auto code=rescued(b,y,support);
            std::array<std::array<bool,256>,256> graph{};
            int all=0,cnt=0;
            for(auto q:pairs){
                bool ok=feasible(code,a[q.a],a[q.b],q.diff);
                graph[q.a][q.b]=graph[q.b][q.a]=ok; all+=ok;
                if(q.d<=26)cnt+=ok;
            }
            int triangles=0,trip=0;std::string first="none";
            if(triples){
                for(int u=0;u<p;++u)for(int v=u+1;v<p;++v)if(graph[u][v])for(int w=v+1;w<p;++w)if(graph[u][w]&&graph[v][w]){
                    ++triangles;U diff=(a[u]^a[v])|(a[u]^a[w]);
                    if(has(code,a[u],diff)&&has(code,a[v],diff)&&has(code,a[w],diff)){
                        if(!trip)first=std::to_string(u)+"/"+std::to_string(v)+"/"+std::to_string(w);
                        ++trip;
                    }
                }
            }
            std::cout<<seed<<','<<(bi?"random":"actual")<<','<<name<<','<<positions[35]<<','<<code.size()<<','<<close<<','<<bclose<<','<<gclose<<','<<cnt<<','<<cnt-bclose<<','<<cnt-gclose<<','<<all<<','<<triangles<<','<<trip<<','<<first<<','<<std::popcount(support)<<','<<std::hex<<support<<','<<y<<std::dec<<'\n';
        }
    }
}
