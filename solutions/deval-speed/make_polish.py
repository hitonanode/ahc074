from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for parent,name in [('deval-sixlong','deval-sixpolish'),('deval-anneal125','deval-annealpolish')]:
 s=(ROOT/'solutions'/parent/'main.cpp').read_text()
 old='if (climb_iters > 0 && phase!=2)';assert old in s;s=s.replace(old,'if (climb_iters > 0)',1)
 d=ROOT/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/{parent}。

Vによる一次選別後、通過した2候補にfiller climbをさらに25,000回行ってから残りの仕上げをする。選択された候補には計50,000回のclimbを割り当て、一次選別で落ちる候補の後半を省く。選別前の再割当てにより、後半climbの確率と需要は再計算される。親の窓割当て・焼きなまし・V・穴あけ8サンプル・注文処理は同じ。

時間による探索削減なし。固定予算、固定乱数。DesignStoreと@paper/@ops・目次を維持。
''')
 print(name,len(s.encode()))
