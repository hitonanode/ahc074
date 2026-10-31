# cons-stack

改良元: solutions/audit3-stack と solutions/cons-tab（合流）

audit3-stack に、cons-tab の設計の変更をそのまま当てた版。audit3-stack からは注文処理（狭い段と、同じ段に 2 枚を重ねる穴埋め紙）とそれまでの全部を、cons-tab からは焼きなましの 2 つの変更だけを取った。

## 変更点（cons-tab から取ったもの）

- 焼きなましの汎用層の費用を、触れたブロックの数でなく、対の 2 目標が求める向き（オンのブロックの数）による表 kBlkTab で見積もる。
- ブロック全体の Y を反転する近傍を足す。

中身は cons-tab の README のとおり。cons-tab の実験用の環境変数 `BLK_TAB6` と `SPARE` は入れていない。

## パラメータと指標

- 環境変数 `BLK_TABLE`（既定 1）、`BLK_CMP`（既定 0.001）は cons-tab と同じ。stderr の指標は audit3-stack と同じ。
