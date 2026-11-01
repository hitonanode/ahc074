// Exact goal-set and legal-distance oracle for the joint pairing study.
#define main retained_entry
#include "reference.hpp"
#undef main
#include <unordered_map>
#include <stdexcept>

struct SetHash {
    size_t operator()(const LatticeSet& s) const {
        u64 h=1469598103934665603ULL;
        for(u64 w:s) h=(h^w)*1099511628211ULL;
        return h;
    }
};
struct JointEngine {
    static constexpr int S=720, stride=736, edges=256*255/2;
    struct Rule { unsigned opaque,black; LatticeSet one; };
    struct Pair {int a,b,hd,full;u64 diff;LatticeSet x,y;};
    Comparator c;
    std::array<u64,256> A;
    std::vector<Rule> rule;
    std::array<int,36> choice;
    LatticeSet all;
    std::vector<Pair> pairs;
    std::vector<uint8_t> transpose;
    std::unordered_map<LatticeSet,int,SetHash> memo;
    u64 prepared=~u64(0);
    JointEngine(const u64* aa,const u64* op,const u64* bl) {
        std::copy(aa,aa+256,A.begin());
        c.M=6;c.G=36;c.complete=true;c.build_tables();
        all.fill(~u64(0));all[11]=(u64(1)<<16)-1;
        for(unsigned m=1;m<64;m++) {
            int n=__builtin_popcount(m);
            if(n!=2&&n!=4)continue;
            for(unsigned b=m;b;b=(b-1)&m)if(2*__builtin_popcount(b)==n) {
                Rule r{m,b,{}};
                for(int s=0;s<S;s++)for(int k:c.perms[s])if(m>>k&1) {
                    if(b>>k&1)r.one[s/64]|=u64(1)<<(s%64);break;
                }
                rule.push_back(r);
            }
        }
        if(rule.size()!=120)throw std::runtime_error("rule count");
        for(int j=0;j<36;j++) {
            unsigned m=0,b=0;
            for(int k=0;k<6;k++){m|=(op[k]>>j&1)<<k;b|=(bl[k]>>j&1)<<k;}
            choice[j]=-1;
            for(int t=0;t<int(rule.size());t++)if(rule[t].opaque==m&&rule[t].black==b)choice[j]=t;
            if(choice[j]<0)throw std::runtime_error("unknown rule");
        }
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++) {
            u64 d=A[a]^A[b];pairs.push_back({a,b,__builtin_popcountll(d>>36),__builtin_popcountll(d),d,{},{}});
        }
        transpose.assign(S*stride,0);
        for(int t=0;t<S;t++)for(int s=0;s<S;s++)transpose[t*stride+s]=c.distance(s,t);
        memo.reserve(32768);
    }
    static bool any(const LatticeSet& s){u64 z=0;for(u64 w:s)z|=w;return z!=0;}
    int cost(const LatticeSet& s) {
        auto it=memo.find(s);if(it!=memo.end())return it->second;
        int val=lattice_distance_sum(s,transpose);
        if(memo.size()>500000)memo.clear();
        memo.emplace(s,val);return val;
    }
    void prepare(u64 erased) {
        if(prepared==erased)return;
        for(auto& p:pairs) {
            p.x=p.y=all;
            u64 hs=p.diff&low_bits(36)&~erased;
            while(hs) {
                int k=__builtin_ctzll(hs);hs&=hs-1;
                const auto& one=rule[choice[k]].one;
                const bool black=A[p.a]>>k&1;
                u64 ex=0,ey=0;
                for(int w=0;w<12;w++) {
                    const u64 m=black?one[w]:~one[w];
                    ex|=(p.x[w]&=m);ey|=(p.y[w]&=~m);
                }
                if(!ex||!ey){p.x.fill(0);p.y.fill(0);break;}
            }
        }
        prepared=erased;
    }
    // out rows: a,b,mean-distance-sum(a)*720,mean-distance-sum(b)*720,handle diff,full diff.
    int evaluate(u64 erased,u64 negative,int t,int* out) {
        prepare(erased);int n=0;
        for(const auto& p:pairs) {
            if(!any(p.x))continue;
            LatticeSet x=p.x,y=p.y;
            const u64 changed=p.diff&erased;
            if(changed) {
                const u64 bits=(A[p.a]^negative)&changed;
                if(bits && bits!=changed)continue;
                const auto& one=rule[t].one;bool b=bits!=0;
                u64 ex=0,ey=0;
                for(int w=0;w<12;w++){u64 m=b?one[w]:~one[w];ex|=(x[w]&=m);ey|=(y[w]&=~m);}
                if(!ex||!ey)continue;
            }
            int* r=out+6*n++;r[0]=p.a;r[1]=p.b;r[2]=cost(x);r[3]=cost(y);r[4]=p.hd;r[5]=p.full;
        }
        return n;
    }
};
extern "C" {
void* joint_new(const u64* a,const u64* op,const u64* bl) {try{return new JointEngine(a,op,bl);}catch(...){return nullptr;}}
void joint_delete(void* e){delete static_cast<JointEngine*>(e);}
void joint_rules(void* p,int* out){auto& e=*static_cast<JointEngine*>(p);for(int t=0;t<120;t++){out[2*t]=e.rule[t].opaque;out[2*t+1]=e.rule[t].black;}}
void joint_choices(void* p,int* out){auto& e=*static_cast<JointEngine*>(p);std::copy(e.choice.begin(),e.choice.end(),out);}
void joint_layout(void* p,const int* in){auto& e=*static_cast<JointEngine*>(p);std::copy(in,in+36,e.choice.begin());e.prepared=~u64(0);}
int joint_evaluate(void* p,int j,int t,int* out){return static_cast<JointEngine*>(p)->evaluate(j<0?0:u64(1)<<j,0,t,out);}
int joint_evaluate_group(void* p,u64 erased,u64 negative,int t,int* out){return static_cast<JointEngine*>(p)->evaluate(erased,negative,t,out);}
void joint_distances(void* p,unsigned char* out){auto& e=*static_cast<JointEngine*>(p);std::copy(e.c.dist.begin(),e.c.dist.end(),out);}
}
