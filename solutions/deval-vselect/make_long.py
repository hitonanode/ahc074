"""Spend the measured O3 saving on five percent more anneal iterations."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'deval-vbranch-o3'
DEST=HERE.parent/'deval-vlong'
src=(PARENT/'main.cpp').read_text()
assert src.count('kAnnealIters = int(11175000 * ITER_SCALE)')==1
src=src.replace('kAnnealIters = int(11175000 * ITER_SCALE)','kAnnealIters = int(11733750 * ITER_SCALE)')
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
f=json.loads((PARENT/'FROZEN.json').read_text())
f.update(parent=str(PARENT.relative_to(HERE.parent.parent)),generator='solutions/deval-vselect/make_long.py',
         parent_sha256=hashlib.sha256((PARENT/'main.cpp').read_bytes()).hexdigest(),
         source_sha256=hashlib.sha256(src.encode()).hexdigest(),source_bytes=len(src.encode()))
f['settings']['ANNEAL_ITERS']=11733750
(DEST/'FROZEN.json').write_text(json.dumps(f,indent=2)+'\n')
(DEST/'README.md').write_text('''# deval-vlong

改良元: `solutions/deval-vbranch-o3`。

GCCの設計関数の最適化で短縮した時間を使い、焼きなまし反復数を11,175,000から11,733,750へ5%増やす。前半2段共有、後半4分岐、後発候補の温度2倍、V16での選択、仕上げ予算と時間ガードは親と同じ。

提出用は `main.cpp` 1ファイル。Vの係数はseed 0–499で学習済み。DesignStoreは選択済みの設計を保存する。診断項目は親と共通。再生成は `../deval-vselect/make_long.py`。`FROZEN.json` に設定とソースハッシュを記録する。
''')
print('source bytes',len(src.encode()))
