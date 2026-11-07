from pathlib import Path
import re
P=Path(__file__).resolve().parent;root=P.parents[1]
base=(root/'solutions/deval-flex125-plan3/main.cpp').read_text()
s=base
s=s.replace('    int solve_edges(const Edges& edges) const { return forward_values(edges)[H]; }\n','')
start=s.index('inline void add_filler_features(');end=s.index('// Two-state mean-field update.',start)
s=s[:start]+s[end:]
s=s.replace('// Empty for ordinary finishing. The final design-only search can accept a\n// complete Hungarian cycle using V instead of its linear proposal model.\n','// Statistics of the native finishing objective; V selects completed designs.\n')
def emit(name,text,detail):
 p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-flex125-plan3`。\n\n'+detail+'\n\n呼出しのないsolve_edgesと旧add_filler_featuresを削除し、誤ってVで巡回受理と記載したコメントを修正。ログ・プロファイラ・実験スイッチ・目次は維持。予算は固定、時間不足による切替えなし。\n')
 print(name,len(text.encode()))
emit('deval-trim6',s,'出力を変えずに、到達不能な2関数を除いてソースの余地を作る。')
variants={
 'deval-r6-ns3':('get("NS_ROUNDS", 2)','get("NS_ROUNDS", 3)','neutral rewriteの上限を2から3反復に増やす。'),
 'deval-r6-width4':('if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";','if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "4";','neutral候補の保持幅を3から4にする。'),
 'deval-r6-plans2':('get("PLAN_LIMIT", mode ? 1 : 99)','get("PLAN_LIMIT", mode ? 2 : 99)','追加計画の本探索を1件から2件にする。'),
 'deval-r6-short0':('get("PLAN_SHORTLIST", mode == 1 ? 3 : 0)','get("PLAN_SHORTLIST", 0)','追加計画を手数によるshortlistで除かず、費用順に本探索する。探索件数上限は同じ。'),
 'deval-r6-post8':('if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";','if(std::strcmp(name,"POST_CANDIDATES")==0)return "8";','安い後処理で比較する計画の収集幅を5から8へ増やす。'),
 'deval-r6-nmix75':('next_mix = 0.5, next_keep','next_mix = 0.75, next_keep','計画末端の列MDPの係数を0.5から0.75にする。挿入費用は同じ。'),
 'deval-r6-charge60':('kFillerCharge = 0.7','kFillerCharge = 0.6','取り出したままのfillerの将来返却費用を0.7から0.6にする。'),
 'deval-r6-charge80':('kFillerCharge = 0.7','kFillerCharge = 0.8','取り出したままのfillerの将来返却費用を0.7から0.8にする。'),
}
for n,(a,b,d) in variants.items():
 assert s.count(a)==1,(n,a)
 emit(n,s.replace(a,b),d+' 設計は変えない。')
