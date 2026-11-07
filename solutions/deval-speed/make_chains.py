from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-refinish8/main.cpp').read_text()
fast=(R/'solutions/deval-climbcache/main.cpp').read_text()
a='    // Expected fixes saved minus placement/return cost; probability(j) gives'
b='// ==== Head-aware reassignment of the targets (Hungarian matching) ===='
base=base[:base.index(a)]+fast[fast.index(a):fast.index(b)]+base[base.index(b):]
for name,extras,climb in [('deval-refinish-fast',4,25000),('deval-chain8',4,25000),('deval-chain10',6,12000)]:
 s=base
 if name!='deval-refinish-fast':
  s=s.replace('    auto complete=[&](int id,int extra) {','    std::unique_ptr<Design> best_assignment;\n    auto complete=[&](int id,int extra) {',1)
  s=s.replace('if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();}', 'if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);}',1)
  s=s.replace('des=std::make_unique<Design>(*branches[origin].raw);','if(!best_assignment)break;\n        des=std::make_unique<Design>(*best_assignment);',1)
  s=s.replace('for(int j=0;j<4;++j)',f'for(int j=0;j<{extras};++j)',1)
  s=s.replace('extra?25000:climb_iters',f'extra?{climb}:climb_iters',1)
  s=s.replace('// extra finishing attempts on the completed assignments of the best two branches.','// restart the native finishing pipeline from the best completed assignment so far.',1)
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 desc='親の4+4候補の探索を変えず、covered_gainの初期化とclimb内の幾何情報の再利用を加える。出力一致を比較する。' if name=='deval-refinish-fast' else f'元の4完成候補を保持する。以降は、現在最良の完成Vを得た配置からclimb{climb}回・再割当て1回・穴あけ8サンプル・最終再割当てを計{extras}回試す。改善した場合だけ次の開始配置を更新し、固定saltを変える。単一のslot交換をVで最適化せず、従来の仕上げ全体を通した候補で比較する。'
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-refinish8。

{desc}

出力を保つ高速化はdeval-climbcacheと同じ。窓割当て・焼きなまし・注文予算は元と同じで、時間不足の切替えはない。DesignStore、ログ、@paper/@ops、目次・段の目印を維持。
''')
 print(name,len(s.encode()))
