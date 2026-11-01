# abl0702-norepl

改良元: solutions/gpt6pro-07-02-replace

機能を 1 つ外した切り分け用（cmp-anneal へ取り込む工夫の効果を見積もるため）。先頭に `#define BARCODE_PAIR_REPLACE_RATE 0` を足しただけ。外したもの: 設計の対の組み替え近傍 (a,b)+c+d → (c,d)+a+b。
