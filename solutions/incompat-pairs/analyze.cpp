// Saved-design analysis only. The included solver is never executed.
#define main inherited_main
#include "main.cpp"
#undef main
#include <bit>
#include <iomanip>
#include <map>
#include <set>

namespace study {
u64 parse(const std::string& s) {
    u64 x = 0;
    for (int j = 0; j < int(s.size()); ++j) if (s[j] == '1') x |= 1ULL << j;
    return x;
}
u64 relation(const Comparator& c, u64 target, u64 holes) {
    const auto r = c.closure(target, holes);
    u64 key = 0;
    for (int i = 0; i < c.M; ++i) key |= u64(r[i]) << (8 * i);
    return key;
}
double mean_cost(const Comparator& c, u64 target, u64 holes) {
    const u64 key = relation(c, target, holes);
    return key & kDiagonal ? 1e6 : PosetSums::get().both_of(key) / 1440.0;
}
// Every sheet placed above a helper must be a source of the remaining
// requested comparisons. Removing all such sources maximizes the shielding
// of the helper, independent of the order in which sources are removed.
u64 residue(const Comparator& c, u64 target, u64 holes) {
    std::array<unsigned, 6> pred{};
    for (u64 z = holes; z; z &= z - 1) {
        int j = std::countr_zero(z);
        auto [a,b] = c.edge[j];
        if (int(target >> j & 1) != c.polarity[j]) std::swap(a,b);
        pred[b] |= 1U << a;
    }
    unsigned left = 63;
    for (;;) {
        unsigned sources = 0;
        for (int a = 0; a < 6; ++a)
            if ((left >> a & 1) && !(pred[a] & left)) sources |= 1U << a;
        if (!sources) break;
        left &= ~sources;
    }
    u64 result = 0;
    for (u64 z = holes; z; z &= z - 1) {
        int j = std::countr_zero(z);
        const auto [a,b] = c.edge[j];
        if ((left >> a & 1) && (left >> b & 1)) result |= 1ULL << j;
    }
    return result;
}
struct Candidate {
    int a, b, errors;
    u64 ra, rb;
    double gc;
    int column = -1;
    std::array<std::vector<int>, 2> donors;
    double fee = 1e6;
    double helper_price = 1e6, free_access_price = 1e6;
};
struct Row {
    int a,b,c;
    double model;
};

int run(int argc, char** argv) {
    if (argc < 4) return 2;
    std::ifstream input(argv[1]);
    int n,k,p,r;
    input >> n >> k >> p >> r;
    if (n != 64 || k != K || p != P || r != 1024) return 3;
    std::vector<u64> original(P);
    std::string line;
    for (auto& a : original) { input >> line; a = parse(line); }
    setenv("DESIGN_LOAD_DIR", argv[2], 1);
    DesignStore store(original);
    std::ostringstream log;
    auto* old_log = std::cerr.rdbuf(log.rdbuf());
    DesignState state = store.load(original);
    std::cerr.rdbuf(old_log);
    if (state.emergency || state.M != 6 || state.G != 38) return 4;
    auto solver = make_solver(state);
    auto& comp = solver.comparator;
    comp.build_tables();
    const u64 gm = solver.gmask, hm = solver.hmask;
    std::vector<u64> displays;
    std::vector<std::array<u64,7>> prefixes;
    for (const auto& order : comp.perms) {
        u64 b = 0, cov = 0;
        std::array<u64,7> pref{};
        int depth = 0;
        for (int x : order) { b |= comp.black[x] & ~cov; cov |= comp.opq[x]; pref[++depth] = cov; }
        displays.push_back(b);
        prefixes.push_back(pref);
    }
    std::map<std::string, double> stats;
    std::array<int, 39> hist{}, residual_hist{};
    std::vector<Candidate> candidates;
    std::vector<std::array<int,2>> overcoat;
    for (int x = 0; x < 6; ++x) for (int u = 0; u < P; ++u)
        if (!((state.A[u] ^ state.papers[x].black) & state.papers[x].opaque)) overcoat.push_back({x,u});
    std::map<std::pair<int,int>, double> compatible_gc;
    std::vector<int> nc(state.H), nt(state.H), served(K);
    for (int x : state.ded) ++served[x];
    for (int x = 7; x < K; ++x) { ++nc[state.columns[x]]; nt[state.columns[x]] += served[x]; }
    std::vector<u64> prefix(state.H);
    for (int c = 0; c < state.H; ++c)
        prefix[c] = (c ? prefix[c-1] : 0) | (1ULL << state.handle[c]);
    for (int a = 0; a < P; ++a) for (int b = a+1; b < P; ++b) {
        u64 diff = state.A[a] ^ state.A[b], gh = diff & gm;
        const double normal = mean_cost(comp,state.A[a],gh);
        if (normal < 100) compatible_gc[{a,b}] = normal;
        if (std::popcount(diff) > 26) continue;
        ++stats["near"];
        int errors = 39;
        std::set<u64> repairs;
        for (u64 display : displays) {
            const u64 wrong = (display ^ state.A[a]) & gh;
            const int count = std::popcount(wrong);
            if (count < errors) { errors = count; repairs.clear(); }
            if (count == errors && count <= 2) repairs.insert(wrong);
        }
        ++hist[errors];
        if (!errors) { ++stats["compatible"]; continue; }
        Candidate q{a,b,errors,residue(comp,state.A[a],gh),residue(comp,state.A[b],gh),1e6,-1,{},1e6};
        bool coat_possible = false;
        for (auto [sheet,target] : overcoat) if (target == a || target == b)
            coat_possible |= !residue(comp,state.A[a],gh & ~state.papers[sheet].opaque);
        stats["overcoat_new_pairs"] += coat_possible;
        ++residual_hist[std::popcount(q.ra)];
        ++residual_hist[std::popcount(q.rb)];
        for (u64 repair : repairs)
            q.gc = std::min(q.gc,mean_cost(comp,state.A[a],gh & ~repair));
        if (errors == 1) {
            stats["one_residual_sum"] += (std::popcount(q.ra)+std::popcount(q.rb))*0.5;
            stats["one_residual_max_sum"] += std::max(std::popcount(q.ra),std::popcount(q.rb));
            stats["one_repaired_gc_sum"] += q.gc;
        }
        // A donor must survive replacing both current owner papers. Its handle
        // colors are checked exactly for the hypothetical pair at each column.
        std::array<std::vector<int>,2> generic_donors;
        for (int side = 0; side < 2; ++side) {
            const int u = side ? b : a;
            const u64 rem = side ? q.rb : q.ra;
            for (int x = 7; x < K; ++x) {
                if (x == state.ded[a] || x == state.ded[b]) continue;
                const auto& pp = state.papers[x];
                if ((pp.black ^ state.A[u]) & pp.opaque & rem) continue;
                if (residue(comp,state.A[u],rem & ~pp.opaque)) continue;
                generic_donors[side].push_back(x);
            }
            // Independent finite check: all 720 generic orders and all seven
            // insertion gaps, for the first four incompatible pairs per seed.
            if (candidates.size() < 4) for (int x = 7; x < K; ++x) {
                if (x == state.ded[a] || x == state.ded[b]) continue;
                bool exact = false;
                const auto& pp = state.papers[x];
                for (int s = 0; s < 720 && !exact; ++s) for (int t = 0; t <= 6 && !exact; ++t) {
                    const u64 cover = pp.opaque & ~prefixes[s][t];
                    const u64 show = (displays[s] & ~cover) | (pp.black & cover);
                    exact = !((show ^ state.A[u]) & gh);
                }
                const bool predicted = std::find(generic_donors[side].begin(),generic_donors[side].end(),x) != generic_donors[side].end();
                ++stats["helper_validation_checks"];
                if (exact != predicted) { std::cerr << "helper validation failed " << a << ' ' << b << ' ' << x << '\n'; return 8; }
            }
        }
        if (!generic_donors[0].empty() && !generic_donors[1].empty()) ++stats["generic_rescuable"];
        for (int c = 0; c < state.H; ++c) {
            if (diff >> state.handle[c] & 1) continue;
            const u64 hh = hm & ~(prefix[c] & ~diff);
            std::array<std::vector<int>,2> donors;
            double access = 0;
            for (int side = 0; side < 2; ++side) {
                const int u = side ? b : a;
                double rate = 0;
                for (int x : generic_donors[side]) {
                    const auto& pp = state.papers[x];
                    if (state.columns[x] == c || ((pp.black ^ state.A[u]) & pp.opaque & hh)) continue;
                    donors[side].push_back(x);
                    rate += 1.0 / nc[state.columns[x]];
                }
                access += rate ? 1.0/rate - 1.0 : 1e6;
            }
            // Same coarse screening price as weave-lab: placement+return 1.8,
            // geometric access to a usable head. This is not an exact cost.
            const double fee = 1.8 + access*0.5;
            if (fee < q.fee && !donors[0].empty() && !donors[1].empty()) {
                q.fee = fee; q.column = c; q.donors = std::move(donors);
            }
        }
        if (q.column >= 0) {
            ++stats["rescuable"];
            if (errors == 1) ++stats["one_rescuable"];
            stats["rescue_fee_sum"] += q.fee;
            stats["rescue_min_donors_sum"] += std::min(q.donors[0].size(),q.donors[1].size());
        }
        candidates.push_back(std::move(q));
    }
    // Existing cap ignored here: even this favorable count bounds the supply
    // of targets that one generic sheet can safely cover above the product.
    for (int x = 0; x < 6; ++x) for (int u = 0; u < P; ++u)
        if (!((state.A[u] ^ state.papers[x].black) & state.papers[x].opaque)) ++stats["overcoat_targets"];

    // Replay only the already recorded baseline output. For every hypothetical
    // rescued pair incident to the requested target, ask whether a usable donor
    // is the previous product, is initially visible, or moves anywhere in the
    // baseline plan. The last is an optimistic opportunity, not a free legal plan.
    std::ifstream output(argv[3]);
    for (int o = 0; o < K; ++o) {
        output >> line;
        const int x = o == 0 ? 6 : o <= 6 ? o-1 : o;
        std::string expected(64,'.');
        for (int j=0; j<64; ++j) if (state.papers[x].opaque >> j & 1)
            expected[state.permutation[j]] = (state.papers[x].black >> j & 1) ? '1' : '0';
        if (line != expected) { std::cerr << "saved design differs from output\n"; return 9; }
    }
    std::vector<int> order(K);
    std::iota(order.begin(),order.end(),0);
    std::rotate(order.begin(),order.begin()+6,order.begin()+7);
    std::vector<std::array<int,7>> replay_examples;
    std::array<double,K> access_sum{};
    int previous = -1;
    for (int request = 0; request < r; ++request) {
        int u,m; input >> u; output >> m;
        if (!input || !output || m < 0 || m > 2*K) return 5;
        std::array<bool,K> visible{},moved{};
        const auto start_order = order;
        u64 seen = 0;
        for (int x : order) { visible[x] = bool(state.papers[x].opaque & ~seen); seen |= state.papers[x].opaque; }
        for (int t = 0; t < m; ++t) {
            int x,d; output >> x >> d;
            x = x == 0 ? 6 : x <= 6 ? x-1 : x;
            moved[x] = true;
            const auto at = std::find(order.begin(),order.end(),x);
            if (at == order.end() || d < 0 || d >= K) return 6;
            u64 covering = 0;
            for (auto it = order.begin(); it != at; ++it) covering |= state.papers[*it].opaque;
            if (!(state.papers[x].opaque & ~covering)) return 10;
            order.erase(at); order.insert(order.begin()+d,x);
        }
        u64 show = 0, cover = 0;
        for (int x : order) { show |= state.papers[x].black & ~cover; cover |= state.papers[x].opaque; }
        if (show != state.A[u]) return 11;
        // Exact minimum removals until x can first become visible, allowing
        // every blocker to be placed below x. The variant counting only papers
        // not moved by the baseline is a lower bound on new distinct moves;
        // it grants all baseline moves their most favorable destination.
        std::array<int,64> above{}, new_above{};
        std::array<int,K> depth{}, new_moves{};
        for (int x : start_order) {
            depth[x] = new_moves[x] = K;
            for (u64 z = state.papers[x].opaque; z; z &= z-1) {
                const int j = std::countr_zero(z);
                depth[x] = std::min(depth[x],above[j]);
                new_moves[x] = std::min(new_moves[x],new_above[j]+int(!moved[x]));
                ++above[j]; new_above[j] += !moved[x];
            }
            access_sum[x] += depth[x];
        }
        for (const auto& q : candidates) {
            if (q.column < 0 || (q.a != u && q.b != u)) continue;
            const int side = q.b == u;
            bool prev = false, vis = false, mov = false;
            int best_depth = K, best_new = K;
            for (int x : q.donors[side]) {
                prev |= previous >= 0 && x == state.ded[previous];
                vis |= visible[x]; mov |= moved[x];
                best_depth = std::min(best_depth,depth[x]);
                best_new = std::min(best_new,new_moves[x]);
                if (moved[x] && replay_examples.size() < 12)
                    replay_examples.push_back({request,q.a,q.b,u,x,int(previous>=0 && x==state.ded[previous]),int(visible[x])});
            }
            ++stats["replay_pair_requests"];
            stats["replay_previous"] += prev;
            stats["replay_visible"] += vis;
            stats["replay_moved"] += mov;
            stats["replay_access_sum"] += best_depth;
            stats["replay_new_moves_sum"] += best_new;
            if (q.errors == 1) {
                ++stats["replay_one_requests"];
                stats["replay_one_previous"] += prev;
                stats["replay_one_visible"] += vis;
                stats["replay_one_moved"] += mov;
                stats["replay_one_access_sum"] += best_depth;
                stats["replay_one_new_moves_sum"] += best_new;
            }
        }
        previous = u;
    }
    if (argc >= 5 && std::stoi(argv[4]) > 0) {
        // Further favorable pricing experiment: existing helper patterns, free
        // choice among all usable donors, no conflicts with newly re-paired
        // donors, and the best target column regardless of actual assignment.
        // Exposure uses its empirical minimum visible-removal depth, averaged
        // over all baseline request starts. Every handle covered receives a
        // generous 0.5-move credit. Placement + eventual return costs 1.8.
        std::vector<std::vector<int>> pred(720);
        for (int s=0; s<720; ++s) for (int t : comp.next[s]) if (t>=0) pred[t].push_back(s);
        for (auto& q : candidates) if (q.column >= 0) {
            const u64 diff = state.A[q.a]^state.A[q.b], gh = diff&gm;
            std::array<std::map<int,std::vector<int>>,2> costs;
            auto distances = [&](int side,int x) -> const std::vector<int>& {
                auto [it,inserted] = costs[side].try_emplace(x);
                if (!inserted) return it->second;
                auto& dist = it->second;
                dist.assign(720,99);
                std::array<int,720> queue{};
                int begin=0,end=0;
                const int u = side ? q.b : q.a;
                const auto& pp=state.papers[x];
                for (int s=0; s<720; ++s) {
                    bool ok=false;
                    for (int t=0; t<=6 && !ok; ++t) {
                        const u64 cover=pp.opaque&~prefixes[s][t];
                        const u64 show=(displays[s]&~cover)|(pp.black&cover);
                        ok=!((show^state.A[u])&gh);
                    }
                    if (ok) { dist[s]=0; queue[end++]=s; }
                }
                while (begin<end) {
                    const int s=queue[begin++];
                    for (int t : pred[s]) if (dist[t]>dist[s]+1) { dist[t]=dist[s]+1; queue[end++]=t; }
                }
                assert(end==720);
                return dist;
            };
            for (int c=0; c<state.H; ++c) {
                if (diff>>state.handle[c]&1) continue;
                const u64 hh=hm&~(prefix[c]&~diff);
                double price=0,freeprice=0;
                for (int side=0; side<2; ++side) {
                    const int u=side?q.b:q.a;
                    const u64 rem=side?q.rb:q.ra;
                    std::array<double,720> best,freebest;
                    best.fill(1e6); freebest.fill(1e6);
                    for (int x=7; x<K; ++x) {
                        if (x==state.ded[q.a] || x==state.ded[q.b] || state.columns[x]==c) continue;
                        const auto& pp=state.papers[x];
                        if ((pp.black^state.A[u])&pp.opaque&(rem|hh)) continue;
                        if (residue(comp,state.A[u],rem&~pp.opaque)) continue;
                        const auto& d=distances(side,x);
                        const double credit=0.5*std::popcount(pp.opaque&hh);
                        for (int s=0; s<720; ++s) {
                            best[s]=std::min(best[s],d[s]+access_sum[x]/r+1.8-credit);
                            freebest[s]=std::min(freebest[s],d[s]+1.8-credit);
                        }
                    }
                    price+=std::accumulate(best.begin(),best.end(),0.0)/1440;
                    freeprice+=std::accumulate(freebest.begin(),freebest.end(),0.0)/1440;
                }
                q.helper_price=std::min(q.helper_price,price);
                q.free_access_price=std::min(q.free_access_price,freeprice);
            }
            stats["helper_price_sum"]+=q.helper_price;
            stats["helper_free_access_price_sum"]+=q.free_access_price;
        }
    }
    std::cout << std::setprecision(12) << "{\"stats\":{";
    bool comma = false;
    for (const auto& [key,value] : stats) { std::cout << (comma ? "," : "") << '\"' << key << "\":" << value; comma = true; }
    std::cout << "},\"errors_hist\":[";
    for (int i = 0; i < 39; ++i) std::cout << (i ? "," : "") << hist[i];
    std::cout << "],\"residual_hist\":[";
    for (int i = 0; i < 39; ++i) std::cout << (i ? "," : "") << residual_hist[i];
    std::cout << "],\"rescued\":[";
    comma = false;
    for (const auto& q : candidates) if (q.column >= 0) {
        std::cout << (comma ? "," : "") << "[" << q.a << ',' << q.b << ',' << q.errors << ',' << q.column
                  << ',' << q.donors[0].size() << ',' << q.donors[1].size() << ',' << std::popcount(q.ra)
                  << ',' << std::popcount(q.rb) << ',' << q.fee << ',' << q.helper_price << ',' << q.free_access_price << ']';
        comma = true;
    }
    std::cout << "],\"replay_examples\":[";
    for (size_t i=0; i<replay_examples.size(); ++i) {
        std::cout << (i ? "," : "") << '[';
        for (int j=0; j<7; ++j) std::cout << (j ? "," : "") << replay_examples[i][j];
        std::cout << ']';
    }
    std::cout << "],\"models\":[" << std::flush;
    if (argc >= 5 && std::stoi(argv[4]) > 0) {
        const int iterations = std::stoi(argv[4]);
        // Fixed map. The hypothetical window patch consumes no paper, works
        // in either color, and has a specified per-paired-request surcharge.
        // This is a pricing experiment, not a realizable solution.
        for (int mode = 0; mode < 10; ++mode) {
            const int allowed = mode >= 8 ? 38 : mode == 7 ? 2 : 1;
            const double fee = mode >= 8 ? 1.8 : mode == 7 ? 1.0 : std::max(0,mode-1)*0.5;
            std::map<std::pair<int,int>,double> prices = compatible_gc;
            if (mode) for (const auto& q : candidates) {
                if (mode<8 && q.errors <= allowed) prices[{q.a,q.b}] = q.gc + fee;
                if (mode>=8 && q.column>=0) prices[{q.a,q.b}] = mode==8?q.helper_price:q.free_access_price;
            }
            auto A = state.A;
            for (u64& a : A) a &= kActiveWindows;
            std::map<u64,int> index;
            for (int u = 0; u < P; ++u) index[A[u]] = u;
            auto key = [&](u64 a,u64 b) { return std::minmax(index.at(a),index.at(b)); };
            auto des = std::make_unique<Design>(A,6,state.G);
            des->handle = state.handle;
            for (int u = 0; u < P; ++u) des->hb[u] = solver.handle_bits(A[u]);
            if (!des->initialize([&](u64 a,u64 b){ return prices.contains(key(a,b)); },
                                 [&](u64 a,u64 b){ return prices.at(key(a,b)); },[](){return false;})) return 7;
            des->anneal(1e300,iterations);
            des->filler_climb(1e300,kClimbIters);
            const auto match = rematch_probability(*des,kMatchIterations,1.0,2.0);
            (void)match;
            double col=0,hole=0,generic=0;
            for (int c = 0; c < des->H; ++c) { col+=des->colcost(c); hole+=des->hcost(c); }
            int selected=0;
            for (const auto& u : des->unit) {
                generic+=des->gc(u);
                if (u.b >= 0 && !comp.compatible(A[u.a],A[u.b])) ++selected;
            }
            std::cout << (mode ? "," : "") << "{\"mode\":" << mode << ",\"allowed\":" << allowed
                      << ",\"fee\":" << fee << ",\"model\":" << (col+hole+generic)/P
                      << ",\"col\":" << col/P << ",\"hole\":" << hole/P << ",\"generic\":" << generic/P
                      << ",\"selected\":" << selected << '}' << std::flush;
        }
    }
    std::cout << "]}\n";
    return 0;
}
}
int main(int argc, char** argv) { return study::run(argc,argv); }
