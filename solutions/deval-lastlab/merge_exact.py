"""Compose disjoint, identity-checked source changes without touching their parents."""
from pathlib import Path
import difflib,re
ROOT=Path(__file__).resolve().parents[2]
def read(name):return (ROOT/'solutions'/name/'main.cpp').read_text()
def delta(s,before,after):
    a=before.splitlines(keepends=True);b=after.splitlines(keepends=True)
    for g in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_grouped_opcodes(3):
        old=''.join(a[g[0][1]:g[-1][2]]);new=''.join(b[g[0][3]:g[-1][4]])
        assert s.count(old)==1,(old[:120],s.count(old));s=s.replace(old,new,1)
    return s

def drop_dead_features(s):
    for name in ['features_from_design','head_features_from_design']:
        assert len(re.findall(r'\b'+name+r'\s*\(',s))==1,name
    i=s.index('    template<class DesignState> FeatureMap features_from_design')
    j=s.index('\n};\n} // namespace deval',i)
    s=s[:i]+s[j:]
    s=s.replace('// A proposal exchanges complete single/pair target units between physical slots.\n\n\n','')
    return s

def emit(name,base,s,detail):
    p=ROOT/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/'+base+'`。\n\n'+detail+'\n\n基準の固定予算、ログ・統計・注釈・実験switch・profiler・段の目印を保つ。時刻による切替えはない。\n')
    assert len(s.encode())<=522000,(name,len(s.encode()))
    print(name,len(s.encode()))
