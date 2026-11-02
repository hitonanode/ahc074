#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
h=Path(__file__).resolve().parent
base=(h.parent/'as6-cap38/main.cpp').read_text()
def split(s):
 a=s.index('WindowStats assign_windows(');b=s.index('// kBitLanes',a)
 m=s.index('    auto matching_cost =',a);n=s.index('    // A move:',m)
 return s[:a],s[b:],s[m:n]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
expected=split(base);summary={}
for name in ['main','cand2/main']:
 s=(h/(name+'.cpp')).read_text();parts=split(s)
 assert parts==expected, name
 assert '#include <bits/stdc++.h>' not in s
 summary[name]={'only_assign_windows_changed':True,'matching_cost_byte_identical':True,'source_sha256':sha(s),'prefix_sha256':sha(parts[0]),'suffix_sha256':sha(parts[1]),'matching_cost_sha256':sha(parts[2])}
(h/'scope-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
