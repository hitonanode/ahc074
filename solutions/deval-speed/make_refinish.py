from pathlib import Path
R=Path(__file__).resolve().parents[2]
for n in [6,8]:
 parent=f'deval-best{n}';name=f'deval-refinish{n}'
 s=(R/'solutions'/parent/'main.cpp').read_text()
 needle='        branches.back().value=complete(i,0);'
 assert needle in s;s=s.replace(needle,needle+'''\n        // Restart the finishing from the completed target assignment; physical
        // perforations are rebuilt independently by the next completion.
        branches.back().raw=std::make_unique<Design>(*des);''',1)
 s=s.replace('// extra finishing attempts only on the two most promising raw branches.','// extra finishing attempts on the completed assignments of the best two branches.',1)
 # Retain the original diagnostic metrics for the chosen completion.
 needle='''        Design::kClimbProxyWeight=.5;
        double begin=elapsed_sec();'''
 repl='''        Design::kClimbProxyWeight=.5;
        std::cerr<<"colswap_tried = "<<des->colswap_tried<<"\\ncolswap_accepted = "<<des->colswap_accepted
                 <<"\\nreplace_tried = "<<des->replace_tried<<"\\nreplace_accepted = "<<des->replace_accepted<<'\\n';
        double begin=elapsed_sec();'''
 assert needle in s;s=s.replace(needle,repl,1)
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/{parent}。

最初の4候補を完成させて保持し、完成後のVが良い2候補の「穴あけ後再割当てまで済んだ対象・列の配置」を追加仕上げの開始点にする。climb25k・再割当て1回・穴あけ8サンプル・最終再割当ての一式を、固定saltを変えて計{n-4}回追加する。既存の物理的な穴は引き継がず、新しい対象配置に対して作り直す。元の4完成候補も含め、Vで選ぶ。

1交換ずつVで最適化する方式ではなく、従来の仕上げ工程をもう一度通した完成候補を比較する。窓割当て・焼きなまし・注文の予算は親と同じ。時間による打切りはない。DesignStore・ログ・@paper/@ops・段の目印を維持。
''')
 print(name,len(s.encode()))
