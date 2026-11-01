// Global cardinality-70 weighted matching versus the initializer's greedy
// matching. Boost is used only in this research tool, not submission code.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/maximum_weighted_matching.hpp>
using Graph=boost::adjacency_list<boost::vecS,boost::vecS,boost::undirectedS,boost::no_property,boost::property<boost::edge_weight_t,long long>>;
struct Edge {int u,v,c;};
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8;
    std::cout<<"seed,edges,greedy70,global70,gap_per_request,gap_fraction_of_total,lambda,calls\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);std::vector<Edge>edges;
        for(int u=0;u<256;++u)for(int v=u+1;v<256;++v){
            double gc=d.cost(u,v,0);if(gc<0)continue;
            u64 delta=d.a[u]^d.a[v];int cost=2340*std::popcount(delta>>36)+int(std::llround(7200*gc))+144*std::popcount(delta);
            edges.push_back({u,v,cost});
        }
        std::sort(edges.begin(),edges.end(),[](Edge a,Edge b){return std::tuple(a.c,a.u,a.v)<std::tuple(b.c,b.u,b.v);});
        std::array<bool,256>used{};int count=0;long long greedy=0;
        for(auto e:edges)if(!used[e.u]&&!used[e.v]){used[e.u]=used[e.v]=true;greedy+=e.c;if(++count==70)break;}
        assert(count==70);
        // Lexicographic perturbation preserves integer primary costs. If an
        // optimum for lambda*|M|-cost(M) has 70 edges, it is a certified global
        // optimum among cardinality-70 matchings for the primary costs.
        constexpr long long scale=10000000;
        long long left=0,right=1000000LL*scale,answer=-1,chosen_lambda=0;int calls=0;
        while(left<=right){
            long long lambda=(left+right)/2;Graph graph(256);
            for(int i=0;i<(int)edges.size();++i){auto e=edges[i];long long w=lambda-e.c*scale-i;if(w>0)boost::add_edge(e.u,e.v,w,graph);}
            std::vector<Graph::vertex_descriptor>mate(256);auto map=boost::make_iterator_property_map(mate.begin(),boost::get(boost::vertex_index,graph));
            boost::maximum_weighted_matching(graph,map);calls++;int n=0;long long cost=0;
            for(int u=0;u<256;++u)if(mate[u]!=boost::graph_traits<Graph>::null_vertex()&&u<int(mate[u])){
                ++n;auto it=std::find_if(edges.begin(),edges.end(),[&](Edge e){return e.u==u&&e.v==int(mate[u]);});assert(it!=edges.end());cost+=it->c;
            }
            if(n==70){answer=cost;chosen_lambda=lambda;break;}
            if(n<70)left=lambda+1;else right=lambda-1;
        }
        double gap=answer<0?0:(answer-greedy)/(3600.0*256);
        std::cout<<seed<<','<<edges.size()<<','<<greedy/3600.0<<','<<answer/3600.0<<','<<gap<<','<<gap/10.62036<<','<<chosen_lambda<<','<<calls<<'\n'<<std::flush;
    }
}
