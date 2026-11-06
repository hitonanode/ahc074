# deval-vmap

改良元: `solutions/deval-vclean`。

窓割当てが元から保持していた 8 個の良い状態を、設計候補として再利用する。追加の窓探索は行わない。最良割当てと、費用順の別の割当てから初期化して焼きなましを行い、完成後の V16 で選ぶ。候補内の総反復数は `ANNEAL_ITERS`、候補数は `DEVAL_CANDIDATES`（既定 2）。仕上げは親と同じ 50,000 回と再割当て 2 回。

`dv_map_pool` は取り出せた割当て数、`dv_map_gap` は元の最良割当てからの gobj の差。時間ガード、DesignStore、既存診断は維持。生成は `solutions/deval-vselect/make_mapelite.py`。
