"""Byte-compare exact candidate traces, then verify first-minimum V selection."""
from pathlib import Path
import argparse,json,re,struct
p=argparse.ArgumentParser();p.add_argument('nine');p.add_argument('ten');p.add_argument('--output',required=True);a=p.parse_args()
R=Path('/home/sato/ahc074/runs')
for rid in [a.nine,a.ten]:assert json.loads((R/rid/'meta.json').read_text())['status']=='ok'
rx=re.compile(r'^@dcomp_candidate (\d+) (.+)$',re.M)
seeds=sorted(f.name for f in (R/a.nine/'err').glob('*.txt') if (R/a.ten/'err'/f.name).exists());assert len(seeds)>=200
def value(t):return struct.unpack('>d',int(t.split()[0],16).to_bytes(8,'big'))[0]
def chosen(log):return int(re.findall(r'^dv_chosen = (\d+)$',log,re.M)[-1])
same=selected10=0
for seed in seeds:
    logs=[(R/rid/'err'/seed).read_text() for rid in [a.nine,a.ten]]
    traces=[dict((int(i),s) for i,s in rx.findall(t)) for t in logs]
    x,y=traces;assert sorted(x)==list(range(9)) and sorted(y)==list(range(10))
    assert all(x[i]==y[i] for i in range(9)),seed
    for log,t in zip(logs,traces):assert chosen(log)==min(t,key=lambda i:value(t[i])),seed
    if chosen(logs[1])<9:
        assert chosen(logs[0])==chosen(logs[1]),seed
        assert (R/a.nine/'out'/seed).read_bytes()==(R/a.ten/'out'/seed).read_bytes(),seed
        same+=1
    else:
        assert value(y[9])<min(map(value,x.values())),seed
        selected10+=1
out={'nine':a.nine,'ten':a.ten,'seeds':len(seeds),'first_nine_exact_records':9*len(seeds),
     'selection_is_first_argmin_v':True,'ten_not_selected_stdout_identical':same,'ten_selected':selected10}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
