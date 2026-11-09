from pathlib import Path
import json,sys
p=Path(sys.argv[1]);data=json.loads(p.read_text())
print('base:',data['base'])
print('|候補|log比% ± SE|勝/分/敗|ΔV ± SE|H ms ± SE|R ms ± SE|E ms ± SE|net % ± SE|')
print('|---|---:|---:|---:|---:|---:|---:|---:|')
for name,x in data['comparisons'].items():
 def fmt(v,d=4):return f"{v['mean']:+.{d}f} ± {v['se']:.{d}f}"
 vals=[name.split('_',1)[1],fmt(x['score']),'/'.join(map(str,x['wtl'])),fmt(x['paired_metrics']['dv_best'],5)]+[fmt(x['paired_ms'][k],2) for k in ['helper_end_sec','req_sec','end_sec']]+[fmt(x['net_score'])]
 print('|'+ '|'.join(vals)+'|')
print('\np99（H/R/E、ms、基準→候補）')
for name,x in data['comparisons'].items():
 print(name.split('_',1)[1],'/'.join(f'{x["arm_p99_ms"][k][0]:.1f}→{x["arm_p99_ms"][k][1]:.1f}' for k in ['helper_end_sec','req_sec','end_sec']))
