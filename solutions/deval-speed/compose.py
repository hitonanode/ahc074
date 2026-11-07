"""Compose independent exact-output patches onto an owned solver."""
from pathlib import Path
import argparse,difflib
from remove_guards import remove_guards
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('name');p.add_argument('--features',nargs='*',default=[]);p.add_argument('--patch-base',default='deval-vbranch-o3');p.add_argument('--nofb',action='store_true');p.add_argument('--request',nargs='*',default=[]);a=p.parse_args()
s=(R/'solutions'/a.parent/'main.cpp').read_text()
base=(R/'solutions'/a.patch_base/'main.cpp').read_text().splitlines(keepends=True)
for name in a.features:
 target=(R/'solutions'/('deval-'+name)/'main.cpp').read_text().splitlines(keepends=True)
 for op,i,j,k,l in difflib.SequenceMatcher(None,base,target,autojunk=False).get_opcodes():
  if op=='equal':continue
  old=''.join(base[i:j]);new=''.join(target[k:l])
  if not old:
   # Pure insertion needs unambiguous surrounding context.
   old=''.join(base[max(0,i-1):i+1]);new=''.join(base[max(0,i-1):i])+new+''.join(base[i:i+1])
  elif s.count(old)>1:
   for context in range(1,25):
    before=''.join(base[max(0,i-context):i])
    if s.count(before+old)==1:
     old=before+old;new=before+new;break
  assert s.count(old)==1,(name,op,old[:120],s.count(old))
  s=s.replace(old,new,1)
if a.nofb and 'DEVAL_REQUEST_LIMIT' in s:s=remove_guards(s)
if a.request:
 needle='''        return std::getenv(local.c_str());'''
 replacement='''        if (const char* value=std::getenv(local.c_str())) return value;
'''
 for setting in a.request:
  key,val=setting.split('=',1);replacement+=f'        if (std::strcmp(name,"{key}")==0) return "{val}";\n'
 replacement+='        return nullptr;'
 assert s.count(needle)==1;s=s.replace(needle,replacement,1)
assert len(s.encode())<=520000
out=R/'solutions'/a.name;out.mkdir(exist_ok=True);(out/'main.cpp').write_text(s)
(out/'README.md').write_text(f'''# {a.name}

改良元: solutions/{a.parent}。

追加した出力保存の高速化: {', '.join(a.features) or 'なし'}。各変更の内容は対応する deval-* のREADMEと ../deval-speed/make_*.py に記載。生成手順は ../deval-speed/compose.py。

注文探索の固定設定: {', '.join(a.request) or '親と同じ'}。明示的なF3_*環境変数は実験用の上書きとして使える。LOCAL_BENCHで時間に応じて予算を変えない。

{'STATE.md 07:20に従い、時間不足による探索削減は置かない。' if a.nofb else '親の時間ガードを維持。'} DesignStore・@paper/@ops・目次と段の目印を維持する。
''')
print(a.name,len(s.encode()))
