# legal-alloc-rmin0（注文処理の予算を 1 つ変える版）

改良元: `solutions/legal-tie-fast`。`solutions/legal-notes/make_alloc.py` で作った。

## 改良元からの差分

- 中立の書き換えの 2 回目以降を、改善が 0.05 未満でも行う（REPEAT_MIN = 0）。

注文処理の各部分の、時間あたりの価値を測るための版（設計は変えない）。指標は改良元と同じ。
