from pathlib import Path
import difflib,subprocess
R=Path(__file__).resolve().parents[2]
def source(name):return(R/'solutions'/name/'main.cpp').read_text()
B=source('dcomp-combo-alt1')
patch=''.join(difflib.unified_diff(B.splitlines(True),source('dcomp-t11-mergepool').splitlines(True),'a/main.cpp','b/main.cpp',n=3))
for width in [10,12]:
 d=R/'solutions'/f'dcomp-t11-pool{width}';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source('dcomp-t11-tight12'))
 r=subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,text=True,cwd=d,capture_output=True);assert r.returncode==0,r.stdout+r.stderr
 p=d/'main.cpp';s=p.read_text();a='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "12";';assert s.count(a)==1
 p.write_text(s.replace(a,a.replace('"12"',f'"{width}"')))
 for p in d.glob('*.orig'):p.unlink()
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-tight12\n\n最後のnear-tie候補を二重移動結合の後で比較するmergepoolを合成する。中立候補の本修復枠は'+str(width)+'。第二親は最早の合法挿入のみ、候補上位一つという条件を保持する。\n\n設計9候補、raw計画の結合、区間DPの広い同点選択、merge-win、出力同一のanchor/partial-MDP/next初期化/MEMO無効化は親のまま。両コンパイラ共通の固定回数で、時計による切替は使わない。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
