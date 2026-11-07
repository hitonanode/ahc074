from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
s=s.replace('struct NextPaper { int color, type, offset; };','struct NextPaper { uint16_t offset; uint8_t color, type; };',1)
s=s.replace('next_paper[k] = {column_color[k], colmdp_type[k], k * stride};','next_paper[k] = {uint16_t(k * stride), uint8_t(column_color[k]), uint8_t(colmdp_type[k])};',1)
a=s.index('        for (int i = 0; i < in_place; i++) {',s.index('double adaptive_next_cost'))
b=s.index('        // covered[c][color]',a)
s=s[:a]+'''        for(int i=0;i<in_place;) {
            const int c=next_paper[key[i]].color>>1;
            int depth=rank[c];
            uint32_t code=mdp_scan?mdp_code[c]:0;
            // Runs use register-local rank/code, but retain the exact global
            // left-to-right addition order. Disjoint runs of one column also work.
            do {
                const auto& np=next_paper[key[i]];
                if(first[np.color]<0)first[np.color]=depth;
                cost+=depth_terms[np.offset+depth];
                ++depth;
                if(mdp_scan)code=(code<<2)|np.type;
                ++i;
            } while(i<in_place && (next_paper[key[i]].color>>1)==c);
            rank[c]=depth;
            if(mdp_scan)mdp_code[c]=code;
        }
'''+s[b:]
d=ROOT/'solutions/deval-colrun';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-colrun

改良元: solutions/deval-vbranch-o3。

翌注文費用の走査で、同じ列が続く区間は順位と型列コードをレジスタ内で更新する。足す項の順序は紙の並びどおりで変わらず、同じ列が複数区間に分かれる場合も元の順位を引き継ぐ。紙の参照情報を整数の範囲に合わせて4バイトにまとめる。探索予算・浮動小数点の計算順・時間ガードは維持。
''')
print(len(s.encode()))
