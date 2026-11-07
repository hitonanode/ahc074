from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n'+d+'\n\n完成候補をVで選ぶ。時刻による打切り・切替えはなく、設計保存・注釈・統計・プロファイラ・実験スイッチを保つ。\n')
 print(n,len(text.encode()))
for weight in [1.5,1.75,2.]:
 emit('deval-latew'+str(int(weight*100)),s.replace('late_iterations, 1.25, 2.0, &extra','late_iterations, '+str(weight)+', 2.0, &extra'),f'穴あけ後の再割当てのfiller価値係数を1.25から{weight}へ変更する。予算・完成8候補は同じ。')
emit('deval-latewarm2',s.replace('env_real("ARGON_D2_LATE_ITERS", 1)','env_real("ARGON_D2_LATE_ITERS", extra==2?2:1)'),'穴を保持する2回の再仕上げだけ、穴あけ後の再割当てを1反復から2反復へ増やす。アンカーを改めて選んで残った目標を動かす。その他6候補の予算は同じ。')
