#include "saved.hpp"
struct Copy {int paper,column;double estimate;};
int main(int argc,char** argv){
    if(argc<3)return 2;auto input=cover::load(argv[1],argv[2]);if(!input)return 3;
    int tested=argc>3?std::stoi(argv[3]):24;
    auto reference=cover::redesign(*input,0),base=cover::redesign(*input,1);if(!base||!reference)return 4;
    base->init_choices();auto initial=base->save();
    std::vector<std::vector<int>> owners(K);std::vector<int> size(base->H),targets(base->H);
    for(int u=0;u<P;u++)owners[base->ded[u]].push_back(u);
    for(int x=7;x<K-1;x++){size[base->col_of[x]]++;targets[base->col_of[x]]+=owners[x].size();}
    struct Sample {std::array<unsigned char,K> ranks{};};std::vector<Sample> samples;
    std::mt19937_64 rng(7182321);int prev=rng()%P;
    for(int t=0;t<2048;t++){
        if(t%4==0){Sample z;std::vector<int> ranks(base->H);for(int x:base->order)if(base->col_of[x]>=0&&x!=base->top_d&&!base->is_filler(x))z.ranks[x]=ranks[base->col_of[x]]++;samples.push_back(z);}
        int u=rng()%(P-1);if(u>=prev)u++;prev=u;base->process(u);
    }
    base->restore(initial);std::vector<Copy> candidates;
    for(int x=7;x<K-1;x++)for(int c=0;c<base->H;c++)if(c!=base->col_of[x]){
        u64 diff=owners[x].size()==2?base->A[owners[x][0]]^base->A[owners[x][1]]:0;if(diff>>base->handle[c]&1)continue;
        u64 op=base->gmask|kCapBit;for(int j=0;j<=c;j++)op|=1ULL<<base->handle[j];op&=~(diff&~kCapBit);
        // Uniform depth of the extra copy, with half a position charged to
        // every other request served by its destination column.
        double gain=.5*targets[c];
        double delta=.4*(__builtin_popcountll(base->hmask&~op)-__builtin_popcountll(base->hmask&~base->paper[x].opaque));
        double benefit=0;for(const auto& z:samples)for(int rank=0;rank<=size[c];rank++)benefit+=std::min(0.0,rank+delta-z.ranks[x]);
        gain+=owners[x].size()*benefit/(samples.size()*(size[c]+1));
        candidates.push_back({x,c,gain/P});
    }
    std::sort(candidates.begin(),candidates.end(),[](auto a,auto b){return a.estimate<b.estimate;});
    Solver trainbase=*base;double training=cover::simulate(trainbase,4);
    std::cout<<std::setprecision(12)<<"{\"reduced_training\":"<<training<<",\"tests\":[";
    double best=1e100;Copy chosen{};int tests=std::min(tested,int(candidates.size()));
    for(int i=0;i<tests;i++){
        auto c=candidates[i];Solver modified=*base;auto products=cover::copy_to(modified,c.paper,c.column,K-1);
        double value=cover::simulate(modified,4);if(value<best){best=value;chosen=c;}
        std::cerr<<"copy "<<i<<" paper "<<c.paper<<" col "<<c.column<<" estimate "<<c.estimate<<" gain "<<value-training<<'\n';
        std::cout<<(i?",":"")<<"{\"paper\":"<<c.paper<<",\"column\":"<<c.column<<",\"estimate\":"<<c.estimate<<",\"cost\":"<<value<<",\"gain\":"<<value-training<<",\"products\":[";
        for(int j=0;j<int(products.size());j++)std::cout<<(j?",":"")<<products[j];std::cout<<"]}"<<std::flush;
    }
    Solver reduced=*base,modified=*base;cover::copy_to(modified,chosen.paper,chosen.column,K-1);
    double ref=cover::simulate(*reference,16,nullptr,1000),red=cover::simulate(reduced,16,nullptr,1000),value=cover::simulate(modified,16,nullptr,1000);
    std::cout<<"],\"chosen_paper\":"<<chosen.paper<<",\"chosen_column\":"<<chosen.column<<",\"reference\":"<<ref<<",\"reduced\":"<<red<<",\"validation\":"<<value<<",\"difference\":"<<value-ref<<",\"copy_gain\":"<<value-red<<",\"selected\":"<<modified.choice_alternative<<",\"elapsed\":"<<elapsed_sec()<<"}\n";
}
