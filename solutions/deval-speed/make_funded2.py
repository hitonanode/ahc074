from pathlib import Path
from remove_guards import remove_guards,ROOT
base=(ROOT/'solutions/deval-funded650/main.cpp').read_text()
for name,map_iters,cold,stall in [('deval-cold600',600000,True,False),('deval-stall450',450000,False,True)]:
 s=remove_guards(base)
 s=s.replace('kMapIters = int(650000 * ITER_SCALE)',f'kMapIters = int({map_iters} * ITER_SCALE)',1)
 if cold:s=s.replace('0.05 * std::pow(0.00125 / 0.05, progress)','0.025 * std::pow(0.000625 / 0.025, progress)',1)
 if stall:s=s.replace('kMapStall = 256, kClimbStall = 512','kMapStall = 128, kClimbStall = 256',1)
 d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
 (d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-funded650（高速化の元はdeval-vbranch-o3）。

窓割当て{map_iters:,}回。{'温度を全行程で1/2にする。' if cold else '停滞を抜ける提案の間隔を半分にする。'}
Hungarian SIMD、整数の穴あけDPと差分更新、短いfiller列の内部保持を使用。4分岐をclimb25k・再割当て1回後にVで上位2個へ選別し、通過した2個を再割当て1回・穴あけ16サンプル・最終再割当てまで仕上げる。

STATE.mdの07:20追記に合わせて、時間不足による候補削減・設計打切り・注文軽量化は外す。探索予算は固定。時計はCLOCK_SCALE経由。DesignStoreは選択した設計を保存し、@paper/@ops・段の目印と目次を維持する。
''')
 print(name,len(s.encode()))
