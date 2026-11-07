from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
configs={'deval-end90':('kEndWeight = 1.0','kEndWeight = 0.90'),'deval-end95':('kEndWeight = 1.0','kEndWeight = 0.95'),'deval-next25':('next_mix = 0.5','next_mix = 0.25'),'deval-next75':('next_mix = 0.5','next_mix = 0.75'),'deval-demand15':('kFillerDemandWeight = 0.25','kFillerDemandWeight = 0.15'),'deval-demand35':('kFillerDemandWeight = 0.25','kFillerDemandWeight = 0.35')}
for name,(old,new) in configs.items():
 assert b.count(old)==1;s=b.replace(old,new)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text(f'改良元: `solutions/deval-seven-wide`\n\n注文処理の値関数の係数を `{old}` から `{new}` に変える。設計と探索回数は同じ。固定設計の注文列で較正する実験。時間依存の予算や軽量化はない。\n')
