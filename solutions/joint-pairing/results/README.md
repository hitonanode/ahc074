# 評価値

primary.csv: seed6001〜6032、18解法×32注文列。extra.csv: 同じ32公開問題に7本ずつ追加した独立注文列、3解法×224列。deep.csv: 8問題での3000提案SA、4解法×8列。全列は絶対スコア384E+Tで、全件E=0なのでTと一致する。各列1024注文。

Gitに載せた全1280値を元のresult.jsonから抽出した。CSVのproblem_seedでクラスタ化し、primaryとextraを合わせると各問題8列になる。recompute.pyは32クラスタの標準誤差とt分布95%区間を再計算する。256種類の独立公開問題として扱わない。

run接頭辞は順に20261101-152846_joint-pairing、20261101-153219_joint-pairing、20261101-153014_joint-pairing。各armの詳細はEXPERIMENT_PLAN.json。seed6000は実装確認用で集計外。追加7本は初回比較後に決めたが、候補・選択は固定済みで変更していない。

verification.json: 全操作の独立可視性再生とハッシュ検査。oracle-tests.json: 有向距離・実現集合・整数マッチングの独立検査。baseline-equivalence.json: 元のimp-leanとの出力同一性。official-check.json: 別環境で再生成した1問題4設計についての公式Rustテスター照合（全本評価をRustで再実行したわけではない）。diagnostics.json: 模型と採択・計算量の記述統計。
