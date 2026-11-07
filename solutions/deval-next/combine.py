"""Compose only specified, independently measured changes into a new solver."""
from pathlib import Path
import argparse
r=Path(__file__).resolve().parents[2];p=argparse.ArgumentParser()
p.add_argument('base');p.add_argument('name');p.add_argument('--gather',action='store_true');p.add_argument('--terminal',type=int);p.add_argument('--plan3',action='store_true');p.add_argument('--next-mix',type=float);p.add_argument('--initial-rank',action='store_true');p.add_argument('--extra',type=int);p.add_argument('--warm-pattern');a=p.parse_args()
s=(r/'solutions'/a.base/'main.cpp').read_text();changes=[]
if a.gather:
 g=(r/'solutions/deval-map-gather/main.cpp').read_text();start=g.index('        const __m128i rs =',g.index('__m256i closure4('));end=g.index('        const __m256i ones =',start)
 x=s.index('        const __m256i f =',s.index('__m256i closure4('));y=s.index('        const __m256i ones =',x);s=s[:x]+g[start:end]+s[y:];changes.append('窓の4組閉包の関係行列を整数表からgatherする出力同一の高速化。')
if a.terminal:
 old='static constexpr double kTopPenalty = 0.00, kEndWeight = 1.0;';assert old in s
 s=s.replace(old,'static constexpr double kTopPenalty = 0.00;\n    double kEndWeight = 1.0, future_discount = 1.0;\n    int orders_done = 0, total_orders = 1024;',1)
 old='        return charge;\n    }\n    // Expected cost of the next request';assert old in s
 s=s.replace(old,'        return future_discount * charge;\n    }\n    // Expected cost of the next request',1)
 old='    Moves process(int u) {\n        CF_SCOPE(process);';assert old in s
 s=s.replace(old,f'''    Moves process(int u) {{
        CF_SCOPE(process);
        // Finite-order horizon; no clock or benchmark-mode dependency.
        const int remaining = total_orders - 1 - orders_done++;
        future_discount = std::min(1., std::max(0, remaining) / {a.terminal}.);
        kEndWeight = future_discount;''',1)
 changes.append(f'最後の{a.terminal}注文の将来費用を、残り注文数/{a.terminal}（上限1）倍にする。')
 pos=s.rfind('    Solver solver = make_solver(state);')
 assert pos>=0;s=s[:pos]+s[pos:].replace('    Solver solver = make_solver(state);','    Solver solver = make_solver(state);\n    solver.total_orders = R;',1)
if a.plan3:
 old='        if(std::strcmp(name,"REPEAT_MIN")==0)return ".05";';assert old in s
 s=s.replace(old,'        if(std::strcmp(name,"PLAN_SHORTLIST")==0)return "3";\n'+old,1);changes.append('後処理で同じ手数の別計画も検討するPLAN_SHORTLIST=3。')
if a.next_mix is not None:
 old='next_mix = 0.5';assert old in s;s=s.replace(old,f'next_mix = {a.next_mix}',1);changes.append(f'列MDPの次状態価値の混合比を{a.next_mix}にする。')
if a.initial_rank:
 t=(r/'solutions/deval-initial-rank/main.cpp').read_text()
 marker='// ==== V: design-only expected moves ===='
 helper=t[t.index('// ==== Initial column order ===='):t.index(marker)]
 assert marker in s and '// ==== Initial column order ====' not in s
 s=s.replace(marker,helper+marker,1).replace('//   V: design-only expected moves','//   Initial column order\n//   V: design-only expected moves',1)
 needle='    if(!finished)state.emergency=true;\n    std::cerr << chosen_log;'
 assert needle in s;s=s.replace(needle,'    if(!finished)state.emergency=true;\n    if(finished)improve_initial_columns(state);\n    std::cerr << chosen_log;',1)
 changes.append('最終設計を選んだ後、filler需要込みの重み順と2色の小DPで列内の初期の紙の順序を整える。紙番号とdedを対応して更新する。')
if a.extra is not None or a.warm_pattern:
 import re
 pos=s.index('    // Repeat the full native finishing');pre=s[:pos];tail=s[pos:]
 if a.extra is not None:tail,n=re.subn(r'for\(int j=0;j<\d+;\+\+j\)',f'for(int j=0;j<{a.extra};++j)',tail,count=1);assert n==1
 if a.warm_pattern:tail,n=re.subn(r'const bool warm=[^;]+;',f'const bool warm={a.warm_pattern};',tail,count=1);assert n==1
 s=pre+tail;changes.append(f'追加仕上げ{a.extra}回、warm条件 `{a.warm_pattern}`。warmは穴状態から穴あけと再割当てのみ、それ以外は通常の再仕上げ。')
d=r/'solutions'/a.name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s);assert len(s.encode())<=520000
(d/'README.md').write_text(f'改良元: `solutions/{a.base}`\n\n'+'\n\n'.join(changes)+'\n\n全探索予算は固定。時間不足による軽量化・設計打切り・候補数の変更はない。DesignStoreは選んだ完成設計を保存する。\n')
print(a.name,len(s.encode()))
