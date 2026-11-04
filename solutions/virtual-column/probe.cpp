#define VIRTUAL_SCREEN_LIBRARY
#include "screen.cpp"

void convert(Solver&s,const std::vector<int>& chosen){
    for(int x:chosen){
        int k=7+x;s.paper[k].opaque=s.gmask|kCapBit;s.paper[k].black&=s.paper[k].opaque;s.col_of[k]=-2;
        s.h_opq[k]=s.h_blk[k]=0;std::erase(s.order,k);
    }
    auto p=s.order.begin()+s.generic_bottom()+1;
    for(int x:chosen){p=s.order.insert(p,7+x);++p;}
    s.adaptive_initialized=false;s.init_adaptive();
    s.interleave=std::make_shared<Interleave>();
    s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);
    s.init_lookahead();
}
int main(int argc,char**argv){
    if(argc<3)return 2;auto raw=head::load(argv[1],argv[2]);if(!raw)return 3;
    int seqs=argc>3?std::stoi(argv[3]):16,maxn=argc>4?std::stoi(argv[4]):2;
    auto d=recover(*raw);d->refresh_reset();Selection selector(*d);
    materialize(*raw,*d);double reference=0;std::cout<<std::setprecision(12)<<"[";
    for(int n=0;n<=maxn;n++){
        Solver s=*raw;if(n)convert(s,selector.choose(n));auto initial=s.save();
        long long moves=0,wrong=0,failures=0;double begin=elapsed_sec();
        for(int q=0;q<seqs;q++){
            s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
            for(int t=0;t<1024;t++){
                int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
                auto before=s.save();auto path=s.process(u);
                Solver replay=s;replay.restore(before);replay.check_vis=true;replay.invalid=false;
                for(auto[k,depth]:path)replay.move(k,depth);
                assert(!replay.invalid);assert(replay.order==s.order);assert(s.virtual_invariant());
                moves+=path.size();wrong+=s.display()!=s.A[u];
            }
        }
        double avg=double(moves)/(seqs*1024);if(!n)reference=avg;
        std::cout<<(n?",":"")<<"{\"n\":"<<n<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"failures\":"<<s.plan_failures<<",\"seconds\":"<<elapsed_sec()-begin<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
