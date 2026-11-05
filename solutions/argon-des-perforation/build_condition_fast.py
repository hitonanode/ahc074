"""Reuse the interval cache for the old-opacity side of a color flip."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
for source,name,wide in [('argon-des-perf-condition-v2','argon-des-perf-condfast',False),
                         ('argon-des-perf-condwide-v2','argon-des-perf-widefast',True)]:
    out=root/name;out.mkdir(exist_ok=True)
    s=(root/source/'main.cpp').read_text()
    old='                    const double flip_old = solve_edges(make_edges(u, samples[i] ^ changed'+(', i' if wide else '')+'));'
    assert old in s
    call='edge_column(u, samples[i] ^ changed, changed_handle, old_edge'+(', i'if wide else '')+')'
    fallback='solve_edges(make_edges(u, samples[i] ^ changed'+(', i'if wide else '')+'))'
    s=s.replace(old,f'''                    double flip_old;
                    if (cache_opacity[k] & changed) {{
                        // Before a hole is added, its window is covered by the target paper.
                        // Changing the head color changes only this column's donor price.
                        std::array<double, 65> old_edge;
                        const u64 old_starts = {call};
                        flip_old = q.avoid[changed_handle];
                        for (u64 bits = old_starts; bits; bits &= bits - 1) {{
                            const int lo = __builtin_ctzll(bits);
                            flip_old = std::max(flip_old, q.forward[lo] + old_edge[lo] + q.backward[changed_handle+1]);
                        }}
                    }} else {{
                        // A restored hole can affect all donor intervals in the old state.
                        flip_old = {fallback};
                    }}''')
    (out/'main.cpp').write_text(s)
    (out/'README.md').write_text((root/source/'README.md').read_text()+'''
条件付けの旧状態側では、穴を開ける前の窓は商品紙で覆われている。
その窓の列頭色を変えても、当該列から取るフィラーの価格しか変わらない。
全列DPの再計算を避け、既存のavoid/forward/backwardと1列の再評価で同じ最適値を求める。
''')
