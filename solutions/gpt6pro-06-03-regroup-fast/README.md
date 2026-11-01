# gpt6pro-06-03-regroup-fast

改良元: solutions/gpt6pro-06-02-regroup（外部 agent gpt6pro-06 が同時に出した軽量版）

## gpt6pro-06-02-regroup との差分

時間の配分の定数 3 つだけが違い、改良元（gpt6pro-06-01-comparator）と同じ値に戻してある。

- 設計の焼きなまし: 200 万回または実時間 1.00 秒まで（06-02 は 400 万回・1.40 秒）
- 軽量処理への切り替え: CPU 時間 1.55 秒（06-02 は 1.70 秒）

## 移植について

出所は main checkout の other_agents/gpt6pro-06-02-layered_barcode_v2.zip の solution_fast.cpp。移植の変更は gpt6pro-06-02-regroup と同じ。

時計の倍率 CLOCK_SCALE は入れていない（時間で打ち切る部分は、手元ではジャッジより約 1.1 倍多く探索する）。

agent の報告（独自生成 100 件）は 10.935 手/注文（06-02 は 10.901 手）、平均 1.09 秒。
