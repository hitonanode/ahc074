from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-ordered8/main.cpp').read_text()
s=s.replace('''        ANNEAL_TARGET void column_move(int x, int y,''','''        template<int sy>
        ANNEAL_TARGET void column_move(int x, int y,''',1)
s=s.replace('''            const int sy = ny.c == oy.c ? 0 : (oy.c == P ? -1 : 1);
''','',1)
a=s.index('        template<int sy>\n        ANNEAL_TARGET void column_move');z=s.index('        // An exchange of targets',a)
x=s[a:z].replace('if (ny.c != oy.c) {','if constexpr (sy != 0) {');s=s[:a]+x+s[z:]
old='''                column_move(x, y, ox, oy, nx, ny);                               // (the pairs are compatible)'''
new='''                // Specialize the three move kinds without changing any counts or reductions.
                if(ny.c==oy.c)column_move<0>(x,y,ox,oy,nx,ny);
                else if(oy.c==ox.c)column_move<-1>(x,y,ox,oy,nx,ny);
                else column_move<1>(x,y,ox,oy,nx,ny);'''
assert old in s;s=s.replace(old,new,1)
p=R/'solutions/deval-column-kind';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n焼きなましの列移動を、1ユニットだけ移動・2ユニットが同方向・2ユニットを交換の3種類でテンプレート化する。移動種類に依存する整数演算と不要な読み出しをコンパイル時に省く。提案・乱数・浮動小数点の評価と還元順は同じ。固定予算の出力同一高速化案。\n')
print(len(s.encode()))
