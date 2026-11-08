from pathlib import Path
import difflib,subprocess
R=Path(__file__).resolve().parents[2]
def src(n):return(R/'solutions'/n/'main.cpp').read_text()
b=src('dcomp-combo-alt1');s=src('dcomp-t11-altcap2');assert s.count('if(alt_tried==2)break;')==1;s=s.replace('if(alt_tried==2)break;','if(alt_tried==3)break;')
patch=''.join(difflib.unified_diff(b.splitlines(True),s.splitlines(True),'a/main.cpp','b/main.cpp',n=3))
d=R/'solutions/dcomp-t11-funded-alt3';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(src('dcomp-t11-funded-pc6'))
r=subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,text=True,cwd=d,capture_output=True);assert r.returncode==0,r.stdout+r.stderr
for p in d.glob('*.orig'):p.unlink()
(d/'README.md').write_text('改良元: solutions/dcomp-t11-funded-pc6\n\n通常post候補6個に対して、編集後の費用でALT候補を安定sortし、gap条件を満たす先頭3個だけ本修復する。元の4候補版で起こりうるALTの最大個数に合わせ、新しい第二親の探索へ時間を振り替える。2個上限の損失が大きかったため、固定3個の中間を測る。\n\n他の方針とexact高速化は親と同じ。コンパイラ間の予算差、時計分岐はない。既存ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
