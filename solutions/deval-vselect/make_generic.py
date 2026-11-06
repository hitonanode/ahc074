"""Calibrate only the generic-pair term; keep the handle objective unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vgeneric'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
old='gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]);'
assert old in src
src=src.replace('        struct E {\n            double w;',
    '        const double generic_scale=env_real("DEVAL_GENERIC_SCALE",1.3);\n        const double generic_curve=env_real("DEVAL_GENERIC_CURVE",0.);\n        struct E {\n            double w;',1)
src=src.replace(old,'''const double raw_generic=estimate(A[a],A[b]);
                const double curved=(.5325833906124751*raw_generic+.06253738130961652*raw_generic*raw_generic
                    +.015767541973285715*raw_generic*raw_generic*raw_generic)/.5191129881789601;
                gcost[a][b] = gcost[b][a] = generic_scale*((1-generic_curve)*raw_generic+generic_curve*curved);''')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vgeneric

改良元: `solutions/deval-vclean`。

handle の目的値を変えず、generic のペア費用だけを再校正する実験。ペア費用の表を作る際に倍率 `DEVAL_GENERIC_SCALE`（既定 1.3）を掛ける。`DEVAL_GENERIC_CURVE=1` では V の generic 1–3 次モーメントと列費用の係数から作った曲線に置き換える。これらは設計時の代理費用だけを変え、実際の紙と注文処理の規則は同じ。表を前計算するため、焼きなまし 1 手の計算量は増えない。

分岐・仕上げ・V による選択・時間ガードは親と同じ。生成は `solutions/deval-vselect/make_generic.py`。
''')
print('source bytes',len(src.encode()))
