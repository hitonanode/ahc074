from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-t12-postcompact/main.cpp').read_text()
old='if(std::strcmp(name,"NEUTRAL_SLACK")==0)return ".25";';assert b.count(old)==1
for v in ['30','35']:
 s=b.replace(old,old.replace('.25','.'+v));d=S/('dcomp-t12-memo'+v);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t12-postcompact（方策の基準はdcomp-combo-dual25）\n\n出力同一のwhole-post memoを加え、中立候補の許容費用差NEUTRAL_SLACKを0.25から0.'+v+'へ広げる。通常6候補・第二親上位1個・共有6枠・3roundsは変えない。異なる終状態を次の修復へ残す余地の費用を再測定する。\n\n両コンパイラで予算は共通。時刻による切替なし。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。\n')
