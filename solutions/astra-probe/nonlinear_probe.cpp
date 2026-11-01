// Learn ternary (possibly 3+ opaque) generic-window patterns with M=6. Keep one
// untouched 2-paper witness per edge, so legal moves/distances remain EXACTLY
// the original 720-state comparator graph. Saved pairs are held fixed; every
// accepted change must keep both endpoints of all 70 pairs representable.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
#include <unordered_map>
struct ColumnPattern{std::array<int,6>v;std::array<uint8_t,720>bit;int opaque;};
struct GoalCost{
    const Comparator*comp;
    std::vector<int>states;
    std::unordered_map<u64,double>cache;
    double get(u64 mask){
        if(!mask)return 1e9;auto it=cache.find(mask);if(it!=cache.end())return it->second;
        std::vector<int>goals;for(u64 x=mask;x;x&=x-1)goals.push_back(states[__builtin_ctzll(x)]);
        double sum=0;for(int s=0;s<720;++s){int best=6;for(int t:goals)if((best=std::min(best,comp->distance(s,t)))==0)break;sum+=best;}
        return cache[mask]=sum/720;
    }
};
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8,passes=argc>3?std::stoi(argv[3]):2;
    std::cout<<"seed,pass,window,opaque,generic_before,generic_after,delta,changed_windows\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);d.comp.build_tables();std::vector<u64>display(720);
        for(int s=0;s<720;++s){u64 cov=0;for(int k:d.comp.perms[s]){display[s]|=d.papers[k].black&~cov;cov|=d.papers[k].opaque;}}
        std::vector<std::array<int,2>>pairs;
        for(int k=6;k<192;++k){std::vector<int>own;for(int u=0;u<256;++u)if(d.ded[u]==k)own.push_back(u);if(own.size()==2)pairs.push_back({own[0],own[1]});}
        std::vector<ColumnPattern>patterns;
        for(int code=0;code<729;++code){
            int z=code;ColumnPattern p{};bool zero=false,one=false;
            for(int k=0;k<6;++k){p.v[k]=z%3-1;z/=3;if(p.v[k]>=0){p.opaque++;zero|=p.v[k]==0;one|=p.v[k]==1;}}
            if(!zero||!one)continue;
            for(int s=0;s<720;++s)for(int k:d.comp.perms[s])if(p.v[k]>=0){p.bit[s]=p.v[k];break;}
            patterns.push_back(p);
        }
        auto totalcost=[&](){double sum=0;for(auto pair:pairs)for(int u:pair){u64 holes=(d.a[pair[0]]^d.a[pair[1]])&low_bits(36);std::vector<int>goals;for(int s=0;s<720;++s)if(!((display[s]^d.a[u])&holes))goals.push_back(s);assert(!goals.empty());for(int s=0;s<720;++s){int mn=6;for(int t:goals)if((mn=std::min(mn,d.comp.distance(s,t)))==0)break;sum+=mn/720.0;}}return sum/256;};
        const double start=totalcost();double cur=start;std::array<bool,36>mutable_window{};
        for(u64 mask:d.edge_windows){mask&=mask-1;while(mask){int j=__builtin_ctzll(mask);mask&=mask-1;mutable_window[j]=true;}}
        std::array<bool,36>changed{};
        for(int pass=0;pass<passes;++pass){
            double best=0;int bestj=-1,bestp=-1;
            for(int j=0;j<36;++j)if(mutable_window[j]){
                std::vector<GoalCost>rows;std::vector<int>want;double before=0;bool large=false;
                for(auto pair:pairs)if((d.a[pair[0]]^d.a[pair[1]])>>j&1){
                    u64 holes=(d.a[pair[0]]^d.a[pair[1]])&low_bits(36)&~(1ULL<<j);
                    for(int u:pair){
                        GoalCost r{&d.comp,{},{}};for(int s=0;s<720;++s)if(!((display[s]^d.a[u])&holes))r.states.push_back(s);
                        if(r.states.size()>64){large=true;break;}
                        u64 mask=0;for(int z=0;z<(int)r.states.size();++z)if((display[r.states[z]]>>j&1)==(d.a[u]>>j&1))mask|=1ULL<<z;
                        before+=r.get(mask);rows.push_back(std::move(r));want.push_back(d.a[u]>>j&1);
                    }
                    if(large)break;
                }
                if(large)continue;
                for(int pi=0;pi<(int)patterns.size();++pi){
                    // Nonlinear family only; comparator relabeling was already optimized.
                    if(patterns[pi].opaque<3)continue;
                    double after=0;
                    for(int r=0;r<(int)rows.size();++r){
                        u64 mask=0;for(int z=0;z<(int)rows[r].states.size();++z)if(patterns[pi].bit[rows[r].states[z]]==want[r])mask|=1ULL<<z;
                        if(!mask){after=1e9;break;}after+=rows[r].get(mask);
                    }
                    double delta=(after-before)/256;
                    if(delta<best-1e-12){best=delta;bestj=j;bestp=pi;}
                }
            }
            if(bestj<0){std::cout<<seed<<','<<pass<<",-1,0,"<<cur<<','<<cur<<",0,"<<std::count(changed.begin(),changed.end(),true)<<'\n'<<std::flush;break;}
            auto&p=patterns[bestp];for(int s=0;s<720;++s)display[s]=(display[s]&~(1ULL<<bestj))|(u64(p.bit[s])<<bestj);
            for(int k=0;k<6;++k){d.papers[k].opaque&=~(1ULL<<bestj);d.papers[k].black&=~(1ULL<<bestj);if(p.v[k]>=0)d.papers[k].opaque|=1ULL<<bestj;if(p.v[k]==1)d.papers[k].black|=1ULL<<bestj;}
            changed[bestj]=true;double exact=totalcost();assert(std::abs(exact-(cur+best))<1e-8);
            std::cout<<seed<<','<<pass<<','<<bestj<<','<<p.opaque<<','<<std::setprecision(10)<<cur<<','<<exact<<','<<best<<','<<std::count(changed.begin(),changed.end(),true)<<'\n'<<std::flush;cur=exact;
        }
    }
}
