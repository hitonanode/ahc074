"""Write the Japanese report from the verified artifacts."""
from pathlib import Path
import json
import re

p = Path(__file__).resolve().parent
assert 'All adoption criteria passed on the current base.' in (p/'final-validation.log').read_text()
ad = json.loads((p/'adoption.json').read_text())
f, n = ad['fixed'], ad['normal']
fd = json.loads((p/'fixed-details.json').read_text())
nd = json.loads((p/'normal-details.json').read_text())
s = json.loads((p/'screen-results.json').read_text())[fd['runs'][1]]
m = ad['local_gain']
dt = nd['paired_times']['judge']
trace = re.search(r'run-id: (\S+)', (p/'trace.log').read_text())[1]
loads = '、'.join(f"{label}の平均{x['mean_cores']:.3f}・最大{x['max_cores']:.3f}コア" for label,values in ad['outside_load'].items() for x in values)
def wtl(v): return '/'.join(map(str, v['wtl']))
score_rows = '\n'.join(f"| {label} | {v['score_log_pct']:.6f} ± {v['se_pct']:.6f} | {wtl(v)} | {v['baseline_means']['req_sec']:.6f} → {v['means']['req_sec']:.6f} | {v['req_ratio']:.6f} |" for label,v in [('固定200×2',s),('固定2000×2',f),('通常2000',n)])
time_rows = '\n'.join(f"| {label} | {n['baseline_judge'][key]:.6f} | {n['judge'][key]:.6f} |" for label,key in [('平均','mean'),('p99','p99'),('最大','max')])
stage_rows = '\n'.join(f"| {key} | {n['baseline_means'][key]:.6f} | {n['means'][key]:.6f} |" for key in ['map_end_sec','helper_end_sec','req_sec','end_sec'])
report = f'''# R2: 編集済み価値付きDP計画への追加ejectを新基準で再検証

**採用候補は `solutions/argon-req-ejectstats-v2`。PR #143の`argon-req-filterblocks-v2`が基準。固定2000×2と通常2000件で利得・時間単価・予算の条件を満たしたため、指示どおりマージ待ちで停止する。コミットはしていない。**

## 指摘と、現在のコードに残っている問題

助言02-③の「整数のフィラー利得だけでは将来価値の良い候補を落とす」を継続した研究。価値付き共同DPはPR #137、ハンドル修正後の完成計画で重みを測るDPはPR #140で既にある。現在の問題は候補の生成後にある。初期評価で僅かに負けた価値付きDP計画は、`Request processing (process)`内で通常の編集を受けても、勝者でなければejectを受けないことがある。その編集済み経路・状態は`plan_cache`に残る。

旧版`argon-req-ejectstats`はPR #140で通常−0.006965±0.000668%、judge平均+9.496 msだったが、先に採用された設計改善が時間枠を使い、未採用になった。今回の固定設計はPR #141の穴あけ変更を含むため、以前のスコア差を流用せず測り直した。PR #142・#143の完全一致高速化で共有予算は+33 msになっている。

## 変更

旧ejectstatsの5か所の差分を、文脈が一意に完全一致することを確認してPR #143へ移植した（`port.txt`、`change.diff`）。9146 → 9200行、54行追加・削除なし。変更する節は`Request processing (process)`と`main: statistics`だけ。目次と節名は変えない。

- 抽出直後の積層価値で重み付けする共同DPの元計画を1件記録する。
- 通常の探索終了後、既存`plan_cache`から編集済み結果を探す。未eject、現勝者と別積層、完成評価値の差0.5以内の場合だけ対象にする。
- `finish_weighted_plan`から既存の`polish_ejects`を呼び、最大4ラウンドのejectを行う。表示・到達可能性を確認し、変更しない`plan_cost`を厳密に改善したときだけ採用する。失敗時は元の勝者の状態を復元する。
- DPや候補編集の再実行、中立探索の追加はしない。追加処理は専用の非インライン関数へ分け、新しい5統計は静的に保持し、Solverのサイズ・既存メンバ配置を保つ。

設計、目的関数、既存探索予算、乱数は変更しない。将来の注文は参照しない。新しい環境変数はない。候補キャッシュを無効にする既存設定では追加処理も無効になる。既存のログ・スイッチ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@opsを残す。

## 同時比較

差はseedごとの平均logスコア比、単位%。固定設計では各seedの2注文列を先に平均し、seed間のSEを求めた。負が改善。時間は同じ比較の両腕で測った。

| 比較 | 差 ± SE (%) | 勝/分/敗 | req_sec 基準→候補 (s) | 比 |
|---|---:|---:|---:|---:|
{score_rows}

- 保存設計: `20261106-045419_argon-req-filterblocks-v2`。
- 固定比較: `{fd['runs'][0]}` / `{fd['runs'][1]}`。200×2から`--extend`で2000×2へ拡張。固定runは仕様どおりpahcerには未登録。
- 通常比較: `{nd['runs'][0]}` / `{nd['runs'][1]}`。2000件、`--save-design`、pahcerに記録済み。両腕の2000設計を保存した。次回は候補runを`--design-from`に使える。

通常比較のjudgeモデルは `end_sec + 0.04*helper_end_sec + 0.35*req_sec`。

| judgeモデル (s) | 基準 | 候補 |
|---|---:|---:|
{time_rows}
| 2秒超え件数 | {n['baseline_judge']['over2']} | {n['judge']['over2']} |

| 通常比較の累積・要求時間 (s) | 基準 | 候補 |
|---|---:|---:|
{stage_rows}

judge平均増分は **{1000*dt['mean']:.3f} ± {1000*dt['se']:.3f} ms**（対応するseed差の平均±SE）。固定比較の利得を通常比較の全体時間増分で割った効率は **{ad['efficiency_pct_per_judge_sec']:.3f}%/judge秒**。0.6%/秒を超え、共有予算33 ms以内、p99増分{1000*n['judge_p99_delta']:.3f} msも「平均増分+10 ms以内」。要求時間だけで割らず、無変更の設計部を含めた全体増分で判断した。設計annealを削る取引はしていない。

固定比較の絶対時間には保存元の設計時間が入るため、judge時間の採否には通常比較だけを使った。外部負荷は{loads}。いずれも警告基準未満。

## 新しい設計での発火数、予測と実現

固定4000ケースの1ケース平均:

| 指標 | 値 |
|---|---:|
| 追加eject数 | {m['value_seed_trials']:.4f} |
| 合法・表示正しい結果 | {m['value_seed_valid']:.4f} |
| 採用数 | {m['value_seed_accepts']:.4f} |
| 採用時の完成評価値改善の合計 | {m['value_seed_gain']:.6f} |
| 採用時の即時手数差の合計 | {m['value_seed_saved']:.6f} |
| 後続要求込みの総手数差 | {m['realized_saved_moves']:.6f} |

実現総手数差は完成評価値の予測の約{100*m['predicted_realized_ratio']:.1f}%。即時の手数差だけより、積層の将来価値を含む完成値の方が実現値に近いかをこの表で確認できる。これはケース平均の比較であり、各採用の独立な因果効果とは扱わない。`observe.py cases/queries/state/stats --vs`と保存出力の再生による改善・悪化区間は`episodes.log`に残した。

- seed972、注文552は両方10手だが、helperを使う計画からフィラーを再配置する計画へ変わる。次の注文553は14→10手。積層が再合流する注文589までの区間は10手改善した。
- seed1081、注文940は11→9手へ短縮するが、次の注文941は8→11手。再合流する注文998までの区間は9手悪化した。即時短縮だけでは将来の差を保証できず、現行値関数にも個別の誤差が残る。

区間内には後続の別判断も含まれるため、区間の全差を先頭の追加ejectだけの効果とは数えない。今回の追加処理は同じ目的関数を使い、値関数自体の変更はしていない。

旧基準での拡張・切り分けは `../argon-req-ejectstats/REPORT.md` にある。両方の価値付きDPへ広げる追加利得は約0.000635%で時間に見合わず、値差0.25への絞り込みは利得を約半分失った。今回は移植と再測定に絞り、この履歴を新基準での新しい結果とは数えない。

## 正当性と保存した分析機能

- 固定4000ケースと通常2000ケースで、WA / self_wrong / op_label_errors / plan_failures / unsafe_plansは全件0。
- 設計stdout192行・全@paperが各比較の両腕で一致。通常と固定注文列0のstdoutも、両腕それぞれ2000件すべて一致。
- 既存の全数値指標の名前と出力順序を全ケースで確認。探索が増えるため要求側カウンタの値は変わる。追加value_seed_*はプロセス単位で、SIM_HARNESS等のSolverコピーを動かせばそれらも合算する。既存カウンタの集計範囲は変更しない。
- heavy trace/predict単独8件: `{trace}`。既定設定とstdout一致、全#heavyの最終経路・ラベルをstdout/@opsと照合。`trace-validation.log`参照。
- GCC/Clang、LOCAL_BENCHあり・なしの4構成を`-std=c++23 -O2 -Wall -Wextra`でビルドし、警告0。
- 最終main.cppと固定・通常の保存ソースがバイト一致。SHA256: `{fd['source_sha256']}`。
- 開始時、最終比較前、採否集計時にBASE.mdを再読し、PR #143が基準であることを確認。各分析はwhenidle.shと共通ロック経由、1コアで行った。解法・テスターを直接実行していない。

## 残件

採用条件を満たすたびに停止する指示に従う。R2は未完了であり、completeold-full、第2DP解の候補押し出し、seededit-wideを新BASEから続ける。R3の途中repair、R4の旧フィラー付きhelper、R5の難しい要求への予算配分も未完了。この移植だけを根拠に閉じない。

## 再現コマンド

```sh
scripts/pahcer_run.py --compare solutions/argon-req-filterblocks-v2 solutions/argon-req-ejectstats-v2 --design-from 20261106-045419_argon-req-filterblocks-v2 --seeds 0-200 --orders 2 -c "R2 追加ejectの固定設計比較"
scripts/pahcer_run.py --extend {fd['runs'][0]} {fd['runs'][1]} -c "固定設計2000×2への拡張"
scripts/pahcer_run.py --compare solutions/argon-req-filterblocks-v2 solutions/argon-req-ejectstats-v2 --save-design -c "R2 追加ejectの通常2000最終確認"
```

新しく再測定する場合、拡張コマンドのrun-idはその最初の200件比較で作られたものへ置き換える。
'''
(p/'REPORT.md').write_text(report)
print('Japanese REPORT.md written from final verified results.')
