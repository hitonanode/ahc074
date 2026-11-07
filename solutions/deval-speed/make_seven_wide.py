from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=R/'solutions/deval-chain-seven'
target=R/'solutions/deval-seven-wide'
target.mkdir(exist_ok=True)
s=(base/'main.cpp').read_text()
needle='        if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n        if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";',1)
(target/'main.cpp').write_text(s)
readme=(base/'README.md').read_text()
readme=readme.replace('# deval-chain-seven','# deval-seven-wide',1)
readme=readme.replace('改良元: solutions/deval-chain-finish-o3（設計・注文処理の基準はdeval-vbranch-nofb）。','改良元: solutions/deval-chain-seven（設計・注文処理の基準はdeval-vbranch-nofb）。',1)
readme=readme.replace('最良完成配置からの追加仕上げを4回から3回にして、固定で計7完成候補を比較する。','7完成候補の設計を保ち、neutral rewriteで保持する候補幅を2から3へ増やす。固定で計7完成候補を比較する。',1)
readme=readme.replace('注文探索は固定でREPEAT_MIN=0.05、POST_CANDIDATES=5。','注文探索は固定でREPEAT_MIN=0.05、POST_CANDIDATES=5、NEUTRAL_WIDTH=3。',1)
(target/'README.md').write_text(readme)
print(target.name,len(s.encode()))
