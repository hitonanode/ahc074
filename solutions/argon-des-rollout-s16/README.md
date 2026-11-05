改良元: solutions/argon-des-perf-latew105

D5の費用削減の改訂。最終候補3つに対する次注文の先読みを、255種類の全列挙から
固定seed・共通乱数の16標本へ減らす。基準が後処理済みの操作列だけを選択する。
各次目標は3通りの軽い計画の最良値で評価し、既存の終状態価値を含める。
実際の未来の注文は参照しない。ARGON_D5_SAMPLES既定16、他のスイッチ・d5_*指標は
argon-des-rolloutと同じ。計測専用で時間を超えるためpahcer_run.pyに--no-recordを付ける。
既存ログ・プロファイラ・DesignStore・段を保持し、rolloutの段と目次だけ追加する。
