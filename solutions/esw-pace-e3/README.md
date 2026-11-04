# LOCAL_BENCH でも全注文を手間 3（軽い計画）で処理する計測用の版

改良元: solutions/esw-pace

solutions/esw-pace の main.cpp の先頭に次の行を足しただけの、計測用のコピー（提出用ではない）。各スイッチの意味は esw-pace の README と main.cpp 冒頭の「Test switches」にある。

```
#define PACE_FORCE 3
```
