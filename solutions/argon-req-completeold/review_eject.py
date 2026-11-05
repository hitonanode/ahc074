from pathlib import Path
import sys, subprocess, re
p=Path('solutions/argon-req-ejectcache');work=Path(__file__).resolve().parent
if not (p/'builds.log').exists() or 'All four builds passed' not in (p/'builds.log').read_text():
 with (p/'builds.log').open('w') as f:
  subprocess.run([sys.executable,str(work/'check_builds.py'),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
with (p/'fixed-screen-analysis.log').open('w') as f:
 subprocess.run([sys.executable,str(work/'analyze_screen.py'),str(p/'fixed-screen.log')],stdout=f,stderr=subprocess.STDOUT,check=True)
root=Path('/home/sato/ahc074/runs');a=root/'20261106-030749_argon-req-completeeject-old';b=root/'20261106-030749_argon-req-ejectcache'
files=list((a/'out').glob('*.txt'))+list((a/'orders').glob('*/out/*.txt'))
assert len(files)==400
changed=set()
for f in files:
 rel=f.relative_to(a)
 assert f.read_bytes()==(b/rel).read_bytes(),rel
 ef=Path(str(rel).replace('out/','err/'))
 aa=(a/ef).read_text();bb=(b/ef).read_text()
 assert [x for x in aa.splitlines() if x.startswith('@')]==[x for x in bb.splitlines() if x.startswith('@')],ef
 pat=r'^(\w+) = ([-+\d.eE]+)$'
 ad=dict(re.findall(pat,aa,re.M));bd=dict(re.findall(pat,bb,re.M))
 assert ad.keys()==bd.keys()
 for k in ad:
  if ad[k]!=bd[k] and not k.endswith('_sec'):changed.add(k)
assert changed <= {'ns_changed','ns_saved','cf_value_hits','cf_value_misses'},changed
print('400 stdout and @paper/@ops identical to the unsimplified old-DP prototype.',flush=True)
print('Only non-timing metric differences:',sorted(changed),'(final search summary includes the added plan; skipped value evaluations change cache counters).',flush=True)
with (p/'episodes.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/argon-req-oldvalue/episodes.py','20261106-030059_argon-req-completefast-v3','20261106-030059_argon-req-completeeject-old'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Four builds, exact-output checks and selected query replays passed.',flush=True)
