"""Avoid unpredictable merge branches by enumerating a compact pair bitset."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for sparse in [False,True]:
    parent='dcomp-nine-sparserel' if sparse else 'dcomp-nine-livepairs'
    s=(root/'solutions'/parent/'main.cpp').read_text()
    begin=s.index('    // An old compatible pair survives unchanged iff its raw arcs are equal.')
    end=s.index('#if DESIGN_PROFILE >= 3',begin)
    new='''    // Build a compact bitset, then enumerate in ascending pair order.
    // No unpredictable branch is needed to merge old and newly valid pairs.
    u64 live_bits[512];
    std::fill(live_bits,live_bits+P.words,u64(0));
    for(int p:P.live)live_bits[p>>6]|=u64(ndir[p]==pdir[p])<<(p&63);
    for(int k=0;k<nacyclic;++k){const int p=pending[k];live_bits[p>>6]|=u64(1)<<(p&63);}
    int nvalid=0;
    for(int w=0;w<P.words;++w)for(u64 bits=live_bits[w];bits;bits&=bits-1)
        valid[nvalid++]=64*w+__builtin_ctzll(bits);
'''
    if sparse:
        new+='    P.scratch_live.assign(valid,valid+nvalid);\n'
        # Before the new closures write their costs, retain exactly unchanged
        # old valid costs. A changed old pair gets zero here, then its new value.
        a='    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);'
        b='    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p]);\n'+a
        assert s.count(a)==1
        # Replace the list first, so the original indices stay valid.
        s=s[:begin]+new+s[end:]
        s=s.replace(a,b)
    else:s=s[:begin]+new+s[end:]
    name='dcomp-nine-sparsebits' if sparse else 'dcomp-nine-bitlive'
    p=root/'solutions'/name;p.mkdir(exist_ok=True)
    (p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: solutions/dcomp-nine\n\n窓探索で、旧互換ペアのうちrelation不変のものと新たに非循環と確認したペアを、小さなbitsetへ登録して昇順に列挙する。2本のリストの大小比較による分岐を避ける。'+('費用配列も非ゼロ要素だけを消去・更新する。受理時は状態用と作業用の非ゼロ一覧を交換する。' if sparse else '費用配列の更新は元のSIMD走査のまま。')+'\n\n互換一覧とその順序、すべての整数・浮動小数点費用、乱数、固定反復数、9候補、注文処理を保持。ログ、CLOCK_SCALE、@paper/@ops、DesignStore、段の目印、実験スイッチ・プロファイラはそのまま。時間不足の切替なし。\n')
