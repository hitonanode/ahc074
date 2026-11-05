from pathlib import Path
import json,re,hashlib
p=Path('solutions/argon-req-completefast-v3');base='20261106-022300_argon-des-perf-gaincache';cand='20261106-022300_argon-req-completefast-v3'
config=Path('/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/argon/BASE.md').read_text()
assert re.search(r'Current base \(SOTA\): `solutions/([^`]+)`',config).group(1)=='argon-des-perf-gaincache'
fx=json.loads(p.joinpath('fixed-results.json').read_text())['20261106-021624_argon-req-completefast-v3']
nr=json.loads(p.joinpath('normal-results.json').read_text())[cand]
assert fx['score_log_pct']<=-.005 and -fx['score_log_pct']>=2*fx['se_pct']
assert nr['score_log_pct']<=0 and nr['judge']['mean']<=1.600 and nr['judge']['p99']<=1.770
assert fx['WA']==nr['WA']==0
assert all(r['means'][k]==0 for r in [fx,nr] for k in ['self_wrong','op_label_errors'])
req_delta=nr['means']['req_sec']-nr['baseline_means']['req_sec'];rate=-fx['score_log_pct']/(1.35*req_delta)
if nr['judge_mean_delta']>.01:assert rate>.6
assert p.joinpath('builds.log').read_text().endswith('All four builds passed with no warnings.\n')
assert '2000 passed' in p.joinpath('validation.log').read_text()
assert 'byte-identical current source' in p.joinpath('validation.log').read_text()
source=p.joinpath('main.cpp').read_bytes();sha=hashlib.sha256(source).hexdigest()
w=lambda r:'/'.join(map(str,r['wtl']))
text=f'''# R2: ハンドル修正後の積層価値による共同DP

**採用対象は `solutions/argon-req-completefast-v3`。改良元は `solutions/argon-des-perf-gaincache`（PR #139）。全採用条件を満たしたため、順次マージの指示に従ってここで停止する。コミットはしていない。**

## 指摘と変更

助言02-③の「整数のフィラー利得では、将来の積層価値が良い候補を落とす」という指摘を継続検証した。前回採用のPR #137では新規フィラーの抽出直後の価値を使う計画を加えたが、掘り出しを省くことが、ハンドル修正後の列の並びも変える点が残っていた。

`Request plans: options, fillers and the joint interval DP` の `run_joint` に、候補1枚を置いて残りのハンドルを直す局所計画と、全ハンドルを直す局所計画の `plan_cost` 差で区間を重み付けする計画を追加した。従来の正の整数利得の閾値・全既存計画を残す。目的関数、設計、探索予算、乱数、将来注文を見ない性質は変更しない。仮配置の保存・復元は既存の `filler_value_increment` に統合した。

従来の価値付き計画と同じ区間を選ぶ追加計画は再実行しない。同じ開始状態・返却方法で連続して試すため、紙・位置・種類・順序が一致すれば以降の操作生成は同じ。参照となる局所修正が不可能な場合も、従来の重みを使う重複案なので省く。完成した候補は従来の可視性・表示・回収可能性の検査と `plan_cost` で比較する。

## 最新基準での比較

PR #138で一度全条件を満たした後、最終報告時にBASE.mdがPR #139へ更新された。旧版は履歴として残し、同じ要求処理の差分を最新mainのソースへ移植して以下を再評価した。最終固定比較の前、通常比較の前、報告時にBASE.mdを確認した。

保存設計は `20261106-015850_argon-des-perf-gaincache`。固定runは `20261106-021624_argon-des-perf-gaincache` / `20261106-021624_argon-req-completefast-v3`。200 × 2では −0.014353 ± 0.002984%、134/0/66、req_sec 0.443165→0.454153秒。そのrunを `--extend` で2000 × 2へ拡張した。通常runは `{base}` / `{cand}`、2000 seeds、`--save-design`。通常runはpahcerへ記録済み、両腕2000設計を保存した。

| 比較 | 平均log比 ± SE (%) | 勝/分/敗 | req_sec 基準→候補 | 比 |
|---|---:|---:|---:|---:|
| 固定2000 × 2 | **{fx['score_log_pct']:.6f} ± {fx['se_pct']:.6f}** | **{w(fx)}** | {fx['baseline_means']['req_sec']:.8f}→{fx['means']['req_sec']:.8f} | {fx['req_ratio']:.6f} |
| 通常2000 | **{nr['score_log_pct']:.6f} ± {nr['se_pct']:.6f}** | **{w(nr)}** | {nr['baseline_means']['req_sec']:.8f}→{nr['means']['req_sec']:.8f} | {nr['req_ratio']:.6f} |

通常比較のジャッジモデル（BASE.mdの式。提供されたjudge_model.pyでも照合）:

| 指標 | 基準 | 候補 |
|---|---:|---:|
| 平均 | {nr['baseline_judge']['mean']:.8f} | **{nr['judge']['mean']:.8f}** |
| p99 | {nr['baseline_judge']['p99']:.8f} | **{nr['judge']['p99']:.8f}** |
| 最大 | {nr['baseline_judge']['max']:.8f} | **{nr['judge']['max']:.8f}** |
| 2秒超え | {nr['baseline_judge']['over2']} | **{nr['judge']['over2']}** |

固定比較の利得を、通常比較のreq増分だけを1.35倍した費用で割ると **{rate:.3f}%/秒**。設計部の時間差を改善効率の根拠にしていない。実用閾値0.005%、2SE、モデル平均1.600秒・p99 1.770秒、費用あたり0.6%/秒の条件を満たす。

## 正当性と保守性

- 固定4000ケース・通常2000ケースでWA / self_wrong / op_label_errorsはすべて0。
- 通常2000件の設計のstdout部分と全 `@paper` が基準と一致。候補の通常2000 stdoutは固定比較の注文列0とバイト一致。
- 既存stderr指標名・順序を全件確認。ユーザー指定の常時0だった `value_filler_zero` / `value_filler_zero_useful` だけを削除。その他のログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、`@paper` / `@ops`、段の目印・目次は維持。
- 最終main.cppは固定・通常runの保存ソースとバイト一致。SHA256: `{sha}`。
- GCC / Clang、LOCAL_BENCH有無の4構成を `-std=c++23 -O2 -Wall -Wextra` でビルドし、すべて警告0。
- **9056→9090行、45追加・11削除**。差分の段は区間DP、Request processing、main: statisticsだけで、設計部は現行基準と一致。

詳細な数値と検証記録は同ディレクトリのfixed-results.json、normal-results.json、judge-model.log、validation.log、builds.logに残した。

## 再開時に残る方向

R2全体の終了ではない。旧紙の重みをハンドル修正後の局所価値へ広げる余地と、異なる紙集合のDP第2解・編集済み計画への追加ejectの残余効果が残る。後二者はPR #138上ではそれぞれ−0.012110 ± 0.001227%、−0.006154 ± 0.000480%だったが、今回の採用候補との併用は未検証なので含めない。R3・R4・R5はまだ未着手。新BASE.mdへの更新後に続ける。

## 以下はPR #139への移植前の研究履歴

旧基準での採用判断・旧ディレクトリ名は当時の結果であり、現在のマージ対象は上記v3だけである。

'''
history=Path('solutions/argon-req-oldvalue/REPORT.md').read_text()
p.joinpath('REPORT.md').write_text(text+history)
print('Final Japanese report written; all adoption assertions passed. Rate:',rate,flush=True)
