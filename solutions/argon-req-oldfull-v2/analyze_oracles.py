from pathlib import Path
import argparse
import json
import re
import statistics as st

p=argparse.ArgumentParser()
p.add_argument('base')
p.add_argument('candidates',nargs='+')
p.add_argument('--json',dest='output',required=True)
a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
metric=re.compile(r'^(\w+) = ([-+\d.eE]+)$',re.M)
all_results={}
for name in a.candidates:
    directory=root/name
    files=sorted(directory.glob('out/*.txt'))+sorted(directory.glob('orders/*/out/*.txt'))
    rows=[]
    for file in files:
        rel=file.relative_to(directory)
        assert file.read_bytes()==(root/a.base/rel).read_bytes(),(name,rel)
        relerr=rel.parent.parent/'err'/rel.name
        err=(directory/relerr).read_text()
        orig=(root/a.base/relerr).read_text()
        assert [s for s in err.splitlines() if s.startswith('@')] == [s for s in orig.splitlines() if s.startswith('@')],(name,relerr)
        m={k:float(v) for k,v in metric.findall(err)}
        assert m['self_wrong']==m['op_label_errors']==0,(name,rel)
        rows.append(m)
    assert rows
    result={k:st.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('old_probe_','joint_probe_','old_full_','joint_extra_')) or k in ['total_moves','req_sec']}
    all_results[name]=result
    print(name,len(files),'stdout/@paper/@ops identical to base; errors = 0',flush=True)
    print('local', {k:v for k,v in result.items() if k.startswith(('old_full_','joint_extra_')) or k.endswith(('_raw','_duplicate'))},flush=True)
    prefix='joint_probe_' if 'joint_probe_raw' in result else 'old_probe_'
    print('stage gate trials same better gain saved positive_moves sec',flush=True)
    for stage in range(3):
        for g,gate in enumerate(['0','.25','.5','1','2','inf']):
            head=f'{prefix}{stage}_{g}_'
            print(stage,gate,*[round(result[head+k],6) for k in ['trials','same','better','gain','saved','ceiling','sec']],flush=True)
    print('all stages by gate:',flush=True)
    for g,gate in enumerate(['0','.25','.5','1','2','inf']):
        values={k:sum(result[f'{prefix}{stage}_{g}_{k}'] for stage in range(3)) for k in ['trials','same','better','gain','saved','ceiling','sec']}
        print(gate,values,'predicted_pct',100*values['gain']/result['total_moves'],flush=True)
Path(a.output).write_text(json.dumps(all_results,indent=2)+'\n')
