from pathlib import Path
import difflib,subprocess
R=Path(__file__).resolve().parents[2]
def src(n):return(R/'solutions'/n/'main.cpp').read_text()
for cap in [False,True]:
 name='dcomp-t11-shared6'+('-alt2'if cap else '')
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(src('dcomp-t11-stack-pc6'))
 changes=[('dcomp-t11-seed-one','dcomp-t11-seedone-cap1'),('dcomp-combo-alt1','dcomp-t11-merge-win')]
 if cap:changes.append(('dcomp-combo-alt1','dcomp-t11-altcap2'))
 for before,after in changes:
  patch=''.join(difflib.unified_diff(src(before).splitlines(True),src(after).splitlines(True),'a/main.cpp','b/main.cpp',n=3))
  r=subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,text=True,cwd=d,capture_output=True)
  assert r.returncode==0,(after,r.stdout,r.stderr)
 for p in d.glob('*.orig'):p.unlink()
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-stack-pc6\n\n通常post候補6個、共有neutral枠6個のまま、第二親の生成候補だけ上位一つへ絞る。第二親の挿入時点は最早・最遅の両方を試す。合法試行がbestを更新する時の二重移動結合も加える。'+('ALT修復は編集後費用で安定sortして先頭二つまで。通常候補を6にするとALTも増えるため、その費用を第二親の修復へ振り替える。'if cap else 'ALTの件数上限は元のままの対照。')+'\n\n9設計候補と既存exact高速化は同じ。両コンパイラで固定予算は共通、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
