"""Rebuild tables of completed training experiments. Run under flock."""
from pathlib import Path
import json,argparse
from analyze_quality import compare
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
STAGE={
'gaincache':'dv_finish_sec','filterundo':'req_sec','repairmask':'req_sec','perfflat':'dv_finish_sec',
'find16':'req_sec','find32':'req_sec','nextcache':'req_sec','badblock':'req_sec','fixedcfg':'req_sec',
'msd':'map_end_sec','hungarian':'dv_finish_sec','qtable':'dv_anneal_sec','dirtyall':'dv_anneal_sec','dirtyfirst':'dv_anneal_sec',
'recompute':'dv_anneal_sec','geometry':'dv_finish_sec','negative':'req_sec','radixscan':'map_end_sec',
'hungarian-vec':'dv_finish_sec','perfint':'dv_finish_sec','smallfill':'req_sec','colcache64':'req_sec','colcache256':'req_sec',
'hash4':'req_sec','holebound':'dv_anneal_sec','perfsparse':'dv_finish_sec','columnvalue':'req_sec',
'coltable':'dv_anneal_sec','colscalar':'dv_anneal_sec','colrun':'req_sec','ejectprefix':'req_sec','edit4':'req_sec','blockbad':'req_sec','gainprob':'dv_finish_sec','speedcore':'judge',
'fast':'judge','fastedit':'req_sec','fastcolor':'dv_eval_sec','fastprefix':'req_sec','fastrecip':'dv_anneal_sec',
'headcache':'dv_finish_sec','coverstart':'dv_finish_sec','ejectskeleton':'req_sec','ejectinterval':'req_sec','fast2':'judge','climbcache':'dv_finish_sec','smallmoves':'req_sec','reqo3':'req_sec'}
NAMES={'map_end_sec':'窓割当て','dv_anneal_sec':'焼きなまし','dv_finish_sec':'仕上げ','dv_eval_sec':'V','req_sec':'注文','judge':'judge全体'}
def loadmeta(run):return json.loads((R/run/'meta.json').read_text())
def warning(run):
 d=loadmeta(run).get('outside_load',{});return d.get('mean_cores',0)>.5 or d.get('max_cores',0)>3
lines=['## 出力を保つ高速化の試行','',
'段の時間差は候補−基準のlocal scaled秒。±は対応のあるseed間の標準誤差。出力は実際の`out/*.txt`を照合した。「打切り差」は候補数も異なった出力差で、「その他」はそれ以外。†は外部CPU負荷の警告があり、小さな時間差の採否には使わない。各試行の内容は同名解法のREADMEと`make_*.py`に残した。','',
'| 解法 | 基準 | 比較段 | 秒差 ± SE | 出力一致 / 件数 | 打切り差 / その他 | run（候補） |','|---|---|---|---:|---:|---:|---|']
seen=set();speed=[]
for f in sorted(P.glob('*.json')):
 try:d=json.loads(f.read_text())
 except (ValueError,OSError):continue
 if not isinstance(d,dict) or 'stdout_mismatches' not in d:continue
 tag=d['candidate'].split('_',1)[1].removeprefix('deval-')
 if tag not in STAGE or not any(d['reference'].endswith('_'+name) for name in ['deval-vbranch-o3','deval-vbranch-nofb','deval-fast','deval-fast2','deval-climbcache']):continue
 if tag in ['fastedit','fastcolor','fastprefix','fastrecip'] and not d['reference'].endswith('_deval-fast'):continue
 key=(d['reference'],d['candidate'])
 if key in seen:continue
 seen.add(key);speed.append(d);v=d['time'][STAGE[tag]];n=d['n'];other=len(d['unexplained']);mismatch=len(d['stdout_mismatches'])
 compiler=loadmeta(d['candidate']).get('compiler','');suffix=' Clang' if 'clang' in compiler.lower() else ''
 lines.append(f"| {tag}{suffix}{'†' if warning(d['candidate']) else ''} | {d['reference'].split('_',1)[1]} | {NAMES[STAGE[tag]]} | {v['delta']:+.6f} ± {v['se']:.6f} | {n-mismatch}/{n} | {mismatch-other}/{other} | `{d['candidate']}` |")
normal_time={}
for f in P.glob('*.json'):
 try:d=json.loads(f.read_text())
 except (ValueError,OSError):continue
 if not isinstance(d,dict) or 'time' not in d or 'judge' not in d['time']:continue
 ref=d.get('reference','');cand=d.get('candidate','')
 if ref.endswith('_argon-des-perf-latew105'):normal_time.setdefault(cand,{})['ratio']=d['time']['judge']['ratio']
 if ref.endswith('_deval-vbranch-nofb'):normal_time.setdefault(cand,{})['p99delta']=d['time']['judge']['candidate_p99']-d['time']['judge']['reference_p99']
reference='20261107-094653_deval-vbranch-nofb' 
lines += ['','## 設計変更の学習側評価','',
f'すべてseed 0–499。基準は `{reference}` の同じseedと注文列。中断前の試行も現在の基準へ揃えて再集計した。負が改善。通常runの設計時間はhelper表完成までで、別run間の差は同時比較の時間比と区別する。','',
'| 試行 | 列1–7 ± SE | 全8列 ± SE | 実列 ± SE | 設計秒 | judge比（旧SOTA） | p99差（nofb） | design / replay |','|---|---:|---:|---:|---:|---:|---:|---|']
quality=[]
manifest=P/'experiments.jsonl'
if manifest.exists():
 for line in manifest.read_text().splitlines():
  item=json.loads(line)
  if item['seeds']!='0-500':continue
  d=compare(reference,item['replay'],(0,500));d['experiment']=item;quality.append(d)
  m=json.loads((R/item['design']/'metrics.json').read_text())['cases'];t=sum(v['stderr']['helper_end_sec'] for v in m.values())/len(m)
  vals=[d['results'][k] for k in ['fresh','all','real']]
  nt=normal_time.get(item['design'],{});ratio=f"{nt['ratio']:.4f}" if 'ratio' in nt else '—';p99=f"{nt['p99delta']:+.4f} s" if 'p99delta' in nt else '—'
  lines.append('| '+item['tag']+' | '+' | '.join(f"{v['mean']:+.4f} ± {v['se']:.4f}%" for v in vals)+f" | {t:.4f} | {ratio} | {p99} | `{item['design']}` / `{item['replay']}` |")
lines += ['','## 注文探索設定の学習側評価','',
'seed 0–499、4注文列。保存設計は原則 `20261107-063721_deval-vbranch-o3`、seven-wideのみ `20261107-110423_deval-chain-seven`。各群で同時に走らせた基準との比。注文時間は実列の平均差で、最終のjudge時間判定には通常の同時比較を使う。','',
'| 試行 | 全4列 ± SE | 注文秒差 | replay |','|---|---:|---:|---|']
requests=[]
for filename in ['request-settings-quality.json','request-neighbors-quality.json','request-threshold-quality.json','requestfund-quality.json','seven-wide-quality.json']:
 f=P/filename
 if not f.exists():continue
 for d in json.loads(f.read_text()):
  requests.append(d);r=d['results']['all']
  def req(run):
   v=json.loads((R/run/'metrics.json').read_text())['cases'];return sum(x['stderr']['req_sec'] for x in v.values())/len(v)
  lines.append(f"| {d['candidate'].split('_',1)[1]} | {r['mean']:+.4f} ± {r['se']:.4f}% | {req(d['candidate'])-req(d['reference']):+.6f} | `{d['candidate']}` |")
(P/'EXPERIMENTS.md').write_text('\n'.join(lines)+'\n')
(P/'experiment-results.json').write_text(json.dumps({'speed':speed,'design':quality,'requests':requests},ensure_ascii=False,indent=2)+'\n')
print('speed',len(speed),'design',len(quality),'requests',len(requests))
