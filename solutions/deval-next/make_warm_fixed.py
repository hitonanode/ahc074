from pathlib import Path
r=Path(__file__).resolve().parents[2]
for oldname,name,addonly in [('deval-warm9','deval-warmfix9',False),('deval-warm7','deval-warmfix7',False),('deval-warm10','deval-warmfix10',False),('deval-warm9','deval-warmadd9',True)]:
 s=(r/'solutions'/oldname/'main.cpp').read_text()
 if addonly:
  s=s.replace('        if(extra==2)perforation.allowed=natural_opacity;','        // Existing holes remain; this pass only adds perforations.',1)
 else:
  old='''            solver.paper[k]=warm_state.papers[old];
            solver.h_opq[k]=solver.handle_bits(solver.paper[k].opaque);
            solver.h_blk[k]=solver.handle_bits(solver.paper[k].black);'''
  new='''            // Keep the natural physical mask/color as the restoration source.
            // Only the initial opacity of the perforation model has the old holes.
            solver.h_opq[k]=solver.handle_bits(warm_state.papers[old].opaque);'''
  assert old in s;s=s.replace(old,new,1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-seven-wide`。試験版{oldname}の穴保存処理を整理。\n\n'+('既存の穴を固定し、新しい穴と再割当てだけを試す。' if addonly else '最良完成配置の穴を初期状態にし、穴あけと再割当てを反復する。穴を復元するときの色と印刷可能な窓は、現時点の対象の自然な紙模様から取る。Perforationの模型だけ旧穴で開始し、installが新しい模型の穴だけを自然な紙から消すため、復元も物理紙へ反映される。')+'\n\n候補数と通常/穴保存の構成は改良元の試験版と同じ。V16で選択し、固定予算で動く。\n')
 print(name,len(s.encode()))
