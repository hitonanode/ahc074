from pathlib import Path
P=Path(__file__).resolve().parent; root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
old='selected.size() == unsigned(need) && rng.mod(16) == 0;'
assert s.count(old)==1
for divisor in [32,64]:
    name=f'deval-cross{divisor}'
    p=root/'solutions'/name;p.mkdir()
    t=s.replace(old,f'selected.size() == unsigned(need) && rng.mod({divisor}) == 0;')
    (p/'main.cpp').write_text(t)
    (p/'README.md').write_text(f'''改良元: `solutions/deval-trim6b`。

窓割当てのcross移動（汎用窓をハンドルへ移し、別の辺に別のハンドルを入れる）の提案率を1/16から1/{divisor}へ下げ、その分は通常の窓交換を提案する。プロファイルでcrossの候補生成・matchingが重いため、同じ固定反復数で時間と品質の釣合いを調べる。目的関数、受理、窓割当ての450kとclimb 133k、完成8候補、注文処理は元のまま。時間による予算変更はない。gobjだけで採否を決めず、8列replayで確認する。
''')
    assert len(t.encode())<=522000
    print(name,len(t.encode()))
