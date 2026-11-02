from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'research.cpp').read_text()
s=s.replace('#define CAP_COUNT 1','#define CAP_COUNT 0\n#define CAP_WIDTH 1')
s=s.replace('struct Comparator {', '''int sparse_links=2;
uint32_t sparse_directions=0;
bool allowed_edge(int a,int b) {return b<5 || a<sparse_links;}
struct Comparator {''')
s=s.replace('for (int b = a + 1; b < M; ++b) all.emplace_back(a, b);','for (int b = a + 1; b < M; ++b) if(allowed_edge(a,b))all.emplace_back(a, b);')
s=s.replace('for (int c : counts)\n        if (!c) return stats;', 'for(int e=0;e<ne;++e)if(allowed_edge(ep[e].first,ep[e].second)&&!counts[e])return stats;')
s=s.replace('((1U << 30)-1)','sparse_directions').replace('((1U<<30)-1)','sparse_directions')
s=s.replace('} else eb = rng.mod(ne);','} else { eb=rng.mod(ne);if(!allowed_edge(ep[eb].first,ep[eb].second))return false; }')
s=s.replace(' || !cap_compatible(A[u], A[v])','')
s=s.replace('int main() {','int unused_solver_main() {')
s+=r'''
int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    int n,k,p,R;if(!(std::cin>>n>>k>>p>>R))return 0;
    std::vector<u64>A(P);for(auto&a:A){std::string s;std::cin>>s;for(int j=0;j<64;++j)if(s[j]=='1')a|=1ULL<<j;}
    sparse_links=env_int("SPARSE_LINKS");
    int e=0;for(int a=0;a<6;++a)for(int b=a+1;b<6;++b,++e)if(allowed_edge(a,b))sparse_directions|=(1U<<e)|(1U<<(e+15));
    const int G=env_int("G_PROBE");
    Comparator comp;std::mt19937_64 rng(779879);comp.init(6,G,rng);
    std::vector<int>perm(64);std::iota(perm.begin(),perm.end(),0);
    auto ws=assign_windows(A,6,G,comp.edge,comp.polarity,perm,1e9,400000,100000,0);
    std::cerr<<"gobj_optimistic = "<<ws.gobj_after<<'\n';
    std::cout<<G<<" 1 1 1\n";
    for(int x:perm)std::cout<<x<<' ';std::cout<<'\n';
    for(int j=0;j<G;++j)std::cout<<comp.edge[j].first<<' '<<comp.edge[j].second<<' '<<comp.polarity[j]<<'\n';
    for(auto a:A)std::cout<<a<<'\n';
}
'''
(r/'sparse_mapping.cpp').write_text(s)
f=r/'shared_cap_model.cpp';s=f.read_text()
if 'ONLY_SELECTOR' not in s:s=s.replace('for(int selector=0;selector<6;++selector)for(int capcolor=0;capcolor<2;++capcolor) {','for(int selector=0;selector<6;++selector)for(int capcolor=0;capcolor<2;++capcolor) {\n            if(env_int("ONLY_SELECTOR") && selector+1!=env_int("ONLY_SELECTOR"))continue;')
s=s.replace('''                for(int x:comp.next[s])if(x>=0)adj[s].push_back(x);''', '''                u64 covered=0;
                for(int pos=0;pos<6;++pos) {
                    const int paper=comp.perms[s][pos];
                    const bool visible=paper==selector || (comp.opq[paper]&~covered);
                    covered|=comp.opq[paper];
                    if(!visible || pos==5)continue;
                    for(int d=0;d<6;++d) {const int x=comp.next[s][pos*6+d];if(x>=0)adj[s].push_back(x);}
                }''')
f.write_text(s)
