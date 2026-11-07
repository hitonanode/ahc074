from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-ejectskeleton/main.cpp').read_text()
a=s.index('    void eject_repairs(');b=s.index('    // ==== Post-processing: two deletions and two repairs',a);v=s[a:b]
v=v.replace('        std::array<int, K> owner_stamp{};','''        std::array<int,K> thin,thin_position,thin_stamp{};
        int thin_count=0;
        std::array<int, K> owner_stamp{};''',1)
v=v.replace('''                trial_stamp++;
                {''','''                trial_stamp++;thin_count=0;
                {''',1)
v=v.replace('''                    for(int k=nx[root];k!=root;k=nx[k]) {
                        const u64 two''','''                    for(int k=nx[root];k!=root;k=nx[k]) {
                        thin[thin_count]=k;thin_position[k]=thin_count++;thin_stamp[k]=trial_stamp;
                        const u64 two''',1)
old='''                    for (int t = 0; t < K; t++) {
                        int k = ord[t];
                        u64 two = paper[k].opaque & once_seen & ~twice_seen, one = paper[k].opaque & ~once_seen;
                        for (u64 z = two; z; z &= z - 1) second[__builtin_ctzll(z)] = t;
                        for (u64 z = one; z; z &= z - 1) first[__builtin_ctzll(z)] = t;'''
new='''                    // Store owner IDs: both compressed and full positions can
                    // later be read without rebuilding the top-two layers.
                    for (int t = 0; t < thin_count; t++) {
                        int k = thin[t];
                        u64 two = paper[k].opaque & once_seen & ~twice_seen, one = paper[k].opaque & ~once_seen;
                        for (u64 z = two; z; z &= z - 1) second[__builtin_ctzll(z)] = k;
                        for (u64 z = one; z; z &= z - 1) first[__builtin_ctzll(z)] = k;'''
assert old in v;v=v.replace(old,new,1)
old='''                    prepare_order();
                    prepare_positions();
                    // without_pos(w):'''
new='''                    prepare_positions();
                    // Feasibility requires every lower-bound owner to precede
                    // every upper-bound owner. Filtering preserves that strict
                    // order, so reject empty intervals before materializing K papers.
                    const int thin_pos=thin_stamp[k]==trial_stamp?thin_position[k]:K;
                    int lower=0,upper=K-1;
                    auto thin_without=[&](int w) {
                        const int owner=first[w]==k?second[w]:first[w];
                        const int p=owner==K?K:thin_position[owner];
                        return p-int(p>thin_pos);
                    };
                    for(u64 z=bad;z;z&=z-1)upper=std::min(upper,thin_without(__builtin_ctzll(z)));
                    for(u64 z=wrong;z&&lower<=upper;z&=z-1)lower=std::max(lower,thin_without(__builtin_ctzll(z))+1);
                    if(lower>upper)continue;
                    prepare_order();
                    // without_pos(w):'''
assert old in v;v=v.replace(old,new,1)
v=v.replace('''                        int p = first[w] == pos ? second[w] : first[w];
                        return p - int(p > pos);''','''                        const int owner=first[w]==k?second[w]:first[w];
                        const int p=owner==K?K:ord_position[owner];
                        return p - int(p > pos);''',1)
s=s[:a]+v+s[b:]
d=R/'solutions/deval-ejectinterval';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-ejectinterval

改良元: solutions/deval-ejectskeleton。

修復する紙の差込区間が空かどうかを、短い列の順位で先に判定する。条件は「下限を決める紙が、上限を決める紙より先にある」なので、紙の相対順序を保つ間引きで変わらない。上位2枚は紙IDで保存し、実際に区間がある試行だけ全192枚の位置を作る。差込先の列挙には従来と同じ完全な順位を使う。

探索予算・列挙順・浮動小数点の計算順は親と同じ。時間による探索削減はない。
''')
print(len(s.encode()))
