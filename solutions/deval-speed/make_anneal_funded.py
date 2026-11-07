from pathlib import Path
from remove_guards import remove_guards,ROOT
base=remove_guards((ROOT/'solutions/deval-funded650/main.cpp').read_text())
base=base.replace('kMapIters = int(650000 * ITER_SCALE)','kMapIters = int(450000 * ITER_SCALE)',1)
base=base.replace('static constexpr int kSamples = 16;','static constexpr int kSamples = 8;',1)
for name,six in [('deval-sixlong',True),('deval-anneal125',False)]:
 s=base
 if six:s=s.replace('const int candidates=4;','const int candidates=6;',1)
 else:s=s.replace('kAnnealIters = int(11175000 * ITER_SCALE)','kAnnealIters = int(13968750 * ITER_SCALE)',1)
 d=ROOT/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 desc='共有前半はそのまま、後半の分岐を同じ1/4予算のまま4個から6個へ増やす。焼きなましの総反復数は元の約1.25倍。' if six else '前半2段と4分岐の形はそのまま、焼きなましの反復予算を1.25倍にする。'
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-funded650（高速化の元はdeval-vbranch-o3）。

窓割当ては元の450,000回。{desc}
各分岐をclimb25k・再割当て1回後にVで上位2個へ選別し、通過した2個を再割当て1回・穴あけ8サンプル・最終再割当てまで仕上げる。Hungarian SIMD・整数の穴あけDPと差分更新・短いfiller列の内部保持を使う。

STATE.md07:20に合わせ、時間不足による候補削減・設計打切り・注文軽量化は外す。固定予算、固定乱数。DesignStoreと@paper/@ops・目次を維持。
''')
 print(name,len(s.encode()))
