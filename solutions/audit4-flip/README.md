# audit4-flip

改良元: solutions/cons-flip と solutions/audit4-fix（合流）

cons-flip に、audit4-fix の変更（audit3-stack からの差分）をそのまま当てた版。cons-flip からは紙の設計（反転紙がほかのブロックも覆う形と、模擬による汎用層の費用）と、それまでの全部を、audit4-fix からは列の外の紙の記録の修正 3 つ（gen_harm、free_return、canonicalize）だけを取った。2 つの差分は別の部分（設計・汎用層と、列の外の紙の扱い）にあり、コードの変更は audit4-fix と同じ。

全体の解説は docs/audit4-flip-explained.html にある。

## 変更点（audit4-fix から取ったもの）

- gen_harm: 土台より上に残った前の専用紙が、次の注文の汎用窓の穴で目標と色が違うなら、置き直しで汎用層の下へ動かし、その場には残さない。
- free_return: 巡回順の前の紙が列の下端になった紙は、列の上端へも戻せる。
- canonicalize: 毎注文の後に、列の外の紙の記録を重なりの順から作り直す。

中身は audit4-fix の README のとおり。

## パラメータと指標

- 環境変数は cons-flip のものに、audit4-fix の `GEN_FIX`・`PRED_BOTTOM`・`CANON`（既定 1）を加えたもの。
- stderr の指標は cons-flip のものに、audit4-fix の `canon_fail`・`canon_change`・`pb_try`・`pb_top`・`gh_try`・`req_sec`・`end_sec` を加えたもの。
