"""Reproduce the compiler-selective Task 10 starting solver from frozen parents."""
from pathlib import Path
import difflib,hashlib,json
root=Path(__file__).resolve().parents[2]
read=lambda name:(root/'solutions'/name/'main.cpp').read_text()
nine,fast,ten,combo=map(read,['dcomp-nine','dcomp-nine-fast','dcomp-ten-fast','combo-m1-nine'])
def transform(s,a,b,conditional=False):
    changes=[]
    for tag,i,j,k,l in difflib.SequenceMatcher(None,a.splitlines(True),b.splitlines(True),autojunk=False).get_opcodes():
        if tag=='equal':continue
        old=''.join(a.splitlines(True)[i:j]);new=''.join(b.splitlines(True)[k:l])
        if conditional:
            new='#if !defined(__clang__)\n'+new+'#else\n'+old+'#endif\n'
        # Pure insertions need an unchanged anchor.
        if not old:
            depth=2
            anchor=''.join(a.splitlines(True)[max(0,i-depth):i])
            while s.count(anchor)!=1 and depth<30:
                depth+=1;anchor=''.join(a.splitlines(True)[max(0,i-depth):i])
            assert anchor and s.count(anchor)==1
            old=anchor;new=anchor+new
        assert s.count(old)==1,(s.count(old),old[:90])
        changes.append((old,new))
    for a,b in changes:
        assert s.count(a)==1;s=s.replace(a,b)
    return s
s=transform(combo,nine,fast,True)
s=transform(s,fast,ten)
for name,source,desc in [
 ('dcomp-combo-ten',s,'combo-m1-nineにTask 9の10候補目を加える。窓探索のsparsebits高速化はGCCだけで使い、Clangでは元の全走査を使う。注文処理はcombo-m1-nineのまま。'),
 ('dcomp-combo-gnative',combo,'combo-m1-nineそのもの。GCC -O2 -march=nativeとClangの同時比較用。'),
 ('dcomp-combo-cnative',combo,'combo-m1-nineそのもの。Clang -O2 -march=nativeとGCCの同時比較用。')]:
    p=root/'solutions'/name;assert not p.exists();p.mkdir()
    (p/'main.cpp').write_text(source)
    (p/'README.md').write_text('改良元: solutions/combo-m1-nine\n\n'+desc+'\n\n反復数、既存9候補の生成・選択、実験スイッチ、ログ、DesignStoreを維持する。時間による打切りや軽いモードは使わない。fast-mathは使わない。\n')
(root/'solutions/dcomp-notes/t10-start-source.json').write_text(json.dumps({n:hashlib.sha256(read(n).encode()).hexdigest() for n in ['combo-m1-nine','dcomp-nine','dcomp-ten-fast','dcomp-combo-ten']},indent=2)+'\n')
