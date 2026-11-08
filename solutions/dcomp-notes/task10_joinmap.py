from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/dcomp-combo-ten/main.cpp').read_text()
for mode in ['if','mask']:
 s=b.replace('#if !defined(__clang__)\n','#if 1 // jointly maintain costs and the sorted live set\n')
 old='''    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p]);
#else
#endif
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);'''
 body='''    // Scratch costs outside scratch_live are already zero. Share the old-live
    // loads between cost retention and validity, then add newly closed pairs.
    u64 live_bits[512];
    std::fill(live_bits,live_bits+P.words,u64(0));
'''
 if mode=='if':body+='''    for(int p:P.live)if(ndir[p]==pdir[p]) {
        nrel[p]=prel[p];live_bits[p>>6]|=u64(1)<<(p&63);
    }
'''
 else:body+='''    for(int p:P.live) {
        const int keep=ndir[p]==pdir[p];
        nrel[p]=prel[p]*keep;live_bits[p>>6]|=u64(keep)<<(p&63);
    }
'''
 body+='''    for (int k = 0; k < nacyclic; ++k) {
        const int p=pending[k];
        nrel[p]=1+relations.sums.both_of(closures[k]);
        live_bits[p>>6]|=u64(1)<<(p&63);
    }
#else
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);
#endif'''
 assert s.count(old)==1;s=s.replace(old,body)
 a=s.index('    // Build a compact bitset, then enumerate in ascending pair order.\n');e=s.index('    int nvalid=0;\n',a)
 s=s[:a]+'    // Enumerate the shared validity bitset in the original ascending order.\n'+s[e:]
 name='dcomp-map-join-'+mode;p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('''改良元: solutions/dcomp-combo-ten

sparsebitsの旧互換ペアを走査する2本のループを統合する。同じndir/pdirを読み、費用を保持すると同時にvalidのbitsetを作る。新しい互換ペアも費用のlookupと同じループでbitを立てる。非ゼロ一覧だけを消す不変条件と昇順列挙は保持。'''+('relationが不変のときだけ費用とbitを書き、変わった場合のゼロ書込みを省く。' if mode=='if' else '費用とbitをkeepでマスクし、データ依存分岐を増やさない。')+'''\n\nClangでもこの統合経路を使う。探索・乱数・採否・浮動小数点は不変で、コンパイラごとに親との完全一致を検証する。ログ・実験スイッチを保持、固定予算で時間fallbackなし。\n''')
