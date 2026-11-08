from pathlib import Path
R=Path(__file__).resolve().parents[2];s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "6";';assert s.count(a)==1
s=s.replace(a,a.replace('"6"','"24"')+'\n        if(std::strcmp(name,"HEAVY_PREDICT")==0)return "1";')
a='''                auto proposals = std::move(neutral_candidates);''';assert s.count(a)==1
s=s.replace(a,'''                const double training_floor=incumbent_value-parent_value;
'''+a)
a="+ ' ' + std::to_string(better) + ' ' + std::to_string(c.hides) + '\\n';";assert s.count(a)==1
s=s.replace(a,"+ ' ' + std::to_string(better) + ' ' + std::to_string(c.hides) + ' ' + trace_value(training_floor) + '\\n';")
d=R/'solutions/dcomp-t11-neutral-train';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n研究用。中立候補の修復枠を24に広げ、既存のHEAVY_PREDICTで修復前の特徴と修復後の費用を記録する。各roundの直接改善後のincumbent費用も記録し、候補選択の利得を過大に数えない。\n\nseed0–99で順位予測を当てはめ、100–199で予備判定する。研究版は固定設計replayだけで実行し、記録しない。修復数は固定、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
