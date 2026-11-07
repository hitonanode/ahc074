from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
for name,pre,late in [('deval-match-shift4',1,'extra?1:2'),('deval-match-shift8',0,'2'),('deval-match-late2',1,'2')]:
    x=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);',f'rematch_probability(*des, extra?1:{pre}, 1.0, 2.0);')
    x=x.replace('const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", 1));',f'const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", {late}));')
    p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
    (p/'README.md').write_text(f'''改良元: `solutions/deval-trim6b`。

最初の4枝の穴あけ前rematchを2回から{pre}回へ減らし、穴あけ後の色を自由にしたrematchを{'最初の4枝で' if name.endswith('4') else '全8候補で'}1回から2回へ増やす。cold再仕上げ2回の穴あけ前rematchは1回を維持する。穴あけ前に余分に整える代わりに、穴あけ済みの物理的な模様に合わせて再割当てを進める。色固定の解除、係数1.25、完成8候補のV選択は元のまま。全予算固定、時計による切替えなし。ARGON_D2_LATE_ITERSの明示設定は従来通り優先する。
''')
    assert len(x.encode())<=522000;print(name,len(x.encode()))
