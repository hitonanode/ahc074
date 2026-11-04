    static inline double correlation_strength=0;
    static inline std::array<std::array<double,25>,25> head_covariance{};
    void refresh_covariance(){
        if(correlation_strength==0)return;
        std::array<std::array<int,25>,25>both{},black_first{},black_second{},black_both{};
        for(int t=0;t<P;t++){
            u64 mask=holes(unit[owner[t]]);
            for(u64 a=mask;a;a&=a-1){int j=__builtin_ctzll(a);for(u64 b=a&(a-1);b;b&=b-1){int k=__builtin_ctzll(b);int x=hb[t]>>j&1,y=hb[t]>>k&1;both[j][k]++;black_first[j][k]+=x;black_second[j][k]+=y;black_both[j][k]+=x*y;}}
        }
        std::array<double,25>rate{},black{},prob{};
        for(int j=0;j<H;j++){double r=2.0*nt[j];rate[j]=hn[j][0]+hn[j][1]+r;black[j]=hn[j][1]+r*(hn[j][1]>hn[j][0]);prob[j]=rate[j]?black[j]/rate[j]:.5;}
        for(int j=0;j<H;j++){head_covariance[j][j]=prob[j]*(1-prob[j]);for(int k=j+1;k<H;k++){
            double den=rate[j]+rate[k]-both[j][k],joint=den?((black[j]-black_first[j][k])*prob[k]+(black[k]-black_second[j][k])*prob[j]+black_both[j][k])/den:prob[j]*prob[k];
            assert(joint>=std::max(0.,prob[j]+prob[k]-1)-1e-8&&joint<=std::min(prob[j],prob[k])+1e-8);
            head_covariance[j][k]=head_covariance[k][j]=joint-prob[j]*prob[k];
        }}
    }
