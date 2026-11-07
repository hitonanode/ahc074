from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-free-color/main.cpp').read_text()
for name,mode in [('deval-free-late',1),('deval-free-all',2),('deval-free-body',3)]:
 s=b
 if mode in [1,2]:
  s=s.replace('const int extra_mode=warm_pass?4:0;','const int extra_mode=4;',1)
 if mode==2:
  s=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);','rematch_probability(*des, extra?1:2, 1.0, 2.0,nullptr,4);',1)
 if mode==3:
  s=s.replace('const bool flexible=(search_mode&4) && a<0;','const bool flexible=(search_mode&4) && a<0 && !head.beta[i];',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 description={1:'全8候補の穴あけ後の再割当てで、単独紙の元の色を固定しない。',2:'穴あけ前・後の全ての再割当てで、単独紙の元の色を固定しない。',3:'穴保存の2回の再割当てで、代表紙以外の単独紙だけ元の色を固定しない。代表紙の色を保ち、列の両色を確保する。'}[mode]
 (p/'README.md').write_text('改良元: `solutions/deval-free-color`。\n\n'+description+'巡回は従来の仕上げ目的の改善で受理し、完成設計をVで選ぶ。片色が消える提案は不採用。探索回数・候補数は同じで、時間不足の切り替えなし。\n')
 print(name,len(s.encode()))
