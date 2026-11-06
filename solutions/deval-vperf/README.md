# deval-vperf

改良元: `solutions/deval-vclean`。

焼きなましと filler climb 154,000 回、再割当て 4 回を共有し、穴あけと最終再割当てだけを 4 通り試す。穴あけの filler 利益の重みは 0.7 / 0.4 / 1.0 / 1.3、乱数 salt は 0–3。`DEVAL_PERF_GRID=0` は重みを全て 0.7 にする。V16 で完成状態を選ぶ。既定の mode は 7。

時間ガード、DesignStore、診断は親と同じ。生成は `solutions/deval-vselect/make_perfselect.py`。
