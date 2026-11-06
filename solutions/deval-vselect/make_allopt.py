"""Extend the measured O3 experiment to the request functions."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vallopt'
src=(HERE.parent/'deval-vo3/main.cpp').read_text()
src=src.replace('#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC pop_options\n#endif\n// ==== Solver:', '// ==== Solver:')
src=src.replace('#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC push_options\n#pragma GCC optimize("O3")\n#endif\n// ==== Handle perforation', '// ==== Handle perforation')
assert src.count('#pragma GCC push_options')==src.count('#pragma GCC pop_options')==1
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vallopt

改良元: `solutions/deval-vo3`。

GCCのO3を注文処理の関数にも広げる速度比較。fast-mathを使わず、候補生成や計画の規則は変更しない。Clangでは既定の最適化。生成は `solutions/deval-vselect/make_allopt.py`。
''')
print('source bytes',len(src.encode()))
