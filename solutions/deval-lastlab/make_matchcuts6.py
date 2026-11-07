from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
for n in [0,1]:
 name='deval-prematch'+str(n);p=root/'solutions'/name;p.mkdir()
 x=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);',f'rematch_probability(*des, extra?1:{n}, 1.0, 2.0);')
 assert x!=s
 (p/'main.cpp').write_text(x)
 (p/'README.md').write_text(f'改良元: `solutions/deval-trim6b`。\n\n最初の4分岐で、穴あけ前のHungarian再割当てを2回から{n}回へ減らす。追加coldの再割当ては1回、穴あけ後の再割当ては全候補1回を保つ。完成8候補をVで選択する。その他の設計と注文の予算は同じ。全て固定回数で、時刻による切替えはない。\n')
