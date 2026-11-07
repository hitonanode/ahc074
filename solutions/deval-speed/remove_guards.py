"""Apply the guard removal from the supplied nofb baseline to our own source."""
from pathlib import Path
import difflib
ROOT=Path(__file__).resolve().parents[2]
def remove_guards(s):
 a=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text().splitlines(keepends=True)
 b=(ROOT/'solutions/deval-vbranch-nofb/main.cpp').read_text().splitlines(keepends=True)
 for op,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
  if op=='equal':continue
  old=''.join(a[i:j]);new=''.join(b[k:l])
  if 'DEVAL_DESIGN_LIMIT' in old and old not in s:
   s=''.join(line for line in s.splitlines(keepends=True) if 'DEVAL_DESIGN_LIMIT' not in line)
   continue
  assert old and s.count(old)==1,(op,old[:160],s.count(old))
  s=s.replace(old,new,1)
 assert 'DEVAL_REQUEST_LIMIT' not in s and 'DEVAL_DESIGN_LIMIT' not in s
 assert 'light_requests' not in s
 return s
if __name__=='__main__':
 import sys
 p=Path(sys.argv[1]);p.write_text(remove_guards(p.read_text()))
