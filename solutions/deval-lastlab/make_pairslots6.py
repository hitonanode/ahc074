from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-unit-warm/main.cpp').read_text()
# Whole paired papers may move among pair slots; singleton slots remain fixed.
# The number of targets and papers of each column is unchanged, so reset rates stay fixed.
s=s.replace('d.rebuild();if(whole)d.refresh_reset();','d.rebuild();')
old='''                int a=whole?units[j].b:anchor[i],b=whole?units[j].a:mobile[j];'''
new='''                if(whole && i!=j && (units[i].b<0 || units[j].b<0))continue;
                int a=whole?units[j].b:anchor[i],b=whole?units[j].a:mobile[j];'''
assert s.count(old)==1;s=s.replace(old,new)
for last in [False,True]:
    x=s
    if last:x=x.replace('const int extra_mode=4|(whole_units?8:0);','const int extra_mode=4|((whole_units && deval_salt==first_salt+7)?8:0);')
    name='deval-pairslots-'+('last' if last else 'warm')
    p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
    (p/'README.md').write_text('''改良元: `solutions/deval-unit-warm`。

'''+('最後のwarm再仕上げだけ' if last else 'warm再仕上げ2回')+'''、最終再割当てでペア紙全体を別のペアslotに動かせるようにする。単独紙のslotはこの回では固定し、各列の紙数・ペア数・目標数は変えない。ペアは窓割当てへの互換性と自列のハンドルの一致を満たす必要があり、列の両色を失う巡回は棄却する。紙の色固定は外し、色別ペア数の列費用差を提案に含める。巡回は既存の穴＋列＋汎用費用−1.25×filler価値の正確な減少で受理し、完成8候補をVで選ぶ。穴は物理slotに付随する。他の再割当ては従来の1目標ずつの移動を使う。全予算固定、時刻による切替えはない。
''')
    assert len(x.encode())<=522000;print(name,len(x.encode()))
