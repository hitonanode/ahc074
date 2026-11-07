"""Apply only exact-output changes to the combined training candidate."""
from pathlib import Path
import difflib
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
s=(R/'solutions/deval-flex8/main.cpp').read_text()
for name in ['deval-column-kind','deval-vstatic']:
    a=b.splitlines(keepends=True);v=(R/'solutions'/name/'main.cpp').read_text().splitlines(keepends=True)
    for tag,i,j,k,l in difflib.SequenceMatcher(None,a,v,autojunk=False).get_opcodes():
        if tag=='equal':continue
        old=''.join(a[i:j]);new=''.join(v[k:l])
        # Include adjacent unchanged lines for insertion-only edits.
        if not old:old=''.join(a[j:j+3]);new+=old
        assert s.count(old)==1,(name,old)
        s=s.replace(old,new,1)
s=s.replace('    double generic_bias() const {','    __attribute__((target("popcnt"))) double generic_bias() const {',1)
# The fitted coefficient table is generated; whitespace carries no information.
a=s.index('inline constexpr std::array<ModelTerm,142> kTerms{{');z=s.index('}};',a)
s=s[:a]+s[a:z].replace('\n    {','\n{')+s[z:]
s=s.replace('        const bool warm_pass=extra==2;\n','',1)
for name,plan3 in [('deval-flex8-fast',False),('deval-flex8-fast-plan3',True)]:
    t=s
    if plan3:
        old='get("PLAN_SHORTLIST", mode == 1 ? 2 : 0)';assert old in t;t=t.replace(old,'get("PLAN_SHORTLIST", mode == 1 ? 3 : 0)',1)
    assert len(t.encode())<=522000,len(t.encode())
    p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(t)
    (p/'README.md').write_text('改良元: `solutions/deval-flex8`。\n\n'+
      '穴あけ後の単独紙の色固定解除、列MDPの需要分類、汎用紙の末端評価を引き継ぐ。窓割当ての整数累積和とVの色マスク生成の高速化も同じ。\n\n'+
      '追加の出力同一高速化: 焼きなましの列移動を3種類にテンプレート化する。Vの静的特徴量は値への参照を先に求め、内側ループで文字列生成とmap検索を繰り返さない。新しい汎用紙の順序評価ではpopcount命令を明示的に有効にする。浮動小数点の式と更新順を保つ。\n\n'+
      ('F3_PLAN_SHORTLISTの既定値を2から3へ変え、現在の解と同手数の計画も後処理する。候補への後処理回数上限は同じ。\n\n' if plan3 else '')+
      'ソース容量のため、生成されたVの係数表の行頭空白と使われない局所変数だけを削る。係数値・ログ・実験スイッチは同じ。8候補、全探索予算は固定。時間不足による切り替えなし。DesignStoreは選んだ最終設計を保存する。\n')
    print(name,len(t.encode()))
