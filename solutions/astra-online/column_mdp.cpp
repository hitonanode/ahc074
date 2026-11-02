#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <unordered_map>
#include <vector>

// Research model: the only movable paper is the top one. A paper request is
// completed when that identity reaches the top, then its mandatory lift/return
// is represented as a free choice of reinsertion gap. Constant lift/return
// charges are omitted. Color requests stop at the first desired color.
struct Model {
    int n=0, ns=0;
    double q[2]{}, den=0;
    std::vector<std::vector<int>> seq, tr;
    std::unordered_map<uint64_t,int> ids;
    std::vector<double> h, immediate;
    static int color(int x) { return x&1; }
    static int weight(int x) { return 1+(x>>1); }
    static uint64_t code(const std::vector<int>& s) {
        uint64_t k=0; for(int x:s) k=(k<<2)|x; return k;
    }
    Model(std::array<int,4> cnt,double a,double b) {
        q[0]=a;q[1]=b;
        std::vector<int> s;
        for(int i=0;i<4;i++) for(int k=0;k<cnt[i];k++) s.push_back(i);
        n=s.size(); den=a+b; for(int x:s) den+=weight(x);
        do { ids[code(s)]=seq.size();seq.push_back(s); }
        while(std::next_permutation(s.begin(),s.end()));
        ns=seq.size();tr.assign(ns,std::vector<int>(n));
        immediate.assign(ns,0);
        for(int j=0;j<ns;j++) {
            for(int d=0;d<n;d++) {
                auto v=seq[j];int x=v.front();v.erase(v.begin());v.insert(v.begin()+d,x);
                tr[j][d]=ids.at(code(v));
            }
            int first[2]={n,n};
            for(int r=n-1;r>=0;r--) first[color(seq[j][r])]=r;
            double v=q[0]*first[0]+q[1]*first[1];
            for(int r=0;r<n;r++) v+=r*weight(seq[j][r]);
            immediate[j]=v/den;
        }
        h.assign(ns,0);
    }
    double bellman(const std::vector<double>& value,std::vector<double>& out) const {
        // target[r,s] and fix[r,s]: r compulsory top removals remain. A top
        // removal inserts only below the tracked target, so r decreases.
        std::vector<double> target(ns*n),fix(ns*n);
        for(int s=0;s<ns;s++) {
            fix[s]=value[s];target[s]=1e100;
            for(int d=0;d<n;d++) target[s]=std::min(target[s],value[tr[s][d]]);
        }
        for(int r=1;r<n;r++) for(int s=0;s<ns;s++) {
            double va=1e100,vb=1e100;
            for(int d=r;d<n;d++) {
                va=std::min(va,target[(r-1)*ns+tr[s][d]]);
                vb=std::min(vb,fix[(r-1)*ns+tr[s][d]]);
            }
            target[r*ns+s]=1+va;fix[r*ns+s]=1+vb;
        }
        out.assign(ns,0);
        for(int s=0;s<ns;s++) {
            int first[2]={n,n};
            for(int r=n-1;r>=0;r--) first[color(seq[s][r])]=r;
            for(int c=0;c<2;c++) if(first[c]<n) out[s]+=q[c]*fix[first[c]*ns+s];
            for(int r=0;r<n;r++) out[s]+=weight(seq[s][r])*target[r*ns+s];
            out[s]/=den;
        }
        return out[0];
    }
    // stationary evaluation of an insertion policy that greedily minimizes
    // its supplied potential after each top removal, exactly as adaptive_insert.
    double policy(const std::vector<double>& value) const {
        std::vector<int> best(ns*n);
        for(int s=0;s<ns;s++) for(int r=0;r<n;r++) {
            int z=tr[s][n-1];double v=value[z];
            for(int d=r;d<n;d++) if(value[tr[s][d]]<v-1e-12) v=value[tr[s][d]],z=tr[s][d];
            best[r*ns+s]=z;
        }
        std::vector<std::vector<std::pair<int,double>>> kernel(ns);
        std::vector<double> costs(ns,0),p(ns,1.0/ns),next(ns);
        for(int s=0;s<ns;s++) {
            int first[2]={n,n};
            for(int r=n-1;r>=0;r--) first[color(seq[s][r])]=r;
            for(int c=0;c<2;c++) if(first[c]<n) {
                int z=s; for(int r=first[c];r>0;r--) z=best[r*ns+z];
                kernel[s].push_back({z,q[c]/den});costs[s]+=q[c]*first[c]/den;
            }
            for(int r0=0;r0<n;r0++) {
                int z=s;for(int r=r0;r>0;r--) z=best[r*ns+z];
                z=best[z];double w=weight(seq[s][r0])/den;
                kernel[s].push_back({z,w});costs[s]+=w*r0;
            }
        }
        double old=-1;
        for(int it=0;it<10000;it++) {
            std::fill(next.begin(),next.end(),0.0);
            for(int s=0;s<ns;s++) for(auto [t,w]:kernel[s]) next[t]+=p[s]*w;
            p.swap(next);
            double v=std::inner_product(p.begin(),p.end(),costs.begin(),0.0);
            if(it>100 && std::abs(v-old)<1e-13) return v;
            old=v;
        }
        return old;
    }
};

int main(int argc,char** argv) {
    if(argc!=7) { std::cerr<<"usage: column_mdp n00 n01 n10 n11 q0 q1\n";return 1; }
    std::array<int,4> counts{};for(int i=0;i<4;i++) counts[i]=std::atoi(argv[i+1]);
    Model m(counts,std::atof(argv[5]),std::atof(argv[6]));
    std::vector<double> next;double gain=0,span=0;int it=0;
    for(;it<1000;it++) {
        gain=m.bellman(m.h,next);
        double lo=1e100,hi=-1e100;
        for(int s=0;s<m.ns;s++) lo=std::min(lo,next[s]-m.h[s]),hi=std::max(hi,next[s]-m.h[s]);
        span=hi-lo;
        for(double& v:next) v-=gain;
        m.h.swap(next);
        if(span<1e-10) break;
    }
    std::cout<<std::setprecision(12)<<"states="<<m.ns<<" iterations="<<it<<" optimal="<<gain
             <<" myopic="<<m.policy(m.immediate)<<" h_greedy="<<m.policy(m.h)<<" residual="<<span<<'\n';
    return 0;
}
