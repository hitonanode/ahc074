"""Task11 menu: all copies start from the committed alt1 source."""
from pathlib import Path
import re,json
R=Path(__file__).resolve().parents[2]
B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def setting(s,key,value):
    m=re.search(r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";',s)
    n=f'if(std::strcmp(name,"{key}")==0)return "{value}";'
    if m:return s[:m.start()]+n+s[m.end():]
    x='if(const char* value=std::getenv(local.c_str()))return value;'
    assert s.count(x)==1
    return s.replace(x,x+'\n        '+n)
def write(name,s,desc):
    p=R/'solutions'/name;assert not p.exists();p.mkdir()
    (p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n設定選別はseed 0–499。予算は固定回数で両コンパイラ共通、時計による軽量化や候補数変更はない。実験用環境変数、既存ログ・指標・trace・profiler・@paper/@ops、段の目印と目次、DesignStoreを保持する。\n')

for name,values in [('rmin0',{'REPEAT_MIN':'0'}),('slack50',{'NEUTRAL_SLACK':'.5'}),
                    ('alt125',{'NS_ALTERNATE_GAP':'1.25'}),('alt150',{'NS_ALTERNATE_GAP':'1.5'}),
                    ('exp8',{'POST_CANDIDATES':'8'})]:
    s=B
    for key,value in values.items():s=setting(s,key,value)
    write('dcomp-t11-'+name,s,'alt1上の追加探索の単独価格を測る。'+', '.join(f'{k}={v}' for k,v in values.items())+'。')
s=B;x='    static constexpr int kPostCandidates = 4;';assert s.count(x)==1
write('dcomp-t11-pc8',s.replace(x,x.replace('4;','8;')),'通常のpost_optimizeへ渡す候補数kPostCandidatesを4から8にする。拡張候補数F3_POST_CANDIDATESとは別の定数で、そちらは6のまま。')
s=B;x='        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;\n';assert s.count(x)==1
s=s.replace(x,x+'        std::array<bool,K> end_filler{};\n        for(const auto& f:fillers)end_filler[f.paper]=true;\n')
x='                if (!initial_extra[k]) continue;\n';assert s.count(x)==1
s=s.replace(x,'                if (!initial_extra[k] && !end_filler[k]) continue;\n')
write('dcomp-t11-rwf',s,'削除と付け替えの組を、要求開始時だけでなく計画終了時にfillerとなる紙にも広げる。')
# Apply only the known tenth-candidate delta, using exact local context.
import difflib
a=(R/'solutions/dcomp-nine-fast/main.cpp').read_text().splitlines(True)
b=(R/'solutions/dcomp-ten-fast/main.cpp').read_text().splitlines(True)
s=B
for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
    if tag=='equal':continue
    old=''.join(a[i:j]);new=''.join(b[k:l])
    if not old:
        anchor=''.join(a[i-2:i]);assert s.count(anchor)==1
        old=anchor;new=anchor+new
    assert s.count(old)==1,(tag,old[:80]);s=s.replace(old,new)
write('dcomp-t11-ten',s,'最初の9候補を変更せず、現最良設計にlate-rematchのみを施した10候補目をVで選択する。要求側はalt1のまま。')
write('dcomp-t11-profile','#define COLFAST_PROFILE 1\n#define F3_PROFILE 1\n'+B,
      '要求の包含・排他時間と演算種別の診断を有効にする。探索予算と出力はalt1と同じ。計測による時間増分があるため時間条件の判断には使わない。')

with (R/'solutions/dcomp-notes/PROGRESS.md').open('a') as f:
    f.write('''\n# Task 11\n\n## 11-08 16:24 — 開始、alt1上で費用を再測定\n\n- 基準はPR #172のdcomp-combo-alt1。GCC/Clangは各コンパイラの親に対する同一性を条件とする。両コンパイラで予算は共通。0–499だけで設定選別し、目標は通常2000で−0.03%以上、平均≤1.10×argon、p99はalt1より有意に悪くしない、Clang native500も遅くしない。\n- CLAUDEとSTATEの既知の記録を再読。Task8–10ソース・スクリプトは凍結し、Task11の新規dcomp-t11-*とnotesだけを変更する。\n- menu: REPEAT_MIN0、RWF、slack.5、ALT gap1.25/1.5、F3_POST_CANDIDATES8(exp8)、通常kPostCandidates8(pc8)を分ける。POST_CANDIDATES8とEXP8は実装上同じ設定なので二重実験せず、pc8は通常側の4→8として追加する。10候補目は通常比較で測る。\n- tailはGCC155517/Clang155242の0–499で上位5%を選び、段別・試行回数との関係を分析する。要求profileも両コンパイラで取る。\n''')
