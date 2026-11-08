from pathlib import Path
import re
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def setting(s,key,value):
 p=r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";';m=re.search(p,s);assert m
 return s[:m.start()]+f'if(std::strcmp(name,"{key}")==0)return "{value}";'+s[m.end():]
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n固定回数を両コンパイラで共用。設計・既存ログ・trace・profiler・実験スイッチ・段・DesignStoreは保持。時計による予算変更なし。予算拡大の研究版は通常評価なら--no-recordを使用する。\n')
for name,settings in [('ns2',{'NS_ROUNDS':'2'}),('pl1',{'PLAN_LIMIT':'1'}),('exp4',{'POST_CANDIDATES':'4'}),('width12',{'NEUTRAL_WIDTH':'12'}),('slack0',{'NEUTRAL_SLACK':'0'})]:
 s=B
 for k,v in settings.items():s=setting(s,k,v)
 write('dcomp-t11-'+name,s,'alt1上で余分な予算を減らす、または中立探索を広げる単独費用測定。'+str(settings))
x='    static constexpr int kPostCandidates = 4;';assert B.count(x)==1
write('dcomp-t11-pc6',B.replace(x,x.replace('4;','6;')),'通常側のpost候補を4→6にする中間点。expanded側は6のまま。')
s=B
for k,v in {'REPEAT_MIN':'0','NS_ALTERNATE_GAP':'1.5','NEUTRAL_WIDTH':'12','NEUTRAL_SLACK':'0','POST_CANDIDATES':'8'}.items():s=setting(s,k,v)
s=s.replace(x,x.replace('4;','8;'))
# Include the measured RWF extension, but no rejected early/tie value changes.
a='        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;\n';assert s.count(a)==1
s=s.replace(a,a+'        std::array<bool,K> end_filler{};\n        for(const auto& f:fillers)end_filler[f.paper]=true;\n')
a='                if (!initial_extra[k]) continue;\n';assert s.count(a)==1
s=s.replace(a,'                if (!initial_extra[k] && !end_filler[k]) continue;\n')
write('dcomp-t11-menu-wide',s,'残る既知の予算拡張をまとめて測る研究用: REPEAT_MIN0、RWF、ALT1.5、width12、slack0（正の費用余裕なし）、通常候補8、expanded候補8。追加computeの到達点を確かめるもので、時間条件を満たす提出候補とは扱わない。')
