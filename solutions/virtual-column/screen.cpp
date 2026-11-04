#include "common.hpp"

// The ordinary columns retain both colours. Removed single-target papers get
// a fully opaque generic mask and holes at every ordinary handle.
struct Selection {
    const Design& d;
    std::vector<int> candidates;
    explicit Selection(const Design& x): d(x) {
        for(int u=0;u<d.U;u++) if(d.unit[u].b<0)candidates.push_back(u);
    }
    double cost(const std::vector<int>& selected) const {
        auto nc=d.nc,nt=d.nt,n1=d.n1;
        auto hn=d.hn;
        for(int x:selected){
            const auto&u=d.unit[x];
            --nc[u.c];--nt[u.c];n1[u.c]-=d.color(u,u.c);
            for(u64 z=low_bits(d.H)&~d.holes(u);z;z&=z-1){
                int c=__builtin_ctzll(z);++hn[c][d.hb[u.a]>>c&1];
            }
        }
        int n=selected.size();
        double value=n*(2.+(n-1)*.5);
        for(int c=0;c<d.H;c++){
            value+=Design::colcost_of(nc[c],nt[c],n1[c],d.pairOne[c]);
            double x=hn[c][0],y=hn[c][1],t=Design::reset_strength*nt[c];
            value+=4*Design::kHoleWeight*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);
        }
        return value;
    }
    std::vector<int> choose(int n) const {
        std::vector<int> selected;
        for(int step=0;step<n;step++){
            double best=1e100;int bx=-1;
            for(int x:candidates){
                if(std::find(selected.begin(),selected.end(),x)!=selected.end())continue;
                selected.push_back(x);double value=cost(selected);selected.pop_back();
                if(value<best){best=value;bx=x;}
            }
            selected.push_back(bx);
        }
        // Small interactions between removals can change the cheapest members.
        for(int pass=0;pass<8;pass++){
            double best=cost(selected);int bi=-1,bx=-1;
            for(int i=0;i<n;i++)for(int x:candidates){
                if(std::find(selected.begin(),selected.end(),x)!=selected.end())continue;
                int old=selected[i];selected[i]=x;double value=cost(selected);selected[i]=old;
                if(value<best-1e-9){best=value;bi=i;bx=x;}
            }
            if(bi<0)break;selected[bi]=bx;
        }
        return selected;
    }
};

#ifndef VIRTUAL_SCREEN_LIBRARY
int main(int argc,char**argv){
    if(argc<3)return 2;auto s=head::load(argv[1],argv[2]);if(!s)return 3;
    auto d=recover(*s);d->refresh_reset();Selection selector(*d);
    double base=selector.cost({});std::cout<<std::setprecision(12)<<"[";
    for(int n=1;n<=8;n++){
        auto chosen=selector.choose(n);
        std::cout<<(n>1?",":"")<<"{\"n\":"<<n<<",\"difference\":"<<(selector.cost(chosen)-base)/P<<",\"units\":[";
        for(int i=0;i<n;i++)std::cout<<(i?",":"")<<chosen[i];std::cout<<"],\"columns\":[";
        for(int i=0;i<n;i++)std::cout<<(i?",":"")<<d->unit[chosen[i]].c;std::cout<<"]}";
    }
    std::cout<<"]\n";
}
#endif
