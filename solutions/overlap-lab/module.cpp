#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using u64 = std::uint64_t;

static std::map<std::string, std::string> g_args;
static int g_code = 0;  // number of locked code windows (handle sub-model), 0 = plain model
static int g_zcode = -1;  // code of the generic paper K-1 (zcode=1), -1 if none
static std::string arg_s(const std::string& k, const std::string& d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : it->second;
}
static long arg_i(const std::string& k, long d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : std::atol(it->second.c_str());
}
static double arg_d(const std::string& k, double d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : std::atof(it->second.c_str());
}
static double now_sec() {
    static auto t0 = std::chrono::steady_clock::now();
    return CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
}

struct Model {
    int N = 0, K = 0, T = 0, S = 0;
    std::vector<std::uint8_t> perm;  // perm[s*K + pos] = paper at position pos (0 = top)
    std::vector<std::int32_t> succ;  // succ[(s*K + q)*K + p] = state after moving position q to p
    std::vector<u64> tg;             // targets

    static int rank_perm(const std::uint8_t* p, int K) {
        int r = 0;
        unsigned used = 0;
        for (int i = 0; i < K; i++) {
            int c = __builtin_popcount(((1u << p[i]) - 1) & ~used);
            r = r * (K - i) + c;
            used |= 1u << p[i];
        }
        return r;
    }

    void build(int n, int k) {
        N = n;
        K = k;
        S = 1;
        for (int i = 2; i <= K; i++) S *= i;
        perm.resize((size_t)S * K);
        std::vector<std::uint8_t> p(K);
        std::iota(p.begin(), p.end(), 0);
        int s = 0;
        do {
            std::copy(p.begin(), p.end(), perm.begin() + (size_t)s * K);
            s++;
        } while (std::next_permutation(p.begin(), p.end()));
        succ.resize((size_t)S * K * K);
        std::vector<std::uint8_t> q(K);
        for (int st = 0; st < S; st++) {
            const std::uint8_t* pp = &perm[(size_t)st * K];
            for (int a = 0; a < K; a++) {
                for (int b = 0; b < K; b++) {
                    if (a == b) {
                        succ[((size_t)st * K + a) * K + b] = st;
                        continue;
                    }
                    // remove position a, insert at position b
                    int m = 0;
                    std::uint8_t x = pp[a];
                    for (int i = 0; i < K; i++)
                        if (i != a) q[m++] = pp[i];
                    // q has K-1 elements; insert x at b
                    for (int i = K - 1; i > b; i--) q[i] = q[i - 1];
                    q[b] = x;
                    succ[((size_t)st * K + a) * K + b] = rank_perm(q.data(), K);
                }
            }
        }
    }
};

struct Design {
    std::vector<u64> op, bk;  // opaque and black masks per paper
    std::string str(int N) const {
        std::string out;
        for (size_t k = 0; k < op.size(); k++) {
            for (int w = 0; w < N; w++) out += (op[k] >> w & 1) ? ((bk[k] >> w & 1) ? '1' : '0') : '.';
            out += '\n';
        }
        return out;
    }
    int cell(int k, int w) const { return (op[k] >> w & 1) ? int(bk[k] >> w & 1) : 2; }
    void set(int k, int w, int v) {
        u64 b = 1ULL << w;
        op[k] &= ~b;
        bk[k] &= ~b;
        if (v == 0) op[k] |= b;
        if (v == 1) op[k] |= b, bk[k] |= b;
    }
};

struct Evaluator {
    const Model& M;
    double PEN;
    std::vector<std::uint16_t> vis;  // visible positions of each state
    std::vector<std::int16_t> tgt;   // target shown by each state, -1 if none
    std::vector<std::vector<int>> rest;
    std::vector<float> h, Th, dist;
    std::vector<int> que;
    std::vector<std::uint8_t> done;
    std::vector<std::vector<float>> F;  // F[t][s], kept only when keepF
    bool keepF = false;
    double access_probability = 0.2, generic_probability = 0.5;
    int full_patterns=0, handle_patterns=0, controls=0;
    std::vector<float> terminal;
    bool own_holes = true;
    std::vector<int> full_color;
    double g_lo = 0, g_hi = 0;
    int infeasible = 0;

    Evaluator(const Model& m, double pen) : M(m), PEN(pen), tg(m.tg) {
        full_patterns=1<<M.N;handle_patterns=1<<(M.N-1);controls=full_patterns+handle_patterns;
        vis.resize(M.S);
        tgt.resize(M.S);
        h.assign(M.S, 0.f);
        Th.assign(M.S, 0.f);
        dist.resize(M.S);
        que.resize(M.S + 8);
        done.resize(M.S);
    }

    std::vector<u64> tg;  // targets of this evaluator (M.tg unless replaced)
    int target_index(u64 d) const {
        for (int t = 0; t < M.T; t++)
            if (tg[t] == d) return t;
        return -1;
    }

    void prepare(const Design& D) {
        rest.assign(controls + M.K, {});
        const int K = M.K;
        for (int s = 0; s < M.S; ++s) {
            const auto* order = &M.perm[(size_t)s * K];
            unsigned covered = 0, display = 0, visible = 0;
            for (int i = 0; i < K; ++i) {
                int paper = order[i];
                unsigned shown = D.op[paper] & ~covered;
                if (shown) {
                    visible |= 1u << i;
                    rest[controls + paper].push_back(s);
                }
                display |= D.bk[paper] & shown;
                covered |= D.op[paper];
            }
            vis[s] = visible;
            tgt[s] = display;
            rest[display].push_back(s);
            rest[full_patterns+(display>>1)].push_back(s);
        }
        infeasible = 0;
        for(int t=0;t<int(rest.size());t++)if(t!=controls&&t!=controls+1)infeasible+=rest[t].empty();
        if (own_holes)
            for (int paper=2; paper<K; ++paper) {
                bool possible=false;
                for (int s: rest[full_color[paper]])
                    if (M.perm[(size_t)s*K]==paper) { possible=true; break; }
                infeasible += !possible;
            }
        // Reverse adjacency (CSR) of the legal moves: pred of x = states y with a move y -> x.
        pstart.assign(M.S + 1, 0);
        for (int y = 0; y < M.S; y++) {
            int c = __builtin_popcount(vis[y]) * (K - 1);
            const std::int32_t* row = &M.succ[(size_t)y * K * K];
            for (unsigned v = vis[y]; v; v &= v - 1) {
                int p = __builtin_ctz(v);
                for (int q = 0; q < K; q++)
                    if (q != p) pstart[row[p * K + q] + 1]++;
            }
            (void)c;
        }
        for (int s = 0; s < M.S; s++) pstart[s + 1] += pstart[s];
        pred.resize(pstart[M.S]);
        fillp.assign(pstart.begin(), pstart.end() - 1);
        for (int y = 0; y < M.S; y++) {
            const std::int32_t* row = &M.succ[(size_t)y * K * K];
            for (unsigned v = vis[y]; v; v &= v - 1) {
                int p = __builtin_ctz(v);
                for (int q = 0; q < K; q++)
                    if (q != p) pred[fillp[row[p * K + q]]++] = y;
            }
        }
    }
    std::vector<int> pstart, pred, fillp;

    // dist[s] = min_{s' in rest[t]} dist(s, s') + h(s') for all s.
    void propagate(std::vector<int>& src, int fixed_front = -1) {
        const float INF = 1e30f;
        std::fill(dist.begin(), dist.end(), INF);
        std::fill(done.begin(), done.end(), 0);
        std::sort(src.begin(), src.end(), [&](int a, int b) { return terminal[a] < terminal[b]; });
        for (int s : src) dist[s] = terminal[s];
        size_t si = 0;
        int qh = 0, qt = 0;
        while (si < src.size() || qh < qt) {
            int x;
            if (qh < qt && (si >= src.size() || dist[que[qh]] <= terminal[src[si]])) {
                x = que[qh++];
            } else {
                x = src[si++];
                if (dist[x] < terminal[x]) continue;  // improved through the queue
            }
            if (done[x]) continue;
            done[x] = 1;
            float L = dist[x] + 1.f;
            for (int e = pstart[x]; e < pstart[x + 1]; e++) {
                int y = pred[e];
                if (fixed_front >= 0 && M.perm[(size_t)y*M.K] != fixed_front) continue;
                if (dist[y] > L) {
                    dist[y] = L;
                    que[qt++] = y;
                }
            }
        }
    }

    void dijkstra(int t) {
        terminal = h;
        if (t < controls) { propagate(rest[t]); return; }
        const int paper = t - controls;
        if (own_holes) {
            // Phase 1: the requested paper has been lifted. Its opaque cells
            // hide the rest, but its holes still have to show the requested color.
            // Keeping it first gives exactly this visibility. The terminal cost
            // allows its eventual return at any depth, without charging that move.
            std::vector<int> source;
            for (int s : rest[full_color[paper]]) if (M.perm[(size_t)s*M.K] == paper) {
                for (int depth=0; depth<M.K; ++depth)
                    terminal[s] = std::min(terminal[s], h[M.succ[(size_t)s*M.K*M.K+depth]]);
                source.push_back(s);
            }
            propagate(source, paper);
            const auto after_lift = dist;
            // Phase 0: one may lift the requested paper for free as soon as it
            // is visible. Other preparatory moves use the full module graph.
            for (int s : rest[t]) {
                const auto* order = &M.perm[(size_t)s*M.K];
                int pos=0;
                while (order[pos]!=paper) ++pos;
                terminal[s] = after_lift[M.succ[((size_t)s*M.K+pos)*M.K]];
            }
        } else {
            for (int s : rest[t]) {
                const auto* order = &M.perm[(size_t)s*M.K];
                int pos=0;
                while (order[pos]!=paper) ++pos;
                for (int depth=0; depth<M.K; ++depth)
                    terminal[s] = std::min(terminal[s], h[M.succ[((size_t)s*M.K+pos)*M.K+depth]]);
            }
        }
        propagate(rest[t]);
    }

    // The event distribution is independent of the preceding display.
    void step() {
        std::fill(Th.begin(), Th.end(), 0.f);
        for (int t = 0; t < controls + M.K; ++t) {
            if(t==controls||t==controls+1)continue;
            const double probability=t<full_patterns?(1-access_probability)*generic_probability/full_patterns:
                t<controls?(1-access_probability)*(1-generic_probability)/handle_patterns:access_probability/(M.K-2);
            if (rest[t].empty()) {
                for (int s=0; s<M.S; ++s) Th[s] += probability*(PEN+h[s]);
                continue;
            }
            dijkstra(t);
            for (int s=0; s<M.S; ++s) Th[s] += probability*dist[s];
        }
    }

    // Relative value iteration. Returns the estimate of the average cost g (midpoint of the
    // bounds min/max over rest states of Th - h).
    double solve(int max_iter, double tol, double alpha = 1.0) {
        for (int it = 0; it < max_iter; it++) {
            step();
            double lo = 1e30, hi = -1e30;
            for (int s = 0; s < M.S; s++)
                if (tgt[s] >= 0) {
                    double d = Th[s] - h[s];
                    lo = std::min(lo, d);
                    hi = std::max(hi, d);
                }
            if (lo > hi) lo = hi = PEN;  // no rest state at all
            g_lo = lo;
            g_hi = hi;
            // normalize by the mean over rest states
            double mean = 0;
            int cnt = 0;
            for (int s = 0; s < M.S; s++)
                if (tgt[s] >= 0) mean += Th[s], cnt++;
            mean = cnt ? mean / cnt : 0;
            for (int s = 0; s < M.S; s++) h[s] = (float)((1 - alpha) * h[s] + alpha * (Th[s] - mean));
            if (hi - lo < tol) break;
        }
        return 0.5 * (g_lo + g_hi);
    }
};


int main(int argc,char** argv) {
    for(int i=1;i<argc;i++){std::string s=argv[i];auto j=s.find('=');if(j!=s.npos)g_args[s.substr(0,j)]=s.substr(j+1);}
    int H=arg_i("H",2),K=arg_i("K",2+2*H),seed=arg_i("seed",1),iterations=arg_i("iters",2000);
    double q=arg_d("q",.1),gprob=arg_d("gprob",.5),seconds=arg_d("seconds",120);
    bool triangle=arg_i("triangle",0);
    Model model;model.T=(1<<(H+1))+(1<<H)+K;model.build(H+1,K);
    Design design;design.op.resize(K);design.bk.resize(K);
    std::vector<int> full_color(K),counts(H);std::mt19937_64 rng(seed);
    for(int k=0;k<2;k++){design.op[k]=1;design.bk[k]=k;full_color[k]=k;}
    for(int k=2;k<K;k++) {
        int c=(k-2)*H/(K-2);
        full_color[k]=(rng()&((1<<(H+1))-1))&~(1<<(c+1));
        full_color[k]|=(counts[c]++&1)<<(c+1);
        design.op[k]=(1<<(c+2))-1;design.bk[k]=full_color[k]&design.op[k];
    }
    rng.seed(arg_i("search_seed",seed));
    Evaluator ev(model,1000);ev.access_probability=q;ev.generic_probability=gprob;ev.full_color=full_color;
    ev.prepare(design);double baseline=ev.solve(300,1e-5,.6),baseline_lo=ev.g_lo,baseline_hi=ev.g_hi;
    double current=baseline,best=baseline;Design best_design=design;
    std::vector<int> chain(H);for(int i=0;i<H;i++)chain[i]=(1<<(i+2))-1;
    double start=now_sec();int completed=0,accepted=0;
    std::cerr<<"baseline "<<baseline<<" gap "<<ev.g_hi-ev.g_lo<<'\n';
    for(int it=0;it<iterations;it++) {
        double progress=std::max(double(it)/iterations,(now_sec()-start)/seconds);if(progress>=1)break;
        Design proposal=design;auto next_chain=chain;
        if(triangle) {
            if(rng()%8==0) {
                int a=1+rng()%H,b=1+rng()%H;
                auto swap=[&](unsigned mask){bool change=((mask>>a)^(mask>>b))&1;return mask^(unsigned(change)<<a)^(unsigned(change)<<b);};
                for(int& c:next_chain)c=swap(c);for(int k=2;k<K;k++)proposal.op[k]=swap(proposal.op[k]);
            }else proposal.op[2+rng()%(K-2)]=chain[rng()%H];
        } else {
            int k=rng()%K,j=rng()%(H+1);
            if(k<2)proposal.set(k,j,rng()%3);
            else proposal.op[k]^=1ULL<<j;
        }
        for(int k=2;k<K;k++)proposal.bk[k]=full_color[k]&proposal.op[k];
        auto old_h=ev.h;ev.prepare(proposal);if(ev.infeasible){ev.h=std::move(old_h);continue;}
        double value=ev.solve(10,2e-4,.6);if(ev.g_hi-ev.g_lo>.002)value=ev.solve(60,2e-4,.6);
        double temp=.025*std::pow(.008,progress),coin=(rng()>>11)*0x1.0p-53;
        if(value<current||coin<std::exp((current-value)/temp)) {
            design=std::move(proposal);chain=std::move(next_chain);current=value;accepted++;
            if(value<best-.0002){value=ev.solve(200,1e-5,.6);current=value;if(value<best){best=value;best_design=design;std::cerr<<"best "<<it<<' '<<best<<" elapsed "<<now_sec()-start<<'\n';}}
        } else ev.h=std::move(old_h);
        completed=it+1;
    }
    ev.prepare(best_design);std::fill(ev.h.begin(),ev.h.end(),0);best=ev.solve(400,1e-5,.6);
    std::cout<<"{\"H\":"<<H<<",\"K\":"<<K<<",\"seed\":"<<seed<<",\"triangle\":"<<triangle<<",\"q\":"<<q<<",\"gprob\":"<<gprob
        <<",\"baseline\":"<<baseline<<",\"baseline_lo\":"<<baseline_lo<<",\"baseline_hi\":"<<baseline_hi<<",\"best\":"<<best<<",\"best_lo\":"<<ev.g_lo<<",\"best_hi\":"<<ev.g_hi
        <<",\"iterations\":"<<completed<<",\"accepted\":"<<accepted<<",\"elapsed\":"<<now_sec()-start<<",\"colors\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<full_color[k];std::cout<<"],\"opaque\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.op[k];std::cout<<"],\"black\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.bk[k];std::cout<<"]}\n";
}
