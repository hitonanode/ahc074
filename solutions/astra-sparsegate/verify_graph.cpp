#define main submitted_main
#include "main.cpp"
#undef main
#include <cstdio>

int main() {
    Comparator c;
    std::mt19937_64 rng(779879);
    c.init(6,36,rng);
    c.nonlinear = true;
    c.rebuild_truth();
    long long edges = 0;
    double sum = 0;
    for (int s=0;s<720;++s) {
        for (int code=0;code<36;++code) if(c.next[s][code]>=0) {
            const int pos=code/6, paper=c.perms[s][pos];
            bool witness=false;
            for(int j=pos+1;j<6;++j) witness |= c.witness_edge(paper,c.perms[s][j]);
            assert(witness);
            // The printed fixed witness really makes the moved sheet visible.
            u64 seen=0;
            for(int j=0;j<pos;++j) seen |= c.opq[c.perms[s][j]];
            assert(c.opq[paper]&~seen);
            ++edges;
        }
        for(int t=0;t<720;++t) sum += c.distance(s,t);
    }
    XorShift random{123456789};
    for(int sample=0;sample<1000;++sample) {
        Comparator::StateBits bits{};
        const int count=1+random.mod(80);
        for(int j=0;j<count;++j) {int s=random.mod(720);bits[s/64]|=1ULL<<(s%64);}
        const auto goals=Comparator::enumerate(bits);
        int exact=0;
        for(int s=0;s<720;++s) {int best=255;for(int t:goals)best=std::min(best,c.distance(s,t));exact+=best;}
        assert(std::abs(c.exact_goal_mean(bits)-double(exact)/720)<1e-10);
    }
    std::cout<<"PASS states=720 reachable_pairs=518400 legal_edges="<<edges
             <<" diameter="<<c.safe_diameter<<" mean_distance="<<sum/(720*720)
             <<" radius_goal_sets=1000 witness_mode="<<SPARSE_WITNESS<<'\n';
}
