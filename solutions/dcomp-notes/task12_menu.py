from pathlib import Path
import difflib
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
def make(name,s,desc):
 d=S/name
 if d.exists():
  assert (d/'main.cpp').read_text()==s;return
 d.mkdir();(d/'main.cpp').write_text(s);(d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\n'+desc+'\n\n設計・探索予算は親のまま、両コンパイラ共通。CLOCK_SCALE・ログ・実験switch・段と目次・DesignStoreを保持し、時計による軽量化なし。\n')
for suffix,old,new,desc in [
 ('charge75','kFillerCharge = 0.7;','kFillerCharge = 0.75;','終状態に残すfillerの費用を0.7から0.75へ上げる。near-tie補正が示したfiller費用の過小評価を、候補生成側でも弱く補正する試験。'),
 ('charge65','kFillerCharge = 0.7;','kFillerCharge = 0.65;','終状態に残すfillerの費用を0.7から0.65へ下げる対照試験。'),
 ('end105','kEndWeight = 1.0;','kEndWeight = 1.05;','次状態の列費用の係数を1.0から1.05へ上げる。near-tie補正と計画生成側の尺度の違いを小さい変更で調べる。'),
 ('gen60','return 0.5*future[rank];','return 0.6*future[rank];','比較シートの終状態費用を0.5から0.6へ上げる。near-tie補正の方向が候補生成にも有効かを調べる。')]:
 assert b.count(old)==1;make('dcomp-t12-'+suffix,b.replace(old,new),desc)
# Apply the previously tested standalone mergepool delta to the new combination.
a=(S/'dcomp-combo-alt1/main.cpp').read_text().splitlines(True);c=(S/'dcomp-t11-mergepool/main.cpp').read_text().splitlines(True);s=b
for group in difflib.SequenceMatcher(None,a,c,autojunk=False).get_grouped_opcodes(2):
 i,j=group[0][1],group[-1][2];k,l=group[0][3],group[-1][4]
 old=''.join(a[i:j]);new=''.join(c[k:l]);assert old and s.count(old)==1;s=s.replace(old,new)
make('dcomp-t12-mergepool',s,'Task11で単独利益があったnear-tie候補全体の二重移動修復をdual25へ合成する。Task11のtight12合成では利益がなかったため、異なる通常6候補・両端の追加親の組合せで一度だけ確認する。補正係数は変えない。')
# Replay-prefix cache affects only work, not search budgets; explicitly test current context.
x='''        bool prefix = get("PREFIX", 1);''';assert b.count(x)==1
make('dcomp-t12-noprefix',b.replace(x,'''        bool prefix = get("PREFIX", 0);'''),'postの可視性再生prefix cacheを無効化するexact対照。Task11でClangに小さい短縮があったが採らなかったため、dual25上で両コンパイラの費用を確認する。探索回数・値の計算順は変えない。')
