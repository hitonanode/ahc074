# 再開メモ: design-packedのマージ待ち

**採用条件を満たしたため停止済み。マージ対象は solutions/argon-des-design-packed。**
現BASEはPR #141のargon-des-perf-stratacut。最終比較前・終了後ともBASE.mdで確認した。
再開時はBASE.mdを必ず再読し、新基準と解放時間の配分を確認する。期限なし。

## 確定結果

最終通常2000件:
- 基準: 20261106-043249_argon-des-perf-stratacut
- 候補: 20261106-043249_argon-des-design-packed
- 全stdout・非時刻stderr・保存設計本文が2000/2000一致。得点差0±0%、0/2000/0。
- judge平均1.597371406→1.580431328秒、対応差−16.940078±1.652179ms。
- judge p99 1.787108079→1.760552681秒、差−26.555398ms。
- judge最大2.0336956→1.9190722秒、2秒超え1→0。
- req_sec .441631287→.440911645、helper_end_sec .949071717→.933957005秒。
- 穿孔−6.810226ms、helper段−12.834468ms。map等の無変更部分にも差があるため、解放時間は全体の16.940msとする。
- 外部負荷: 500件 .13/.46、追加1500件 .27/1.27コア（平均/最大）、警告なし。
- 記録・2000設計保存あり。4構成ビルド警告0、WA/self_wrong/op_label_errors全件0。
- build-results.json/final-audit.jsonで照合済み。ビルド実行ファイルは/tmpで作成・削除済み。
- ソースSHA: 0846ef44c60f2a289fdc573bc40335559a37070e53ce4e031530bb68d22f2ae1。
- 自分の評価・分析は全て完了。ソースはこのまま確定し、追加の試作や比較を始めない。

## 内容と失敗も含めた証拠

変更はComparator::build_tablesの全始点BFS→1回＋紙番号置換と、穿孔配列の25/64容量への特殊化。
元の距離表と全518400要素を8件で独立BFS照合。式・順序・乱数・探索予算は同じ。
基準との差+66/−35行。共有型のインターフェース、全ログ・profiler・DesignStore・TOC・段の目印を保持。
候補REPORT.mdに証明と最終表、ここのREPORT.md/MEASUREMENTS.mdに全比較・診断を残した。

単独compact: 20261106-041137_* の500件。全出力一致、穿孔−6.96ms、全体+3.24msで不採用。
単独orbit: 20261106-041647_* の2000件。全出力一致、全体平均−5.178msだがp99+50.708msで不採用。
時間悪化の上位20件中19件がseed890〜1090に集中、主にmap/anneal。原因を単一に断定していない。
finalize_orbit.py / orbitのfinal_audit.pyはその時間assertで停止した旧版用。採用確認JSONは作らない。
最終組合せは別の3版同時500件比較で追加短縮を確認し、基準/組合せだけを2000件へ延長した。

## 次回

D1はclosed。D2の32標本での係数近傍・非head・前段の目的のずれは未完了。
D3（長列MDP）・D4（汎用層価値）・D5（rollout）は未着手。
今回の短縮を自動的に自分だけで消費せず、マージ後のBASE.mdに従う。

全評価はscripts/pahcer_run.pyのみ、通常run記録。分析とcompile-checkはwhenidle.sh＋flock -xで評価と直列化。
statusはPID namespaceのため誤表示しうる。lockを削除・修正しない。
g++ wrapperをPATH先頭へ追加する。ビルド用バイナリはsolutions外で作る。
旧argon-des-perf-*は前回までにコミット済みで変更していない。共有scripts/trial_logも編集せず、コミットなし。
