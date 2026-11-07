#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <vector>
#include <iostream>
#include <random>
#include <cstring>
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC optimize("O3")
#endif
namespace reference {
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
__attribute__((target("popcnt"))) inline CoverResult expectation(const State& s,const Donors& d,
                              const std::array<double,MaxH>& prob,
                              const double* samples,int nSample,double price) {
    CoverResult ans;
    const U64 all=low(s.H);
    std::array<std::uint32_t,MaxH> threshold{};
    for(int c=0;c<s.H;++c)threshold[c]=std::uint32_t(std::clamp(prob[c],0.,1.)*1073741824.);
    static const auto shifts=[] {
        std::array<std::array<std::uint32_t,MaxH>,P> shifts{};
        for(int t=0;t<P;++t)for(int c=0;c<MaxH;++c) {
            std::uint32_t h=0x9e3779b9U*(1+t*MaxH+c);
            h^=h>>16;h*=0x7feb352dU;h^=h>>15;h*=0x846ca68bU;h^=h>>16;
            shifts[t][c]=h&0x3fffffffU;
        }
        return shifts;
    }();
    std::vector<std::array<std::uint32_t,MaxH>> draws(nSample);
    for(int i=0;i<nSample;++i)for(int c=0;c<s.H;++c)
        draws[i][c]=std::uint32_t(samples[i*s.H+c]*1073741824.);
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
            U64 colors=0;
            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;
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
namespace integer {
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
__attribute__((target("popcnt"))) inline CoverResult expectation(const State& s,const Donors& d,
                              const std::array<double,MaxH>& prob,
                              const double* samples,int nSample,double price) {
    assert(price==1.6); // This frozen V uses only the 8/5 placement price.
    CoverResult ans;
    const U64 all=low(s.H);
    std::array<std::uint32_t,MaxH> threshold{};
    for(int c=0;c<s.H;++c)threshold[c]=std::uint32_t(std::clamp(prob[c],0.,1.)*1073741824.);
    static const auto shifts=[] {
        std::array<std::array<std::uint32_t,MaxH>,P> shifts{};
        for(int t=0;t<P;++t)for(int c=0;c<MaxH;++c) {
            std::uint32_t h=0x9e3779b9U*(1+t*MaxH+c);
            h^=h>>16;h*=0x7feb352dU;h^=h>>15;h*=0x846ca68bU;h^=h>>16;
            shifts[t][c]=h&0x3fffffffU;
        }
        return shifts;
    }();
    std::vector<std::array<std::uint32_t,MaxH>> draws(nSample);
    for(int i=0;i<nSample;++i)for(int c=0;c<s.H;++c)
        draws[i][c]=std::uint32_t(samples[i*s.H+c]*1073741824.);
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
            U64 colors=0;
            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;
            const U64 wrong=(colors^s.hb[t])&holes;
            const int raw=std::popcount(wrong);
            std::array<double,MaxH+1> dp{};
            std::array<int,MaxH+1> score{};
            std::array<int,MaxH+1> prev{},picked{};
            std::array<int,MaxH+1> pickdepth{};
            picked.fill(-1);
            for(int c=0;c<s.H;++c) {
                dp[c+1]=dp[c];score[c+1]=score[c];
                if(c==s.col[own])continue;
                for(int b=0;b<2;++b) {
                    const int k=d.head[c][b];if(k<0)continue;
                    const U64 cov=d.cover[t][k];if(!cov)continue;
                    const int depth=(b!=int(colors>>c&1));
                    int saving=std::popcount(cov&wrong);
                    for(int lo=d.start[t][k];lo<=c;++lo) {
                        const int gain5=5*saving-8-5*depth;
                        if(gain5>0&&score[lo]+gain5>score[c+1]) {
                            score[c+1]=score[lo]+gain5;
                            // Keep the original double arithmetic for the reported V features.
                            const double gain=saving-price-depth;
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
namespace skip {
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
__attribute__((target("popcnt"))) inline CoverResult expectation(const State& s,const Donors& d,
                              const std::array<double,MaxH>& prob,
                              const double* samples,int nSample,double price) {
    assert(price==1.6); // This frozen V uses only the 8/5 placement price.
    CoverResult ans;
    const U64 all=low(s.H);
    std::array<std::uint32_t,MaxH> threshold{};
    for(int c=0;c<s.H;++c)threshold[c]=std::uint32_t(std::clamp(prob[c],0.,1.)*1073741824.);
    static const auto shifts=[] {
        std::array<std::array<std::uint32_t,MaxH>,P> shifts{};
        for(int t=0;t<P;++t)for(int c=0;c<MaxH;++c) {
            std::uint32_t h=0x9e3779b9U*(1+t*MaxH+c);
            h^=h>>16;h*=0x7feb352dU;h^=h>>15;h*=0x846ca68bU;h^=h>>16;
            shifts[t][c]=h&0x3fffffffU;
        }
        return shifts;
    }();
    std::vector<std::array<std::uint32_t,MaxH>> draws(nSample);
    for(int i=0;i<nSample;++i)for(int c=0;c<s.H;++c)
        draws[i][c]=std::uint32_t(samples[i*s.H+c]*1073741824.);
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
            U64 colors=0;
            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;
            const U64 wrong=(colors^s.hb[t])&holes;
            const int raw=std::popcount(wrong);
            std::array<double,MaxH+1> dp{};
            std::array<int,MaxH+1> score{},plateau{};
            std::array<int,MaxH+1> prev{},picked{};
            std::array<int,MaxH+1> pickdepth{};
            picked.fill(-1);
            for(int c=0;c<s.H;++c) {
                dp[c+1]=dp[c];score[c+1]=score[c];plateau[c+1]=plateau[c];
                if(c==s.col[own])continue;
                for(int b=0;b<2;++b) {
                    const int k=d.head[c][b];if(k<0)continue;
                    const U64 cov=d.cover[t][k];if(!cov)continue;
                    const int depth=(b!=int(colors>>c&1));
                    int saving=std::popcount(cov&wrong);
                    for(int start=d.start[t][k];start<=c;) {
                        const int gain5=5*saving-8-5*depth;
                        if(gain5<=0)break;
                        const U64 rest=cov&wrong&~low(start);
                        const int end=rest?int(std::countr_zero(rest)):c;
                        // dp is nondecreasing. Within one constant-saving interval,
                        // retain the earliest start attaining its last DP value.
                        const int lo=std::max(start,plateau[end]);
                        if(score[lo]+gain5>score[c+1]) {
                            score[c+1]=score[lo]+gain5;
                            const double gain=saving-price-depth;
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }
                        saving-=int(((cov&wrong)>>end)&1);
                        start=end+1;
                    }
                }
                if(score[c+1]>score[c])plateau[c+1]=c+1;
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
int main(){
 std::mt19937_64 rng(987123);
 for(int trial=0;trial<256;++trial){
  reference::State s;s.H=trial%3==0?25:trial%3==1?31:35;
  for(int c=0;c<s.H;++c)s.handle[c]=c;
  for(int k=0;k<192;++k){
   s.col[k]=k<7?-1:(k-7)%s.H;
   if(k<7)continue;
   int c=s.col[k];uint64_t own=uint64_t(1)<<c;
   s.opaque[k]=reference::low(c+1)&~(rng()&rng()&rng());s.opaque[k]|=own;
   s.black[k]=(rng()&s.opaque[k]&~own)|(((k-7)/s.H%2)?own:0);
  }
  for(int t=0;t<256;++t){s.target[t]=rng();s.ded[t]=7+t%185;}
  s.prepare();
  std::array<double,reference::MaxH> prob;
  for(int c=0;c<s.H;++c)prob[c]=trial%13==0?double(c%2):double(rng()>>11)*0x1p-53;
  std::array<double,16*35> draws;
  for(auto& x:draws)x=double(rng()>>11)*0x1p-53;
  const auto si=std::bit_cast<integer::State>(s);const auto ss=std::bit_cast<skip::State>(s);
  const reference::Donors dr(s,prob);const integer::Donors di(si,prob);const skip::Donors ds(ss,prob);
  const auto a=reference::expectation(s,dr,prob,draws.data(),16,1.6);
  const auto b=integer::expectation(si,di,prob,draws.data(),16,1.6);
  const auto c=skip::expectation(ss,ds,prob,draws.data(),16,1.6);
  if(std::memcmp(&a,&b,sizeof(a)) || std::memcmp(&a,&c,sizeof(a))){std::cerr<<"mismatch trial="<<trial<<"\n";return 1;}
 }
 std::cout<<"256 synthetic designs, 1048576 target/sample DPs: bit-identical target features and flip rates\n";
}
