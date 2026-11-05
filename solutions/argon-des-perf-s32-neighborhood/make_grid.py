"""32 層化標本での受理係数だけを比較する。既存解法は変更しない。"""
from pathlib import Path
import shutil

here = Path(__file__).resolve().parent
root = here.parent
base = root / 'argon-des-design-packed'
source = (base / 'main.cpp').read_text()
assert source.count('perforation.run(0.7);') == 1
(here / 'main.cpp').write_text(source)
for name, weight in [('s32w65', '0.65'), ('s32w75', '0.75'), ('s32w80', '0.8')]:
    out = root / ('argon-des-perf-' + name)
    out.mkdir()
    (out / 'main.cpp').write_text(source.replace('perforation.run(0.7);', f'perforation.run({weight});'))
    (out / 'README.md').write_text(f'''改良元: solutions/argon-des-design-packed

32個の層化色標本を用いる穿孔の受理係数だけを0.7から{weight}に変える。
列の穴コスト増分から、係数×条件付け補正済みフィラー利益を引いた値で受理する。
窓割当、ペア・列・ハンドル、フィラー交換、Hungarian、注文処理は基準と同じ。

新しいスイッチと指標はない。perforation_holes、perf_owner_raw、
perf_owner_conditioned、perf_donor、および既存の時刻・プロファイラで比較する。
既存のログ、@paper/@ops、CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持。
''')
for name in ['summarize.py', 'check_builds.py', 'identity.py']:
    shutil.copyfile(root / 'argon-des-design-speed' / name, here / name)
shutil.copyfile(root / 'argon-des-perf-neighborhood/effects.py', here / 'effects.py')

