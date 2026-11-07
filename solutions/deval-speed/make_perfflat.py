"""Keep perforation cache values contiguous; do not read untouched DP rows."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
dest=root/'solutions/deval-perfflat';dest.mkdir(exist_ok=True)
s=(root/'solutions/deval-vbranch-o3/main.cpp').read_text()
start=s.index('struct Perforation {');end=s.index('// ==== Design state:',start)
b=s[start:end]
b=b.replace('    std::vector<QueryCache> cache;','    std::vector<double> cache_values;\n    std::vector<QueryCache> cache;',1)
b=b.replace('        cache.resize(P * kSamples);','        cache.resize(P * kSamples);\n        cache_values.resize(P * kSamples);',1)
b=b.replace('                cache[i] = make_cache(make_edges(u, samples[i]));','                cache[i] = make_cache(make_edges(u, samples[i]));\n                cache_values[i]=cache[i].value;',1)
b=b.replace('        for (const auto& q : cache) sum += q.value;','        for (double v : cache_values) sum += v;',1)
begin=b.index('        double sum = 0;',b.index('    double total_profit('))
finish=b.index('        if (cache_opacity[k] & changed)',begin)
old=b[begin:finish]
new='''        std::copy(cache_values.begin(),cache_values.end(),values.begin());
        for(int u=0;u<P;++u) {
            if(s.ded[u]==k||same[u])continue;
            for(int sample=0;sample<kSamples;++sample) {
                const int i=u*kSamples+sample;
                const auto& q=cache[i];
                std::array<double, Capacity + 1> edge;
                const u64 valid = edge_column(u, samples[i], c, edge);
                double value = q.avoid[c];
                for (u64 z = valid; z; z &= z - 1) {
                    const int lo = __builtin_ctzll(z);
                    value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                }
                values[i] = value;
            }
        }
        // Same left-to-right addition, with identical row values. Unchanged
        // rows come from the compact value array instead of strided DP records.
        double sum=0;
        for(double value:values)sum+=value;
'''
b=b[:begin]+new+b[finish:]
s=s[:start]+b+s[end:]
(dest/'main.cpp').write_text(s)
(dest/'README.md').write_text('''# deval-perfflat

改良元: solutions/deval-vbranch-o3。

穴あけのDPキャッシュで、各行の最良値だけを連続した配列にも保存する。紙の変更に影響されない行は大きなDP表を読み直さず、その配列をコピーする。変更行の再計算と全行の加算順は元と同じ。探索内容と時間ガードは変更しない。
''')
print(dest,len(s.encode()))
