# esw-pace-slow17 のペース配分を 1.80 秒の切り替えだけにした対照

改良元: solutions/esw-pace

solutions/esw-pace の main.cpp の先頭に次の行を足しただけの、計測用のコピー（提出用ではない）。各スイッチの意味は esw-pace の README と main.cpp 冒頭の「Test switches」にある。

```
#define PACE_SIM 1.7
#define PACE_CLIFF 1
```
