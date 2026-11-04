from pathlib import Path
import json
p=Path(__file__).resolve().parent;out=p/'designs';out.mkdir(exist_ok=True)
for f in sorted(Path('solutions/sparse-map/models').glob('[0-9]*.json')):
 rows=json.loads(f.read_text())
 for row in rows[:3]:
  d=row['design'];lines=['38 185',' '.join(map(str,d['A'])),' '.join(map(str,d['handles']))]
  lines+=[' '.join(map(str,x))for x in d['edge']]
  lines+=[' '.join(map(str,x))for x in d['units']]
  (out/f'{f.stem}-{row["mode"]}.txt').write_text('\n'.join(lines)+'\n')
