    static inline double future_strength=0, future_gate=1e100;
    static inline bool future_enabled=false;
    long long future_changes=0,future_calls=0;
    double future_seconds=0;
    std::vector<u64> future_ranges;
    std::vector<unsigned char> future_levels;
    std::vector<int> direct_frequency;
    // Returns the amount to subtract from the old one-step value. The old
    // linear filler demand is replaced by the disjoint-interval benefit.
    __attribute__((target("popcnt"))) double future_correction(){
        const double started=elapsed_sec();future_calls++;
        if(future_ranges.empty()){
            future_ranges.resize(P*K);future_levels.resize(P*K);direct_frequency.assign(K,0);
            for(int t=0;t<P;t++){
                direct_frequency[ded[t]]++;u64 bits=handle_bits(A[t]);
                for(int k=M+1;k<K;k++){
                    u64 range=h_opq[k]&~h_opq[ded[t]],wrong=(h_blk[k]^bits)&range;
                    int lo=wrong?64-__builtin_clzll(wrong):0;
                    future_ranges[t*K+k]=range&~low_bits(lo);future_levels[t*K+k]=lo;
                }
            }
        }
        std::array<std::array<int,2>,25>head{},depth{};
        std::array<std::array<bool,2>,25>available{};std::array<int,25>rank{};
        for(int c=0;c<H;c++)head[c]={-1,-1},depth[c]={-1,-1};
        double extra=0;
        for(int k:order){
            int c=col_of[k];if(c<0)continue;int color=h_blk[k]>>c&1;
            if(k==top_d||is_filler(k)){available[c][color]=true;continue;}
            if(head[c][color]<0){head[c][color]=k;depth[c][color]=rank[c];}
            extra+=(adaptive_weights[k]-direct_frequency[k])*rank[c]/P;rank[c]++;
        }
        std::array<std::array<u64,6>,2>prices{};
        for(int c=0;c<H;c++)for(int b=0;b<2;b++){
            int value=available[c][b]?0:depth[c][b];if(value<0)value=rank[c];
            for(int bit=0;bit<6;bit++)if(value>>bit&1)prices[b][bit]|=1ULL<<c;
        }
        double total=0;
        for(int t=0;t<P;t++){
            u64 bits=handle_bits(A[t]),holes=low_bits(H)&~h_opq[ded[t]],bad=0;std::array<u64,6>planes{};
            for(int bit=0;bit<6;bit++){planes[bit]=((prices[0][bit]&~bits)|(prices[1][bit]&bits))&holes;bad|=planes[bit];}
            if(!bad)continue;std::array<double,26>dp{};
            for(int c=0;c<H;c++){
                dp[c+1]=dp[c];if(c==col_of[ded[t]])continue;
                for(int b=0;b<2;b++){
                    int k=head[c][b];if(k<0)continue;int lo=future_levels[t*K+k];if(lo>c)continue;
                    u64 covered=future_ranges[t*K+k]&bad;int number=0;
                    for(int bit=0;bit<6;bit++)number+=(1<<bit)*__builtin_popcountll(covered&planes[bit]);
                    double charge=1.6+depth[c][b];
                    for(int start=lo;start<=c&&number>charge;start++){
                        dp[c+1]=std::max(dp[c+1],dp[start]+number-charge);
                        if(covered>>start&1)for(int bit=0;bit<6;bit++)number-=(1<<bit)*int(planes[bit]>>start&1);
                    }
                }
            }
            total+=dp[H]/P;
        }
        future_seconds+=elapsed_sec()-started;return extra+total;
    }
