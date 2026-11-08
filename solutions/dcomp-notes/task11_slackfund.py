from pathlib import Path
R=Path(__file__).resolve().parents[2];b=(R/'solutions/dcomp-t11-funded-shared6/main.cpp').read_text()
for value in [30,25]:
 d=R/'solutions'/f'dcomp-t11-funded-slack{value}';assert not d.exists();d.mkdir()
 a='if(std::strcmp(name,"NEUTRAL_SLACK")==0)return ".35";';assert b.count(a)==1
 (d/'main.cpp').write_text(b.replace(a,a.replace('".35"',f'".{value}"')))
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-funded-shared6\n\n中立候補の許容費用差NEUTRAL_SLACKを0.35から0.'+str(value)+'へ狭め、追加親と通常6候補の探索時間を抑える。新しい候補を増やさず、状態から決まる固定の閾値だけで本修復へ進める候補を選ぶ。ALT件数は元のまま。\n\nその他の探索・設計9候補・exact高速化は親と同じ。両コンパイラ共通の予算で、時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
