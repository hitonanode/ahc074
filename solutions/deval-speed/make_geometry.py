"""Hoist perforation edge geometry out of every head-color sample."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
start=s.index('    __attribute__((target("popcnt"))) u64 edge_column(')
end=s.index('    // The best set of disjoint intervals',start)
s=s[:start]+'''    struct Geometry {
        std::array<u64, 2> cover{};
        std::array<int, 2> lo{};
    };
    Geometry geometry_for(int u,int c) const {
        Geometry g;
        const int own=s.ded[u];
        if(c==columns[own]) { g.lo.fill(H+1); return g; }
        const u64 holes=low_bits(H)&~opacity[own];
        for(int b=0;b<2;++b) {
            const int k=heads[c][b];
            const u64 mask=opacity[k]&holes;
            const u64 wrong=mask&(colors[k]^target[u]);
            g.lo[b]=wrong?64-__builtin_clzll(wrong):0;
            g.cover[b]=mask&~low_bits(g.lo[b]);
        }
        return g;
    }
    std::array<Geometry,Capacity> all_geometry(int u) const {
        std::array<Geometry,Capacity> out;
        for(int c=0;c<H;++c)out[c]=geometry_for(u,c);
        return out;
    }
    // Integer geometry is constant across samples. The two donors, feasible
    // starts, and double operations below keep their original order.
    __attribute__((target("popcnt"))) u64 edge_column(int u, u64 color, int c,
            std::array<double, Capacity + 1>& edge,const Geometry& geometry) const {
        u64 valid=0;
        const u64 bad_mask=color^target[u];
        for(int b=0;b<2;++b) {
            const int lo=geometry.lo[b];
            if(lo>c)continue;
            const u64 covered=bad_mask&geometry.cover[b];
            int number=__builtin_popcountll(covered);
            const double price=1.6+(b!=int(color>>c&1));
            for(int start=lo;start<=c && number>price;++start) {
                const u64 bit=u64(1)<<start;
                const double v=number-price;
                edge[start]=valid&bit?std::max(edge[start],v):v;
                valid|=bit;
                number-=int(covered>>start&1);
            }
        }
        return valid;
    }
    Edges make_edges(int u,u64 color,const std::array<Geometry,Capacity>& geometry) const {
        Edges edges;
        for(int c=0;c<H;++c) {
            edges.starts[c]=edge_column(u,color,c,edges[c],geometry[c]);
            for(u64 z=edges.starts[c];z;z&=z-1)edges.ends[__builtin_ctzll(z)]|=u64(1)<<c;
        }
        return edges;
    }
'''+s[end:]
s=s.replace('            for (int sample = 0; sample < kSamples; sample++) {\n                int i = u * kSamples + sample;\n                cache[i] = make_cache(make_edges(u, samples[i]));',
'''            const auto geometry=all_geometry(u);
            for (int sample = 0; sample < kSamples; sample++) {
                int i = u * kSamples + sample;
                cache[i] = make_cache(make_edges(u, samples[i],geometry));''',1)
s=s.replace('double changed_window_value(int u, u64 color, int h, const QueryCache& q) const {','double changed_window_value(int u, u64 color, int h, const QueryCache& q, const std::array<Geometry,Capacity>& geometry) const {',1)
s=s.replace('edge_column(u, color, c, edge) & low_bits(h + 1)','edge_column(u, color, c, edge,geometry[c]) & low_bits(h + 1)',1)
s=s.replace('''        for (int u = 0; u < P; ++u) for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;''','''        for (int u = 0; u < P; ++u) {
          const auto geometry=geometry_for(u,c);
          for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;''',1)
s=s.replace('edge_column(u, samples[i], c, edge);','edge_column(u, samples[i], c, edge,geometry);',1)
s=s.replace('''            sum += values[i];
        }
        if (cache_opacity[k] & changed)''','''            sum += values[i];
          }
        }
        if (cache_opacity[k] & changed)''',1)
s=s.replace('''        for (int u : owners[k]) for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;''','''        for (int u : owners[k]) {
          const auto new_geometry=all_geometry(u);
          const u64 saved_opacity=opacity[k];
          opacity[k]=cache_opacity[k];
          const auto old_geometry=all_geometry(u);
          opacity[k]=saved_opacity;
          for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;''',1)
s=s.replace('changed_window_value(u, samples[i], changed_handle, q);','changed_window_value(u, samples[i], changed_handle, q,new_geometry);',1)
s=s.replace('changed_window_value(u, samples[i] ^ changed, changed_handle, q);','changed_window_value(u, samples[i] ^ changed, changed_handle, q,new_geometry);',1)
s=s.replace('''            const u64 saved_opacity = opacity[k];
            opacity[k] = cache_opacity[k];
            double flip_old;''','''            double flip_old;''',1)
s=s.replace('edge_column(u, samples[i] ^ changed, changed_handle, old_edge);','edge_column(u, samples[i] ^ changed, changed_handle, old_edge,old_geometry[changed_handle]);',1)
s=s.replace('changed_window_value(u, samples[i] ^ changed, changed_handle, q);','changed_window_value(u, samples[i] ^ changed, changed_handle, q,old_geometry);',1)
s=s.replace('''            opacity[k] = saved_opacity;
            const int b = int(samples[i] >> changed_handle & 1);''','''            const int b = int(samples[i] >> changed_handle & 1);''',1)
s=s.replace('''            values[i] = value;

        }
        // Retain the original order''','''            values[i] = value;
          }
        }
        // Retain the original order''',1)
d=ROOT/'solutions/deval-geometry';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-geometry

改良元: solutions/deval-vbranch-o3。

穴あけのDP辺について、紙と注文先で決まる整数の被覆範囲・開始可能位置を色サンプルのループ外で計算する。同じ対象の32サンプルで共有する。穴を変更した紙自身の注文については変更前後の二種類を先に作る。浮動小数点の計算順、サンプル、探索予算、時間ガードは同じ。
''')
print(len(s.encode()))
