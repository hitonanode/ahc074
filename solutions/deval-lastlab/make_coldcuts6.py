from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
for mode in ['skip6','warm6','warm46']:
 name='deval-cold-'+mode;p=root/'solutions'/name;p.mkdir()
 if mode=='skip6':
  a='for(int j=0;j<4;++j) {\n        const int repeat='
  assert s.count(a)==1;x=s.replace(a,'for(int j=0;j<4;++j) {\n        if(j==2)continue;\n        const int repeat=');d='最後のcold再仕上げ(candidate 6)だけを省く。4本の枝、candidate 4,5,7とsaltは保ち、計7候補を完成する。'
 else:
  a='const bool warm=j%2==1;';assert s.count(a)==1
  x=s.replace(a,'const bool warm=j%2==1 || j==2;' if mode=='warm6' else 'const bool warm=true;')
  d='candidate 6だけを穴を保つwarm再仕上げに変える。計8候補、saltと乱数の初期化は元のまま。' if mode=='warm6' else '追加4候補を全て穴を保つwarm再仕上げに変える。計8候補、saltと乱数の初期化は元のまま。'
 (p/'main.cpp').write_text(x);(p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n'+d+'\n\n仕上げのうち、filler climb・穴あけ前rematch・穴を作り直す処理の費用を減らす実験。注文処理、最初4本の設計、固定予算、ログと実験スイッチは元と同じ。\n');assert len(x.encode())<=522000;print(name,len(x.encode()))
