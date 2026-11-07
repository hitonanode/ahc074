from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=R/'solutions/deval-chain-finish-o3'
target=R/'solutions/deval-chain-wide'
target.mkdir(exist_ok=True)
s=(base/'main.cpp').read_text()
needle='        if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n        if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";',1)
(target/'main.cpp').write_text(s)
(target/'README.md').write_text('''# deval-chain-wide

改良元: solutions/deval-chain-finish-o3。

8完成候補の作り方とV選択、高速化は改良元と同じ。注文のneutral rewriteで持つ候補幅を既定値から3へ増やし、GCC O3で得た残りの時間を注文探索に使う。固定設定はREPEAT_MIN=0.05、POST_CANDIDATES=5、NEUTRAL_WIDTH=3。実験時のF3_*による上書きは可能。時間による予算変更はない。

最初の4候補はclimb50k・再割当て2回、追加4候補は最良完成配置からclimb25k・再割当て1回。どの候補も穴あけ8サンプルと最終再割当てまで完成させる。窓・焼きなましの反復数とV16は基準のまま。物理的な穴は仕上げごとに作り直す。

時間不足による注文軽量化・設計時間上限・候補打切りは含めない。DesignStore、ログ、@paper/@ops、目次と段の目印を維持する。dv_candidatesは完成数、dv_chosenは採用番号、dv_*_secは全候補の合計時間。
''')
print(target.name,len(s.encode()))
