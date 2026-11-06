"""Measure GCC's O3 for the design kernels, without changing floating-point rules."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vo3'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
for begin,end in [('Generic layer: the comparator of the six sheets','Solver: papers, handles and the generic look-ahead'),('Handle perforation','Saving and loading the design state (LOCAL_BENCH: DesignStore)')]:
    src=src.replace('// ==== '+begin+' ====','#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC push_options\n#pragma GCC optimize("O3")\n#endif\n// ==== '+begin+' ====')
    # The second region ends after #ifdef LOCAL_BENCH, so pop before that guard.
    needle='// ==== '+end+' ===='
    if end.startswith('Saving'):
        needle='#ifdef LOCAL_BENCH\n'+needle
    src=src.replace(needle,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC pop_options\n#endif\n'+needle)
assert len(src.encode())<520000
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vo3

改良元: `solutions/deval-vclean`。

設計段の関数だけ GCC の O3 最適化を有効にする比較実験。fast-math は使わない。Clang は既定の最適化のまま。候補作成、V、固定反復数、時間ガードは親と同じ。コンパイルコマンドは通常どおり C++23 / O2。

再生成: `solutions/deval-vselect/make_o3.py`。
''')
print('source bytes',len(src.encode()))
