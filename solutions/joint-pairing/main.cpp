// Research-only design / execution split. No future requests are read by base/refit.
// The retained implementation is pinned to PR #52, blob 05e1f9d32e5b453bca64eeb46a386ec7d600d82c.
#define main retained_lattice_entry
#include "reference.hpp"
#undef main
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <unordered_map>

int work(const char* name, int fallback) {
    return std::getenv(name) ? env_int(name) : fallback;
}
void require(bool ok, const std::string& msg) { if (!ok) throw std::runtime_error(msg); }

void dump_design(const char* path, const std::vector<u64>& A, const std::vector<int>& permutation,
                 const Comparator& comp, const Design& des) {
    require(path, "missing JOINT_OUTPUT");
    std::ofstream f(path);
    require(bool(f), "cannot create design");
    f << "JOINT1\n" << comp.M << ' ' << comp.G << ' ' << des.H << '\n';
    for (u64 a:A) f << a << ' '; f << '\n';
    for (int j:permutation) f << j << ' '; f << '\n';
    for (int j:des.handle) f << j << ' '; f << '\n';
    for (int k=0;k<comp.M;k++) f << comp.opq[k] << ' ' << comp.black[k] << '\n';
    for (int j=0;j<comp.G;j++) f << comp.edge[j].first << ' ' << comp.edge[j].second << ' ' << comp.polarity[j] << '\n';
    f << des.unit.size() << '\n';
    for (auto u:des.unit) f << u.a << ' ' << u.b << ' ' << u.c << '\n';
    f << std::setprecision(17) << des.cur << '\n';
    require(bool(f), "design write failed");
}
void activate(Comparator& c) {
    require(c.M==6 && c.G==36, "research requires 6 sheets / 36 generic windows");
    bool guard[6][6]{};
    c.lattice_four_mask=0;
    for(int j=0;j<c.G;j++) {
        std::vector<int> ids;
        for(int k=0;k<6;k++) if(c.opq[k]>>j&1) ids.push_back(k);
        require(ids.size()>=2, "unprotected singleton template");
        if(ids.size()==2) {
            const int a=ids[0],b=ids[1];
            require(((c.black[a]^c.black[b])>>j&1)!=0,"same-color pair");
            guard[a][b]=true;
            c.edge[j]={a,b}; c.polarity[j]=c.black[a]>>j&1;
        } else c.lattice_four_mask|=u64(1)<<j;
    }
    for(int a=0;a<6;a++) for(int b=a+1;b<6;b++) require(guard[a][b],"missing visibility guard");
    c.complete=true;
    c.build_tables();
    c.lattice_enabled=c.lattice_four_mask!=0 || work("JOINT_FORCE_BFS",1);
    c.lattice_goal_cache.clear(); c.memo.clear();
    c.lattice_code.assign(720,0);
    for(int s=0;s<720;s++) {
        u64 covered=0;
        for(int k:c.perms[s]) { c.lattice_code[s]|=c.black[k]&~covered; covered|=c.opq[k]; }
    }
}
void load_design(const char* path, const std::vector<u64>& original,
                 std::vector<u64>& A, std::vector<int>& permutation, Comparator& c,
                 std::unique_ptr<Design>& des) {
    require(path,"missing JOINT_INPUT");
    std::ifstream f(path); std::string magic; int H;
    f>>magic>>c.M>>c.G>>H;
    require(magic=="JOINT1" && c.M==6 && c.G==36 && H==28,"bad design header");
    A.resize(256); for(auto& a:A) f>>a;
    permutation.resize(64); for(auto& j:permutation) f>>j;
    std::vector<int> sorted=permutation; std::sort(sorted.begin(),sorted.end());
    for(int j=0;j<64;j++) require(sorted[j]==j,"invalid permutation");
    for(int u=0;u<256;u++) {
        u64 a=0; for(int j=0;j<64;j++) a|=(original[u]>>permutation[j]&1)<<j;
        require(a==A[u],"public barcode / design mismatch");
    }
    des=std::make_unique<Design>(A,c.M,c.G);
    for(auto& j:des->handle) f>>j;
    for(int u=0;u<256;u++) {
        des->hb[u]=0;
        for(int j=0;j<H;j++) des->hb[u]|=(A[u]>>des->handle[j]&1)<<j;
    }
    c.opq.resize(6); c.black.resize(6);
    for(int k=0;k<6;k++) {f>>c.opq[k]>>c.black[k]; require(!(c.black[k]&~c.opq[k]),"black outside opaque");}
    c.edge.resize(36); c.polarity.resize(36);
    for(int j=0;j<36;j++) f>>c.edge[j].first>>c.edge[j].second>>c.polarity[j];
    int n; f>>n; require(n==186,"wrong unit count");
    des->unit.resize(n); std::array<int,256> used{};
    for(auto& u:des->unit) {
        f>>u.a>>u.b>>u.c;
        require(0<=u.a&&u.a<256&&-1<=u.b&&u.b<256&&0<=u.c&&u.c<H,"bad unit");
        require(!used[u.a]++ && (u.b<0 || !used[u.b]++),"target occurs twice");
        require(des->valid(u,u.c),"pair differs at its handle");
    }
    for(int u:used) require(u==1,"missing target");
    require(bool(f),"truncated design");
    activate(c);
    for(auto u:des->unit) if(u.b>=0) require(c.compatible(A[u.a],A[u.b]),"unrealizable stored pair");
    des->rebuild();
}
void make_base(std::vector<u64>& A, std::vector<int>& permutation, Comparator& comp,
               std::unique_ptr<Design>& des) {
    std::mt19937_64 rng(779879);
    std::iota(permutation.begin(),permutation.end(),0);
    comp.init(6,36,rng);
    assign_windows(A,6,36,comp.edge,comp.polarity,permutation,1e9,
                   work("MAP_ITERS",12000),work("GOPT_STEPS",3000),0.0);
    comp.rebuild();
    des=std::make_unique<Design>(A,6,36);
    require(des->initialize([&](u64 a,u64 b){return comp.compatible(a,b);},
            [&](u64 a,u64 b){return comp.mean_moves(a,a^b);}, []{return false;}),"initialization failed");
    des->anneal(1e9,work("ANNEAL_ITERS",6000000));
    des->filler_climb(1e9,work("CLIMB_ITERS",30000));
}
void refit(std::vector<u64>& A, Comparator& c, std::unique_ptr<Design>& des) {
    std::ifstream f(std::getenv("JOINT_MATCH"));
    require(bool(f),"missing matching");
    std::array<int,256> mate; mate.fill(-1); int a,b,count=0;
    while(f>>a>>b) { require(a>=0&&a<256&&b>=0&&b<256&&a!=b&&mate[a]<0&&mate[b]<0,"invalid matching");mate[a]=b;mate[b]=a;count++; }
    require(count==70,"matching must contain 70 edges");
    auto d=std::make_unique<Design>(A,6,36);
    d->handle=des->handle; d->hb=des->hb;
    std::unordered_map<u64,int> id; for(int u=0;u<256;u++)id[A[u]]=u;
    auto mean=[&](u64 a,u64 b){ return .5*(c.mean_moves(a,a^b)+c.mean_moves(b,a^b)); };
    require(d->initialize([&](u64 a,u64 b){return mate[id[a]]==id[b]&&c.compatible(a,b);},mean,[]{return false;}),"refit initialization failed");
    if(work("JOINT_ALLOW_REPAIR",1)) {
        for(auto& v:d->partners) v.clear();
        for(int u=0;u<256;u++) for(int v=u+1;v<256;v++) {
            const bool ok=c.compatible(A[u],A[v]);
            d->ok[u][v]=d->ok[v][u]=ok;
            if(ok) { d->partners[u].push_back(v);d->partners[v].push_back(u);d->gcost[u][v]=d->gcost[v][u]=mean(A[u],A[v]); }
        }
    }
    d->rebuild();
    d->anneal(1e9,work("ANNEAL_ITERS",6000000));
    d->filler_climb(1e9,work("CLIMB_ITERS",30000));
    des=std::move(d);
}
int main() { try {
    std::ios::sync_with_stdio(false); std::cin.tie(nullptr);
    int n,k,p,R; if(!(std::cin>>n>>k>>p>>R))return 0;
    require(n==64&&k==192&&p==256&&R==1024,"unexpected constraints");
    std::vector<u64> A(256);
    for(auto& a:A){std::string s;std::cin>>s;require(s.size()==64,"invalid barcode");a=0;for(int j=0;j<64;j++)if(s[j]=='1')a|=u64(1)<<j;}
    const auto originalA=A;
    int M=6,G=36;
    Comparator comp;std::unique_ptr<Design> des;std::vector<int> permutation(64);
    const std::string stage=std::getenv("JOINT_STAGE")?std::getenv("JOINT_STAGE"):"play";
    if(stage=="base") {make_base(A,permutation,comp,des);dump_design(std::getenv("JOINT_OUTPUT"),A,permutation,comp,*des);return 0;}
    load_design(std::getenv("JOINT_INPUT"),originalA,A,permutation,comp,des);
    if(stage=="refit") {refit(A,comp,des);dump_design(std::getenv("JOINT_OUTPUT"),A,permutation,comp,*des);std::cerr<<"model_cost = "<<des->cur/P<<'\n';return 0;}
    require(stage=="play","bad JOINT_STAGE");
    // Papers: the generic sheets, then the columns 0, 1, ... (in each column the colors alternate,
    // the more numerous first; singles before pairs within a color).
    std::vector<Paper> papers(K);
    std::vector<int> columns(K, -1), ded(P, -1);
    for (int i = 0; i < M; i++) papers[i] = {comp.opq[i], comp.black[i]};
    u64 opaque = low_bits(G);
    int next = M;
    for (int c = 0; c < des->H; c++) {
        opaque |= 1ULL << des->handle[c];
        std::array<std::vector<int>, 2> members;
        for (int x = 0; x < des->U; x++)
            if (des->unit[x].c == c) members[des->color(des->unit[x], c)].push_back(x);
        for (auto& group : members)
            std::stable_sort(group.begin(), group.end(),
                             [&](int x, int y) { return des->weight(des->unit[x]) < des->weight(des->unit[y]); });
        while (!members[0].empty() || !members[1].empty()) {
            int color = members[1].size() > members[0].size();
            int x = members[color].back();
            members[color].pop_back();
            const auto& u = des->unit[x];
            u64 mask = opaque;
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            papers[next] = {mask, A[u.a] & mask};
            columns[next] = c;
            ded[u.a] = next;
            if (u.b >= 0) ded[u.b] = next;
            next++;
        }
    }
    if (next != K || std::find(ded.begin(), ded.end(), -1) != ded.end()) return emergency_design(originalA, R);
    Solver solver(A);
    solver.M = M;
    solver.G = G;
    solver.H = des->H;
    solver.comparator = comp;
    solver.paper = papers;
    solver.col_of = columns;
    solver.ded = ded;
    solver.handle = des->handle;
    solver.hidx.assign(64, -1);
    for (int c = 0; c < des->H; c++) solver.hidx[solver.handle[c]] = c;
    solver.gmask = low_bits(G);
    solver.hmask = ~solver.gmask;
    solver.h_opq.resize(K);
    solver.h_blk.resize(K);
    for (int x = 0; x < K; x++) {
        solver.h_opq[x] = solver.handle_bits(papers[x].opaque);
        solver.h_blk[x] = solver.handle_bits(papers[x].black);
    }
    solver.order.resize(K);
    std::iota(solver.order.begin(), solver.order.end(), 0);
    solver.init_adaptive();
    if (M == Interleave::GM && comp.complete) {
        solver.interleave = std::make_shared<Interleave>();
        solver.comparator.build_tables();
        solver.interleave->init(solver.comparator, papers, A, ded, columns, solver.gmask, solver.hmask, 1e9);
    }
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\n';


    std::string output;
    for (const auto& pp : papers) {
        std::string row(N, '.');
        for (int j = 0; j < N; j++) row[permutation[j]] = !(pp.opaque >> j & 1) ? '.' : (pp.black >> j & 1) ? '1' : '0';
        output += row + '\n';
    }
    std::cout << output << std::flush;
    long long total = 0, generic = 0, wrong = 0, lattice_queries = 0;
    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == -1) return 0;
        const double t_req = elapsed_sec();
        if (ded[u] >= 0 && (comp.lattice_four_mask & ~papers[ded[u]].opaque)) lattice_queries++;
        // Safety net against a slow machine: the light plan from kFastAfter on.
        // Research replay deliberately has no online deadline.
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != A[u];
        output = std::to_string(moves.size()) + '\n';
        for (auto [x, d] : moves) {
            output += std::to_string(x) + ' ' + std::to_string(d) + '\n';
            generic += x < M;
        }
        std::cout << output << std::flush;
        total += moves.size();
    }
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total
              << "\nlattice_nonlinear_queries = " << lattice_queries
              << "\nG = " << G << "\nplan_failures = " << solver.plan_failures
              << "\nfast_requests = " << solver.fast_requests << "\npost_saved = " << solver.post_saved
              << "\nhelper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0)
              << "\ninterleave_trials = " << solver.interleave_trials
              << "\ninterleave_selected = " << solver.interleave_selected << "\ntail_hits = " << solver.tail_hits
              << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
} catch(const std::exception& e) {std::cerr<<"joint_error: "<<e.what()<<"\n";return 2;} }
