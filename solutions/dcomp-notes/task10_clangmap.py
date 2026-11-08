from pathlib import Path
r=Path(__file__).resolve().parents[2]
b=(r/'solutions/dcomp-combo-ten/main.cpp').read_text()
sp=b.replace('#if !defined(__clang__)\n','#if 1 // Task 10: diagnose the sparse path also on Clang\n')
for name,s in [('dcomp-clang-map-dense-prof','#define DESIGN_PROFILE 3\n'+b),('dcomp-clang-map-sparse-prof','#define DESIGN_PROFILE 3\n'+sp)]:
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-combo-ten\n\nClangの窓探索の回帰原因をDESIGN_PROFILE=3で分けて測る診断版。denseは旧処理、sparseはTask 9の高速化をClangでも使う。探索内容は不変。計測用で提出候補ではない。\n')
