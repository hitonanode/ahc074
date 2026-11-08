from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-eject-known/main.cpp').read_text();a=s.index('void eject_repairs(');b=s.index('// ==== Post-processing: two deletions and two repairs',a);t=s[a:b]
def sub(x,y):
 global t
 assert t.count(x)==1,(x[:90],t.count(x));t=t.replace(x,y)
sub('if (one) owner_stamp[k] = trial_stamp;', '''// Stamp every materialized prefix paper; non-owners have owned=0.
                        owner_stamp[k] = trial_stamp;''')
sub('''                    prepare_order();
                    prepare_positions();''','''                    prepare_positions();''')
sub('''                    const int pos = ord_position[k];''','''                    // A paper beyond the top-two-layer prefix is below every relevant
                    // first owner. K has the same effect on the geometry as its actual rank.
                    int pos = owner_stamp[k]==trial_stamp?ord_position[k]:K;''')
sub('''                    if (lo > hi) continue;
                    // the order without k:''','''#ifdef EJECT_GEOM_CHECK
                    prepare_order();
                    {
                        const int rp=ord_position[k];int rl=0,rh=K-1;
                        auto actual=[&](int w){const int p=first[w]==rp?second[w]:first[w];return p-int(p>rp);};
                        for(u64 z=bad;z;z&=z-1)rh=std::min(rh,actual(__builtin_ctzll(z)));
                        for(u64 z=wrong;z && rl<=rh;z&=z-1)rl=std::max(rl,actual(__builtin_ctzll(z))+1);
                        if(rl!=lo || rh!=hi){std::cerr<<"EJECT_GEOMETRY_MISMATCH\\n";std::abort();}
                    }
#endif
                    if (lo > hi) continue;
                    prepare_order();pos=ord_position[k];
                    // the order without k:''')
s=s[:a]+t+s[b:]
for check in [False,True]:
 p=r/'solutions'/('dcomp-eject-geometry'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define EJECT_GEOM_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-eject-known\n\n取り出し修復のgap区間が空かどうかを上位2層のprefixだけで判定する。prefixより深い修復紙の順位は、すべての参照する先頭紙より下なので仮にKとして同じ区間を計算できる。区間が残った場合にだけ残りのorderをmaterializeする。元の候補と演算は不変。検証版は毎回完全orderで区間を再計算して照合。予算・ログ・DesignStore・実験スイッチを維持。\n')
