from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-free-color/main.cpp').read_text()
for name,pre in [('deval-free-extra',False),('deval-free-extra-all',True)]:
 s=b.replace('const bool warm_pass=extra==2;','const bool warm_pass=extra>0;',1)
 if pre:s=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);','rematch_probability(*des, extra?1:2, 1.0, 2.0,nullptr,extra?4:0);',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-free-color`。\n\n元の4本の分岐とその仕上げを維持し、その後の4回の再仕上げで単独紙の色固定を外す。'+('穴あけ前・後の再割当ての両方に適用する。' if pre else '穴あけ後の再割当てに適用する。')+'列の両色が残ることを確認し、従来の仕上げ目的が下がる巡回だけ受理する。完成した8候補をVで選ぶ。全予算は固定。\n')
 print(name,len(s.encode()))
