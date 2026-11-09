"""評価JSONを使い、最終回答と同文のREPORTを組み立てる。"""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from report_tables import table,pm
p=argparse.ArgumentParser();p.add_argument('--recommend',choices=['reset6','stack1'],required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];notes=Path(__file__).resolve().parent
read=lambda n:json.loads((notes/(n+'.json')).read_text())
g=read('ablation-2000')[0 if a.recommend=='reset6' else 1]
c=read('clang-2000')[1 if a.recommend=='reset6' else 0]
assert all(x['score_pct']['mean']<=-2*x['score_pct']['se'] and x['net_improvement_pct']>0 for x in [g,c])
link=lambda label,path:f'[{label}]({root/path})'
solver='d30a-'+a.recommend
change='Design::reset_strength を 2.0→6.0 にする変更です。' if a.recommend=='reset6' else 'reset_strength を6、covered_gainの返却費用を0.8にする変更です。'
sections=[f"採用推奨は {link(solver,'solutions/'+solver+'/main.cpp')} です。{change} 2000件で GCC は **{pm(g['score_pct'])}%**、指定フラグの手元 Clang は **{pm(c['score_pct'])}%**。時間換算後の改善見積りは、それぞれ **{g['net_improvement_pct']:.4f}% / {c['net_improvement_pct']:.4f}%** で、0.03%の採用下限を超えます。",
 f"取り込み順は1件、{link(solver,'solutions/'+solver+'/README.md')}。差分は {link(a.recommend+'.patch','solutions/impla-notes/'+a.recommend+'.patch')} に保存しました。",
 "以下の ± は標準誤差、score はケースごとの log(候補/基準) の平均です。負なら改善。時間差は同じ比較の候補−基準、倍率適用済みの ms。helper / req / end の順です。W/T/L は勝/分/敗です。D は同じ比較の dual30、S は stack1、R は reset6。候補 run-id の `_` 以降が solutions/ 内のディレクトリ名です。",
 "Item 1 の判定：reset-strength は成功。finish-return は改善なし（追加時に悪化）。gc-realized と anneal-segments-8 は改善なし。小変更の500件スクリーニングは以下です。",
 table([('screen1',[0,1,2,3],'D'),('screen2',[0,1],'D')],with_v=True),
 "reset4・fret07の V 改善は2 SE未満でした。診断的修正の reset6・fret08は V が2 SE以上改善し、得点に明確な悪化がなかったため stack1 に併用しました。gc09 と seg8 は V が悪化したため終了しました。組合せと追加調整の結果です。",
 table([('stack1-500',[0],'D'),('stack1-2000',[0],'D'),('tune1-500',[1,2],'D'),('tune1-2000',[1],'D'),('fret-full-500',[1],'D'),('fret-full-2000',[1],'D')]),
 "reset10 は stack1 への上積みがなく、返却費用1.0は悪化。返却費用0.8を確率勾配と穴あけDPにも揃えた fret-full も、追加効果を確認できませんでした。",
 table([('tune1-increment-2000',[0],'S'),('fret-full-increment-2000',[0],'S')]),
 "Item 2、mono-columns は改善なし。既定の軟らかい費用1.7と、既存の穴費用との重複を考慮した0.6の両方で悪化しました。Item 3、perf-after-select と map-window-rate-time-neutral も改善なし。最初の版と一回の診断的修正を評価して終了しました。",
 table([('mono-500',[0,1],'D'),('speed-500',[0,1],'D'),('speed2-500',[0,1],'D')]),
 "単色列は各500件×9完成候補すべてで0でした。設計時間は約64 ms増加し、狙った設計は得られませんでした。保存済み run 20261109-003105_dcomp-combo-dual30 の seed 0〜49では、単独の少数色紙921枚は初期深さ0が855枚、1が66枚で、fix操作に0.523回/注文使われていました。「少数色紙が深く埋まり、ほぼ使われない」という前提は支持されません。欠色処理は最終設計では使われておらず、その実戦検証までできたとは扱いません。",
 "穴あけ前後で最良分岐が変わったのは1候補版で135/500件、上位2候補版でも46/500件でした（いずれも丸めのため3件は判定保留）。同じ分岐が選ばれたケースの出力は全件一致。設計は約24 ms／16 ms短縮しましたが、時間の価値を差し引いても平均は悪化側でした。窓交換率0.45・502000回では map_end 差 +0.49 ± 3.57 ms と時間が揃いましたが、gobj差 −0.004971 ± 0.003884、V差 +0.006219 ± 0.002448で改善を確認できませんでした。",
 "採用範囲を確定するための2000件比較です。Clang群のDは 20261109-113526_dcomp-combo-dual30（reset6のrunだけ接頭辞が113527）。手元のコンパイラは Ubuntu Clang 18.1.3、指定の -std=c++23 -O2 -march=native -stdlib=libc++ -ftrivial-auto-var-init=zero と LOCAL_BENCH / CLOCK_SCALE=1.1 を使用しました。ジャッジのClang 21実機による測定ではありません。",
 table([('clang-2000',[0,1],'D'),('ablation-2000',[0,1],'D')]),
 "reset6 に covered_gain の返却費用0.8を加える差を、両コンパイラで直接比較しました。",
 table([('clang-increment-2000',[0],'R'),('ablation-increment-2000',[0],'R')]),
 "Vで単独の改善が見えても、併用時の追加効果は実得点で確認する必要がありました。推奨する変更範囲は上記の直接比較で決めています。",
 "推奨候補の時間p99（基準→候補、ms）は以下です。",
 '|ビルド|helper|req|end|\n|---|---:|---:|---:|']
for name,x in [('GCC',g),('Clang',c)]:
 m=x['metrics'];sections.append('|'+name+'|'+'|'.join(f"{m[k]['base_p99']:.2f} → {m[k]['candidate_p99']:.2f}" for k in ['helper_end_sec','req_sec','end_sec'])+'|')
sections.append('時間の価値は設計100 msあたり0.03%、注文処理100 msあたり0.055%として計算しました。全評価でWA・表示誤りは0。採否に使った比較の外部負荷に警告はありません。18解法すべてでGCC／Clangのビルドと20件の動作確認を行い、段の目印・CLOCK_SCALE・DesignStore・注釈を保持しています。推奨候補はLOCAL_BENCHなしでも両コンパイラでビルドを確認しました。新しい時計読みや時間打切りは加えていません。')
sections.append(f"全段階のp99、代理指標、診断、smokeのrun-idは {link('PROGRESS.md','solutions/impla-notes/PROGRESS.md')} と同ディレクトリの集計JSONに記録しました。変更は自分の新規ディレクトリ内のみで、コミットは作成していません。同文の {link("REPORT.md","solutions/impla-notes/REPORT.md")} を保存しました。")
if (notes/'reset-tune-2000.json').exists():
    index=sections.index('推奨候補の時間p99（基準→候補、ms）は以下です。')
    sections[index:index]=[
        '返却費用を親の0.6へ戻した条件で、reset強度8・10も確認しました。基準Dは20261109-115802_dcomp-combo-dual30、Rは同じ比較のreset6です。',
        table([('reset-tune-500',[1,2],'D'),('reset-tune-2000',[1,2],'D')]),
        'reset6に対する2000件の追加効果です。',
        table([('reset-tune-increment-2000',[0,1],'R')]),
        'reset8・10もdual30比では成功でしたが、reset6に対する上積みはありませんでした。両コンパイラで成功したreset6を採用し、追加調整を終了しました。']
# Keep the two p99 rows in one table rather than inserting blank paragraphs.
text='\n\n'.join(sections)+'\n';text=text.replace('|end|\n|---|---:|---:|---:|\n\n|GCC','|end|\n|---|---:|---:|---:|\n|GCC').replace('|\n\n|Clang','|\n|Clang')
(notes/'REPORT.md').write_text(text)
print(text)
