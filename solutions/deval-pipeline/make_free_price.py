from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-free-late/main.cpp').read_text()
needle='rematch_probability(*des, late_iterations, 1.05, 2.0, &extra, extra_mode)'
assert b.count(needle)==1
for name,weight in [('deval-free-price85','0.85'),('deval-free-price125','1.25'),
                    ('deval-free-pricemix','(warm_pass ? (deval_salt&2 ? 1.25 : 0.85) : 1.05)')]:
    s=b.replace(needle,'rematch_probability(*des, late_iterations, '+weight+', 2.0, &extra, extra_mode)',1)
    p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/deval-free-late`。\n\n単独紙の色固定を解除した穴あけ後の再割当てについて、filler価値の係数を'+
      ('全8候補で1.05から'+weight+'へ変える。' if 'mix' not in name else '元4枝と通常の再仕上げでは1.05、穴保存の再仕上げ2回では0.85と1.25に分ける。')+
      '制約を緩めた後の仕上げの費用対効果・多様性を測る。完成候補は従来のVで選び、候補数8・全ての探索回数は固定。時間不足による切り替えなし。\n')
    print(name,len(s.encode()))
