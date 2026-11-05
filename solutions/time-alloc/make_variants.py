#!/usr/bin/env python3
"""Budget-only variants of esw-memo; source edits are asserted literal substitutions."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--mode',type=int);p.add_argument('--rounds',type=int);p.add_argument('--expanded',type=int);p.add_argument('--post',type=int);p.add_argument('--anneal',type=int);p.add_argument('--map',type=int);p.add_argument('--gopt',type=int);p.add_argument('--climb',type=int);p.add_argument('--match',type=int);p.add_argument('--plan-limit',type=int);p.add_argument('--one-anchors',type=int);p.add_argument('--width',type=int);a=p.parse_args()
root=Path('solutions')/a.name
assert a.name=='time-alloc' or a.name.startswith('time-alloc-')
if root.exists() and a.name!='time-alloc':raise SystemExit(f'already exists: {root}')
root.mkdir(exist_ok=True)
s=Path('solutions/esw-memo/main.cpp').read_text();changes=[]
def put(old,new,desc):
 global s
 assert s.count(old)==1,(old,s.count(old))
 s=s.replace(old,new,1);changes.append(desc)
if a.mode is not None:put('get("MODE", 1)',f'get("MODE", {a.mode})',f'MODE既定値: 1 → {a.mode}')
if a.rounds is not None:put('get("NS_ROUNDS", mode == 1 ? 1 : 2)',f'get("NS_ROUNDS", {a.rounds})',f'NS_ROUNDS既定値: 1 → {a.rounds}')
if a.expanded is not None:put('get("POST_CANDIDATES", mode == 2 ? 8 : mode == 1 ? 3 : 2)',f'get("POST_CANDIDATES", {a.expanded})',f'POST_CANDIDATES既定値: 3 → {a.expanded}')
if a.post is not None:put('static constexpr int kPostCandidates = 2;',f'static constexpr int kPostCandidates = {a.post};',f'通常の後処理候補 kPostCandidates: 2 → {a.post}')
if a.plan_limit is not None:put('get("PLAN_LIMIT", mode ? 1 : 99)',f'get("PLAN_LIMIT", {a.plan_limit})',f'PLAN_LIMIT既定値: 1 → {a.plan_limit}')
if a.one_anchors is not None:put('get("ONE_ANCHORS", mode ? 2 : 0)',f'get("ONE_ANCHORS", {a.one_anchors})',f'ONE_ANCHORS既定値: 2 → {a.one_anchors}')
if a.width is not None:put('return s ? std::max(1, std::atoi(s)) : 2;',f'return s ? std::max(1, std::atoi(s)) : {a.width};',f'NEUTRAL_WIDTH既定値: 2 → {a.width}')
for key,old,symbol in [('anneal',14900000,'kAnnealIters'),('map',450000,'kMapIters'),('gopt',133000,'kGoptSteps'),('climb',154000,'kClimbIters')]:
 value=getattr(a,key)
 if value is not None:put(f'{symbol} = int({old} * ITER_SCALE)',f'{symbol} = int({value} * ITER_SCALE)',f'{symbol}: {old} → {value}')
if a.match is not None:put('kMatchIterations = 4;',f'kMatchIterations = {a.match};',f'kMatchIterations: 4 → {a.match}')
root.joinpath('main.cpp').write_text(s)
root.joinpath('budgets.json').write_text(json.dumps(vars(a),indent=2)+'\n')
root.joinpath('README.md').write_text('改良元: solutions/esw-memo\n\n時間配分だけを変える比較用の版。探索方法・評価関数・乱数生成器・候補の作り方は変更しない。次の既定予算をソースに直接設定する。\n\n'+''.join('- '+v+'\n' for v in changes)+'''\n上記以外の予算は改良元と同じ。既存の実験スイッチ・ログ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@opsと段の目印をすべて保持する。F3_*やMAP_ITERS等の既存の環境変数も引き続き予算を上書きする。比較では基準にも届くこれらの変数を設定しない。\n\n主な指標は、map_end_sec / anneal_end_sec / climb_end_sec / match_end_sec / perforation_end_sec / helper_end_sec（各段の終了時刻）、req_sec（注文計画の合計時間）、end_sec（終了時刻）、gobj_after / model_cost / proxy_after（設計の評価値）、total_moves / self_wrong / op_label_errors（操作数・誤表示・ラベル不整合）。ジャッジ時間は1.04×helper_end_sec + 1.35×req_sec + (end_sec−helper_end_sec−req_sec)で推定する。\n\n比較結果と採否はsolutions/time-alloc/REPORT.mdに記載する。\n''')
print(a.name,changes)
