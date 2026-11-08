"""Apply independent changes against the frozen Task11 parent, with zero-fuzz patches."""
from pathlib import Path
import difflib,subprocess
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def stack(name,changes,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(B)
 for child in changes:
  s=(R/'solutions'/child/'main.cpp').read_text()
  patch=''.join(difflib.unified_diff(B.splitlines(True),s.splitlines(True),'a/main.cpp','b/main.cpp',n=3))
  p=subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,text=True,cwd=d,capture_output=True)
  if p.returncode:raise RuntimeError(child+'\n'+p.stdout+p.stderr)
 # patch creates .orig for offsets; no compiler binaries or stale snapshots in the solution.
 for p in d.glob('*.orig'):p.unlink()
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n合成元: '+', '.join(changes)+'。候補順・計算の加算順・固定予算を保持する。既存ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による切替はない。\n')
 return d
if __name__=='__main__':
 changes=['dcomp-t11-anchor-lazy','dcomp-t11-partial-cache','dcomp-t11-nextinit','dcomp-t11-hash4']
 d=stack('dcomp-t11-fast-hash',changes,'出力同一の要求高速化を合成する。anchor固定配列と最終勝者だけのanchorize、部分MDPの正確な紙ID列cache、prefix hit時の不要初期化省略、end-memoの独立4本hash。')
 d=stack('dcomp-t11-fast-nomemo',changes,'出力同一の要求高速化を合成し、end-memoの純費用を測る対照としてmemoの既定を無効にする。元の実験スイッチは維持。')
 p=d/'main.cpp';s=p.read_text();a='bool memo = get("MEMO", 1);';assert s.count(a)==1;p.write_text(s.replace(a,'bool memo = get("MEMO", 0);'))
