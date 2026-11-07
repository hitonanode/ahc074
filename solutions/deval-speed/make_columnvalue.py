from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
idx=s.index('    double adaptive_next_cost(const GenericSplit& split) const {')
s=s[:idx]+'''    struct ColumnValueEntry {
        u64 low=0,high=0;
        double depth=0;
        float mdp=0;
        uint8_t first0=255,first1=255;
        bool valid=false;
    };
    mutable std::array<std::array<ColumnValueEntry,64>,64> column_value_cache;
    // The mathematical value is unchanged. Cache a column's depth sum and MDP
    // value by its complete ordered paper IDs. Grouping additions by column
    // changes double roundoff, so this path is validated as a search change.
    double grouped_next_cost(const uint8_t* papers,int count,const GenericSplit& split) const {
        std::array<std::array<u64,2>,64> codes{};
        std::array<int,64> sizes{};
        for(int i=0;i<count;++i) {
            const int k=papers[i],c=col_of[k],j=sizes[c]++;
            assert(j<16);
            codes[c][j>>3]|=u64(k+1)<<(8*(j&7));
        }
        std::array<bool,128> available{};
        if(top_d>=0&&column_color[top_d]>=0)available[column_color[top_d]]=true;
        for(const auto& f:fillers)if(column_color[f.paper]>=0)available[column_color[f.paper]]=true;
        std::array<const ColumnValueEntry*,64> entries;
        double cost=0;
        for(int c=0;c<H;++c) {
            const u64 hash=(codes[c][0]^std::rotl(codes[c][1],23))*0x9e3779b97f4a7c15ULL;
            auto& e=column_value_cache[c][hash>>58];
            if(!e.valid||e.low!=codes[c][0]||e.high!=codes[c][1]) {
                e.low=codes[c][0];e.high=codes[c][1];e.depth=0;e.first0=e.first1=255;
                int r=0,rank=0;
                const auto& mdp=colmdp[c];
                for(int j=0;j<sizes[c];++j) {
                    const int k=int(codes[c][j>>3]>>(8*(j&7))&255)-1;
                    const auto& np=next_paper[k];
                    auto& first=(np.color&1)?e.first1:e.first0;
                    if(first==255)first=j;
                    e.depth+=depth_terms[np.offset+j];
                }
                for(int j=sizes[c]-1;j>=0;--j) {
                    const int k=int(codes[c][j>>3]>>(8*(j&7))&255)-1;
                    const int type=next_paper[k].type;
                    r+=mdp.radix[type];rank+=mdp.before[r][type];
                }
                e.mdp=mdp.F[mdp.offset[r]+rank];e.valid=true;
            }
            cost+=e.depth;entries[c]=&e;
        }
        std::array<std::array<double,2>,64> covered{};
        for(const auto& f:fillers)if(split.below(f.paper)) {
            const auto& value=stay_table[f.paper][f.lvl];
            for(int c=0;c<H;++c) {
                const int color=h_blk[f.paper]>>c&1;
                covered[c][color]=std::max(covered[c][color],value.cover[c]);
            }
        }
        for(int c=0;c<H;++c)for(int color=0;color<2;++color) {
            const int first=color?entries[c]->first1:entries[c]->first0;
            const int fixes=available[2*c+color]?0:first==255?sizes[c]:first;
            cost+=(adaptive_holes[c][color]-kCoverStrength*covered[c][color])*fixes;
        }
        double term=-colmdp_next_drop*cost;
        for(int c=0;c<H;++c)term+=colmdp_next_weight[c]*entries[c]->mdp;
        return cost+term;
    }
'''+s[idx:]
needle='''        cf_value_misses++;
        std::array<int, 64> rank{};'''
assert needle in s
s=s.replace(needle,'''        cf_value_misses++;
        if(colmdp_next&&colmdp_columns==H) {
            const double cost=grouped_next_cost(key.data(),in_place,split);
            cached.size=key_size;
            std::memcpy(cached.key.data(),key.data(),key_size);
            cached.value=cost;
            return cost;
        }
        std::array<int, 64> rank{};''',1)
d=ROOT/'solutions/deval-columnvalue';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-columnvalue

改良元: solutions/deval-vbranch-o3。

注文計画の終状態評価で、各列の紙ID列を完全キーとして深さ費用・最初の各色・MDP値を保存する。全列のMDPを作れたケースだけ使い、それ以外は元の評価を使う。数式は同じだが、深さ項を列ごとに足すためdoubleの丸め順が変わる。注文処理の変更として固定設計の4列再評価で確認する。設計段・探索予算・時間ガードは維持。
''')
print(len(s.encode()))
