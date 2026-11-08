"""Assemble the frozen test tables. No fitting or solver execution."""
from pathlib import Path
import hashlib,json,subprocess,sys

h=Path(__file__).resolve().parent;root=h.parents[1];r=Path('/home/sato/ahc074/runs')
records=json.loads((h/'heldout-runs.json').read_text());assert {x['budget'] for x in records}=={2,4,8}
frozen=json.loads((h/'heldout-frozen.json').read_text())
for name,digest in frozen['sha256'].items():
    assert hashlib.sha256((root/'solutions'/name/'main.cpp').read_bytes()).hexdigest()==digest
out={'frozen':frozen,'budgets':{},'gate':{}}
names={'lns-star-study':'star','lns-joint-study':'joint','lns-warm-study':'warm','lns-full-study':'全再設計対照'}

def read(run):
    d=r/run;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
    cs={c['seed']:c for c in json.loads((d/'result.json').read_text())['cases']}
    assert len(cs)==500 and all(c['score']>0 for c in cs.values())
    assert not m['summary']['wa_seeds'] and m['summary']['average_E']==0
    return m,cs

def fmt(x):
    pc=x.get('pct_orders',x['pct']);ps=x.get('pct_orders_se',x['pct_se'])
    return f'{x["moves"]:+.5f} ±{x["moves_se"]:.5f}（{pc:+.3f} ±{ps:.3f}%）'

lines=['# 凍結確認の集計表','','差は候補−基準。単位は手/注文、括弧内は%（各seedの7列のlog比を平均）。±はseed間SE。全てseed500–999、lists1–7。','','| 名目予算 | (a) star−SOTA | (b) star−全再設計 | (c) 全再設計−SOTA |','|---|---:|---:|---:|']
for rec in sorted(records,key=lambda x:x['budget']):
    k=rec['budget'];prefix=f'heldout-b{k}-'
    _,reference_cases=read('20261108-070629_deval-helper-wide')
    _,normal_base_cases=read(rec['normal'][0])
    assert reference_cases.keys()==normal_base_cases.keys()
    assert all(normal_base_cases[s]['score']==reference_cases[s]['order_scores'][0]
               for s in reference_cases),('SOTA baseline generation drift',k)
    normal=json.loads((h/(prefix+'normal-metrics.json')).read_text())
    baseline=json.loads((h/(prefix+'baseline-metrics.json')).read_text())
    paired=json.loads((h/(prefix+'paired-metrics.json')).read_text())
    items={}
    for name,nid,rid in zip(rec['solvers'],rec['normal'][1:],rec['replays']):
        nm,nc=read(nid);rm,rc=read(rid)
        assert nc.keys()==rc.keys()
        different=[s for s in nc if nc[s]['score']!=rc[s]['order_scores'][0]]
        assert not different,('DesignStore request-list0 mismatch',name,k,different)
        items[name]={'normal':nid,'replay':rid,'versus_base':baseline[rid]['score'],
                     'stage':normal[nid]['stage'],'diag':normal[nid].get('diag',{}),
                     'normal_load':nm.get('outside_load'),'replay_load':rm.get('outside_load'),
                     'normal_summary':nm['summary'],'real_list_replay_identical_cases':500}
        if name!='lns-full-study':
            items[name]['versus_control']=paired[rid]['score']
    out['budgets'][k]=items
    star,control=items['lns-star-study'],items['lns-full-study']
    lines.append(f'| {k}× | {fmt(star["versus_base"]["fresh"])} | {fmt(star["versus_control"]["fresh"])} | {fmt(control["versus_base"]["fresh"])} |')

lines+=['','## 他の固定方式','','| 名目予算 | 方式 | 対SOTA | 対全再設計 |','|---|---|---:|---:|']
for k,items in out['budgets'].items():
    for name in ['lns-joint-study','lns-warm-study']:
        x=items[name];lines.append(f'| {k}× | {names[name]} | {fmt(x["versus_base"]["fresh"])} | {fmt(x["versus_control"]["fresh"])} |')
lines+=['','## 実測設計時間','','helper_end_sec（CLOCK_SCALE込み、24並列通常同時比較）。','','| 名目予算 | SOTA | star | joint | warm | 全再設計 |','|---|---:|---:|---:|---:|---:|']
for k,items in out['budgets'].items():
    ref=items['lns-star-study']['stage']['helper_end_sec']['reference_mean']
    cells=[f'{items[n]["stage"]["helper_end_sec"]["mean"]:.4f}s（{items[n]["stage"]["helper_end_sec"]["ratio"]:.3f}×）' for n in names]
    lines.append(f'| {k}× | {ref:.4f}s | '+' | '.join(cells)+' |')
lines+=['','## 最大予算のgate','','改善量=全再設計−候補。上側2SEが0.02手/注文未満なら失敗。','','| 方式 | 改善量 ±SE | 上側2SE | 判定 |','|---|---:|---:|---|']
for name in ['lns-star-study','lns-joint-study','lns-warm-study']:
    x=out['budgets'][8][name]['versus_control']['fresh'];gain=-x['moves'];upper=gain+2*x['moves_se']
    status='失敗' if upper<.02 else '強い成功' if gain>=.05 else '中間'
    out['gate'][name]={'improvement':gain,'se':x['moves_se'],'upper_2se':upper,'status':status}
    lines.append(f'| {names[name]} | {gain:+.5f} ±{x["moves_se"]:.5f} | {upper:+.5f} | {status} |')
control4=out['budgets'][4]['lns-full-study']['replay']
targets=[out['budgets'][8][n]['replay'] for n in ['lns-star-study','lns-joint-study','lns-warm-study']]
cross=json.loads(subprocess.check_output([sys.executable,str(h/'analyze.py'),control4,*targets,'--scores-only'],text=True))
out['lower_compute_control']={'reference':control4,'comparisons':cross}
lines+=['','## 計算量の丸めに対する補助確認','','8倍LNSを、計算量の少ない4倍全再設計対照と同じseed・注文列で比較する。主判定を置き換えるものではない。','','| 8倍方式 | 候補−4倍全再設計 | 改善量の上側2SE |','|---|---:|---:|']
for name,rid in zip(['lns-star-study','lns-joint-study','lns-warm-study'],targets):
    x=cross[rid]['score']['fresh'];lines.append(f'| {names[name]} | {fmt(x)} | {-x["moves"]+2*x["moves_se"]:+.5f} |')
(h/'FINAL_METRICS.json').write_text(json.dumps(out,indent=2)+'\n')
(h/'FINAL_TABLES.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
