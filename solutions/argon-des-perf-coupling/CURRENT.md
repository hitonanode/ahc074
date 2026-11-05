# 継続状態

**2026-11-06 07:52：今回の作業は完了。新規マージ対象なし、実行中の評価・分析・ビルドなし。**

基準は引き続きPR146 `argon-des-perf-latew105`。
BASE.mdの07:00/07:05方針に従い、0.03%以上・2SE・時間条件を満たす候補はなかった。
小改善が有意な系列は拡張したが、追加再割当で積み上がらなかったためD2を終了。
D3–D5も初回対照と必要な改訂まで完了し、REPORTをそれぞれ保存済み。

- D2：通常2000で追加穿孔−0.013795±0.002851%、時間+17.35 ms。改善あり・未採用。
- D3：固定2000×2で全列MDP−0.000879±0.000619%。状態数制限を全て解除しても微小。
- D4：固定200×2、重み0.1 −0.002252±0.001603%、完全同点 −0.001717±0.001370%。
- D5：負荷警告なしの固定100×2、255列挙−0.019067±0.011471%、16標本+0.050917±0.011853%。
  judge増分+16.53秒/+1.04秒で、両方時間超過。最終runは全群20261106-073713。
- D5選択無効の20実行はstdout・非時刻stderr（d5_*と説明済みcf_value_hitsを除く）完全一致。
- 変更13ソースの52ビルドが警告なし。基準と同一のコピー2本を含め15ディレクトリ。
  `package-check.json`にSHA・目次/段/既存指標の保持・バイナリなしを保存。
- 新しいREPORTの入口はこのディレクトリのREPORT.md。D3/D4/D5へのリンクもある。
- 未解決の一般論：非加算フィラー/取り出し価値モデル、本体同等plannerの安価なrollout。
  今回の候補が使えない根拠と、数学的な不可能性を示してはいない範囲は各REPORTに明記。

以下は実行時の履歴メモ。現在の残件を表すものではない。

---

基準は PR146 argon-des-perf-latew105。BASE.md 確認済み。採用が出たら停止する。

**07:00のBASE新方針を07:10に確認。採用閾値0.03%、単独速度改善は採用しない。
D2は追加穿孔−0.013795%を「改善あり・未採用」として終了し、D3へ進んだ。**
今後の項目は初回＋原因を特定した改訂1回まで。D3 dir argon-des-colmdp。
保存設計2000で未被覆212seed/214列、長さは全て12以下。fullのみ143列、full+sequences71列。
候補argon-des-colmdp-fullは250k/800kへ状態上限を拡大。fixed 200×2実行中、full200.log。
altwarmはaltcacheと同一出力を目指すDP再利用版。verify200で1,385,351行を完全一致確認。
新閾値により、altwarmの照合なし時間比較とadoption buildは行わない。

07:33更新：D3終了、全列MDP fixed2000×2で−0.000879±0.000619%、109/1789/102。
214列の完全被覆でも不足、近似版は作らず。REPORTはargon-des-colmdp。
D4終了：argon-des-genvalueの重み0.1 fixed200×2 −0.002252±0.001603%。
改訂tie-onlyは−0.001717±0.001370%。受理8.3025/1024注文、予測和0.000257手/注文。
閾値未満、0.2/0.3や2000への延長は省略。REPORTはargon-des-genvalue。

D5進行中、argon-des-rollout。軽い3計画で全255次目標を評価するover-time oracle。
2×2 smoke 20261106-073015_argon-des-rollout はWA0、約9.5秒/ケース。
重複候補更新時の再ソートを修正し、control10.log（ON=0、fixed10×2）と
oracle100.log（fixed100×2、--no-record）を実行中。make.pyがソース生成。
futureは実際の注文でなく一様255目標。コピーしたworkerでsimulate、候補は合法な既存path。
次：statusとログで完了を確認、argon-des-colmdp/analyze.pyで集計。
pool多様性、予測/実測、時間、gate（費用差0/.02/.05/.1/.25/.5）と必要標本数で
時間内の改訂（最大1回）が有望か判断。D5まで終わったら最終10行、今回のマージ対象は今のところなし。

- 交互穿孔 normal 2000 は完了。alternate −0.0137946±0.0028509%、780/603/617、judge +17.3456±1.6685 ms（15ms予算超過）。alternate2 −0.0107162±0.0040448%、judge +14.9195 msだがp99差37.30msで超過。初期500でaltfocusは−0.002%。
- run: 20261106-064830_argon-des-perf-latew105、20261106-064854_argon-des-perf-{alternate,altfocus,alternate2}。
- whole-unit 診断は fixed 500 完了。modelprobe の run 20261106-065002 / 065003 は、旧 rematch-v2 / whole の設計。
- summarize.py と diagnose.py で、同時比較の時間・モデル差・重なり・操作ラベルを分析する。
- 時間対策altcacheを実装。同じ層化乱数の一様値を再利用。dead if constexprとfocus枝を除去し、追加段のbuild/search時間を計測。500比較 run 20261106-065730_latew105 / 20261106-070010_alternate / 20261106-070021_altcache（いずれもargon-des-perf-）。ログaltcache500.log。identity500とsummaryはwhenidleで待機。
- 順序対照altbefore：2回目穿孔をlate rematchの前へ移動。500比較待機。run 20261106-070053_latew105 / 20261106-070134_altbefore。
- modelcolumnで既存MDP8反復の最後の平均正規化量を計測（値関数・注文処理は変更なし）。500 fixedは完了。run 20261106-065835/065837_argon-des-perf-modelcolumn。column_diagnosis.pyはwhenidle待機。
- wholeの重なりを除くと予測改善0.004133→0.001010手/注文、最良1フィラーだけだと+0.000217悪化。実測+0.003723。区間DP等でcaseを選別する簡易対照はgate-diagnosis.json。最良DP0.5ゲート−0.008525±0.004684%、費用に見合う明確な改善ではない。45設定から選んだ値でもある。
- final_audit.pyを追加。2000 saved designsの各紙・前段指標・ログ・ソース範囲・TOC・4build・時間・score条件を照合。altcacheを採用するならcheck_builds.pyを実行してから使う。
- D2 の残件：交互穿孔を評価、whole-unit のモデル誤差、穴を見た filler climb。
- D3–D5 未着手。REPORT.md はまだ見出しのみ。

新規ディレクトリ：coupling / alternate / altfocus / alternate2 / modelprobe / altcache / altbefore / modelcolumn（全て argon-des-perf-）。
既存・コミット済みディレクトリは編集禁止。分析は whenidle + runs/.lock の排他 flock。
