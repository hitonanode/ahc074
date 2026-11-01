// Internal correctness fixture, not a scoring run or a submitted solution.
#define LATTICE_CHECK
#define main frontier_lattice_submission_main
#include "main.cpp"
#undef main

int main() {
    int n,k,p,r;
    std::cin >> n >> k >> p >> r;
    std::vector<u64> A(p);
    for (auto& a : A) {
        std::string s; std::cin >> s;
        for (int j=0;j<n;j++) if(s[j]=='1') a |= 1ULL<<j;
    }
    std::mt19937_64 rng(779879);
    Comparator c; c.init(6,36,rng); c.build_tables();
    std::vector<bool> used(p,false);
    std::vector<std::pair<int,int>> pairs;
    for(int a=0;a<p&&pairs.size()<10;a++)
        for(int b=a+1;b<p&&pairs.size()<10;b++)
            if(!used[a]&&!used[b]&&c.compatible(A[a],A[b])) {
                pairs.emplace_back(a,b);used[a]=used[b]=true;
            }
    auto stats=refine_lattice(c,A,pairs,1e9,5000);
    assert(stats.after<=stats.before);
    assert(stats.accepted>0);
    for(auto[a,b]:pairs)assert(c.compatible(A[a],A[b]));
    std::cout << "refine_pairs = " << pairs.size() << " accepted = " << stats.accepted
              << " four = " << stats.nonlinear_windows << " before = " << stats.before
              << " after = " << stats.after << '\n';

    // Independently install one balanced four-paper window while retaining one exact
    // comparison window for every edge. This exercises the nonlinear decoder even
    // when the learned fixed-pair refinement happens to choose only two-paper rules.
    Comparator q; q.init(6,36,rng); q.build_tables();
    std::array<int,36> first; first.fill(-1);
    int changed=-1;
    for(int j=0;j<36;j++) {
        auto[a,b]=q.edge[j];int e=6*a+b;
        if(first[e]<0)first[e]=j;else if(changed<0)changed=j;
    }
    assert(changed>=0);
    for(int i=0;i<6;i++) {
        q.opq[i]&=~(1ULL<<changed);q.black[i]&=~(1ULL<<changed);
        if(i<4)q.opq[i]|=1ULL<<changed;
        if(i==0||i==2)q.black[i]|=1ULL<<changed;
    }
    q.lattice_enabled=true;q.lattice_code.assign(720,0);
    for(int s=0;s<720;s++) {
        u64 covered=0;unsigned visible=0;
        for(int i:q.perms[s]) {
            if(q.opq[i]&~covered)visible|=1U<<i;
            q.lattice_code[s]|=q.black[i]&~covered;covered|=q.opq[i];
        }
        assert(visible==(63U^(1U<<q.perms[s].back())));
    }
    int tested=0;
    for(int s=0;s<720;s++) {
        int t=(137*s+53)%720;
        u64 holes=rng()&low_bits(36),target=q.lattice_code[t];
        auto plan=q.plan(q.perms[s],target,holes);
        int expected=6;
        for(int v=0;v<720;v++)
            if(!((q.lattice_code[v]^target)&holes))expected=std::min(expected,q.distance(s,v));
        assert(int(plan.size())==expected);
        auto order=q.perms[s];
        for(auto[paper,depth]:plan) {
            int pos=int(std::find(order.begin(),order.end(),paper)-order.begin());
            u64 covered=0;
            for(int i=0;i<pos;i++)covered|=q.opq[order[i]];
            assert(q.opq[paper]&~covered);
            order.erase(order.begin()+pos);order.insert(order.begin()+depth,paper);
        }
        int finish=q.order_index(order);
        assert(!((q.lattice_code[finish]^target)&holes));tested++;
    }
    std::cout << "nonlinear_legal_plans_checked = " << tested << '\n';
}
