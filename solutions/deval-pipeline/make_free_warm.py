from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-free-color/main.cpp').read_text()
for name,n in [('deval-free-warm8',4),('deval-free-warm9',5)]:
 s=b.replace('for(int j=0;j<4;++j) {',f'for(int j=0;j<{n};++j) {{',1).replace('const bool warm=j%2==1;','const bool warm=j>0;',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-free-color`。\n\n元の4分岐の後、通常の再仕上げを1回、穴を保存する再仕上げを'+str(n-1)+'回行う。穴保存の最終再割当てでは単独紙の色を固定しない。各回は最良完成配置から始め、全'+str(4+n)+'候補をVで選ぶ。2回目の通常仕上げを省くことで、追加候補の費用を下げる。候補数・回数は固定で、時間による打切りなし。\n')
 print(name,len(s.encode()))
