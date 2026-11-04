#ifndef AHC074_ONE_SHOT_PLANNER_HPP
#define AHC074_ONE_SHOT_PLANNER_HPP
#include <algorithm>
#include <bit>
#include <cstdint>
#include <optional>
#include <span>
#include <stdexcept>
#include <vector>
namespace ahc074_one_shot {
using Bits = std::uint64_t;
struct Paper { Bits opaque = 0, black = 0; };
struct Move { int original_index = -1, destination = -1; };
struct Plan { std::vector<int> gaps; std::vector<Move> moves; };
// Exact feasibility for a FIXED final relative order of at most eight selected
// papers. Each selected paper is selected exactly once (visible no-ops allowed).
// All other papers remain fixed. Paper identities are indices in the input stack.
// Choose the componentwise largest feasible base gaps; moving already processed
// papers deeper cannot hide an unprocessed paper. Reachable-subset DP determines
// the legal operation order, with unprocessed papers before processed papers on
// equal base gaps. This tie convention maximizes visibility.
inline std::optional<Plan> solve(std::span<const Paper> stack,
                                std::span<const int> final_order, Bits target) {
    const int K = int(stack.size()), r = int(final_order.size());
    if (r > 8) throw std::invalid_argument("at most eight selected papers");
    std::vector<int> rank(K, -1), base, original_gap(r);
    for (int i=0;i<r;++i) {
        int k=final_order[i];
        if (k<0 || k>=K || rank[k]>=0) throw std::invalid_argument("invalid selection");
        rank[k]=i;
    }
    for (int k=0;k<K;++k) {
        if (stack[k].black & ~stack[k].opaque) throw std::invalid_argument("invalid paper");
        if (rank[k]<0) base.push_back(k);
        else original_gap[rank[k]]=int(base.size());
    }
    const int n=int(base.size());
    std::vector<int> first(64,n), lo(r,0), hi(r,n), gaps(r);
    Bits covered=0, view=0;
    for (int j=0;j<n;++j) {
        Paper p=stack[base[j]]; Bits fresh=p.opaque&~covered;
        for (Bits z=fresh;z;z&=z-1) first[std::countr_zero(z)]=j;
        view|=p.black&~covered; covered|=p.opaque;
    }
    Bits error=view^target; covered=0;
    for (int i=0;i<r;++i) {
        Paper p=stack[final_order[i]];
        Bits owned=p.opaque&~covered, wrong=owned&(p.black^target);
        if (wrong&error) return std::nullopt;
        for (Bits z=wrong;z;z&=z-1) lo[i]=std::max(lo[i],first[std::countr_zero(z)]+1);
        for (Bits z=owned&error;z;z&=z-1) hi[i]=std::min(hi[i],first[std::countr_zero(z)]);
        covered|=p.opaque;
    }
    if (error&~covered) return std::nullopt;
    for (int i=r-1, lim=n;i>=0;--i) {
        lim=std::min(lim,hi[i]); gaps[i]=lim;
        if (gaps[i]<lo[i]) return std::nullopt;
    }
    auto state = [&](unsigned mask) {
        // Merge fixed papers with r inserted items. Unprocessed items precede
        // processed ones on a shared gap; ties within each class are stable.
        std::vector<int> items(r); for(int i=0;i<r;++i) items[i]=i;
        auto key=[&](int i) {
            bool done=(mask>>i)&1;
            return std::pair<int,int>{done?gaps[i]:original_gap[i],
                                     done?K+i:final_order[i]};
        };
        std::sort(items.begin(),items.end(),[&](int a,int b){return key(a)<key(b);});
        std::vector<int> order; order.reserve(K); int at=0;
        for(int g=0;g<=n;++g) {
            while(at<r && key(items[at]).first==g) order.push_back(final_order[items[at++]]);
            if(g<n) order.push_back(base[g]);
        }
        return order;
    };
    const unsigned end=(1U<<r)-1;
    std::vector<int> last(end+1,-1); last[0]=-2;
    for (unsigned mask=0;mask<end;++mask) if (last[mask]!=-1) {
        Bits seen=0; unsigned visible=0;
        for (int k:state(mask)) {
            int i=rank[k];
            if (i>=0 && (stack[k].opaque&~seen)) visible|=1U<<i;
            seen|=stack[k].opaque;
        }
        for (unsigned z=visible&~mask;z;z&=z-1) {
            int i=std::countr_zero(z); unsigned next=mask|(1U<<i);
            if (last[next]<0) last[next]=i;
        }
    }
    if (last[end]==-1) return std::nullopt;
    std::vector<int> operation_order;
    for (unsigned mask=end;mask;) {
        int i=last[mask]; operation_order.push_back(i); mask^=1U<<i;
    }
    std::reverse(operation_order.begin(),operation_order.end());
    Plan result{gaps,{}}; unsigned mask=0;
    for (int i:operation_order) {
        mask|=1U<<i; auto after=state(mask); int k=final_order[i];
        int d=int(std::find(after.begin(),after.end(),k)-after.begin());
        result.moves.push_back({k,d});
    }
    return result;
}
} // namespace ahc074_one_shot
#endif
