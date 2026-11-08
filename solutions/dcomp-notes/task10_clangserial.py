from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=(r/'solutions/dcomp-combo-ten/main.cpp').read_text().replace('#if !defined(__clang__)\n','#if 1 // sparse path, scalar indirect loops on Clang\n')
pr='#ifdef __clang__\n#pragma clang loop vectorize(disable) interleave(disable) unroll(disable)\n#endif\n'
for old in ['    for(int p:P.scratch_live)nrel[p]=0;','    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p]);','    for(int p:P.live)live_bits[p>>6]|=u64(ndir[p]==pdir[p])<<(p&63);','    for(int k=0;k<nacyclic;++k){const int p=pending[k];live_bits[p>>6]|=u64(1)<<(p&63);}','    for(int w=0;w<P.words;++w)for(u64 bits=live_bits[w];bits;bits&=bits-1)']:
 assert s.count(old)==1;s=s.replace(old,pr+old)
p=r/'solutions/dcomp-clang-map-serial';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-combo-ten

ClangでTask 9のsparsebitsを有効にし、非連続indexを扱う短いループだけvectorize/interleave/unrollを抑える。Clangの計測ではSIMD本体は速く、追加の疎なlookupとvalid一覧作成で遅くなっているため、そのループのコード生成を分けて検証する。整数処理だけの変更。元の探索・採否・浮動小数点・ログを維持する。時間fallbackはない。
''')
