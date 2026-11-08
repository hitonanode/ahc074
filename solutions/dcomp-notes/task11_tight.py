from pathlib import Path
import difflib,subprocess
R=Path(__file__).resolve().parents[2]
def source(name):return (R/'solutions'/name/'main.cpp').read_text()
base=source('dcomp-t11-stack-width8')
changes=[('dcomp-t11-seed-one','dcomp-t11-seedone-early'),('dcomp-t11-seed-one','dcomp-t11-seedone-cap1'),('dcomp-combo-alt1','dcomp-t11-merge-win')]
for width in [6,8,12]:
 d=R/'solutions'/f'dcomp-t11-tight{width}';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(base)
 for before,after in changes:
  patch=''.join(difflib.unified_diff(source(before).splitlines(True),source(after).splitlines(True),'a/main.cpp','b/main.cpp',n=3))
  result=subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,text=True,cwd=d,capture_output=True)
  assert result.returncode==0,(after,result.stdout,result.stderr)
 p=d/'main.cpp';s=p.read_text();a='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "8";';assert s.count(a)==1
 p.write_text(s.replace(a,a.replace('"8"',f'"{width}"')))
 for p in d.glob('*.orig'):p.unlink()
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-stack-width8\n\n追加親の1→1修復を、最も早い合法挿入タイミングだけに限定し、元の親のpoolと合わせる前に上位1候補だけ残す。主親の探索は変えない。中立候補の本修復枠は'+str(width)+'。合法な試行が現在のbestを更新する場合だけ、二重移動の結合も試してから値を比較する。\n\nraw候補の二重移動結合、区間DPの広い同点選択、出力同一高速化（anchor遅延、partial MDP cache、next初期化、MEMO=0）はそのまま。追加親の列挙数と本修復数を固定条件で抑える。両コンパイラ共通予算、時計分岐なし。設計・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
