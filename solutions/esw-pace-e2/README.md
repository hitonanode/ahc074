# LOCAL_BENCH でも全注文を手間 2（2 削除 + 1 修復と、2 番目の候補の後処理なし）で処理する計測用の版

改良元: solutions/esw-pace

solutions/esw-pace の main.cpp の先頭に次の行を足しただけの、計測用のコピー（提出用ではない）。各スイッチの意味は esw-pace の README と main.cpp 冒頭の「Test switches」にある。

```
#define PACE_FORCE 2
```
