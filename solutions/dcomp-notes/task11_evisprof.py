from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='CfProfile cf_eject{"eject"};';assert s.count(a)==1
s=s.replace(a,a+'\nCfProfile cf_eject_visibility{"eject_visibility"},cf_eject_positions{"eject_positions"},cf_eject_columns{"eject_columns"};')
a='&cf_eject,';assert s.count(a)==1;s=s.replace(a,a+' &cf_eject_visibility, &cf_eject_positions, &cf_eject_columns,')
a='''                    int earliest = length + 1, latest = -1;
                    replay_order = initial_bytes;''';assert s.count(a)==1
s=s.replace(a,a.replace('                    replay_order','                    {CF_SCOPE(eject_visibility);\n                    replay_order'))
a='''                    if (latest < 0) continue;''';assert s.count(a)==1;s=s.replace(a,'                    }\n'+a)
for name in ['positions','columns']:
 a='''                    if ('''+name+'''_ready) return;
                    '''+name+'''_ready = true;''';assert s.count(a)==1
 s=s.replace(a,a+'\n                    CF_SCOPE(eject_'+name+');')
d=R/'solutions/dcomp-t11-evis-prof';assert not d.exists();d.mkdir();(d/'main.cpp').write_text('#define COLFAST_PROFILE 1\n'+s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\neject_repairsの排他時間を、候補紙の合法な挿入時点を求める可視性再生、窓owner位置、列境界の準備へ分解する計測専用版。全clockは既存scaled timerを使う。探索・出力・予算は同じ。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
