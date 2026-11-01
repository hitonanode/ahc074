# abl0702-nosym

改良元: solutions/gpt6pro-07-02-replace

機能を 1 つ外した切り分け用（cmp-anneal へ取り込む工夫の効果を見積もるため）。先頭に `#define BARCODE_SYMMETRIC_ESTIMATE 0` を足しただけ。外したもの: 対の汎用層の費用を a と b の両側で見積もること（a 側の 2 倍に戻す）。
