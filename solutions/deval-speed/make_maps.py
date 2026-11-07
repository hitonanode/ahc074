from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
for name,changes,desc in [
 ('mapcold',[('0.05 * std::pow(0.00125 / 0.05, progress)','0.025 * std::pow(0.000625 / 0.025, progress)')], '窓割当ての温度を全行程で1/2にする'),
 ('mapwarm',[('0.05 * std::pow(0.00125 / 0.05, progress)','0.1 * std::pow(0.0025 / 0.1, progress)')], '窓割当ての温度を全行程で2倍にする'),
 ('mapwindow8',[('constexpr double kWindowRate = 0.6;','constexpr double kWindowRate = 0.8;')], '窓の交換提案の比率を0.6から0.8にする'),
 ('mapstall128',[('kMapStall = 256, kClimbStall = 512','kMapStall = 128, kClimbStall = 256')], '停滞から抜ける提案を2倍の頻度で行う'),
]:
    s=base
    for a,b in changes:assert a in s;s=s.replace(a,b,1)
    d=ROOT/('solutions/deval-'+name);d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'# deval-{name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{desc}。反復数、仕上げ、Vの選択、注文処理、時間ガードは同じ。\n')
