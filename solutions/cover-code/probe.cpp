#include "saved.hpp"
#include <tuple>

struct Sample {std::array<unsigned char,K> rank{};u64 shown=0;int generic=0;};
struct Candidate {int a,b;double predicted;};
int main(int argc,char** argv){
    if(argc<3)return 2;auto base=cover::load(argv[1],argv[2]);if(!base)return 3;
    int test=argc>3?std::stoi(argv[3]):20,sequences=argc>4?std::stoi(argv[4]):4;
    auto started=elapsed_sec();base->init_choices();
    auto initial=base->save();std::vector<Sample> sample;
    std::mt19937_64 rng(7182321);int prev=rng()%P;
    for(int t=0;t<2048;t++){
        if(t%4==0){
            Sample z;std::vector<int> ranks(base->H),generic;u64 covered=0;
            for(int x:base->order){
                if(x<6)generic.push_back(x);
                if(x>=7){int c=base->col_of[x];if(x==base->top_d||base->is_filler(x))z.rank[x]=0;else z.rank[x]=ranks[c]++;}
                if(x==base->top_d)continue;
                z.shown|=base->paper[x].black&~covered;covered|=base->paper[x].opaque;
            }
            z.generic=base->comparator.order_index(generic);sample.push_back(z);
        }
        int u=int(rng()%(P-1));if(u>=prev)u++;prev=u;base->process(u);
    }
    base->restore(initial);
    std::vector<std::vector<unsigned char>> distance(P,std::vector<unsigned char>(720));
    auto fill_distance=[&](int u,u64 holes){
        std::vector<unsigned char>d(720,255);auto goals=base->comparator.satisfying(base->A[u],holes);
        for(int s=0;s<720;s++)for(int t:goals)d[s]=std::min<int>(d[s],base->comparator.distance(s,t));
        return d;
    };
    for(int u=0;u<P;u++)distance[u]=fill_distance(u,base->gmask&~base->paper[base->ded[u]].opaque);
    auto service=[&](const Sample& z,int u,int paper,u64 opaque,const std::vector<unsigned char>& d){
        return z.rank[paper]+.8*__builtin_popcountll((base->A[u]^z.shown)&base->hmask&~opaque)+d[z.generic];
    };
    std::vector<int> owners(K);for(int u=0;u<P;u++)owners[base->ded[u]]++;
    std::vector<Candidate> candidates;
    for(int b=0;b<P;b++)if(owners[base->ded[b]]==1)for(int a=0;a<P;a++)if(a!=b){
        int x=base->ded[b],y=base->ded[a];u64 diff=base->A[a]^base->A[b];
        if(base->col_of[x]==base->col_of[y])continue;
        if(__builtin_popcountll(diff&~kCapBit)>30||(diff>>base->handle[base->col_of[x]]&1)||!base->comparator.compatible(base->A[a],base->A[b]))continue;
        u64 opaque=base->paper[x].opaque&~(diff&~kCapBit);
        auto da=fill_distance(a,base->gmask&~opaque),db=fill_distance(b,base->gmask&~opaque);
        double gain=0;
        for(const auto& z:sample){
            double old_a=service(z,a,y,base->paper[y].opaque,distance[a]),new_a=service(z,a,x,opaque,da);
            double old_b=service(z,b,x,base->paper[x].opaque,distance[b]),new_b=service(z,b,x,opaque,db);
            gain+=std::min(old_a,new_a)-old_a+new_b-old_b;
        }
        candidates.push_back({a,b,gain/(P*sample.size())});
    }
    std::sort(candidates.begin(),candidates.end(),[](const auto& a,const auto& b){return a.predicted<b.predicted;});
    std::cerr<<"candidates "<<candidates.size()<<" predicted "<<(candidates.empty()?0:candidates[0].predicted)<<" time "<<elapsed_sec()-started<<'\n';
    Solver baseline=*base;std::vector<double> baseline_products;double original=cover::simulate(baseline,sequences,&baseline_products);
    std::cout<<std::setprecision(12)<<"{\"baseline\":"<<original<<",\"sequences\":"<<sequences<<",\"candidates\":"<<candidates.size()<<",\"tests\":[";
    int tested=0;
    for(int i=0;i<std::min(test,int(candidates.size()));i++){
        auto c=candidates[i];Solver modified=*base;cover::share(modified,c.a,c.b);
        std::vector<double> product;double value=cover::simulate(modified,sequences,&product);
        std::cerr<<"test "<<i<<" pair "<<c.a<<' '<<c.b<<" prediction "<<c.predicted<<" difference "<<value-original<<" time "<<elapsed_sec()-started<<'\n';
        std::cout<<(tested++?",":"")<<"{\"rank\":"<<i<<",\"a\":"<<c.a<<",\"b\":"<<c.b<<",\"predicted\":"<<c.predicted<<",\"cost\":"<<value<<",\"difference\":"<<value-original
            <<",\"a_change\":"<<product[c.a]-baseline_products[c.a]<<",\"b_change\":"<<product[c.b]-baseline_products[c.b]<<",\"selected\":"<<modified.choice_alternative<<",\"choice_requests\":"<<modified.choice_requests<<"}"<<std::flush;
    }
    std::cout<<"],\"combined\":[";int comb=0;
    for(int count:{2,4,8,16}){
        Solver modified=*base;std::vector<bool> used(P);std::vector<std::pair<int,int>> selected;
        for(auto c:candidates){if(used[c.a]||used[c.b])continue;cover::share(modified,c.a,c.b);used[c.a]=used[c.b]=true;selected.emplace_back(c.a,c.b);if(int(selected.size())==count)break;}
        if(int(selected.size())!=count)continue;
        double value=cover::simulate(modified,sequences);
        std::cerr<<"combined "<<count<<" difference "<<value-original<<" time "<<elapsed_sec()-started<<'\n';
        std::cout<<(comb++?",":"")<<"{\"count\":"<<count<<",\"cost\":"<<value<<",\"difference\":"<<value-original<<",\"selected\":"<<modified.choice_alternative<<",\"pairs\":[";
        for(int i=0;i<count;i++)std::cout<<(i?",":"")<<'['<<selected[i].first<<','<<selected[i].second<<']';std::cout<<"]}"<<std::flush;
    }
    std::cout<<"],\"elapsed\":"<<elapsed_sec()-started<<"}\n";
}
