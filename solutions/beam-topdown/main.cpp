// AHC074: top-down residual-cover beam construction (standalone experiment).
// No code from esw-clean.cpp is used. Only the initial catalogue is read during design.
//
// Column c has a visible handle at bit c; every paper in it is transparent above c.
// Each column contains both handle colours. This gives a zero-error legal baseline
// even when the thresholded cover construction leaves some target bits uncovered.
//
// Construction has an outer beam over paper prefixes and an inner beam over
// compatible groups of residual target patterns. A target contributes only if the
// new paper fills at least tau(c) bits, or completes its entire residual pattern.
// Remaining bits at execution time are set by legal column-head rotations.
//
// Environment variables (all optional) are described in README.md.
// Compile: g++ -O3 -march=native -std=c++20 topdown_beam.cpp -o topdown_beam
#include <bits/stdc++.h>
using namespace std;
using U=uint64_t;
U low(int n) {
    return n>=64?~0ULL:((1ULL<<n)-1);
}
int pc(U x) {
    return __builtin_popcountll(x);
}
int ei(const char*s, int d) {
    auto v=getenv(s);
    return v?atoi(v):d;
}
double ed(const char*s, double d) {
    auto v=getenv(s);
    return v?atof(v):d;
}

struct Bits {
    array<U, 4>a {};
    bool operator==(const Bits&o)const {
        return a==o.a;
    }
    void add(int x) {
        a[x>>6]|=1ULL<<(x&63);
    }
    int size()const {
        return pc(a[0])+pc(a[1])+pc(a[2])+pc(a[3]);
    }
};

struct BH {
    size_t operator()(const Bits&x)const {
        U h=1234567;
        for(U w:x.a) {
            h^=w+0x9e3779b97f4a7c15ULL+(h<<6)+(h>>2);
        }
        return h;
    }
};

struct Paper {
    // o: opaque mask; b: black mask; c: storage column; ts: accepted targets.
    U o, b;
    int c;
    vector<int> ts;
};

struct Cand {
    Bits t;
    U o=0, b=0;
    double score=0, rank=0;
    int gain=0, support=0;
};

struct Build {
    array<U, 256>A, rem;
    array<array<Bits, 2>, 64> need;
    U mainmask, workmask;
    int H, G, BW, DEP;
    double PEN, BON, REL, MBON;
    int branch_limit;
    bool prune;
    vector<Cand> alts;
    vector<Paper> papers;
    array<vector<int>, 256> recipe;
    int threshold;
    bool finalcol=false;
    U allowed;
    Bits viable;
    Build(array<U, 256>a):A(a), rem(a) {
        H=64;
        G=0;
        mainmask=0;
        workmask=~0ULL;
        rem.fill(~0ULL);
        BW=ei("BW", 12);
        DEP=ei("DEP", 18);
        REL=ed("RELAX", 0.2);
        branch_limit=ei("BRANCH", 4);
        prune=ei("PRUNE", 0);
        MBON=0;
        PEN=ed("PEN", 6);
        BON=ed("BON", 5);
    }
    void offer(const Cand&q) {
        if(!q.support)return;
        int cap=branch_limit;
        if((int)alts.size()>=cap && q.score<=alts.back().score)return;
        for(auto &r:alts)if(r.o==q.o&&r.b==q.b)return;
        alts.push_back(q);
        for(int i=(int)alts.size()-1;i>0&&alts[i].score>alts[i-1].score;i--)swap(alts[i], alts[i-1]);
        if((int)alts.size()>cap)alts.pop_back();
    }
    // Close a compatible target group: a bit can be printed unless both colours
    // are demanded there by unfinished targets in the group. Filled bits are wildcards.
    Cand eval(Bits t) {
        Cand q;
        for(int iteration=0;;iteration++) {
            q= {};
            q.t=t;
            U z=0, o=0;
            for(int w=0;w<4;w++)for(U u=t.a[w];u;u&=u-1) {
                int i=w*64+__builtin_ctzll(u);
                z|=rem[i]&~A[i];
                o|=rem[i]&A[i];
            }
            q.o=allowed&~(z&o);
            q.b=q.o&o;
            Bits core;
            for(int w=0;w<4;w++)for(U u=t.a[w];u;u&=u-1) {
                int i=w*64+__builtin_ctzll(u), g=pc(q.o&rem[i]);
                bool complete=!(rem[i]&workmask&~q.o);
                double v=g-PEN+BON*complete+MBON*((rem[i]&mainmask)&&!(rem[i]&mainmask&~q.o));
                if((g>=threshold&&!finalcol)||complete) {
                    q.score+=v;
                    q.gain+=g;
                    q.support++;
                    core.add(i);
                }
                q.rank+= ((g>=threshold&&!finalcol)||complete)?v:REL*g;
            }
            if(!prune||!q.support||core==t||iteration>=8)break;
            t=core;
        }
        return q;
    }
    // Inner beam: split a residual-target group by one additional colour constraint.
    // Single-target seeds also make highly specialized late papers available.
    Cand choose(int col, const array<bool, 256>&used, int force=-1) {
        alts.clear();
        finalcol=false;
        allowed=low(G+col+1);
        viable= {};
        need= {};
        for(int i=0;i<256;i++) {
            if(used[i]||!(rem[i]&workmask))continue;
            U r=rem[i]&allowed;
            int g=pc(r);
            if(g<threshold && (rem[i]&workmask&~allowed))continue;
            viable.add(i);
            for(U x=r;x;x&=x-1) {
                int j=__builtin_ctzll(x);
                need[j][A[i]>>j&1].add(i);
            }
        }
        vector<Cand> beam;
        Cand best;
        int handle=G+col;
        for(int i=0;i<256;i++) if((viable.a[i>>6]>>(i&63)&1) && (force<0 || int(A[i]>>handle&1)==force)) {
            Bits t;
            t.add(i);
            Cand r=eval(t);
            r.o|=1ULL<<handle;
            r.b=(r.b&~(1ULL<<handle))|(A[i]&(1ULL<<handle));
            if(r.score>best.score)best=r;
            offer(r);
        }
        for(int c=0;c<2;c++) {
            if(force>=0&&c!=force)continue;
            Bits t=viable;
            for(int w=0;w<4;w++)t.a[w]&=~need[handle][c^1].a[w];
            if(!t.size())continue;
            Cand q=eval(t);
            q.o|=1ULL<<handle;
            q.b=(q.b&~(1ULL<<handle))|(U(c)<<handle);
            beam.push_back(q);
            if(q.score>best.score)best=q;
            offer(q);
        }
        for(int dep=0;dep<DEP;dep++) {
            vector<Cand> next;
            unordered_set<Bits, BH> seen;
            for(auto&q:beam) {
                if(q.t.size()<=1)continue;
                U todo=allowed&~q.o;
                for(U x=todo;x;x&=x-1) {
                    int j=__builtin_ctzll(x);
                    for(int c=0;c<2;c++) {
                        Bits t=q.t;
                        for(int w=0;w<4;w++)t.a[w]&=~need[j][c^1].a[w];
                        if(!t.size()||!seen.insert(t).second)continue;
                        Cand r=eval(t);
                        // preserve forced handle's color even when no row constrains it
                        r.o|=1ULL<<handle;
                        r.b=(r.b&~(1ULL<<handle))|(q.b&(1ULL<<handle));
                        if(r.score>best.score)best=r;
                        offer(r);
                        next.push_back(r);
                    }
                }
            }
            if(next.empty())break;
            sort(next.begin(), next.end(), [](const Cand&a, const Cand&b) {
                return a.rank>b.rank;
            });
            if(next.size()>(size_t)BW)next.resize(BW);
            beam=move(next);
        }
        sort(alts.begin(), alts.end(), [](auto&a, auto&b) {
            return a.score>b.score;
        });
        vector<Cand> top;
        set<pair<U, U>> seen;
        for(auto&q:alts) {
            if(seen.insert( {
                q.o, q.b
            }).second) {
                top.push_back(q);
                if((int)top.size()>=branch_limit)break;
            }
        }
        alts=move(top);
        return best;
    }
};

// ----- Outer beam over the sequence of designed papers -----

struct DNode {
    array<U, 256> rem;
    array<vector<int>, 256> recipe;
    vector<Paper> papers;
    array<bool, 256> used {};
    array<int, 2> colors {};
    double key=0;
    U hash=0;
};

// The outer beam retains alternative complete prefixes of the paper sequence.
// One target uses at most one constructed paper in each column. Both handle colours
// are reserved in every column, independently of the residual-cover objective.
void construct_outer(Build&b) {
    int width=max(1, ei("OUTER", 2));
    DNode init;
    init.rem.fill(~0ULL);
    vector<DNode> beam(1, init);
    int made=0;
    double basebonus=b.MBON;
    for(int c=0;c<b.H;c++) {
        int cap=clamp(int(round(192*pow(double(c+1)/b.H, ed("SHAPE", 2.5))))-made, 2, 192-made-2*(b.H-1-c));
        for(auto&n:beam)n.used= {}, n.colors= {};
        b.threshold=int(round(ed("T0", 5)+(ed("T1", 20)-ed("T0", 5))*pow(double(c)/max(1, b.H-1), ed("TPOW", 1))));
        for(int step=0;step<cap;step++) {
            b.MBON=0;
            vector<DNode> next;
            for(auto&n:beam) {
                b.rem=n.rem;
                int forced=-1;
                if(step==cap-1&&(!n.colors[0]||!n.colors[1]))forced=n.colors[0]?1:0;
                b.choose(c, n.used, forced);
                auto candidates=b.alts;
                if(candidates.empty()) {
                    Cand q;
                    int cl=forced<0?step%2:forced;
                    q.o=1ULL<<(b.G+c);
                    q.b=U(cl)<<(b.G+c);
                    candidates.push_back(q);
                }
                for(auto q:candidates) {
                    U constrained=0;
                    array<int, 64> cnt {};
                    int nt=0;
                    for(int w=0;w<4;w++)for(U u=q.t.a[w];u;u&=u-1) {
                        int i=64*w+__builtin_ctzll(u);
                        constrained|=n.rem[i];
                        nt++;
                        for(U x=b.A[i];x;x&=x-1)cnt[__builtin_ctzll(x)]++;
                    }
                    for(U x=q.o&~constrained&~(1ULL<<(b.G+c));x;x&=x-1) {
                        int j=__builtin_ctzll(x);
                        if(cnt[j]*2>=nt)q.b|=1ULL<<j;
                    }
                    DNode v=n;
                    v.colors[q.b>>(b.G+c)&1]++;
                    Paper paper {
                        q.o, q.b, c, {}
                    };
                    for(int i=0;i<256;i++) {
                        if(v.used[i]||!v.rem[i]||((q.b^b.A[i])&q.o&v.rem[i]))continue;
                        int g=pc(q.o&v.rem[i]);
                        if(g<b.threshold && (v.rem[i]&~q.o))continue;
                        paper.ts.push_back(i);
                        v.used[i]=true;
                        v.rem[i]&=~q.o;
                        v.recipe[i].push_back(made);
                    }
                    v.papers.push_back(paper);
                    v.key=0;
                    v.hash=0x123456789ULL;
                    for(int i=0;i<256;i++) {
                        v.key+=pc(v.rem[i])+b.PEN*v.recipe[i].size()+b.MBON*bool(v.rem[i]&b.mainmask)+b.BON*bool(v.rem[i]);
                        U x=v.rem[i]^(U(v.used[i])<<31);
                        v.hash^=x+0x9e3779b97f4a7c15ULL+(v.hash<<6)+(v.hash>>2);
                    }
                    next.push_back(move(v));
                }
            }
            sort(next.begin(), next.end(), [](auto&a, auto&b) {
                return a.key<b.key;
            });
            beam.clear();
            unordered_set<U> seen;
            for(auto&n:next)if(seen.insert(n.hash).second) {
                beam.push_back(move(n));
                if((int)beam.size()==width)break;
            }
            made++;
        }
        int bits=0, mainleft=0;
        for(U r:beam[0].rem)bits+=pc(r), mainleft+=bool(r&b.mainmask);
        if(ei("VERBOSE", 0))cerr<<"outer col "<<c<<" papers "<<made<<" bits "<<bits<<" mainleft "<<mainleft<<"\n";
    }
    b.rem=beam[0].rem;
    b.papers=move(beam[0].papers);
    b.recipe=move(beam[0].recipe);
}

// ----- Catalogue-only searches for short compatible front stacks -----

struct Path {
    vector<int> v;
    U rem=~0ULL, cols=0;
    double cost=0, key=0;
};

// These paths are partial front stacks, not complete target realizations. Holes
// are deliberately allowed: the reactive interval planner and column heads fill them.
struct Search {
    Build& b;
    int width=ei("QBW", 32), length=ei("QLEN", 6), nalt=ei("QALT", 10);
    double mainweight=ed("MAINW", 0.6), handleweight=ed("HANDLEW", 0.35);
    array<vector<Path>, 256> paths;
    vector<double> freq;
    vector<int> colsizes;
    vector<double> ecost;
    Search(Build&bb):b(bb) {
        freq.assign(192, 0);
        colsizes.assign(b.H, 0);
        ecost.assign(192, 0);
        for(auto&p:b.papers)colsizes[p.c]++;
        for(auto&r:b.recipe)for(int k:r)freq[k]++;
        costs();
        for(int i=0;i<256;i++)gen(i);
        for(int it=0;it<ei("QITER", 1);it++) {
            freq.assign(192, 0);
            for(auto &ps:paths)if(!ps.empty())for(int k:ps[0].v)freq[k]++;
            costs();
            for(int i=0;i<256;i++)gen(i);
        }
    }
    void costs() {
        for(int c=0;c<b.H;c++) {
            vector<int> ks;
            for(int k=0;k<192;k++)if(b.papers[k].c==c)ks.push_back(k);
            stable_sort(ks.begin(), ks.end(), [&](int x, int y) {
                return freq[x]>freq[y];
            });
            for(int rank=0;rank<(int)ks.size();rank++)ecost[ks[rank]]=ed("LIFT", 1.7)+ed("DIG", 0.65)*rank;
        }
    }
    double rank(const Path&p)const {
        return p.cost+mainweight*pc(p.rem&b.mainmask)+handleweight*pc(p.rem&~b.mainmask);
    }
    bool validpath(int t, Path &p) {
        U r=~0ULL, cols=0;
        p.cost=0;
        for(int k:p.v) {
            auto q=b.papers[k];
            if(cols>>q.c&1 || ((q.b^b.A[t])&q.o&r))return false;
            cols|=1ULL<<q.c;
            r&=~q.o;
            p.cost+=ecost[k];
        }
        p.rem=r;
        p.cols=cols;
        p.key=rank(p);
        return !(r&b.mainmask);
    }
    void add(int t, Path p) {
        if(p.rem&b.mainmask)return;
        for(auto&q:paths[t])if(q.v==p.v)return;
        p.key=rank(p);
        paths[t].push_back(p);
        sort(paths[t].begin(), paths[t].end(), [](auto&a, auto&b) {
            return a.key<b.key;
        });
        if(paths[t].size()>(size_t)nalt)paths[t].resize(nalt);
    }
    void gen(int t) {
        auto old=paths[t];
        paths[t].clear();
        for(auto p:old)if(validpath(t, p))add(t, p);
        Path original;
        original.v=b.recipe[t];
        if(validpath(t, original)) {
            add(t, original);
            // all valid ordered subsequences for short paths
            int m=original.v.size();
            if(m<=16) {
                for(int mask=0;mask<(1<<m);mask++) {
                    Path p;
                    for(int j=0;j<m;j++)if(mask>>j&1)p.v.push_back(original.v[j]);
                    if(validpath(t, p))add(t, p);
                }
            }
        }
        vector<Path> beam(1);
        if(!b.mainmask)add(t, beam[0]);
        array<U, 192> bad;
        for(int k=0;k<192;k++)bad[k]=(b.papers[k].b^b.A[t])&b.papers[k].o;
        for(int dep=0;dep<length;dep++) {
            vector<Path> next;
            unordered_map<U, double> seen;
            for(auto&p:beam)for(int k=0;k<192;k++) {
                auto q=b.papers[k];
                if((p.cols>>q.c&1)|| (p.rem&bad[k]) || !(p.rem&q.o))continue;
                Path v=p;
                v.rem&=~q.o;
                v.cols|=1ULL<<q.c;
                v.cost+=ecost[k];
                auto it=seen.find(v.rem);
                if(it!=seen.end()&&it->second<=v.cost)continue;
                seen[v.rem]=v.cost;
                v.v.push_back(k);
                v.key=rank(v);
                if(!(v.rem&b.mainmask))add(t, v);
                next.push_back(move(v));
            }
            if(next.empty())break;
            sort(next.begin(), next.end(), [](auto&a, auto&b) {
                return a.key<b.key;
            });
            beam.clear();
            unordered_set<U> used;
            for(auto&p:next)if(used.insert(p.rem).second) {
                beam.push_back(move(p));
                if((int)beam.size()==width)break;
            }
        }
    }
};

// ----- Reactive execution, interval patches, and checked move deletion -----

struct IntervalRuntime {
    Build& b;
    Search* search=nullptr;
    array<int, 192> order {};
    array<bool, 192> extra {};
    vector<pair<int, int>> ops;
    vector<int> tags;
    int tag=0;
    array<double, 192> demand {};
    array<array<double, 2>, 64> need {};
    int targetid=-1;
    long long shortened=0;
    IntervalRuntime(Build&bb):b(bb) {
        iota(order.begin(), order.end(), 0);
        assert(b.G==0);
        for(auto &x:need)x= {
            .25, .25
        };
        array<double, 192>utility {};
        array<double, 64>sums {};
        array<int, 64>nc {};
        for(int k=0;k<192;k++) {
            auto p=b.papers[k];
            for(U a:b.A) {
                U bad=(a^p.b)&p.o;
                int lo=bad?64-__builtin_clzll(bad):0;
                utility[k]+=max(0., pc(p.o&~low(lo))-ed("UTILITY_BASE", 2.5));
            }
            sums[p.c]+=utility[k];
            nc[p.c]++;
        }
        for(int k=0;k<192;k++) {
            int c=b.papers[k].c;
            demand[k]=ed("DEMAND", .03)*(1+ed("UTILITY", 1)*(sums[c]?utility[k]*nc[c]/sums[c]-1:0));
        }
    }
    int pos(int k)const {
        for(int j=0;j<192;j++)if(order[j]==k)return j;
        return -1;
    }
    U display()const {
        U cov=0, v=0;
        for(int k:order) {
            v|=b.papers[k].b&~cov;
            cov|=b.papers[k].o;
        }
        return v;
    }
    bool visible(int k)const {
        U r=b.papers[k].o;
        for(int x:order) {
            if(x==k)return r!=0;
            r&=~b.papers[x].o;
        }
        return false;
    }
    void shift(int k, int from, int d) {
        if(from<d)move(order.begin()+from+1, order.begin()+d+1, order.begin()+from);
        else move_backward(order.begin()+d, order.begin()+from, order.begin()+from+1);
        order[d]=k;
    }
    void move_(int k, int d) {
        int from=pos(k);
        if(from==d)return;
        if(!visible(k))throw runtime_error("invisible");
        shift(k, from, d);
        ops.emplace_back(k, d);
        tags.push_back(tag);
    }
    int head(int c)const {
        for(int k:order)if(!extra[k]&&b.papers[k].c==c)return k;
        return -1;
    }
    void insert_col(int k, int barrier=-1, bool now=false) {
        int c=b.papers[k].c;
        vector<int>v;
        for(int x:order)if(x!=k&&!extra[x]&&b.papers[x].c==c)v.push_back(x);
        int lo=barrier<0?0:int(find(v.begin(), v.end(), barrier)-v.begin())+1;
        int gap=v.size();
        double best=1e99;
        for(int g=lo;g<=(int)v.size();g++) {
            vector<int>w=v;
            w.insert(w.begin()+g, k);
            array<int, 2>fc {
                999, 999
            };
            double val=0;
            for(int j=0;j<(int)w.size();j++) {
                int x=w[j], cl=b.papers[x].b>>c&1;
                fc[cl]=min(fc[cl], j);
                val+=demand[x]*j;
            }
            for(int cl=0;cl<2;cl++)if(fc[cl]<999)val+=need[c][cl]*fc[cl];
            if(now&&targetid>=0) {
                int cl=b.A[targetid]>>c&1;
                val+=ed("NOW", 1)*fc[cl];
            }
            val+=1e-9*(w.size()-g);
            if(val<best)best=val, gap=g;
        }
        int d;
        if(gap<(int)v.size()) {
            d=pos(v[gap]);
            d-=pos(k)<d;
        } else if(v.size()) {
            d=pos(v.back())+1;
            d-=pos(k)<d;
        } else {
            d=0;
            for(int x:order)if(x!=k&&!extra[x]&&b.papers[x].c<c)d=pos(x)+1;
            d-=pos(k)<d;
        }
        move_(k, d);
        extra[k]=false;
    }
    void clear() {
        auto old=order;
        for(int k:old)if(extra[k]) {
            tag=0;
            insert_col(k, -1, true);
        }
    }
    struct Option {
        int lo=0, hi=0, paper=-1;
        double gain=0;
    };
    void run(int t, double charge, int depthlimit, int kind=0, const Path* front=nullptr) {
        targetid=t;
        ops.clear();
        tags.clear();
        clear();
        U target=b.A[t];
        U unfilled=~0ULL;
        if(front) {
            vector<int>todo=front->v;
            sort(todo.begin(), todo.end(), [&](int x, int y) {
                return b.papers[x].c<b.papers[y].c;
            });
            for(int k:todo) {
                int c=b.papers[k].c;
                while(head(c)!=k) {
                    tag=1;
                    insert_col(head(c), k);
                }
                int rank=find(front->v.begin(), front->v.end(), k)-front->v.begin(), d=0;
                for(int j=0;j<rank;j++)if(extra[front->v[j]])d=max(d, pos(front->v[j])+1);
                tag=2;
                move_(k, d);
                extra[k]=true;
            }
            unfilled=front->rem;
        }
        array<vector<int>, 64>col;
        for(int k:order)if(!extra[k])col[b.papers[k].c].push_back(k);
        array<int, 64>fix {};
        for(int c=0;c<64;c++)if(unfilled>>c&1) {
            for(int k:col[c]) {
                if(((b.papers[k].b^target)>>c&1)==0)break;
                fix[c]++;
            }
        }
        array<vector<Option>, 64>choices;
        if(kind!=1)for(int c=0;c<64;c++)if(unfilled>>c&1)for(int d=0;d<(int)col[c].size()&&d<=depthlimit;d++) {
            int k=col[c][d];
            auto p=b.papers[k];
            U wrong=(p.b^target)&p.o&unfilled;
            int lo=wrong?64-__builtin_clzll(wrong):0;
            if(lo>c)continue;
            int saved=0;
            for(U x=p.o&~low(lo);x;x&=x-1)saved+=fix[__builtin_ctzll(x)];
            for(int l=lo;l<=c;l++) {
                if(l==lo||(p.o>>l&1)) {
                    double gain=saved-d-1-charge;
                    if(gain>0)choices[c].push_back( {
                        l, c, k, gain
                    });
                }
                if(p.o>>l&1)saved-=fix[l];
            }
        }
        array<double, 65>dp {};
        array<Option, 65>chosen;
        for(int j=0;j<65;j++)chosen[j].paper=-1;
        for(int c=0;c<64;c++) {
            dp[c+1]=dp[c];
            for(auto opt:choices[c])if(dp[opt.lo]+opt.gain>dp[c+1]+1e-9) {
                dp[c+1]=dp[opt.lo]+opt.gain;
                chosen[c+1]=opt;
            }
        }
        vector<Option> selected;
        for(int j=64;j>0;)if(chosen[j].paper<0)j--;
        else {
            selected.push_back(chosen[j]);
            j=chosen[j].lo;
        }
        reverse(selected.begin(), selected.end());
        U covered=0;
        for(auto opt:selected) {
            int k=opt.paper, c=opt.hi;
            while(head(c)!=k) {
                tag=1;
                insert_col(head(c), k);
            }
            int anchor=-1;
            for(int x:order)if(!extra[x]&&b.papers[x].c>=opt.lo) {
                anchor=x;
                break;
            }
            int d=anchor<0?192:pos(anchor);
            d-=pos(k)<d;
            tag=2;
            move_(k, d);
            extra[k]=true;
            covered|=b.papers[k].o&~low(opt.lo);
        }
        for(int c=0;c<64;c++)if((unfilled&~covered)>>c&1) {
            int barrier=-1;
            for(int k:order)if(!extra[k]&&b.papers[k].c==c&&((b.papers[k].b^target)>>c&1)==0) {
                barrier=k;
                break;
            }
            if(barrier<0)throw runtime_error("no color");
            while(head(c)!=barrier) {
                tag=3;
                insert_col(head(c), barrier);
            }
        }
        if(display()!=target)throw runtime_error("mismatch");
    }
    double future()const {
        array<int, 64>dep {};
        array<array<int, 2>, 64>fc;
        for(auto&x:fc)x= {
            999, 999
        };
        double v=0;
        for(int k:order)if(!extra[k]) {
            int c=b.papers[k].c;
            v+=demand[k]*dep[c];
            int cl=b.papers[k].b>>c&1;
            fc[c][cl]=min(fc[c][cl], dep[c]);
            dep[c]++;
        }
        for(int c=0;c<64;c++)for(int cl=0;cl<2;cl++)if(fc[c][cl]<999)v+=need[c][cl]*fc[c][cl];
        return v;
    }
    double score()const {
        int n=accumulate(extra.begin(), extra.end(), 0);
        return ops.size()+ed("EXTRA", .65)*n+ed("FUT", .7)*future();
    }
    // Recognize moved-up papers after a replay edit. The non-extra subsequence
    // stays in nondecreasing column order, with at least one paper in every column.
    bool canonical() {
        extra.fill(false);
        int c=63;
        array<int, 64>n {};
        for(int i=191;i>=0;i--) {
            int x=order[i], d=b.papers[x].c;
            if(d>c)extra[x]=true;
            else c=d, n[d]++;
        }
        for(int j=0;j<64;j++)if(!n[j])return false;
        return true;
    }
    bool replay(const array<int, 192>&start, const vector<pair<int, int>>& edits, const vector<int>&etags, int skip) {
        order=start;
        ops.clear();
        tags.clear();
        for(int j=0;j<(int)edits.size();j++)if(j!=skip) {
            auto[k, anchor]=edits[j];
            int from=pos(k), d=anchor<0?0:pos(anchor)+1;
            if(from<d)d--;
            if(from==d)continue;
            if(!visible(k))return false;
            shift(k, from, d);
            ops.emplace_back(k, d);
            tags.push_back(etags[j]);
        }
        if(display()!=b.A[targetid])return false;
        return canonical();
    }
    vector<pair<int, int>> anchors(const array<int, 192>&start, const vector<pair<int, int>>&moves) {
        auto saved=order;
        order=start;
        vector<pair<int, int>>ed;
        for(auto[k, d]:moves) {
            shift(k, pos(k), d);
            ed.emplace_back(k, d?order[d-1]:-1);
        }
        order=saved;
        return ed;
    }
    // Every accepted deletion is replayed from the actual incoming stack, with
    // visibility checked before each move and the final 64-bit display checked exactly.
    void process(int t) {
        auto start=order;
        auto prevextra=extra;
        double best=1e99;
        array<int, 192>bo;
        array<bool, 192>be;
        vector<pair<int, int>>bm;
        vector<int>bt;
        targetid=t;
        vector<pair<double, const Path*>> plans= {
            {
                0., nullptr
            }, {
                .7, nullptr
            }, {
                1.4, nullptr
            }
        };
        if(search)for(auto &p:search->paths[t])plans.push_back( {
            .7, &p
        });
        for(auto[pen, path]:plans) {
            order=start;
            extra=prevextra;
            run(t, pen, ei("DEPTH", 4), 0, path);
            double v=score();
            if(v<best) {
                best=v;
                bo=order;
                be=extra;
                bm=ops;
                bt=tags;
            }
        }
        order=bo;
        extra=be;
        ops=bm;
        tags=bt;
        if(ei("POST", 1)) {
            bool changed=true;
            while(changed) {
                changed=false;
                auto ed=anchors(start, bm);
                for(int j=0;j<(int)ed.size();j++) {
                    if(replay(start, ed, bt, j)) {
                        double v=score();
                        if(v<best-1e-9) {
                            shortened+=bm.size()-ops.size();
                            best=v;
                            bo=order;
                            be=extra;
                            bm=ops;
                            bt=tags;
                            changed=true;
                            break;
                        }
                    }
                }
            }
        }
        order=bo;
        extra=be;
        ops=bm;
        tags=bt;
        if(display()!=b.A[t])throw runtime_error("final mismatch");
        if(ops.size()>384)throw runtime_error("max moves");
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    auto start=chrono::steady_clock::now();
    int n, k, p, r;
    if(!(cin>>n>>k>>p>>r))return 0;
    if(n!=64||k!=192||p!=256||r!=1024) {
        cerr<<"Unsupported dimensions\n";
        return 1;
    }
    array<U, 256>a;
    for(int i=0;i<256;i++) {
        string s;
        cin>>s;
        U x=0;
        for(int j=0;j<64;j++)x|=U(s[j]=='1')<<j;
        a[i]=x;
    }
    const double t0=ed("T0",5), t1=ed("T1",20), shape=ed("SHAPE",2.5), power=ed("TPOW",1);
    if(!isfinite(t0)||!isfinite(t1)||t0<1||t1<t0||t1>64||!isfinite(shape)||shape<=0||!isfinite(power)||power<=0||ei("BW",12)<1||ei("DEP",18)<1||ei("BRANCH",4)<1||ei("QBW",32)<1||ei("QLEN",6)<1||ei("QALT",10)<1) {
        cerr<<"Invalid search configuration\n";
        return 1;
    }
    Build b(a);
    construct_outer(b);
    if(b.papers.size()!=192)throw runtime_error("wrong paper count");
    array<array<bool, 2>, 64> colors {};
    for(auto q:b.papers) {
        if(!(q.o>>q.c&1)||(q.o&~low(q.c+1)))throw runtime_error("invalid staircase");
        colors[q.c][q.b>>q.c&1]=true;
    }
    for(auto q:colors)if(!q[0]||!q[1])throw runtime_error("missing handle color");
    if(const char* path=getenv("PROFILE")) {
        ofstream f(path);
        f<<"paper,column,opaque_bits,contributors,new_bits,threshold\n";
        array<U, 256> rem;
        rem.fill(~0ULL);
        for(int id=0;id<192;id++) {
            auto q=b.papers[id];
            int gain=0;
            for(int t:q.ts) {
                gain+=pc(rem[t]&q.o);
                rem[t]&=~q.o;
            }
            int th=int(round(ed("T0", 5)+(ed("T1", 20)-ed("T0", 5))*pow(q.c/63., ed("TPOW", 1))));
            f<<id<<','<<q.c<<','<<pc(q.o)<<','<<q.ts.size()<<','<<gain<<','<<th<<'\n';
        }
    }
    IntervalRuntime runtime(b);
    Search search(b);
    if(ei("FRONT", 1))runtime.search=&search;
    double ds=chrono::duration<double>(chrono::steady_clock::now()-start).count();
    for(auto&q:b.papers) {
        string s(64, '.');
        for(int j=0;j<64;j++)if(q.o>>j&1)s[j]=q.b>>j&1?'1':'0';
        cout<<s<<'\n';
    }
    cout.flush();
    long long total=0;
    int maxm=0;
    array<long long, 4>cnt {};
    for(int it=0;it<r;it++) {
        int t;
        if(!(cin>>t)||t<0)return 0;
        runtime.process(t);
        total+=runtime.ops.size();
        maxm=max(maxm, int(runtime.ops.size()));
        cout<<runtime.ops.size()<<'\n';
        for(auto[k, d]:runtime.ops)cout<<k<<' '<<d<<'\n';
        for(int tag:runtime.tags)cnt[tag]++;
        cout.flush();
    }
    double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();
    cerr<<"RESULT {\"moves\":"<<total<<",\"avg\":"<<total/double(r)<<",\"max\":"<<maxm<<",\"design_sec\":"<<ds<<",\"sec\":"<<sec<<",\"ret\":"<<cnt[0]<<",\"dig\":"<<cnt[1]<<",\"lift\":"<<cnt[2]<<",\"fix\":"<<cnt[3]<<",\"shortened\":"<<runtime.shortened<<"}\n";
}
