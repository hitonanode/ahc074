from merge_exact import *
import ast
tree=ast.parse((ROOT/"solutions/deval-lastlab/make_helper_fund.py").read_text())
changes=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="changes" for t in n.targets))
for name,base in [('deval-helper-wide','deval-equalwide-fast'),('deval-helper-one','deval-helpeq-fast')]:
 s=delta(read(base),read('deval-trim6b'),read('deval-canonicalstamp6'))
 for a,b in changes:
  assert s.count(a)==1
  s=s.replace(a,b)
 detail='''canonicalizeのK要素初期化を、現在の世代と旧fillerの印を一緒に保存するunsigned stampへ置き換える。世代のwrap時だけ配列を初期化する。候補の順・重複・旧filler優先順位を保つ。ejectの整数SIMDとcache keyの整数圧縮は改良元を引き継ぐ。設計の全予算・出力はflex125-plan3と同じ。注文だけの変更で、同generic移動数のhelperを見積り上位1件追加し、同距離goalは既存future優先で選ぶ。単独helper全体は上位6件、NS_ROUNDS=2、PLAN_SHORTLIST=3。'''
 detail += '\n\nNEUTRAL_WIDTH='+('4' if name.endswith('wide') else '3')+'。全予算は固定で、時間不足による切替えはない。DesignStoreは選んだ設計を保存し、@paper/@ops・全指標・trace・profiler・実験switch・段の目次を保つ。\n'
 p=ROOT/"solutions"/name;p.mkdir(exist_ok=True)
 assert len(s.encode())<=522000
 (p/"main.cpp").write_text(s)
 (p/"README.md").write_text("改良元: `solutions/"+base+"`。\n\n"+detail)
 print(name,len(s.encode()))
