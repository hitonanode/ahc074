#pragma once
// Design-only handle surrogate. Contents: State; Donors; Cover expectation.
// There is deliberately no Solver, stack, request sequence or operation emitter.
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <istream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace deval {
using U64 = std::uint64_t;
constexpr int P=256,K=192,MaxH=63;
inline U64 low(int n) { return n==64 ? ~U64(0) : (U64(1)<<n)-1; }
inline int high(U64 x) { return int(std::bit_width(x)); }

// ==== State ====
struct State {
    int M=6,G=38,H=25;
    std::array<U64,P> target{};
    std::array<U64,K> opaque{},black{};
    std::array<int,K> col{};
    std::array<int,P> ded{};
    std::array<int,MaxH> handle{};
    std::array<std::array<int,2>,64> edge{};
    std::array<int,64> polarity{};
    std::array<U64,P> hb{};
    std::array<U64,K> op{},bl{};
    std::array<double,K> freq{};
    std::array<double,MaxH> nc{},nt{},n1{},p1{};
    std::array<std::array<double,2>,MaxH> xy{};

    U64 handles(U64 b) const {
        U64 z=0;
        for(int c=0;c<H;++c) z|=((b>>handle[c])&1)<<c;
        return z;
    }
    // Called after copying the public fields from the solver's DesignState.
    void prepare() {
        freq={};nc={};nt={};n1={};p1={};xy={};
        for(int k=0;k<K;++k) op[k]=handles(opaque[k]),bl[k]=handles(black[k]);
        for(int t=0;t<P;++t) {
            hb[t]=handles(target[t]);
            const int k=ded[t];
            ++freq[k];++nt[col[k]];
            for(int c=0;c<H;++c) if(!(op[k]>>c&1)) ++xy[c][hb[t]>>c&1];
        }
        for(int k=0;k<K;++k) if(col[k]>=0) {
            const int c=col[k],b=bl[k]>>c&1;
            ++nc[c];n1[c]+=b;p1[c]+=(freq[k]==2)*b;
        }
    }
    static State read(std::istream& in) {
        State s;
        std::string line,key;
        while(std::getline(in,line)) {
            std::istringstream r(line);r>>key;
            if(key=="stderr") break;
            if(key=="M")r>>s.M;
            else if(key=="G")r>>s.G;
            else if(key=="H")r>>s.H;
            else if(key=="A") {int n;r>>n;for(int i=0;i<n;++i)r>>s.target[i];}
            else if(key=="papers") {int n;r>>n;for(int i=0;i<n/2;++i)r>>s.opaque[i]>>s.black[i];}
            else if(key=="columns") {int n;r>>n;for(int i=0;i<n;++i)r>>s.col[i];}
            else if(key=="ded") {int n;r>>n;for(int i=0;i<n;++i)r>>s.ded[i];}
            else if(key=="handle") {int n;r>>n;for(int i=0;i<n;++i)r>>s.handle[i];}
            else if(key=="edge") {int n;r>>n;for(int i=0;i<n/2;++i)r>>s.edge[i][0]>>s.edge[i][1];}
            else if(key=="polarity") {int n;r>>n;for(int i=0;i<n;++i)r>>s.polarity[i];}
        }
        if(s.H<=0||s.H>MaxH)throw std::runtime_error("bad H");
        s.prepare();return s;
    }
    std::array<double,MaxH> probabilities(double strength) const {
        std::array<double,MaxH> p{};
        for(int c=0;c<H;++c) {
            const auto [x,y]=xy[c];const double r=strength*nt[c];
            p[c]=(y+r*(y>x))/std::max(1.,x+y+r);
        }
        return p;
    }
};

// ==== Donors ====
struct Donors {
    std::array<std::array<U64,K>,P> cover{};
    std::array<std::array<std::uint8_t,K>,P> start{};
    std::array<double,K> utility{};
    std::array<std::array<int,2>,MaxH> head{};
    explicit Donors(const State& s,const std::array<double,MaxH>& prob) {
        for(auto& a:head)a={-1,-1};
        for(int t=0;t<P;++t) {
            const int own=s.ded[t];
            for(int k=0;k<K;++k) {
                const int c=s.col[k];
                if(c<0||c==s.col[own])continue;
                const U64 shown=s.op[k]&~s.op[own];
                const int lo=high(shown&(s.bl[k]^s.hb[t]));
                if(lo>c)continue;
                const U64 cv=shown&~low(lo);
                cover[t][k]=cv;start[t][k]=std::uint8_t(lo);
                double p0=1,p1=0,e=0;
                for(U64 z=cv&low(c);z;z&=z-1) {
                    const int j=std::countr_zero(z);
                    const double p=(s.hb[t]>>j&1) ? 1-prob[j] : prob[j];
                    p1=p1*(1-p)+p0*p;p0*=1-p;e+=p;
                }
                utility[k]+=std::max(0.,e-(1-p0)-.6*(1-p0-p1));
            }
        }
        for(int k=0;k<K;++k) {
            const int c=s.col[k];if(c<0)continue;
            int& old=head[c][s.bl[k]>>c&1];
            if(old<0||s.freq[k]>s.freq[old]||(s.freq[k]==s.freq[old]&&utility[k]>utility[old]))old=k;
        }
    }
    double head_utility(const State& s,const std::array<double,MaxH>& p) const {
        double v=0;
        for(int c=0;c<s.H;++c)v+=(1-p[c])*utility[head[c][0]]+p[c]*utility[head[c][1]];
        return v/P;
    }
};

// ==== Cover expectation ====
struct CoverResult {
    // raw, total cost, residual fix, filler count, donor digs, covered handles,
    // interval length, squared residual fix. Rows are equally likely targets.
    std::array<std::array<double,8>,P> target{};
    std::array<std::array<double,2>,MaxH> flips{};
    std::array<double,8> mean() const {
        std::array<double,8> a{};
        for(const auto& row:target)for(int j=0;j<8;++j)a[j]+=row[j]/P;
        return a;
    }
};
// Samples are row-major Sobol uniforms, [nSample,H]. They are fixed design-independent
// quadrature points shipped with the evaluator; no random request stream is sampled.
inline CoverResult expectation(const State& s,const Donors& d,
                              const std::array<double,MaxH>& prob,
                              const double* samples,int nSample,double price) {
    CoverResult ans;
    const U64 all=low(s.H);
    std::vector<U64> color_masks(nSample);
    for(int sample=0;sample<nSample;++sample) {
        U64 colors=0;
        for(int c=0;c<s.H;++c)colors|=U64(samples[sample*s.H+c]<prob[c])<<c;
        color_masks[sample]=colors;
    }
    // A target's donor intervals are reused for every quadrature point; this
    // order keeps them in L1 while preserving each target's summation order.
    for(int t=0;t<P;++t) {
        const int own=s.ded[t];
        const U64 holes=all&~s.op[own];
        double exact_raw=0;
        for(U64 z=holes;z;z&=z-1) {
            const int c=std::countr_zero(z),b=s.hb[t]>>c&1;
            const double mismatch=b?1-prob[c]:prob[c];
            exact_raw+=mismatch;ans.flips[c][b]+=mismatch;
        }
        for(int sample=0;sample<nSample;++sample) {
            const U64 colors=color_masks[sample];
            const U64 wrong=(colors^s.hb[t])&holes;
            const int raw=std::popcount(wrong);
            std::array<double,MaxH+1> dp{};
            std::array<int,MaxH+1> prev{},picked{};
            std::array<int,MaxH+1> pickdepth{};
            picked.fill(-1);
            for(int c=0;c<s.H;++c) {
                dp[c+1]=dp[c];
                if(c==s.col[own])continue;
                for(int b=0;b<2;++b) {
                    const int k=d.head[c][b];if(k<0)continue;
                    const U64 cov=d.cover[t][k];if(!cov)continue;
                    const int depth=(b!=int(colors>>c&1));
                    int saving=std::popcount(cov&wrong);
                    for(int lo=d.start[t][k];lo<=c;++lo) {
                        const double gain=saving-price-depth;
                        if(gain>0&&dp[lo]+gain>dp[c+1]+1.e-12) {
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }
                        saving-=int(((cov&wrong)>>lo)&1);
                        if(saving<=price+depth)break;
                    }
                }
            }
            U64 covered=0;int nf=0,digs=0,length=0;
            for(int j=s.H;j>0;) {
                const int k=picked[j];
                if(k<0){--j;continue;}
                const int lo=prev[j];
                covered|=d.cover[t][k]&~low(lo);
                ++nf;digs+=pickdepth[j];length+=j-lo;j=lo;
            }
            const U64 left=wrong&~covered;
            const int fixes=std::popcount(left);
            const std::array<double,8> row{exact_raw,exact_raw-dp[s.H],exact_raw-(raw-fixes),double(nf),double(digs),
                double(std::popcount(covered)),double(length),double(fixes*fixes)};
            for(int j=0;j<8;++j)ans.target[t][j]+=row[j]/nSample;
            for(U64 z=wrong&covered;z;z&=z-1) {
                const int c=std::countr_zero(z);
                ans.flips[c][s.hb[t]>>c&1]-=1./nSample;
            }
        }
    }
    for(auto& f:ans.flips)for(double& x:f)x=std::max(0.,x);
    return ans;
}
} // namespace deval
