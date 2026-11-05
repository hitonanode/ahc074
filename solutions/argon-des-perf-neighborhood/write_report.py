"""Assemble the evidence already measured. Run under the evaluation lock."""
import difflib,json,math,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
load=lambda name:json.loads((H/name).read_text())
grid=load('grid-500.json');full=load('grid-2000.json');donor=load('donor-500.json');dense=load('dense-500.json');refresh=load('refresh-500.json');nonhead=load('nonhead-500.json')
b,c=full[0],full[-1];d=load('proxy-drift200.json')['summary']
m=lambda r,k:r['metrics'][k]['mean']
diff=lambda r:f"{r['score']['mean']:+.6f} ± {r['score']['se']:.6f}"
wtl=lambda r:'/'.join(map(str,r['wtl']))
groups=[('係数・標本、500件',grid),('標本、最終2000件',full),('donor条件付け、500件',donor),('512標本、500件・記録なし',dense),('追加1周と確率更新、500件',refresh),('非head、500件',nonhead)]
lines=['# 全比較の測定値','', '差は各表の先頭runに対する平均log比（%）。±はseed間の標準誤差。負が改善。',
'judge = end_sec + 0.04 × helper_end_sec + 0.35 × req_sec。時間は秒。',
'512標本だけは時間超過の測定専用で記録なし。他は通常比較として記録し、設計を保存した。','']
for title,rows in groups:
    lines+=['## '+title,'','| run-id | n | 差 ± SE (%) | 勝/分/敗 | req | helper end | judge平均 | p99 | 最大 | >2秒 | 穴数 | 穿孔時間 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        j=r['judge'];lines.append(f"| {r['run']} | {r['n']} | {diff(r)} | {wtl(r)} | {m(r,'req_sec'):.6f} | {m(r,'helper_end_sec'):.6f} | {j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} | {m(r,'perforation_holes'):.4f} | {m(r,'perforation_sec'):.6f} |")
    lines+=['']
(H/'MEASUREMENTS.md').write_text('\n'.join(lines)+'\n')
# Direct differences among the measured 32-sample candidates; avoid attributing all gain to stratification.
R=Path('/home/sato/ahc074/runs');cc=json.loads((R/c['run']/'metrics.json').read_text())['cases'];pairwise=[]
for r in full[1:-1]:
    ref=json.loads((R/r['run']/'metrics.json').read_text())['cases']
    z=[100*math.log(cc[s]['score']/ref[s]['score'])for s in cc]
    pairwise.append(dict(base=r['run'],candidate=c['run'],n=len(z),mean=statistics.mean(z),se=statistics.stdev(z)/math.sqrt(len(z))))
(H/'pairwise32.json').write_text(json.dumps(pairwise,indent=2)+'\n')
base_source=(H.parent/'argon-des-perf-gaincache/main.cpp').read_text();source=(H.parent/'argon-des-perf-strata32/main.cpp').read_text()
changes=list(difflib.unified_diff(base_source.splitlines(),source.splitlines()))
add=sum(s.startswith('+')and not s.startswith('+++')for s in changes);remove=sum(s.startswith('-')and not s.startswith('---')for s in changes)
ratio=-c['score']['mean']/(c['judge']['mean']-b['judge']['mean'])
scoretable='\n'.join(f"| {r['run'].split('_',1)[1]} | {diff(r)} | {wtl(r)} | {m(r,'perforation_holes'):.3f} |"for r in grid[1:])
finaltable='\n'.join(f"| {r['run'].split('_',1)[1]} | {diff(r)} | {wtl(r)} | {r['judge']['mean']:.6f} / {r['judge']['p99']:.6f} |"for r in full[1:])
report=f'''# D2 続き: PR #139 の動作点と色標本の分散

**マージ対象: `solutions/argon-des-perf-strata32`。**
通常2000件で **{diff(c)}%**、勝/分/敗 **{wtl(c)}**。
judge平均 **{b['judge']['mean']:.6f}→{c['judge']['mean']:.6f}秒**、p99 **{c['judge']['p99']:.6f}秒**。
採用条件を満たしたので、この版で停止し、マージを待つ。D2自体は継続中。
採用版だけの説明は[REPORT](../argon-des-perf-strata32/REPORT.md)。
全比較のrun-id、差、勝分敗、req_sec、設計終了、judge平均/p99/最大/超過数は
[MEASUREMENTS.md](MEASUREMENTS.md) に保存した。

## 助言と現行コード

助言01-1「穿孔処理とフィラー評価の対象拡大」を引き続き検証した。
基準は `solutions/argon-des-perf-gaincache`（PR #139、db7752ca）。
保存設計は `20261106-015850_argon-des-perf-gaincache`。
前回までのowner条件付けと差分キャッシュは[前回報告](../argon-des-perf-variance/REPORT.md)。

`Handle perforation` の `Perforation::total_profit` はowner側の変更窓の色を両側評価し、
他目標へのdonor利益は8個の色標本で評価する。`rebuild`のhead選択は最初の1回だけ。
headだけを穿孔する、という助言の指摘は現行でも正しい。
補正後の係数0.7で穴が3.5→7.6に増えたため、係数・標本・donor補正・非head候補を一緒に再検証した。

`Design::covered_gain` / `filler_climb` と `ProbabilityHead` / `rematch_probability` は解析的期待値を使う。
少数の乱数標本の最大値を選ぶ偏りはないが、穿孔前の紙・色需要で最適化するずれは残る。
これは後述の保存設計の分析と、確率更新を分離した比較で調べた。

## 係数と色標本

全て通常比較。先頭500件の共通接頭辞は `20261106-021800_`、基準は `argon-des-perf-gaincache`。
候補順、受理係数以外の費用、owner条件付け、利益上限、差分キャッシュは維持した。

| 候補 | 差 ± SE (%) | 勝/分/敗 | 平均穴数 |
|---|---:|---:|---:|
{scoretable}

w65/w75は係数0.65/0.75、s32c70/s32c75は独立32標本と係数0.7/0.75。
strata70は層別8標本、strata32は層別32標本で、両方とも係数0.7。
層別化は各目標・列で一様分布を等分して1個ずつ抽出し、列ごとに独立に並べ替える。
各標本の列ごとの色確率と独立性は保つが、標本全体の黒個数の偏りは小さくなる。
非線形DP全体の分散が必ず減るという数学的保証ではない。

改善方向の32標本3案を同じrun-idで2000件へ延長した。

| 候補 | 差 ± SE (%) | 勝/分/敗 | judge平均 / p99 (秒) |
|---|---:|---:|---:|
{finaltable}

32標本への増加は3案とも改善した。層別32標本を、観測した利得と時間当たりの効率から採用する。
ただし層別化だけが独立32標本を上回るとは確定していない。
独立32・係数0.7に対する層別32の差は {pairwise[0]['mean']:+.6f} ± {pairwise[0]['se']:.6f}%、
係数0.75に対しては {pairwise[1]['mean']:+.6f} ± {pairwise[1]['se']:.6f}%。
採用する変更全体と基準の差が採用基準を満たす、という判断である。

採用版の穴は {m(b,'perforation_holes'):.3f}→{m(c,'perforation_holes'):.3f}。
先頭500件の操作再生では499件の紙が変わり、905穴を新設し1593穴を復元した。
変更紙自身の17081注文で−1419手、他の494919注文で+922手、合計−497手。
単にdonor利益を増やす方向ではなく、回収しにくい穴を減らしてowner費用を抑える効果が見える。
ラベル差はrepair −786、fret −1100、fix +1134など。
`strata32-effects500.json` に全件とラベル集計を保存した。
前段のgobj・model_cost・列/穴/汎用費用・proxyは変更しない。

## donor側の条件付けを目標の穴へ広げる

前回は、目標紙がdonor列の窓を覆う場合だけ、安価な1列再計算を行った。
今回は変更窓（donorhole）とdonor列の窓（donorcolumn）を別々に条件付けした。
窓が目標の穴なら他のdonor区間も変わるので、変更前後の全DPを色反転して解く。
受理式と利益上限に補正量を足し、元の標本キャッシュとの整合は維持した。

接頭辞 `20261106-022157_`、500件。

- donorhole: **{diff(donor[1])}%**、{wtl(donor[1])}。
  毎ケース24204.1標本で全DPの条件付けが働いた。
  穿孔 {m(donor[0],'perforation_sec')*1000:.3f}→{m(donor[1],'perforation_sec')*1000:.3f} ms、
  judge平均 {donor[0]['judge']['mean']:.6f}→{donor[1]['judge']['mean']:.6f}秒。
- donorcolumn: **{diff(donor[2])}%**、{wtl(donor[2])}。
  24186.4標本中16429.9標本が穴に触れる全DP評価。
  穿孔 {m(donor[2],'perforation_sec')*1000:.3f} ms、judge平均 {donor[2]['judge']['mean']:.6f}秒。

発火不足ではない。donorholeは7.480→7.042穴となり、ownerで−81手、他目標で+539手、合計+458手。
ownerの費用減少を上回るdonor利益を失っている。
受理候補の補正量の平均は+0.0000175手/注文と小さく、条件付けが一方向の大きな偏りを消す状況でもない。

具体例はseed383の紙107の2穴復元。ownerで−9手だが他目標で+58手、総計+49手。
この紙のfillは28→19、repairは15→5回になった。
`observe.py queries/state`でも確認した（`donor-case383.log`）。
最初の相違は注文7の紙110の返却深さ114→110で、注文8は9→7手に減るが、1024注文では悪化する。
一部の短い区間の改善だけを成功と数えず、全体の利用減少と費用を見た。

現状は時間を増やしても得点が改善しないため採用しない。
色1次元の補正だけで残る分散全体が消えるとはいえず、32標本採用後の必要性は再判断する。

## 大標本の測定

基準 `20261106-023231_argon-des-perf-gaincache`、候補は
`20261106-023813_argon-des-perf-dense70` / `argon-des-perf-dense80`。
512標本、係数0.7/0.8、500件。時間超過の測定版なので **--no-record**、設計は保存した。

- 係数0.7: {diff(dense[1])}%、{wtl(dense[1])}、{m(dense[1],'perforation_holes'):.3f}穴。
  judge平均 {dense[1]['judge']['mean']:.6f}、p99 {dense[1]['judge']['p99']:.6f}、
  最大 {dense[1]['judge']['max']:.6f}秒、2秒超え {dense[1]['judge']['over2']}/500。
- 係数0.8: {diff(dense[2])}%、{wtl(dense[2])}、{m(dense[2],'perforation_holes'):.3f}穴。
  judge平均 {dense[2]['judge']['mean']:.6f}、p99 {dense[2]['judge']['p99']:.6f}、
  最大 {dense[2]['judge']['max']:.6f}秒、2秒超え {dense[2]['judge']['over2']}/500。

穿孔時間はそれぞれ659/726 ms。予測変化は−0.00738/−0.01117手/注文だが、これは各候補の
穿孔前に対する変化であり、既に穿孔した基準に対する得点差とは直接比較しない。
512標本へ増やすだけでは、実得点の大きな改善を確認できなかった。
列間の独立性・固定head・返却費用などのモデル誤差は別に残り得る。
この測定の基準もjudge平均1.680秒と遅く、測定版が混ざる比較の絶対時間を採用版の時間判定に流用しない。
単純な標本増加の伸びが大きいとは見えないが、500件の不確かさがあるため、
厳密な上界や「残る可能性が0.01%未満」とは主張しない。

## 非head紙の再確認

基準の保存設計200件・204800注文を `exposure.py` で再生した（`exposure-new200.json`）。
列・色内の順位は穿孔前の担当目標数とフィラー効用で固定し、穿孔紙が全て順位0なのも照合した。
fillはhead 75830、第2紙3297、第3紙581。
列先頭はhead 4920758、第2紙150817、第3紙20695。
同色最上位はhead 9344146、第2紙591550、第3紙51358。
第2紙の同色先頭露出は約6%。前回の約6%から大きく変わらない。
前回とはrequest側の採用変更もあるため、頻度の差全てを穴数だけに帰属させない。

基準 `20261106-022926_argon-des-perf-gaincache`、候補は
`20261106-023813_argon-des-perf-nonhead70` / `argon-des-perf-nonhead70wide`。
基準のhead穿孔を終えてから、同色第2紙の露出率1/16・1/8で追加穿孔した。
新係数0.7、owner条件付け、上限、差分キャッシュを保持した。

- 露出率1/16: **{diff(nonhead[1])}%**、{wtl(nonhead[1])}、追加1.526穴/ケース。
- 露出率1/8: **{diff(nonhead[2])}%**、{wtl(nonhead[2])}、追加1.608穴/ケース。

1/16版の予測は穴費用+0.001681、補正利益+0.002793手/注文で、係数込み−0.000275手/注文。
実際は763穴を追加し、変更紙自身の4395注文で+831手、他の507605注文で−173手、合計+658手。
非headを使う機会はあるが、ownerの追加費用の回収が足りない。
補正後でも同色紙IDの少数標本、他窓の色、モデルの返却費用などは残るため、
この比較だけで全ての非head穿孔が不可能とはしない。採用32標本の下での再確認は残る。

## 穿孔前後の目的のずれ

`proxy_drift.py` は同じ200設計について、穿孔前の紙をペアと列から復元した。
`filler_gain`と同じく対象自身の列を除き、全256目標と解析的な色確率でproxyを評価した。
前後とも同じ規則でheadを選ぶ。これは実注文列を使った設計選択ではない。
結果は `proxy-drift200.json`。

| 指標 | 平均 |
|---|---:|
| head黒確率の絶対差（列平均） | {d['prob_mean']['mean']:.6f} |
| 同じ差の列最大値 | {d['prob_max']['mean']:.6f} |
| 需要色の多数派反転 | {d['majority_flips']['mean']:.3f}列/ケース |
| proxyからheadを選び直すと変わる紙 | {d['head_changes']['mean']:.3f}/ケース |
| 穿孔前proxy | {d['proxy_before']['mean']:.6f}手/注文 |
| 穿孔後の紙・旧確率 | {d['proxy_after_fixedprob']['mean']:.6f} |
| 穿孔後の紙・新確率 | {d['proxy_after']['mean']:.6f} |
| さらにhead再選択 | {d['proxy_after_rerank']['mean']:.6f} |

平均の確率差は小さいが、最大の単列差は0.350694。実際の列頭色頻度に対する二乗誤差は
0.012086→0.011714となった。head再選択だけのproxy増加は約0.000429手/注文で小さい。
proxyはdonor間の競合を無視するため、この値を実得点の上界とは扱わない。

基準 `20261106-023600_argon-des-perf-gaincache`、候補は
`20261106-023813_argon-des-perf-pass2` / `argon-des-perf-reprob2`。
単純な2周目と、色需要・標本・効用・DPを再構築した2周目を分離した。
headの紙IDは固定、500件。

- 追加1周: {diff(refresh[1])}%、{wtl(refresh[1])}、1.326回受理、穴差+0.302。
- 色確率更新付き: {diff(refresh[2])}%、{wtl(refresh[2])}、1.956回受理、穴差−0.184。

確率更新は発火している（絶対差和0.0994/ケース）が、最初の比較では改善しない。
前段の目的そのものを穿孔可能性に合わせて最適化した結果ではないので、
この結果をもって前段への組み込みまで否定しない。新しい採用版の後に残る検討とする。

## 最終比較、採用条件、引き継ぎ

最終比較は `{b['run']}` / `{c['run']}`。
500件から2000件へ延長し、両側2000設計を保存した。開始・延長前と最終確認時にBASE.mdを再読し、
基準がPR #139のままであることを確認した。

- 得点差 {diff(c)}%、{-c['score']['mean']/c['score']['se']:.2f} SE。実用閾値も超える。
- req_sec {m(b,'req_sec'):.6f}→{m(c,'req_sec'):.6f}、helper_end_sec {m(b,'helper_end_sec'):.6f}→{m(c,'helper_end_sec'):.6f}、
  end_sec {m(b,'end_sec'):.6f}→{m(c,'end_sec'):.6f}秒。
- judge平均 {b['judge']['mean']:.6f}→{c['judge']['mean']:.6f}、p99 {b['judge']['p99']:.6f}→{c['judge']['p99']:.6f}、
  最大 {b['judge']['max']:.6f}→{c['judge']['max']:.6f}秒、2秒超えは両側0。
- 追加judge平均 {(c['judge']['mean']-b['judge']['mean'])*1000:.3f} ms、改善効率 **{ratio:.3f}%/秒**。0.6%/秒を上回る。
- 穿孔時間 {m(b,'perforation_sec')*1000:.3f}→{m(c,'perforation_sec')*1000:.3f} ms。
- 外部負荷は先頭500件が平均0.24/最大1.10コア、追加1500件が平均0.13/最大0.45コア。警告なし。
- WA・self_wrong・op_label_errorsは全2000件で0。GCC/Clang、LOCAL_BENCH有無の4構成で警告0。
- 変更は `Perforation::kSamples` と `rebuild` の標本生成、+{add}/−{remove}行。
  全ログ・profiler・switch・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持。
  実行ファイルは/tmpで作り、削除済み。保存ソースとの一致を `final-audit.json` で照合した。

**この版を採用対象として停止する。**
D2を完了にはしない。再開後はBASE.mdを読み直し、層別16/64などの時間効率、
32標本での係数近傍・非head候補、色確率更新と前段の目的のずれを診断に沿って続ける。
今回の負けた案をそのまま全件に広げるのではなく、owner費用回収不足や候補選択の誤差を分離する。
D1は既報どおり閉じたまま。D3（長列MDP）、D4（汎用層価値）、D5（rollout）は未開始。
既存解法・共有スクリプト・trial_log.mdは変更せず、コミットしていない。
'''
(H/'REPORT.md').write_text(report)
short=f'''# D2 採用候補: 層別32標本による穿孔

改良元は `solutions/argon-des-perf-gaincache`（PR #139）。
外部助言01-1「穿孔処理とフィラー評価の対象拡大」の継続検証から得た変更。
詳細な比較・失敗案・診断は [調査REPORT](../argon-des-perf-neighborhood/REPORT.md)、
全runの時間は [MEASUREMENTS](../argon-des-perf-neighborhood/MEASUREMENTS.md)。

`Handle perforation` の `Perforation::rebuild` が使う8個の独立色標本を、32個の層別標本へ変更する。
各目標・列で等分した区間から抽出して独立に並べ替える。受理係数0.7、owner条件付け、利益上限、
不変なDPキャッシュの再利用は維持する。色標本の選択誤差を抑え、回収しにくい穴が減る。
変更は+{add}/−{remove}行。他の段、段の目印と目次、全ログ・profiler・switchは不変。

基準 `{b['run']}`、候補 `{c['run']}`。
通常2000件、両側設計保存、記録あり。

- **{diff(c)}%**、勝/分/敗 **{wtl(c)}**、{-c['score']['mean']/c['score']['se']:.2f} SE。
- judge平均 **{b['judge']['mean']:.6f}→{c['judge']['mean']:.6f}秒**、p99 **{b['judge']['p99']:.6f}→{c['judge']['p99']:.6f}秒**。
- judge最大 {b['judge']['max']:.6f}→{c['judge']['max']:.6f}秒、2秒超え0→0。
- req_sec {m(b,'req_sec'):.6f}→{m(c,'req_sec'):.6f}、helper_end_sec {m(b,'helper_end_sec'):.6f}→{m(c,'helper_end_sec'):.6f}秒。
- 追加時間当たり **{ratio:.3f}%/秒**、平均穴数 {m(b,'perforation_holes'):.3f}→{m(c,'perforation_holes'):.3f}。
- WA・self_wrong・op_label_errors全件0。GCC/Clang × LOCAL_BENCH有無で警告0。
- 外部負荷に警告なし。`build-results.json` / `final-audit.json` でソースと検証物を照合。
  ビルド用バイナリは/tmpに作り、削除した。

採用条件を満たしたため、この版で停止してマージを待つ。
層別化だけの効果と独立32標本との差は有意ではないため、改善全体を層別化だけに帰属させない。
D2は未完了で、より安い標本数や新しい動作点での残る候補は再開後に扱う。D3〜D5は未開始。
'''
(H.parent/'argon-des-perf-strata32/REPORT.md').write_text(short)
print('reports written', 'changed lines',add,remove,'gain per judge second',ratio)
print('32 sample pairwise',pairwise)
