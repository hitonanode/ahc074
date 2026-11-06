# deval-vcol

改良元: `solutions/deval-vtarget`（SOTA からの設計評価器統合版）。

通常の設計を完成させた後、列全体と専用 handle を同時に並べ替える近傍を 24 回試す。ペアの組合せと各列の両色を保つ。紙の prefix の印刷範囲を再計算し、列順に紙を番号付けし直すため、初期のスタックも正しい列順になる。V が下がった変更だけを採用する。

V は対象ごとの digital shift と解析的な不一致数補正を使う 16 点モデル。学習は seed 0–499。`DEVAL_COL_REFINE` は試行数（既定 24）。追加設計は経過 1.2 秒で止める。リクエストの軽量化は提出時のみ 1.72 秒から有効。LOCAL_BENCH では無効。

`dv_col_accepted` は採用数、`dv_col_sec` はその計算時間。その他の記録、@paper/@ops、DesignStore は親と共通。生成は `solutions/deval-vselect/make_col.py`。
