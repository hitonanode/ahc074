from pathlib import Path
import sys,json,re,difflib,hashlib
root=Path('/home/sato/ahc074/runs');b=root/sys.argv[1];c=root/sys.argv[2];fixed=root/sys.argv[3]
source=Path('solutions/argon-req-filldp-positive/main.cpp').read_bytes()
for f in [c/'src/main.cpp',fixed/'src/main.cpp']:
 assert f.read_bytes()==source,f
print('source_sha256',hashlib.sha256(source).hexdigest())
bsource=Path('solutions/esw-slim/main.cpp').read_text().splitlines();csource=source.decode().splitlines()
markers=lambda lines:[x.strip() for x in lines if re.match(r'\s*// ====',x)]
assert markers(bsource)==markers(csource)
changed=set()
for tag,i,j,k,l in difflib.SequenceMatcher(a=bsource,b=csource,autojunk=False).get_opcodes():
 if tag!='equal':
  changed.add(next((x.strip() for x in reversed(bsource[:i+1]) if re.match(r'\s*// ====',x)),'header'))
print('changed_sections',sorted(changed))
files=sorted((b/'out').glob('*.txt'));bad_design=[];bad_paper=[];bad_metric=[];bad_fixed=[]
for bf in files:
 cf=c/'out'/bf.name
 if bf.read_bytes().splitlines()[:192]!=cf.read_bytes().splitlines()[:192]:bad_design.append(bf.name)
 bl=(b/'err'/bf.name).read_text();cl=(c/'err'/bf.name).read_text()
 if re.findall(r'^@paper .*$',bl,re.M)!=re.findall(r'^@paper .*$',cl,re.M):bad_paper.append(bf.name)
 names=lambda text:re.findall(r'^(\w+) = ',text,re.M)
 bn=names(bl);cn=names(cl)
 if [x for x in cn if x in set(bn)]!=bn:bad_metric.append(bf.name)
 if cf.read_bytes()!=(fixed/'out'/bf.name).read_bytes():bad_fixed.append(bf.name)
print('normal_cases',len(files),'different_designs',bad_design[:8], 'different_paper_labels',bad_paper[:8], 'missing_or_reordered_base_metrics',bad_metric[:8], 'normal_fixed_output_differences',bad_fixed[:8])
assert len(files)==2000 and not any([bad_design,bad_paper,bad_metric,bad_fixed])
for run in [b,c]:
 meta=json.loads((run/'meta.json').read_text())
 print(run.name,'design_files',len(list((run/'design').glob('*'))),'outside_load',meta.get('outside_load'))
 assert len(list((run/'design').glob('*')))==2000
print('audit_passed')
