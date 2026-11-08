from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-spend-alt75-e2/main.cpp').read_text()
for mode in ['short','top1','one']:
 s=base
 if mode=='short':
  a='''                    if (c.state.order == ordinary_eject_start || c.cost > baseline_value + cfg.alternate_gap) continue;'''
  assert s.count(a)==1;s=s.replace(a,a+'\n                    if(c.path.size()>baseline_path.size())continue;')
 elif mode=='top1':
  a='''                for (auto& c : edited_candidates) {
                    if (c.state.order == ordinary_eject_start'''
  b='''                std::stable_sort(edited_candidates.begin(),edited_candidates.end(),by_cost);
                int alternate_attempts=0;
                for (auto& c : edited_candidates) {
                    if (c.state.order == ordinary_eject_start'''
  assert s.count(a)==1;s=s.replace(a,b)
  a='''                    if (c.state.order == ordinary_eject_start || c.cost > baseline_value + cfg.alternate_gap) continue;'''
  assert s.count(a)==1;s=s.replace(a,a+'\n                    if(alternate_attempts++==1)break;')
 else:
  a='''    struct SearchConfig {''';assert s.count(a)==1;s=s.replace(a,'    bool alternate_one_repair=false;\n'+a)
  a='''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 2);''';assert s.count(a)==1;s=s.replace(a,'                    alternate_one_repair=true;\n'+a+'\n                    alternate_one_repair=false;')
  a='''                eject_repairs(initial, edits, u, initial_next, initial_prev, initial_bytes, evaluate);''';assert s.count(a)==1;s=s.replace(a,a[:-2]+', alternate_one_repair?1:2);')
 p=r/'solutions'/('dcomp-alt-'+mode);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 desc={'short':'現行最良より手数の多い次点を除外する。','top1':'編集済み費用が低い順の1候補だけに絞る。同点順序は保持。','one':'次点に対してだけ2削除1修復を1削除1修復に置き換える。'}[mode]
 (p/'README.md').write_text('改良元: solutions/dcomp-spend-alt75-e2\n\n次点の再編集を固定予算で安くする実験。'+desc+' 既定NS_ALTERNATE=1、gap=.75、次点再編集最大2回。設計と通常の現行最良の処理は維持。実験スイッチ・ログ・DesignStoreを保持、時刻による打切りはない。\n')
