"""Independent exact request micro-optimizations, built from the same parent."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/deval-vbranch-o3/main.cpp').read_text()
def save(name,source,description):
    d=root/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(source)
    (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{description}\n探索予算、候補の順序、浮動小数点の計算順、時間ガードは変更しない。\n')
    print(name,len(source.encode()))
old='''        return int(static_cast<const uint8_t*>(std::memchr(o.data(), k, K)) - o.data());'''
for n in [16,32]:
    code='''        const auto needle=_mm_set1_epi8(char(k));
        unsigned bits=unsigned(_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_loadu_si128(reinterpret_cast<const __m128i*>(o.data())),needle)));
'''
    if n==32:code+='''        bits|=unsigned(_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_loadu_si128(reinterpret_cast<const __m128i*>(o.data()+16)),needle)))<<16;
'''
    code+=f'''        if(bits)return __builtin_ctz(bits);
        const auto* p=static_cast<const uint8_t*>(std::memchr(o.data()+{n},k,K-{n}));
        return p?int(p-o.data()):-1;'''
    s=base.replace(old,code,1)
    s=s.replace('''        const auto* found = static_cast<const uint8_t*>(std::memchr(order.data(), k, K));
        return found ? int(found - order.data()) : -1;''','''        return find_paper(order,k);''',1)
    save(f'deval-find{n}',s,f'紙の位置を調べるとき、先頭{n}枚をインラインのSSE2比較で調べる。そこに無ければ残りにmemchrを使う。整数・バイト比較だけの変更。')
s=base.replace('mutable std::array<NextValueEntry, 256> next_value_cache;','mutable std::array<NextValueEntry, 1024> next_value_cache;',1)
save('deval-nextcache',s,'列の次状態価値の完全一致キャッシュを256項から1024項へ増やす。完全なキーの照合と格納値は同じ。')
s=base.replace('void prepare_post_context(const State& initial) {','void prepare_post_context(const State& initial, int target) {',1)
s=s.replace('c.blocks[0][j] = {paper[k].opaque, paper[k].black};','c.blocks[0][j] = {paper[k].opaque, (paper[k].black^A[target])&paper[k].opaque};',1)
s=s.replace('prepare_post_context(initial);','prepare_post_context(initial,u);',1)
s=s.replace('''                u64 seen = 0, view = 0;''','''                u64 seen = 0;''',1)
s=s.replace('''                    if ((disp ^ A[u]) & cov & ~seen) return false;
                    view |= disp & ~seen;''','''                    if (disp & ~seen) return false;''',1)
s=s.replace('                if (view != A[u]) return false;','                if (A[u] & ~seen) return false;',1)
s=s.replace('''        // A block maps incoming coverage to the first color on its opaque windows. Combining
        // overlapping sparse-table blocks is exact: the repeated overlap is already covered.''','''        // A block stores coverage and the windows whose first opaque paper
        // disagrees with this request. Overlap is already covered, as before.''',1)
save('deval-badblock',s,'後処理の区間表に、黒窓の代わりに注文と不一致の窓を保存する。毎回の区間判定でのXORと表示再構成を省く。未被覆の黒要求窓は元と同様に拒否する。')
