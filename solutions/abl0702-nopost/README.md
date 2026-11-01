# abl0702-nopost

改良元: solutions/gpt6pro-07-02-replace

機能を 1 つ外した切り分け用（cmp-anneal へ取り込む工夫の効果を見積もるため）。先頭に `#define BARCODE_DISABLE_POST 1` を足しただけ。外したもの: 操作列の後処理（1 手削除・戻し位置の変更・2 手削除 + 1 手修復）全部。
