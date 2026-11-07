from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
s=s.replace('if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";','if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "4";')
def emit(name,x,text):
    p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(x)
    (p/'README.md').write_text('改良元: `solutions/deval-helpeq1`。\n\n'+text+'\n\n単独helperの同generic距離候補を見積り上位1件まで追加し、最少generic距離のgoalは既存futureの低い方を選ぶ。元のgeneric移動を減らすhelperは残し、合計上位6候補とする。時計による切替えはない。元のログ・注釈・実験スイッチを保つ。\n')
    assert len(x.encode())<=522000;print(name,len(x.encode()))
emit('deval-equalwide6',s,'NEUTRAL_WIDTHを3から4へ増やす。設計とその他の注文予算は同じ。')
# Retain the existing modes and add modes 4/5 as in the isolated shortlist experiment.
before='''                        (cfg.plan_shortlist == 3 && c.path.size() == chosen_path.size()))) {'''
after='''                        ((cfg.plan_shortlist == 3 || cfg.plan_shortlist >= 4) && c.path.size() == chosen_path.size()) || ((cfg.plan_shortlist == 5 || (cfg.plan_shortlist == 4 && repeated)) && c.path.size() == chosen_path.size()+1))) {'''
assert s.count(before)==1
t=s.replace(before,after).replace('int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 3 : 0);','int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 5 : 0);')
emit('deval-equalplus6',t.replace('get("NS_ROUNDS", 2)','get("NS_ROUNDS", 3)'),
     'NEUTRAL_WIDTHを4、NS_ROUNDSを3にし、PLAN_SHORTLIST=5で1手長い候補まで後処理する。設計は同じ。')
emit('deval-equalshift6',t.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);','rematch_probability(*des, extra?1:1, 1.0, 2.0);'),
     '最初の4枝の穴あけ前rematchを2回から1回へ減らし、浮いた時間をNEUTRAL_WIDTH=4とPLAN_SHORTLIST=5（1手長い候補も後処理）へ回す。NS_ROUNDS=2を維持する。完成8候補・焼きなまし・窓割当ては同じ。')
