from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-ordered8/main.cpp').read_text()
a='''                for (int g = offset[m], e = offset[m] + int(mult[m]); g < e; g++)
                    for (int x = edge_start[g]; x < edge_start[g + 1]; x++) {
                        const int target = edge[x] >> 1;
                        Fv[target] = std::min(Fv[target], Fv[g]);
                        if (!(edge[x] & 1)) Hv[target] = std::min(Hv[target], Hv[g]);
                    }'''
b='''                for (int g = offset[m], e = offset[m] + int(mult[m]); g < e; g++) {
                    // Every edge deletes one paper, so no destination is g.
                    // Only the first deletion can be restricted to F.
                    const double fv=Fv[g],hv=Hv[g];
                    int x=edge_start[g];const int end=edge_start[g+1];
                    if(x<end && (edge[x]&1)) {
                        const int target=edge[x++]>>1;
                        Fv[target]=std::min(Fv[target],fv);
                    }
                    for(;x<end;++x) {
                        const int target=edge[x]>>1;
                        Fv[target]=std::min(Fv[target],fv);
                        Hv[target]=std::min(Hv[target],hv);
                    }
                }'''
assert a in s;s=s.replace(a,b,1)
p=R/'solutions/deval-mdp-dag';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n列MDPの値反復の削除DAG伝播を同値変形する。削除先は必ず短い列なので、伝播元F/Hを内側ループ外に読む。またHが使えない辺は最初の削除だけなので先に処理し、残りの辺から分岐を除く。浮動小数点の値・比較・列挙順を保ち、探索・予算は同じ。\n')
print(len(s.encode()))
