"""保存した1000列のstderrを検査する。共有runs/.lockを保持して実行する。"""
from pathlib import Path
import re,json,sys
root=Path('/home/sato/ahc074/runs')/(sys.argv[1] if len(sys.argv)>1 else '20261106-141955_nogen-payload-transition')
paths=list(root.glob('err/*.txt'))+list(root.glob('orders/*/err/*.txt'));assert len(paths)==1000,len(paths)
for p in paths:
 text=p.read_text();m={k:float(v) for k,v in re.findall(r'^([a-zA-Z_0-9]+) = ([-+0-9.eE]+)$',text,re.M)}
 for k in ['self_wrong','op_label_errors','audit_owner_violations','audit_cap_violations','audit_unowned_papers']:assert m[k]==0,(p,k,m[k])
 assert m['light_requests']==512,(p,m['light_requests'])
 assert m['audit_product_papers']==191 and m['audit_certificate_targets']==256
cases=json.loads((root/'result.json').read_text())['cases'];assert len(cases)==500
assert all(len(c['order_scores'])==2 and min(c['order_scores'])>0 for c in cases)
print('PASS 1000 order sequences: 512 normal + 512 light; ownership/cap/display/labels valid')
