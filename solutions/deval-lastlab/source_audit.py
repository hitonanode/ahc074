"""Read-only structural checks on the final one-file solver; write an audit beside it."""
from pathlib import Path
import re,json,sys,hashlib
root=Path(__file__).resolve().parents[2];p=root/'solutions'/sys.argv[1]
a=(root/'solutions/deval-flex125-plan3/main.cpp').read_text();b=(p/'main.cpp').read_text()
markers=lambda s:re.findall(r'^\s*// ==== (.*?) ====\s*$',s,re.M)
assert markers(a)==markers(b)
assert len(b.encode())<=522000 and 'bits/stdc++.h' not in b
for name in ['F3_','COLMDP_','AF_PROFILE','COLFAST_PROFILE','SIM_HARNESS','POSET_VERIFY','DesignStore','@paper','@ops']:
 assert name in b,name
for name in ['DEVAL_GUARD_STRESS','request_light','design_cap','guard_light']:
 assert name not in b,name
for name in ['solve_edges','add_filler_features','features_from_design','head_features_from_design']:
 assert len(re.findall(r'\b'+name+r'\b',a))==1 and not re.search(r'\b'+name+r'\b',b),name
clock=lambda s:re.findall(r'.*(?:Clock::now\(|elapsed_sec\(|scaled_since\().*',s)
# No new clock reads: these edits contain no time-budget decision.
assert clock(a)==clock(b)
sha=hashlib.sha256(b.encode()).hexdigest()
for f in ['builds.json','builds-native.json']:
 if (p/f).exists():
  x=json.loads((p/f).read_text());assert len(x)==2 and all(z['returncode']==0 and z['source_sha256']==sha for z in x)
result={'sha256':sha,'source_bytes':len(b.encode()),'section_markers_unchanged':len(markers(b)),
        'clock_lines_unchanged':len(clock(b)),'required_annotations_and_switches_present':True,
        'removed_export_methods_unreferenced':True,'time_fallback_names_absent':True,
        'manual_review':'diff against flex125-plan3 reviewed: declared helper/width/shortlist budgets and, only for fund/gap1, four fewer prematch rounds; exact integer optimizations; dead-value/function/comment cleanup. Six-sheet comparator graph contains every adjacent transposition, so all goal distances are finite and the first helper goal is selected before the future tie-break reads it.'}
(p/'source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
