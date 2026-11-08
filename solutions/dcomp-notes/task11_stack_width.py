from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-stack-one/main.cpp').read_text()
for w in [8,12]:
 a='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "6";';assert B.count(a)==1
 s=B.replace(a,a.replace('"6"',f'"{w}"'))
 a='bool memo = get("MEMO", 1);';assert s.count(a)==1;s=s.replace(a,'bool memo = get("MEMO", 0);')
 d=R/'solutions'/f'dcomp-t11-stack-width{w}';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-stack-one\n\nraw候補の二重移動結合、広いfiller区間のDP同点規則、完成ALT計画を1→1中立探索の追加親にする変更を保持し、中立候補の本修復枠を6→'+str(w)+'にする。追加親との共有poolで落ちる候補を減らす。\n\nend memoは両コンパイラで無効が速かったので、既定をMEMO=0にする（実験スイッチは残す）。他の出力同一高速化、9設計候補、通常post4、PLAN_LIMIT2はそのまま。探索設定は両コンパイラ共通の固定値。時刻による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
