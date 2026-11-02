"""目的だけを変える実験用コード。提出候補は結果を見て別途生成する。"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'probe.cpp').read_text()
needle='    // Only `valid[0..nvalid)` is traversed here.'
new=r'''
    const double proxy_bias = std::getenv("PROXY_BIAS") ? std::atof(std::getenv("PROXY_BIAS")) : 0.0;
    const double proxy_sd = std::getenv("PROXY_SD") ? std::atof(std::getenv("PROXY_SD")) : 0.0;
    // Sum of squared global color imbalances for the handle mask, in eight table lookups.
    // This is independent of matching and can be precomputed once from the public barcodes.
    std::array<std::array<double,256>,8> bias_table{};
    for (int b=0; b<8; ++b) {
        std::array<double,8> weights{};
        for (int l=0; l<8; ++l) {
            int ones=0;
            for (u64 a:A) ones+=(a>>(8*b+l))&1;
            weights[l]=double((ones-128)*(ones-128))/(63-g);
        }
        for (int v=1; v<256; ++v)
            bias_table[b][v]=bias_table[b][v&(v-1)]+weights[__builtin_ctz(v)];
    }
'''
assert s.count(needle)==1
s=s.replace(needle,new+'\n'+needle)
needle='        return double(total) / (need * 3600) + (need - matched) * 10.0;'
new=r'''
        double bonus=0;
        if (proxy_bias) {
            double b2=0;
            for (int b=0; b<8; ++b) b2+=bias_table[b][(handle_mask>>(8*b))&255];
            bonus+=proxy_bias*b2;
        }
        if (proxy_sd) {
            // Bit-sliced counters: bit j of count[k] is bit k of the number of selected
            // pairs differing at window j. Seven lanes suffice for at most 71 pairs.
            u64 count[7]{};
            for (int p:candidate_selected) {
                u64 carry=pairs.diff[p]&handle_mask;
                for (int b=0; b<7; ++b) {
                    const u64 next=count[b]&carry;
                    count[b]^=carry;
                    carry=next;
                }
            }
            int sum=0, sq=0;
            for (int b=0; b<7; ++b) {
                int nbit=__builtin_popcountll(count[b]);
                sum+=nbit<<b;
                sq+=nbit<<(2*b);
                for (int c=0; c<b; ++c)
                    sq+=__builtin_popcountll(count[b]&count[c])<<(1+b+c);
            }
            const double mean=double(sum)/(63-g);
            bonus+=proxy_sd*std::sqrt(std::max(0.0,double(sq)/(63-g)-mean*mean));
        }
        return double(total) / (need * 3600) + (need - matched) * 10.0 - bonus;
'''
assert s.count(needle)==1
s=s.replace(needle,new)
(HERE/'variants.cpp').write_text(s)
