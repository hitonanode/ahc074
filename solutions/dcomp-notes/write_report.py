"""Render the reproducible Task 8 report from completed metric files."""
from pathlib import Path
import json
N=Path(__file__).resolve().parent
J=lambda f:json.loads((N/f).read_text())
F=J('final-stats.json');M=J('final-runs.json');Z=J('FROZEN.json');rid=M['final-normal'];chosen=rid[-1];fix=rid[2]
held=next(iter(J('final-heldout.json').values()))
def ps(x):return f"{x['mean']:+.5f} ± {x['se']:.5f}"
def pflat(x,k='pct_orders'):return f"{x[k]:+.5f} ± {x[k+'_se']:.5f}"
def ms(x):return f"{1000*x['mean']:+.2f} ± {1000*x['se']:.2f}"
def scorefile(name):return next(iter(J(name).values()))
def stage(file,name):return J(file)['results'][name]['stage']['helper_end_sec']['paired_delta']
def row(name,sf,nf,nr):
 r=scorefile(sf);s=r['score'];return f"| {name} | {pflat(s['fresh'])} | {pflat(s['all'])} | {pflat(s['real'])} | {ms(stage(nf,nr))} | `{nr}` / `{next(iter(J(sf)))}` |"
lines=[]
add=lines.append
add('# Task 8: 1倍の設計予算の再配分\n')
x=F['compare'][fix]['all']['pct'];ratio=F['timing'][chosen]['judge_ratio_argon']
add(f"最良の時間内候補は **solutions/dcomp-nine**。通常2000件ではlegal-tie-fix比 **{ps(x)}%**、judgeモデル平均はargon比 **{ratio:.5f}倍**。採用基準の0.03%には届かなかった。未見500件の新規7列は−0.00347±0.00250%で2SEに届かず、平均注文リスト上の改善も未確定。新しい探索方向は最初の公平な500件・8列比較で改善がなければ打ち切った。小改善と、出力同一の時間短縮を選択肢として残す。\n")
add('## 最終候補の変更\n')
add('改良元はlegal-tie-fast。注文処理、補助表、column MDP、mainの注文処理以降は元ソースと文字列単位で同一（`nine-source-check.json`）。既存の4枝＋4再仕上げを保ち、最良の完成割当から穴を引き継ぐ再仕上げを1回追加する。追加候補はfiller climbと穴あけ前rematchを省き、従来の穿孔・後段Hungarian・Vを行う。完成した9候補からVで選ぶ。初期列順DPは最後の選択設計だけに適用する。\n')
add('時間資金はfiller climbの出力同一高速化で作る。climb中の確率qは固定なので、各target/donorの現在の寄与を保存する。交換試行で古い寄与を引く際の再計算を省き、動く2 donorと最大4 targetの新しい寄与だけを計算する。元の加減算順序を保ち、受理したときだけ保存値を更新する。棄却時には前の保存値をそのまま使う。`gain_cache`は通常185×256個のdouble（約370 KiB）。近似計算やfast-mathは使わない。\n')
add('map450k、gopt133k、annealの基準反復数と温度、既存8候補の乱数と仕上げは元のまま。新候補のsaltは8。すべて固定回数で、時刻による候補数変更・設計打切り・軽い注文処理はない。ログ、@paper/@ops、DesignStore、プロファイラ、実験スイッチ、段の目印を維持した。\n')
add('## 方法と凍結\n')
add('差は `100 × mean_seed(mean_list(log(candidate/base)))`。負が改善。±はseedを標本とした1標準誤差で、8列を独立な4000標本とは数えない。表に使った通常runとreplayのresult.jsonが完了・WAなしであることを確認した。\n')
add('設定選択はseeds 0–499だけ。基準replayは `20261108-102842_legal-tie-fast`（設計元 `20261107-165305_deval-flex125-plan3`、8列）。全設計変更のreplayにはlegal-tie-fastの同じ注文処理を使った。実列0は参考値、選択の主指標は新規lists1–7。\n')
add(f"凍結: `{Z['time']}`、SHA256 `{Z['sha256']}`。その後はソースと設定を変更していない。通常2000件の比較は `--no-record` なしで記録。未見500–999の8列再生はこの凍結ソースの保存設計を使った。\n")
add('## 通常2000件の最終比較\n')
add(f"run群: `{rid[0].split('_')[0]}`。順序はargon-des-perf-latew105、deval-helper-wide、legal-tie-fix、dcomp-nine。24並列、各seedで順番を回す標準compare。\n")
add('| 比較対象 | 全2000件 (%) | 勝/分/敗 | 0–999 (%) | 1000–1999 (%) |\n|---|---:|---:|---:|---:|')
for r in rid[:-1]:
 s=F['compare'][r];add(f"| {r.split('_',1)[1]} | {ps(s['all']['pct'])} | {'/'.join(map(str,s['all']['wtl']))} | {ps(s['0-999']['pct'])} | {ps(s['1000-1999']['pct'])} |")
add('\n| 解法 | judge平均(s) | argon比 | p99(s) | 最大(s) |\n|---|---:|---:|---:|---:|')
for r in rid:
 t=F['timing'][r];j=t['judge_sec'];add(f"| {r.split('_',1)[1]} | {j['mean']:.6f} | {t['judge_ratio_argon']:.5f} | {j['p99']:.6f} | {j['max']:.6f} |")
b=F['p99_paired_bootstrap'];p=F['paired'];t=F['timing'][chosen]
add(f"\njudge = `1.04×helper_end_sec + 1.35×req_sec + (end_sec−helper_end_sec−req_sec)`。legal-tie-fixとの同一seed差は、helper_end **{ms(p['helper_end_sec'])} ms**、req **{ms(p['req_sec'])} ms**、judge **{ms(p['judge_sec'])} ms**。p99差は **{1000*b['difference']:+.2f} ms**、seedを組で再抽出する4000回bootstrapの95%区間は **[{1000*b['ci95'][0]:+.2f}, {1000*b['ci95'][1]:+.2f}] ms**。\n")
add(f"end_sec: 平均 {t['end_sec']['mean']:.6f}s、p99 {t['end_sec']['p99']:.6f}s、最大 {t['end_sec']['max']:.6f}s。1.8/1.9/2.0s超は {t['end_above']['1.8']}/{t['end_above']['1.9']}/{t['end_above']['2.0']}件。時刻による軽量化は入れていない。dv_candidatesは全件9（`final-stats.json`）。\n")
add('通常比較の外部負荷は平均0.142 core、最大0.599 core。reqの短縮には既存legal-tie-fastの高速化も含むため、設計高速化だけの成果として数えない。\n')
add('## 凍結した未見500件・8列リプレイ\n')
add(f"基準 `{M['final-base-replay'][0]}`、候補 `{M['final-candidate-replay'][0]}`。いずれもlegal-tie-fastで、seeds500–999。\n")
add('| 注文列 | 差 (%) | 差 (moves/order) | 勝/分/敗 |\n|---|---:|---:|---:|')
for label,title in [('fresh','新規1–7'),('all','全8列'),('real','実列0')]:
 q=held['score'][label];add(f"| {title} | {pflat(q)} | {q['moves']:+.7f} ± {q['moves_se']:.7f} | {'/'.join(map(str,q['wtl']))} |")
add('\n新規7列の差は2SEに届かないので、未見リストの改善が確定したとは言えない。候補の実列0は通常runの同じseedのスコアと500/500一致。DesignStoreはVで選んだ最終設計を保存・再生している。設定を未見結果へ合わせる追加試行は行わなかった。\n')
add('## 設計の配分・再投資: 訓練500件\n')
add('時間差は同時compare内のlegal-tie-fastに対するhelper_end_sec。高速化を含む候補はその効果込みの純増減。\n')
add('| 変更 | 新規1–7 (%) | 全8列 (%) | 実列0 (%) | 設計時間差(ms) | 通常 / replay run-id |\n|---|---:|---:|---:|---:|---|')
for args in [
 ('tabu停滞解放','unstall-replay.json','tabu-normal.json','20261108-103125_dcomp-unstall'),
 ('独立anneal×2','two-anneals-replay.json','diversity-normal.json','20261108-103318_dcomp-two-anneals'),
 ('独立半予算map×2','two-maps-replay.json','diversity-normal.json','20261108-103318_dcomp-two-maps'),
 ('6枝→raw Vで4枝','halving6-dcomp-halving6-scores.json','halving6-normal.json','20261108-113929_dcomp-halving6'),
 ('map470k','reinvest-dcomp-map470-scores.json','reinvest-normal.json','20261108-111044_dcomp-map470'),
 ('gopt165k','reinvest-dcomp-gopt165-scores.json','reinvest-normal.json','20261108-111044_dcomp-gopt165'),
 ('9候補','nine-dcomp-nine-scores.json','nine-normal.json','20261108-112115_dcomp-nine'),
 ('10候補・最後はrematchのみ','ten-late-dcomp-ten-late-scores.json','ten-late-normal.json','20261108-112915_dcomp-ten-late')]:add(row(*args))
add('\n- tabu: auditの出力は500/500同一。最後の受理から4×stallを超え、退避候補がない状態はmapで7/500件（seeds76,91,105,177,215,225,460）、平均2590反復（450kの0.576%）、最大443572反復。climb側は0件。世代を5進める修正は5ケースだけ設計を変え、新規列で改善なし。8倍予算の問題が1倍でも起きるが、ここでの得点改善にはつながらなかった。\n- 独立anneal×2は前半を半分長の2系統とし、各2枝を伸ばす。独立map×2はmap/gopt/annealを各半分、各2枝＋2再仕上げ。総反復数と完成候補数を保ったが、深さの損失を多様性で返せなかった。\n- successive halvingは共有prefixを保持し、その後の総反復数を6枝に等分。未仕上げVで4本を選び、全仕上げと従来4再仕上げを行った。最初の公平な8列評価で改善なし。\n- map470k/gopt165kはclimb高速化で払う範囲の追加探索。完成設計で明瞭な利得がなく延長しなかった。\n')
q=scorefile('ten-vs-nine.json')['score']['fresh']
add(f"9候補の改善が2SEを超えたため、後段rematchだけの10候補目へ延長した。増分も **{pflat(q)}%** と小さいが明瞭だった。ただし訓練4解法compare `20261108-113748` で10候補版はjudge平均1.755067s、argon比1.10241、p99 1.911775s（fix 1.900067s）。時間上限を超えたため、候補数の追加はそこで止めた。これは予算外の参考値であり、採用推奨ではない。\n")
add('## プロファイルと出力同一高速化\n')
add('既存DESIGN_PROFILE/AS_PROFILE/AF_PROFILEを有効化した `20261108-103133_dcomp-profile`、詳細窓計測 `20261108-104044_dcomp-profile-deep`、各200件。計測オーバーヘッド込みの24並列値で、時間短縮の判定自体にはプロファイラを外した同時compareを使った。両profile版のGCC stdoutは基準と200/200同一。\n')
add('| 段 | 平均local scaled ms |\n|---|---:|\n| mapまで | 478.70 |\n| anneal＋4枝 | 396.40 |\n| finishing全8候補 | 214.33 |\n| V全8候補 | 20.88 |\n| 初期列順DP | 0.56 |')
add('\n| finishing 1回 | climb | 前rematch | 穿孔 | 後rematch |\n|---|---:|---:|---:|---:|\n| 元の4枝 | 13.46 | 9.53 | 6.84 | 5.10 |\n| cold再仕上げ2回 | 7.53 | 4.81 | 6.99 | 5.41 |\n| warm再仕上げ2回 | 0 | 0 | 6.56 | 5.69 |')
add('\n単位ms。rematch全体90.20msのうちHungarian24.42ms、donor36.51ms、target18.38ms。rebuild34.21msはdonorを含むため重ねて加算しない。詳細窓計測seed0では関係更新が約半分、matchingが約23%。matchingは有効辺の85.6%を走査するため、部分ソートで大きく省く案は実装しなかった。\n')
add('| 出力同一案 | helper_end差(ms) | 確認・採否 | run-id |\n|---|---:|---|---|')
speedrows=[
 ('窓raw relation費用cache','speed-normal.json','20261108-104939_dcomp-relcache','GCC stdout500同一。ただし再比較で逆転'),
 ('同cache再比較','cache-layout-normal.json','20261108-105525_dcomp-relcache','得が安定せず不採用'),
 ('packed cache 2^14','cache-layout-normal.json','20261108-105525_dcomp-cache14','500件スコア同一、遅い'),
 ('packed cache 2^16','cache-layout-normal.json','20261108-105525_dcomp-cache16','500件スコア同一、遅い'),
 ('packed cache 2^18','cache-layout-normal.json','20261108-105525_dcomp-cache18','500件スコア同一、遅い'),
 ('gatherを通常ロードへ','speed-normal.json','20261108-104939_dcomp-expand','GCC stdout500同一、不採用'),
 ('hole費用の正確な表引き','hole-table-normal.json','20261108-110024_dcomp-hole-table','GCC stdout500同一、遅い'),
 ('climb現在寄与cache','climb-cache-normal.json','20261108-105401_dcomp-climb-cache','GCC stdout500同一、採用'),
 ('同cache再比較','climb-mask-normal.json','20261108-110326_dcomp-climb-cache','GCC stdout500同一'),
 ('同cache再々比較','climb-bound-normal.json','20261108-110906_dcomp-climb-cache','GCC stdout500同一'),
 ('covered mask memo追加','climb-mask-normal.json','20261108-110326_dcomp-climb-mask','GCC500/Clang200同一、単純cacheとの差が小さい'),
 ('非先頭donorの遅延計算','climb-bound-normal.json','20261108-110906_dcomp-climb-bound','GCC500同一、単純cacheより遅い'),
 ('rematch多項式memo','rematch-memo-normal.json','20261108-113533_dcomp-rematch-memo','climb-cache比。GCC500同一、遅い')]
for label,f,r,note in speedrows:add(f"| {label} | {ms(stage(f,r))} | {note} | `{r}` |")
add('\n採用したclimb cacheはGCC既定500件、GCC `-march=native` 200件（112116）、Clang `-march=native` 200件（110743）で各コンパイラの親出力とbyte単位で同一。nativeの比較でも速く、既定GCCだけに依存する短縮ではない。棄却した高速化案をすべてClangで追試したわけではない。最終dcomp-nineもClang C++23 nativeでビルドした。\n')
add('## 小改善の選択肢と次に試すこと\n')
add(f"1. **dcomp-nine**: 通常列での小改善。未見新規列の改善は未確定。通常2000件 {ps(x)}%、未見新規列 {pflat(held['score']['fresh'])}%。時間は上の最終比較。0.03%の採用条件には届かない。\n2. **dcomp-climb-cacheだけ**: 得点を変えずに設計を約17〜20ms短縮する部品。GCC/Clangで出力同一を確認済み。候補を増やさず時間余裕として残す使い方ができる。\n3. 10候補版は訓練新規列−0.01093±0.00265%だが、同時比較の平均が1.10241倍で予算外。追加設計候補の現在の限界効用は小さい。\n")
add('次に設計側で試すなら、完成前のVで枝を落とすより、短い実際の仕上げを選別段として使う方が筋がある。ただし今回の6→4ではraw Vだけで時間内の得を示せず、追加の選別費用も要るので優先度は低い。まず独立に使えるclimb高速化の約20msを残し、注文側の担当が測る限界効用と比較して使途を決めるのがよい。Task8では注文側の変更・他のlegal-*の読取りは行っていない。\n')
add('## 再現・ファイル\n')
add(f"最終ソース: `../dcomp-nine/main.cpp`、{Z.get('source_bytes',532212):,} bytes（本Taskの指示どおりサイズ削減はしていない）。READMEは各dcomp-*に配置。コミットなし、既存解法・共有scripts・trial_log・STATEは未編集。\n")
add('`make_sources.py` が停滞・profile・配分案、`make_speed.py` が高速化と9/10候補、`make_halving.py` と `make_rematch.py` が追加の各1案を再生成する。`metrics.py`、`analyze.py`、`identity.py`、`final_stats.py` が集計。全run-id、source hash、JSON指標、実行ログを本ディレクトリに保存した。\n')
add('`run.py` は標準 `scripts/pahcer_run.py` を呼ぶ薄いwrapper。共有runnerの評価lockと記録をそのまま使い、コンパイルにも同じflock＋niceを付ける。完了runのバイナリ再利用は、ソースSHA・コンパイラ版・全フラグ・解法名の完全一致時だけ。solver binaryを直接実行しない。\n')
add('```sh\n# 通常評価（記録する。標準runnerへ渡す）\n/home/sato/ahc074/.venv/bin/python solutions/dcomp-notes/run.py \\\n  --compare solutions/argon-des-perf-latew105 solutions/deval-helper-wide \\\n  solutions/legal-tie-fix solutions/dcomp-nine --seeds 0-2000 --save-design \\\n  -c "Task8 frozen verification"\n\n# 完了run群の集計。JSONのfinal-runs.jsonを参照する\nflock -x /home/sato/ahc074/runs/.lock nice -n 10 \\\n  /home/sato/ahc074/.venv/bin/python solutions/dcomp-notes/final_stats.py\n```\n')
add('最終再現の全手順は `final_check.py`。既存のFROZEN.jsonを上書きしない設計なので、新規再実行は個別のrunnerコマンドを使う。時間超過するプロファイル研究版だけ `--no-record` とし、それ以外の通常runはすべて記録した。\n')
(N/'REPORT.md').write_text('\n'.join(lines))
