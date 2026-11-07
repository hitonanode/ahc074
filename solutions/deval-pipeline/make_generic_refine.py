from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for iterations in [500,3000,12000]:
 name=f'deval-gref{iterations}'
 s=b.replace('// ==== Initial column order ====\n',(P/'generic_refine.inc').read_text()+'// ==== Initial column order ====\n',1)
 s=s.replace('//   Initial column order','//   Finished generic layout\n//   Initial column order',1)
 s=s.replace('if(finished)improve_initial_columns(state);',f'if(finished){{improve_initial_columns(state);improve_generic_layout(state,{iterations});}}',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n完成した専用紙とハンドルを固定し、最後に汎用紙6枚の比較窓配置だけを{iterations}回の山登りで調整する。実際のペアについて、汎用紙の全順序からの最小移動数の平均をPosetSumsで厳密計算する。全ペアの比較関係が非巡回、かつ汎用紙の全15組が比較される条件を守る。手は窓の極性反転、2窓の役割交換、他の比較組への移動。同費用も探索するが、出力は厳密改善をした最良配置。Vを直接最適化しない。\n\ngref_initial/finalは汎用紙の予測手数、gref_secは追加時間。固定seed・固定回数、時間不足による切り替えなし。保存設計には最終の汎用紙を含む。\n')
 print(name,len(s.encode()))
