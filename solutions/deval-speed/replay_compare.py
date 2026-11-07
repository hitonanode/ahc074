from pathlib import Path
import sys,time,re,json
from experiment import run
p=Path(sys.argv[1])
if not p.is_absolute() and not p.exists():p=Path(__file__).resolve().parent/p
while not p.exists() or 'ダッシュボードを更新しました' not in p.read_text():time.sleep(10)
names=sys.argv[2:]
manifest=Path(__file__).resolve().parent/'experiments.jsonl'
have_base=manifest.exists() and any(json.loads(line).get('tag')=='vbranch-nofb' for line in manifest.read_text().splitlines())
if not have_base and '_deval-vbranch-nofb' in p.read_text() and 'deval-vbranch-nofb' not in names:
 names=['deval-vbranch-nofb']+names
for name in names:
 design=re.search(r'run-id: (\S+_'+re.escape(name)+r')',p.read_text())[1]
 run(name.removeprefix('deval-'),'solutions/'+name,{'DESIGN_FROM':design},'0-500')
