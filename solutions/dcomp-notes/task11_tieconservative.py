"""One actual-policy check: rollout SE is too large to resolve a sub-0.01% gain."""
from pathlib import Path
import json,re
N=Path(__file__).resolve().parent;ROOT=N.parents[1]
d=json.loads((N/'t11-tiefit.json').read_text())
# Select by mean+1SE of the held-out training-label split. The most regularized
# fit wins this conservative criterion; do not search more models on real scores.
m=min(d['models'],key=lambda m:m['validation']['moves']['mean']+m['validation']['moves']['se'])
assert m['alpha']==1000.
s=(ROOT/'solutions/dcomp-combo-alt1/main.cpp').read_text()
s=re.sub(r'kTieConst = [-+0-9.eE]+',f"kTieConst = {m['intercept']:.17g}",s)
s=re.sub(r'kTieCoef = \{[^}]+\}', 'kTieCoef = {'+', '.join(f'{x:.17g}'for x in m['coefficients'])+'}',s)
p=ROOT/'solutions/dcomp-t11-tie-conservative';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n近接選択の9特徴・gap .3・探索予算を変えず、線形係数だけをalt1のロールアウトで再推定する。seed0–199で従来係数をpriorとするridge、200–299のラベルで平均差+1SEが最小となるalpha1000を選んだ。ラベルのSEは小利得の判定には大きいため、この係数1本だけを実replayで検証する。\n\n教師run '+d['run']+'。ラベルは当該候補の最終merge前の手数と、同じ乱数による未来40本×5注文の実方策の手数の和。最終mergeで当該手数が減る効果はラベルに含まれず、実replayを最終判定とする。追加探索はなく、両コンパイラ共通係数。時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
