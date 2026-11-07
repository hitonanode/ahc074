from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
a='double mix = 0.5, ctrl = 0, keep = 0.5, next_mix = 0.5, next_keep = 1.0;';assert s.count(a)==1
for v in [.25,.35]:
 name='deval-nextlow'+str(int(v*100));p=root/'solutions'/name;p.mkdir()
 x=s.replace(a,a.replace('next_mix = 0.5','next_mix = '+str(v)));(p/'main.cpp').write_text(x)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n列MDPを次状態のplan_costへ加える既定重みNEXTMIXだけを0.5から'+str(v)+'へ下げる。挿入位置のMDP重み、one-step模型、設計と探索予算は変えない。列ごとのMDPが互いのfillerを独立に扱うことによる、次状態価値の過大計上を弱める実験。全ログとスイッチを保ち、時刻では切り替えない。\n');print(name,len(x.encode()))
