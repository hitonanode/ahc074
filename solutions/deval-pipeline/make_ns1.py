from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
for name,parent in [('deval-flex8-ns1','deval-flex8-fast'),('deval-flex8-ns1-plan3','deval-flex8-fast-plan3')]:
    s=(R/'solutions'/parent/'main.cpp').read_text();old='get("NS_ROUNDS", 2)';assert s.count(old)==1
    s=s.replace(old,'get("NS_ROUNDS", 1)',1);p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/'+parent+'`。\n\n注文後処理のneutral rewriteの反復数を2から1へ減らす。'+('同手数の計画も後処理するPLAN_SHORTLIST=3との費用対効果を測る。' if 'plan3' in name else '元のPLAN_SHORTLIST=2で反復削減の対照を測る。')+'設計・他の予算は同じで、全て固定回数。時間不足による切り替えなし。\n')
    print(name,len(s.encode()))
