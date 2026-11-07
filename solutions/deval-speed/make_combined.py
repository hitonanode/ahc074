"""Compose tested independent blocks; do not edit their parent solutions."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[2]
def block(s,start,end):
    a=s.index(start);b=s.index(end,a);return s[a:b]
def replace_block(s,new,start,end):
    a=s.index(start);b=s.index(end,a);return s[:a]+block(new,start,end)+s[b:]
p=argparse.ArgumentParser();p.add_argument('--name',default='deval-speedcore');p.add_argument('--screen',type=int,default=0);p.add_argument('--samples',type=int,default=32);p.add_argument('--map',type=int,default=450000);p.add_argument('--climb',type=int,default=50000);p.add_argument('--preview-match',type=int,default=2);a=p.parse_args()
s=(ROOT/('solutions/deval-screen2/main.cpp' if a.screen else 'solutions/deval-vbranch-o3/main.cpp')).read_text()
hung=(ROOT/'solutions/deval-hungarian-vec/main.cpp').read_text()
start='// The assignment of least total cost of a square cost matrix'
end='// The filler value of the column heads for rematch_probability'
s=replace_block(s,hung,start,end)
s=replace_block(s,(ROOT/'solutions/deval-perfsparse/main.cpp').read_text(),'template<int Capacity>\nstruct Perforation','// ==== Design state:')
small=(ROOT/'solutions/deval-smallfill/main.cpp').read_text()
a0=small.index('    // State snapshots normally have at most four fillers.')
a1=small.index('    FillerList fillers;',a0)
s=s.replace('#include <algorithm>','#include <algorithm>\n#include <initializer_list>',1)
s=s.replace('std::vector<Filler>','FillerList')
where=s.index('    FillerList fillers;');s=s[:where]+small[a0:a1]+s[where:]
s=s.replace('std::erase_if(fillers, [&](const Filler& f) { return f.paper == k; });','fillers.erase_if([&](const Filler& f) { return f.paper == k; });',1)
s=s.replace('static constexpr int kSamples = 32;',f'static constexpr int kSamples = {a.samples};',1)
s=s.replace('kMapIters = int(450000 * ITER_SCALE)',f'kMapIters = int({a.map} * ITER_SCALE)',1)
s=s.replace('const int climb_env = 50000',f'const int climb_env = {a.climb}',1)
if a.screen and a.preview_match==1:
    s=s.replace('    if(!raw && phase!=2) {\n    if (climb_iters > 0)','    if(!raw) {\n    if (climb_iters > 0 && phase!=2)',1)
    s=s.replace('rematch_probability(*des, std::max(1,int(2)), 1.0, 2.0);','rematch_probability(*des, phase?1:2, 1.0, 2.0);',1)
assert len(s.encode())<=520000
d=ROOT/'solutions'/a.name;d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text(f'''# {a.name}

改良元: solutions/deval-vbranch-o3。生成スクリプト: ../deval-speed/make_combined.py。

Hungarian法の4列SIMD更新、穴あけの整数DP・被覆範囲共有・変化したサンプルだけの再構築、短いfiller列の内部保持を組み合わせる。

窓割当て {a.map:,} 回、filler climb {a.climb:,} 回、穴あけの色サンプル {a.samples} 個。{'4分岐を穴あけ前のVで選別し、上位2候補だけ最後まで仕上げる。' if a.screen else '元と同じ4分岐をすべて仕上げる。'} {'一次選別前に再割当て1回、通過後に1回。' if a.preview_match==1 else '一次選別前に再割当て2回。'}

設計の保存・@paper/@ops・段の目印・時間ガードを維持。LOCAL_BENCHでは注文探索予算は固定。
''')
print(a.name,len(s.encode()))
