// Reproducible semantic checks against the submitted implementation itself.
// This is not a contest score evaluator; the repository comparison runner is
// required for full reactive cases.
#ifdef NDEBUG
#undef NDEBUG
#endif
#define main rescue_submission_main
#include "main.cpp"
#undef main

int main() {
    std::mt19937_64 rng(217113);
    Comparator base;
    base.init(6, 35, rng);
    for(int variant=0;variant<5;variant++) {
        HybridComparator hybrid;
        const u64 support=variant==0 ? low_bits(35) : variant==3 ? 0 : variant==4 ? 0x418c01120ULL
            : rng() & (variant==2 ? rng() : ~0ULL);
        const u64 rescue_y=variant==4 ? 0x365f993b3ULL : rng();
        hybrid.build(base,rescue_y,support);
        // Mix arbitrary bit patterns and known full displays. The latter make
        // many guaranteed-compatible pairs, avoiding a vacuous all-false test.
        std::vector<u64> targets;
        for (int t=0;t<64;t++)
            targets.push_back(t<32 ? rng() : hybrid.hybrid->display[rng()%HybridComparator::STATE_COUNT]
                              | (rng() & ~low_bits(36)));
        int greedy_checks=0, greedy_positive=0;
        for (int a=0;a<64;a++) for (int b=a+1;b<64;b++) {
            const auto pair=rescue_pair(base,targets[a],targets[b]);
            const bool greedy=rescue_greedy_compatible(pair,support,rescue_y);
            const bool exact=hybrid.goal_count(targets[a],pair.holes)>0
                && hybrid.goal_count(targets[b],pair.holes)>0;
            assert(greedy==exact);
            greedy_checks++;
            greedy_positive+=greedy;
        }
        std::vector<std::pair<u64,u64>> goals;
        for(int t=0;t<12;t++) {
            u64 holes=rng()&low_bits(36);
            u64 target=hybrid.hybrid->display[rng()%HybridComparator::STATE_COUNT];
            goals.push_back({target,holes});
            int brute=0;
            for(auto shown:hybrid.hybrid->display) brute+=!((shown^target)&holes);
            assert(brute==hybrid.goal_count(target,holes));
        }
        int checks=0;
        std::vector<int> order(8);
        std::iota(order.begin(),order.end(),0);
        for(int t=0;t<1800;t++) {
            std::shuffle(order.begin(),order.end(),rng);
            auto [target,holes]=goals[t%goals.size()];
            auto moves=hybrid.plan(order,target,holes);
            assert(moves.empty() || moves[0].first>=0);
            for(auto [paper,depth]:moves) {
                int pos=std::find(order.begin(),order.end(),paper)-order.begin();
                u64 covered=0;
                for(int i=0;i<pos;i++) covered|=hybrid.opq[order[i]];
                assert(hybrid.opq[paper]&~covered);
                hybrid.relocate(order,pos,depth);
            }
            assert(!((hybrid.display_of(order)^target)&holes));
            checks++;
        }
        std::cout<<"support="<<__builtin_popcountll(support&low_bits(35))
                 <<" states="<<hybrid.hybrid->orders.size()<<" edges="<<hybrid.hybrid->forward.size()
                 <<" checks="<<checks<<" caches="<<hybrid.hybrid->cache_builds
                 <<" normalized="<<hybrid.hybrid->normalization_moves
                 <<" greedy_checks="<<greedy_checks<<" greedy_positive="<<greedy_positive<<"\n";
    }
}
