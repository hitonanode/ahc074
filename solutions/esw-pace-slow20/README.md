# esw-pace-slow14 の伸ばしを 2.0 倍にした版（ペース配分の負荷試験）

改良元: solutions/esw-pace

solutions/esw-pace の main.cpp の先頭に次の行を足しただけの、計測用のコピー（提出用ではない）。各スイッチの意味は esw-pace の README と main.cpp 冒頭の「Test switches」にある。

```
#define PACE_SIM 2.0
```
