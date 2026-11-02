#!/usr/bin/env python3
"""選定した3案の未使用宣言と到達しない分岐を整理する。"""
from pathlib import Path
import argparse, json
p=argparse.ArgumentParser()
p.add_argument('--all-tried',action='store_true',help='不採用になった再確認用の2案も復元する')
a=p.parse_args()
h=Path(__file__).resolve().parent
items=[('row256','main.cpp'),('row-temp25','cand2/main.cpp'),('row-rate80','cand3/main.cpp')]
if not a.all_tried: items=items[:1]
common='''交換元の汎用窓を初めて選んだとき、全ハンドル窓と2色の組合せを調べる。
現在の70対のうち不適合になる対が3未満の交換だけを、2本の64bit集合に保存する。
候補は同じ状態では重複なく選び、状態が受理されたら表を無効にする。
事前判定は改良元の「窓を1つ外したときの禁止方向」を再利用する。
繰り返し除外される交換を引き直す時間を、全商品対の評価へ回す。

候補生成が変わるため、停滞から脱出するまでの試行数を1024/2048から**256/512**へ短縮する。
逆手禁止は4受理分、不適合の除外境界は3対のまま。
目的関数、距離上限26、時間区切り0.50 / 0.61秒、他の段、CLOCK_SCALEは維持する。

追加のstderr指標:

- `window_rows`: 現在の状態で交換候補を列挙した窓数の累計。
- `window_samples`: 列挙した候補から提案した交換の累計。
'''
for source,target in items:
    s=(h/(source+'.cpp')).read_text()
    s=s.replace('    std::array<std::array<int, 128>, 64> window_priority{};\n','',1)
    start=s.index('        const bool checked = swindow;')
    end=s.index('            int lost = 0;',start)
    s=s[:start]+'''        // Window replacements and transfers have already passed their candidate tables.
        // Flips and exchanges of two generic windows still use the original scalar screen.
        if (selected.size() == unsigned(need) && !swindow && transfer < 0) {
'''+s[end:]
    s=s.replace('''                if (!(options[0] | options[1])) return false;

''','''                if (!(options[0] | options[1])) return false;
''')
    path=h/target;path.parent.mkdir(exist_ok=True);path.write_text(s)
    if source=='row256':
        extra='窓交換の割合0.6、残りの近傍の比率（色反転:組交換:組移動）3:5:2、温度0.05→0.00125は改良元と同じ。'
    elif source=='row-temp25':
        extra='窓交換の割合0.6、残りの近傍の比率3:5:2は同じ。焼きなまし温度だけを改良元の1/4、**0.0125→0.0003125**にする。低温での探索と停滞脱出を組み合わせる。'
    else:
        extra='窓交換の割合を0.6→**0.8**へ増やす。残りの近傍の比率（色反転:組交換:組移動）を3:5:2→**3:5:42**とし、組移動も調べる。温度0.05→0.00125は同じ。'
    (path.parent/'README.md').write_text('# astra-search5'+('' if source=='row256' else ' '+path.parent.name)+'\n\n改良元: solutions/astra-search4\n\n'+common+'\n'+extra+'\n')
(h/'final-sources.json').write_text(json.dumps(dict(items),indent=2)+'\n')
