"""自分の候補だけを静的に監査する。ケースは実行しない。"""
from pathlib import Path
import json,re
base=Path('solutions/dcomp-combo-dual30/main.cpp').read_text()
markers=lambda s:re.findall(r'// ==== .*? ====',s)
clocks=lambda s:{x:len(re.findall(r'\b'+re.escape(x)+r'\s*\(',s)) for x in ['scaled_since','elapsed_sec','now']}
result=[]
for directory in sorted(Path('solutions').glob('d30a-*')):
 source=directory/'main.cpp';s=source.read_text()
 checks={'readme':(directory/'README.md').is_file(),'stages':markers(s)==markers(base),
         'clock_expression_counts':clocks(s)==clocks(base),'no_bits_header':'#include <bits/stdc++.h>' not in s,
         'design_store':'class DesignStore' in s or 'struct DesignStore' in s,
         'clock_scale':'CLOCK_SCALE' in s,'annotations':'@paper ' in s and '@ops ' in s,
         'files':sorted(x.name for x in directory.iterdir())==['README.md','main.cpp']}
 assert all(checks.values()),(str(directory),checks,clocks(s),clocks(base))
 result.append({'directory':str(directory),'checks':checks,'stage_count':len(markers(s))})
Path('solutions/impla-notes/audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('audited',len(result),'solvers; all checks passed; clock counts',clocks(base))
