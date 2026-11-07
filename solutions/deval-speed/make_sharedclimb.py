from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-best8/main.cpp').read_text()
for name,extras,rounds,top in [('deval-sharedclimb8',4,2,2),('deval-sharedclimb10',6,1,3)]:
 s=base.replace('    auto finish = [&](Design* des,bool raw=false,int extra=0) {','    std::unique_ptr<Design> climbed;\n    auto finish = [&](Design* des,bool raw=false,int extra=0) {',1)
 s=s.replace('if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);','if (climb_iters > 0 && !extra) des->filler_climb(1e300, climb_iters);\n    if(!extra)climbed=std::make_unique<Design>(*des);',1)
 s=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);',f'rematch_probability(*des, extra?{rounds}:2, 1.0, 2.0);',1)
 s=s.replace('        branches.back().value=complete(i,0);','        branches.back().value=complete(i,0);\n        branches.back().raw=std::move(climbed);',1)
 s=s.replace('for(int j=0;j<4;++j)',f'for(int j=0;j<{extras};++j)',1)
 s=s.replace('j%std::min(2,int(branches.size())),repeat=1+j/2',f'j%std::min({top},int(branches.size())),repeat=1+j/{top}',1)
 s=s.replace('// extra finishing attempts only on the two most promising raw branches.','// extra matching/perforation attempts share the completed filler climb.',1)
 needle='''        Design::kClimbProxyWeight=.5;
        double begin=elapsed_sec();'''
 s=s.replace(needle,'''        Design::kClimbProxyWeight=.5;
        std::cerr<<"colswap_tried = "<<des->colswap_tried<<"\\ncolswap_accepted = "<<des->colswap_accepted
                 <<"\\nreplace_tried = "<<des->replace_tried<<"\\nreplace_accepted = "<<des->replace_accepted<<'\\n';
        double begin=elapsed_sec();''',1)
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-best8。

元の4分岐・climb50k・再割当て2回・穴あけ8サンプル・最終再割当てを実行し、4完成候補を残す。完成Vが良い上位{top}分岐の「climb50kを済ませた時点」を再利用して、固定saltを変えた再割当て{rounds}回・穴あけ・最終再割当てを計{extras}回追加する。climbを繰り返さず、独立したmatchingと穴あけの結果を安く比較する。

全部で{4+extras}完成候補からVで選ぶ。窓割当て・焼きなまし・注文処理の予算は親と同じ。時間不足の切替えはない。DesignStoreは採用設計を保存し、ログ・@paper/@ops・目次・段の目印を維持。
''')
 print(name,len(s.encode()))
