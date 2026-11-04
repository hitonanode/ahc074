# ジャッジの遅さを真似る版: 注文処理の段の時計を 1.4 倍に伸ばし、LOCAL_BENCH でもペース配分を使う（--design-from で使える）

改良元: solutions/esw-pace

solutions/esw-pace の main.cpp の先頭に次の行を足しただけの、計測用のコピー（提出用ではない）。各スイッチの意味は esw-pace の README と main.cpp 冒頭の「Test switches」にある。

```
#define PACE_SIM 1.4
```
