"""Render completed experiment summaries; input is the locked analysis JSON, no new fitting."""
from pathlib import Path
import json
N=Path(__file__).resolve().parent
out=['# Task 11: 完了済み実験の一覧','', '差は各試験の基準比（原則alt1）のseedごとの平均log比×100、±1SE。各行に基準runを併記する。固定設計replayの時間は対応req差であり、judgeの絶対時間には使わない。表は解析JSONから再生成する。','']
groups=[('要求メニュー',['menu','menu2','menuplus','cuts']),('修復後の比較と新しい出発点',['repair','tie','family','interval','interval2','seed2','seed3','mergeearly','neutraltail-gcc','stack-search','stack-width']),('出力同一候補とコンパイラ',['cover-gcc','cover-clang','owner-gcc','owner-clang','hash-gcc','hash-clang','anchor-gcc','anchor-clang','partial-gcc','partial-clang','smallmoves-gcc','smallmoves-clang','cacheoff-gcc','cacheoff-clang','nextinit-gcc','nextinit-clang','pending-gcc','pending-clang','closure-gcc','closure-clang','direction-gcc','direction-fixed-gcc','direction-clang','holetable-gcc','holetable-clang','genericsplit-gcc','genericsplit-clang','neutraltail-clang','validmask-clang','fast-gcc','fast-clang']),('10番目の設計候補',['ten'])]
groups.insert(2,('追加の効率化・合成',['seedcap','interval3','postspecial-gcc','postspecial-clang','scan4-gcc','scan4-clang']))
groups.insert(3,('後半の検証',['tight','onecuts','tieconservative','seedrank','mergepool','stacktime-gcc','stacktime-clang','canonprefix-gcc','canonprefix-clang','nextcolors-gcc','nextcolors-clang','latememo-gcc','latememo-clang','linkless-gcc','linkless-clang','ejectbmi-gcc','ejectbmi-clang']))
groups.insert(4,('最終合成と凍結前の選別',['directgeom-gcc','directgeom-clang','fastlate-gcc','fastlate-clang','fastlate-gccnative','funded-gcc','funded-clang','funded-gcc-identity','funded-clang-identity','alt3','alt3-clang','alt3-clang-repeat','shared6','poolstack','slackfund','slackfund-clang']))
for heading,tags in groups:
 out+=['## '+heading,'','|試験・run|N×列|差%±SE|req差ms±SE|helper差ms±SE|stdout一致|','|---|---:|---:|---:|---:|---:|']
 for tag in tags:
  p=N/f't11-{tag}.json'
  if not p.exists():continue
  d=json.loads(p.read_text());n=d['seeds'][1]-d['seeds'][0]
  for rid,v in d['results'].items():
   if rid.endswith('-prof'):continue
   q=v['score_pct'];m=v['metrics'];iden=v['identity']
   def ms(k):
    z=m.get(k,{}).get('paired');return f"{1000*z['mean']:+.3f}±{1000*z['se']:.3f}"if z else '—'
   out.append(f"|{tag}: `{rid}`<br>基準 `{d['reference']}`|{n}×{d['orders']}|{q['mean']:+.6f}±{q['se']:.6f}|{ms('req_sec')}|{ms('helper_end_sec')}|{iden['same']}/{iden['total']}|")
 out+=['']
(N/'TABLES11.md').write_text('\n'.join(out)+'\n')
