#include "common.hpp"

int main(int argc,char**argv){
    if(argc<3)return 2;auto raw=head::load(argv[1],argv[2]);if(!raw)return 3;
    int seqs=argc>3?std::stoi(argv[3]):16,iters=argc>4?std::stoi(argv[4]):65000;
    auto initial=recover(*raw);double reference=0;std::cout<<std::setprecision(12)<<"[";
    std::vector<double> weights={0,.5,1,2};
    for(int i=0;i<int(weights.size());i++){
        Design::old_weight=weights[i];auto d=*initial;double start=elapsed_sec();d.filler_climb(1e9,iters);double design_sec=elapsed_sec()-start;
        Solver s=*raw;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
        for(int q=0;q<seqs;q++){
            s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}
        }
        double avg=double(total)/(seqs*1024);if(!i)reference=avg;
        std::cout<<(i?",":"")<<"{\"weight\":"<<weights[i]<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<d.cur/P<<",\"proxy\":"<<d.proxy_after/P<<",\"design_seconds\":"<<design_sec<<",\"seconds\":"<<elapsed_sec()-start<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
