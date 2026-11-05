from pathlib import Path
import sys,re
sys.path.insert(0,str(Path('scripts').resolve()))
import replay
root=Path('/home/sato/ahc074/runs')
log=Path('solutions/argon-req-ejectcache/trace-correct.log')
name=re.search(r'run-id: (\S+)',log.read_text())[1]
r=root/name;n=0;plans=0
for f in (r/'out').glob('*.txt'):
 assert f.read_bytes()==(root/'20261106-030749_argon-req-ejectcache'/'out'/f.name).read_bytes(),f.name
 seed=int(f.stem);inp=replay.load_input(seed)
 out=replay.parse_output(inp,f.read_text());err=(r/'err'/f.name).read_text()
 ann=replay.parse_annotations(err,inp.k)
 for line in err.splitlines():
  if not line.startswith('#heavy '):continue
  fields=line.split();q=int(fields[1]);last=fields[-1]
  ops=[];labels=[]
  if last!='-':
   for item in last.split(','):
    k,d,label=item.split(':');ops.append((int(k),int(d)));labels.append(label)
  assert ops==out.queries[q],(seed,q,ops,out.queries[q])
  assert labels==ann.labels_of(q,len(ops)),(seed,q,labels,ann.labels_of(q,len(ops)))
  n+=1;plans+=fields[3].startswith('plans.')
 assert 'self_wrong = 0' in err and 'op_label_errors = 0' in err
print('Trace run',name,'heavy records',n,'plans records',plans,'all final paths and labels match stdout/@ops.')
assert n>0 and plans>0
