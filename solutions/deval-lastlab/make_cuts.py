from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6/main.cpp').read_text()
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6`（deval-flex125-plan3と出力同一の整理）。\n\n'+d+'\n\n注文処理は元と同じ。元の探索回数を各ケース共通に固定し、時刻で候補数・予算を変えない。DesignStoreと注釈・統計・実験スイッチを保つ。\n')
 print(n,len(text.encode()))
for n in [3,2]:
 x=s.replace('const int candidates=4;',f'const int candidates={n};').replace('id=candidates+j;','id=4+j;')
 emit(f'deval-cut{n}-branches',x,f'焼きなまし後半の枝を4本から{n}本に減らす。共有前半・各枝の回数は同じ。追加のcold/warm各2回の再仕上げとsalt 4–7は維持する。')
emit('deval-cut-climb30',s.replace('const int climb_env = 50000','const int climb_env = 30000'),'最初の4枝のfiller climbを50kから30kへ短縮する。cold再仕上げの25k、候補数8は同じ。')
emit('deval-cut-gopt80',s.replace('kGoptSteps = int(133000','kGoptSteps = int(80000'),'窓割当て後のマッチングclimbを133kから80kへ短縮する。他の予算と完成8候補は同じ。')
emit('deval-cut-anneal90',s.replace('kAnnealIters = int(11175000','kAnnealIters = int(10057500'),'設計の焼きなまし回数を全段0.9倍にする。窓割当て・仕上げ・8候補は同じ。')
