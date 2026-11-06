#pragma once
// Contents: Exact generic costs; Static design features; Filler features.
#include "branch_surrogate.hpp"
#include "../deval-model/poset_data.hpp"
#include "../deval-model/quadrature.hpp"
#include <map>
#include <unordered_map>

namespace deval {
using FeatureMap=std::map<std::string,double>;

// ==== Exact generic costs ====
// A design-independent initialization shared by every candidate. In an integrated
// solver this table can share the existing exact generic-layer cost infrastructure.
struct GenericTable {
    std::unordered_map<U64,double> mean;
    GenericTable() {
        mean.reserve(140000);
        for(const auto& cls:kClasses) {
            std::array<int,6> p{0,1,2,3,4,5};
            do {
                U64 r=0;
                for(U64 z=cls.relation;z;z&=z-1) {
                    const int bit=std::countr_zero(z);
                    r|=U64(1)<<(8*p[bit/8]+p[bit%8]);
                }
                mean.emplace(r,cls.sum/720.);
            } while(std::next_permutation(p.begin(),p.end()));
        }
        if(mean.size()!=130023)throw std::runtime_error("generic table size");
    }
    std::pair<double,int> cost(const State& s,int t) const {
        if(s.M!=6)throw std::runtime_error("expected six generic papers");
        std::array<unsigned,6> reach{};
        U64 holes=(~s.opaque[s.ded[t]])&low(s.G);
        for(U64 z=holes;z;z&=z-1) {
            const int j=std::countr_zero(z);
            auto [a,b]=s.edge[j];
            if(int(s.target[t]>>j&1)!=s.polarity[j])std::swap(a,b);
            reach[a]|=1U<<b;
        }
        for(int k=0;k<6;++k)for(int a=0;a<6;++a)if(reach[a]>>k&1)reach[a]|=reach[k];
        U64 relation=0;int nr=0;
        for(int a=0;a<6;++a){relation|=U64(reach[a])<<(8*a);nr+=std::popcount(reach[a]);}
        return {mean.at(relation),nr};
    }
};

// ==== Static design features ====
inline FeatureMap static_features(const State& s,const GenericTable& gt) {
    FeatureMap out;
    std::array<double,MaxH> colcost{},dem{},minor{},balance{},unitminor{},pairminor{},np{},depth{};
    for(int c=0;c<s.H;++c) {
        np[c]=s.nt[c]-s.nc[c];
        colcost[c]=(s.nc[c]*(s.nc[c]-1)+np[c]*(np[c]-1))/2
            +std::max(0.,np[c]-1)*(s.p1[c]==0||s.p1[c]==np[c]);
        dem[c]=s.xy[c][0]+s.xy[c][1];minor[c]=std::min(s.xy[c][0],s.xy[c][1]);
        balance[c]=dem[c]>0?minor[c]/dem[c]:0.;
        unitminor[c]=std::min(s.n1[c],s.nc[c]-s.n1[c]);
        pairminor[c]=std::min(s.p1[c],np[c]-s.p1[c]);
        depth[c]=double(c)/std::max(1,s.H-1);
        out["col"]+=colcost[c]/P;
    }
    out["G"]=s.G;out["H"]=s.H;out["holes"]=0;out["extra_holes"]=0;out["gc"]=0;
    const std::array<std::string,8> tn{"generic","gen_holes","gen_relations","holes","early_holes","minor_requests","hole_bal","hole_bal2"};
    std::array<std::array<double,3>,8> moments{};
    for(int t=0;t<P;++t) {
        const auto [gc,nrel]=gt.cost(s,t);
        const int k=s.ded[t],cown=s.col[k];
        const U64 holes=low(s.H)&~s.op[k];
        std::array<double,8> a{gc,double(std::popcount(~s.opaque[k]&low(s.G))),double(nrel),
            double(std::popcount(holes)),double(std::popcount(holes&low(cown))),0,0,0};
        for(U64 z=holes;z;z&=z-1) {
            const int c=std::countr_zero(z);
            a[5]+=(int(s.hb[t]>>c&1)!=int(s.xy[c][1]>s.xy[c][0]));
            a[6]+=balance[c];a[7]+=balance[c]*balance[c];
        }
        out["gc"]+=gc/P;out["holes"]+=a[3]/P;out["extra_holes"]+=a[4]/P;
        for(int j=0;j<8;++j) {
            double v=a[j];
            for(int power=1;power<=3;++power){moments[j][power-1]+=v/P;v*=a[j];}
        }
    }
    for(int j=0;j<8;++j)for(int power=1;power<=3;++power)
        out["t_"+tn[j]+"_p"+std::to_string(power)]=moments[j][power-1];
    const std::array<double,6> strengths{0,.5,1,2,4,8};
    const std::array<std::string,6> sn{"0","0.5","1","2","4","8"};
    for(int si=0;si<6;++si) {
        const auto p=s.probabilities(strengths[si]);
        const std::string key="h"+sn[si];
        for(int power=0;power<4;++power)out[key+"_d"+std::to_string(power)]=0;
        for(int band:{1,2,3,5})out[key+"_last"+std::to_string(band)]=0;
        out[key+"_balance"]=0;out[key+"_balance2"]=0;
        for(int c=0;c<s.H;++c) {
            const double h=(s.xy[c][0]*p[c]+s.xy[c][1]*(1-p[c]))/P;
            double v=h;
            for(int power=0;power<4;++power){out[key+"_d"+std::to_string(power)]+=v;v*=depth[c];}
            for(int band:{1,2,3,5})if(c>=s.H-band)out[key+"_last"+std::to_string(band)]+=h;
            out[key+"_balance"]+=h*balance[c];out[key+"_balance2"]+=h*balance[c]*balance[c];
        }
    }
    const std::array<std::string,7> cn{"dem","minor","balance","unit_minor","pair_minor","nc","np"};
    const std::array<const std::array<double,MaxH>*,7> ca{&dem,&minor,&balance,&unitminor,&pairminor,&s.nc,&np};
    for(int j=0;j<7;++j)for(int power=1;power<=3;++power) {
        double sum=0;
        for(int c=0;c<s.H;++c) {
            double x=(*ca[j])[c];if(j<2)x/=P;
            double v=1;for(int k=0;k<power;++k)v*=x;
            sum+=v;
        }
        out[cn[j]+"_p"+std::to_string(power)]=sum;
    }
    return out;
}

// ==== Filler features ====
inline void add_cover_summary(FeatureMap& out,const std::string& key,
                              const CoverResult& r,bool moments) {
    const std::array<std::string,8> names{"raw","cost","fix","fill","fdig","covered","length","fix2"};
    const auto mean=r.mean();
    for(int j=0;j<8;++j)out[key+"_"+names[j]]=mean[j];
    if(moments)for(int power:{2,3}) {
        double v=0;
        for(const auto& t:r.target)v+=std::pow(t[1],power)/P;
        out[key+"_moment"+std::to_string(power)]=v;
    }
}
inline void add_filler_features(FeatureMap& out,const State& s,double strength,
                                const std::vector<double>& prices,int nSamples) {
    const auto p=s.probabilities(strength);
    const Donors donors(s,p);
    const std::string skey="f_s"+std::to_string(int(strength));
    out[skey+"_headutility"]=donors.head_utility(s,p);
    for(double price:prices) {
        std::ostringstream name;name<<price;
        const std::string key=skey+"_p"+name.str();
        const auto r=expectation(s,donors,p,samples_for(s.H),nSamples,price);
        add_cover_summary(out,key,r,true);
    }
}

// Two-state mean-field update. Conditional rates, rather than surviving demand
// counts, account for the fact that a filler is selected depending on current
// head colours. Representatives remain fixed during this cheap approximation.
inline void add_stationary_features(FeatureMap& out,const State& s,int nSamples,int steps) {
    auto p=s.probabilities(2.);
    const Donors donors(s,p);
    out["f_s2_headutility"]=donors.head_utility(s,p);
    auto r=expectation(s,donors,p,samples_for(s.H),nSamples,1.6);
    add_cover_summary(out,"f_s2_p1.6",r,true);
    for(int step=1;step<=steps;++step) {
        for(int c=0;c<s.H;++c) {
            const double a=r.flips[c][1]/std::max(1.e-4,1-p[c]);
            const double b=r.flips[c][0]/std::max(1.e-4,p[c]);
            const double reset=2*s.nt[c];
            const double next=(a+reset*(s.xy[c][1]>s.xy[c][0]))/std::max(1.,a+b+reset);
            p[c]=.5*p[c]+.5*next;
        }
        r=expectation(s,donors,p,samples_for(s.H),nSamples,1.6);
        const std::string key="m_s2_it"+std::to_string(step);
        add_cover_summary(out,key,r,false);
        out[key+"_lastfix"]=(r.flips[s.H-1][0]+r.flips[s.H-1][1])/P;
        double tail=0;
        for(int c=std::max(0,s.H-5);c<s.H;++c)tail+=r.flips[c][0]+r.flips[c][1];
        out[key+"_tailfix"]=tail/P;
    }
}
} // namespace deval
