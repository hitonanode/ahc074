from pathlib import Path
import time,re
from experiment import run
p=Path(__file__).resolve().parent/'anneal-funded.log'
while not p.exists() or 'ダッシュボードを更新しました' not in p.read_text():time.sleep(10)
for name in ['deval-sixlong','deval-anneal125']:
 design=re.search(r'run-id: (\S+_'+name+r')',p.read_text())[1]
 run(name.removeprefix('deval-'),'solutions/'+name,{'DESIGN_FROM':design},'0-500')
