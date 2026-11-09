from pathlib import Path
import json,sys,importlib.util
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
run=sys.argv[1];reference='20261109-114428_d30a-reset6';d=runs/run
current=json.loads((d/'result.json').read_text());old=json.loads((runs/reference/'result.json').read_text())
a={int(c['seed']):c['score'] for c in current['cases']};b={int(c['seed']):c['score'] for c in old['cases']}
assert set(a)==set(b)==set(range(2000)),(len(a),len(b))
unequal=[{'seed':s,'saved_run':a[s],'reference':b[s]} for s in sorted(a) if a[s]!=b[s]]
wa=[s for s in a if a[s]<=0]
spec=importlib.util.spec_from_file_location('verify_saved_pahcer',root/'scripts/pahcer_run.py');mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
mod.check_designs(d/'design',Path('/home/sato/ahc074/tools/in'),range(2000))
files=list((d/'design').glob('*.txt'));assert len(files)==2000 and all(p.stat().st_size>0 for p in files)
meta=json.loads((d/'meta.json').read_text());assert meta['status']=='ok' and meta.get('save_design') and meta.get('out_dir')=='/home/sato/ahc074/pahcer'
summary={'run':run,'reference':reference,'seeds':2000,'score_equal':2000-len(unequal),'score_mismatches':unequal,'wa':wa,'design_files':len(files),'design_seed_mapping_verified':True,'status':meta['status'],'comment':meta.get('comment'),'source_equal':(d/'src/main.cpp').read_bytes()==(runs/reference/'src/main.cpp').read_bytes()}
(root/'solutions/implb-notes/reset6-save-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
assert not unequal and not wa
