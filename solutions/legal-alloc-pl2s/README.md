# legal-alloc-pl2s（注文処理の予算を 1 つ変える版）

改良元: `solutions/legal-tie-fast`。`solutions/legal-notes/make_alloc.py` で作った。

## 改良元からの差分

- 追加の候補を長さで絞らず（PLAN_SHORTLIST = 0）、本探索を 2 つにする（PLAN_LIMIT = 2）。

注文処理の各部分の、時間あたりの価値を測るための版（設計は変えない）。指標は改良元と同じ。
