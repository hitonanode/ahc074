from pathlib import Path
import sys
sys.dont_write_bytecode=True
from task11_stack import stack
changes=['dcomp-t11-anchor-lazy','dcomp-t11-partial-cache','dcomp-t11-nextinit','dcomp-t11-hash4','dcomp-t11-family-merge','dcomp-t11-interval-wide','dcomp-t11-seed-one']
for name,pc6,pl1 in [('dcomp-t11-stack-one',False,False),('dcomp-t11-stack-pc6',True,False),('dcomp-t11-stack-pl1',True,True)]:
 d=stack(name,changes,'要求高速化の上に、trainingで得があった三つの探索変更を合成する。')
 p=d/'main.cpp';s=p.read_text()
 if pc6:
  a='    static constexpr int kPostCandidates = 4;';assert s.count(a)==1;s=s.replace(a,a.replace('4;','6;'))
 if pl1:
  a='if(std::strcmp(name,"PLAN_LIMIT")==0)return "2";';assert s.count(a)==1;s=s.replace(a,a.replace('"2"','"1"'))
 p.write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n出力同一の要求高速化（anchor配列・遅延anchorize、部分MDP cache、next_cost初期化省略、end-memoの4本hash）を基礎にする。探索の変更は、raw候補の二重移動結合をfamily選別の前に行うこと、joint filler DPの同点で広い区間を選ぶこと、完成ALT計画をもう一つ中立探索の親にして1→1だけ列挙すること。追加親はgap .3以内で最大1個、元の6候補枠を共用する。\n\n通常post候補数は'+('6'if pc6 else'4')+'、expandedの本修復枠は'+('1'if pl1 else'2')+'。それ以外の予算・9設計候補は親のまま。両コンパイラで同じ設定を使い、時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
