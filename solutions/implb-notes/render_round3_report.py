from pathlib import Path
import json
p=Path('solutions/implb-notes')
c500=json.loads((p/'round3-cover-500.json').read_text())
c2000=json.loads((p/'round3-cover-2000.json').read_text())
r500=json.loads((p/'round3-ramp-500.json').read_text())
root='/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629'
rows=[]
for data,names,label in [(c500,['d30b-cover040','d30b-cover045','d30b-cover050'],'500×4'),(c2000,['d30b-cover050'],'2000×4'),(r500,['d30b-ramp-a','d30b-ramp-b'],'500')]:
 for name in names:
  run=next(k for k in data['comparisons'] if k.endswith('_'+name));x=data['comparisons'][run]
  rows.append((name,label,run,x))
def stat(s,n=4):return f"{s['mean']:+.{n}f} ± {s['se']:.{n}f}"
s='''Bからの追加採用候補はありません。**今回の3項目は取り込まない判定**です。最後の評価開始は13:49、全評価・検査は完了しました。

±は1SE、得点は候補／基準の平均log比（%、負が改善）。固定設計の4注文列はseed内で平均してからSEを計算しました。

**Item 1 — cover-credit：below the floor、時間条件未達**

`solutions/d30b-cover040`、`solutions/d30b-cover045`、`solutions/d30b-cover050`をreset6から作成。kCoverStrengthだけを0.40／0.45／0.50に変更し、kStayStrength=0.25を維持しました。

基準runは`20261109-132432_d30a-reset6`。候補runは`20261109-132432_d30b-cover040`、`20261109-132432_d30b-cover045`、`20261109-132432_d30b-cover050`です。保存設計`20261109-130035_d30a-reset6`を使用しました。

|候補|seed×注文列|得点% ± SE|勝/分/敗|
|---|---:|---:|---:|
'''
for name,label,run,x in rows[:4]:s+=f"|{name}|{label}|{stat(x['score'],6)}|{'/'.join(map(str,x['wtl']))}|\n"
s+='''
500 seedで平均が最良の0.50を2000 seedへ延長しました。得点は2SE以上改善しましたが、注文時間は**+16.468 ± 0.384 ms**。時間課金後は**−0.004730 ± 0.001686%**で、「追加時間がノイズを超えない」という成功条件を満たしません。

定数だけの変更でも探索量は増えました。2000 seedでf2再生ステップ+5.21%、rewrite試行+8.37%、partial MDP misses+5.54%。提案時の「時間費用0」という前提は成立しませんでした。Clangの本評価は行っていません。

**Item 2 — reset-ramp-by-segment：no gain（改善未確認）**

`solutions/d30b-ramp-a`は{2,4,6,6}、`solutions/d30b-ramp-b`は{6,6,10,10}。焼きなましには絶対区間番号を渡し、仕上げは両方6に保ちました。

通常500 seed比較の基準runは`20261109-134929_d30a-reset6`、候補は`20261109-134929_d30b-ramp-a`と`20261109-134929_d30b-ramp-b`です。

|候補|得点% ± SE|勝/分/敗|Δdv_best ± SE|
|---|---:|---:|---:|
'''
for name,label,run,x in rows[4:]:s+=f"|{name}|{stat(x['score'],6)}|{'/'.join(map(str,x['wtl']))}|{stat(x['paired_metrics']['dv_best'],6)}|\n"
s+='''
Vの改善はAが約1.10SE、Bが約0.06SEで、どちらも延長条件の2SEに届きません。得点も有意な改善がなく、2000 seedへ延長しませんでした。この2通りの区間別係数では、一定6を上回る根拠は得られませんでした。

**Item 3 — stack3：not started（実施条件未達）**

Item 1・2の両方成功という条件を満たさず、`solutions/d30b-stack3`は作成していません。stackのGCC／Clang 2000 seed比較も実施していません。取り込みを推奨するディレクトリはありません。

**同じ比較内のpaired時間差**

H=helper_end_sec、R=req_sec、E=end_sec。単位ms、CLOCK_SCALE込み、候補−基準です。

|候補・評価|ΔH ± SE|ΔR ± SE|ΔE ± SE|
|---|---:|---:|---:|
'''
for name,label,run,x in rows:
 s+=f"|{name} {label}|"+'|'.join(stat(x['paired_ms'][k],3) for k in ['helper_end_sec','req_sec','end_sec'])+'|\n'
s+='''
|候補・評価|H p99 基準→候補|R p99 基準→候補|E p99 基準→候補|
|---|---:|---:|---:|
'''
for name,label,run,x in rows:
 s+=f"|{name} {label}|"+'|'.join(f"{x['arm_p99_ms'][k][0]:.1f}→{x['arm_p99_ms'][k][1]:.1f}" for k in ['helper_end_sec','req_sec','end_sec'])+'|\n'
s+='''
時間課金は得点log比に`0.0003×ΔH(ms) + 0.00055×ΔR(ms)`を加算。rampの課金後平均はA +0.007513%、B +0.035347%です。固定設計比較のH/Eは保存時刻を含むため、その絶対値を最終版の時間予測には使いません。p99は各注文列の値から算出しました。

全評価WA 0。全5候補で標準GCCと指定Clang flagsのビルドを確認し、通常20 seed smokeを通過しました（cover：group `20261109-132202`、ramp：`20261109-134756`）。coverの通常smokeでは設計が基準と全20 seed一致しました。0.50は既存のbit完全一致assertを変えず、NEXT_PREFIX_CHECKをGCC・Clangで各20 seed通過しています（`20261109-133747_d30b-cover050`／`20261109-133747_d30b-cover050-2`）。

今回の得点・時間評価はGCCです。Clangは18.1.3でビルド・参照計算の検証までであり、ジャッジのClang21での効果は未測定です。固定反復、CLOCK_SCALE、DesignStore、既存注釈・目次を維持し、時計・打切り・fallbackは追加していません。

'''
s+=f"集計は[cover 500]({root}/solutions/implb-notes/round3-cover-500.json)、[cover 2000]({root}/solutions/implb-notes/round3-cover-2000.json)、[ramp 500]({root}/solutions/implb-notes/round3-ramp-500.json)。[PROGRESS.md]({root}/solutions/implb-notes/PROGRESS.md)も更新済みです。前ラウンドの報告は[REPORT-before-round3.md]({root}/solutions/implb-notes/REPORT-before-round3.md)に保存しています。\n"
(p/'REPORT.md').write_text(s)
print(s)
