from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-sharedclimb8/main.cpp').read_text()
s=s.replace('rematch_probability(*des, extra?2:2, 1.0, 2.0);','rematch_probability(*des, 2, extra?(extra==1?.5:1.5):1.0, 2.0);',1)
s=s.replace('        complete(id,1);','        complete(id,repeat);',1)
d=R/'solutions/deval-sharedmix8';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-sharedmix8

改良元: solutions/deval-sharedclimb8。

元の4完成候補を保持し、良い2分岐のclimb後から追加するmatchingで、filler価値の重みを0.5・1.5に変える。各重みで各分岐を1回ずつ仕上げ、全部で8完成候補からVで選ぶ。元の候補は重み1.0、穴あけ後の再割当ては全候補1.05のまま。乱数saltも親と同じ固定値。

時間予算・探索回数は親と同じ。時間不足による切替えはない。DesignStore、@paper/@ops、ログ、目次・段の目印を維持。
''')
print(len(s.encode()))
