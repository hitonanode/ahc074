// Research prototype: voluntary handle holes in dedicated papers, priced
// against their usefulness as fillers. Saved design; no design-time search or
// official evaluation. Simulated requests are freshly generated fixed seeds.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"

std::array<double,192> head_prob(Data&d){
    auto ptr=make_solver(d,false);auto&s=*ptr;std::array<double,192> count{};
    std::vector<int> trace(192);std::iota(trace.begin(),trace.end(),0);int samples=0;
    for(int r=0;r<1024;++r){
        if(r%8==0){
            s.order=trace;s.fillers.clear();s.canonicalize();s.ops.clear();s.invalid=false;s.check_vis=true;
            if(s.top_d>=0)s.return_paper(s.top_d,-1,1);auto old=s.fillers;s.return_visible_fillers(old,-1,1);assert(!s.invalid);
            for(int c=0;c<28;++c)count[s.column_top(c)]++;samples++;
        }
        for(auto[k,z]:d.queries[r]){trace.erase(std::find(trace.begin(),trace.end(),k));trace.insert(trace.begin()+z,k);}
    }
    for(double&x:count)x/=samples;return count;
}
double filler_proxy(const Data&d,int k,u64 opq,double head){
    double total=0;int c=d.cols[k];u64 mask=opq>>36,black=d.papers[k].black>>36;
    for(int u=0;u<256;++u){
        if(d.ded[u]==k || d.cols[d.ded[u]]==c)continue;
        u64 holes=(~d.papers[d.ded[u]].opaque>>36)&low_bits(28),range=mask&holes;
        u64 wrong=(black^(d.a[u]>>36))&range;
        int level=wrong?64-__builtin_clzll(wrong):0;
        u64 covered=range&~low_bits(level)&~(1ULL<<c);
        total+=std::max(0.0,.5*std::popcount(covered)-1.6);
    }
    return total*head/256;
}
std::pair<int,double> cut(Data&d,const std::array<double,192>&head,double boost){
    std::array<int,192>weight{};for(int k:d.ded)weight[k]++;
    int cuts=0;double predicted=0;
    for(int iter=0;iter<64;++iter){
        double best=0;int bk=-1,bj=-1;
        for(int k=6;k<192;++k)if(head[k]>0){
            double before=filler_proxy(d,k,d.papers[k].opaque,head[k]);
            for(int j=36;j<36+d.cols[k];++j)if(d.papers[k].opaque>>j&1){
                double after=filler_proxy(d,k,d.papers[k].opaque&~(1ULL<<j),head[k]);
                double gain=boost*(after-before)-.4*weight[k]/256;
                if(gain>best){best=gain;bk=k;bj=j;}
            }
        }
        if(bk<0)break;d.papers[bk].opaque&=~(1ULL<<bj);d.papers[bk].black&=d.papers[bk].opaque;
        cuts++;predicted+=best;
    }
    return {cuts,predicted};
}
std::pair<double,long long> simulate(Data&d,int seqs){
    auto original=make_solver(d,true);double total=0;long long wrong=0;
    for(int q=0;q<seqs;++q){
        Solver sim=*original;std::mt19937_64 rng(7100003ULL+q*100003ULL);int prev=-1;
        for(int r=0;r<1024;++r){
            int u=r?int(rng()%255):int(rng()%256);if(r&&u>=prev)++u;prev=u;
            auto ops=sim.process(u);total+=ops.size();wrong+=sim.display()!=sim.A[u];
        }
    }
    return {total/(seqs*1024),wrong};
}
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):4,seqs=argc>3?std::stoi(argv[3]):4;
    std::cout<<"seed,proxy_boost,cuts,predicted_gain,moves,wrong\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);auto head=head_prob(d);
        for(double boost:{0.0,1.0,2.0,4.0}){
            Data cand=d;auto [cuts,gain]=boost?cut(cand,head,boost):std::pair(0,0.0);
            auto [moves,wrong]=simulate(cand,seqs);
            std::cout<<seed<<','<<boost<<','<<cuts<<','<<gain<<','<<std::setprecision(10)<<moves<<','<<wrong<<'\n'<<std::flush;
        }
    }
}
