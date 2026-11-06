# deval-vguided

改良元: `solutions/deval-vclean`。

前半 2 段は元の焼きなまし。第 3 段の現在状態を 32 個保存し、仕上げ後の V を予測する軽いモデルで最良の状態を選んで、第 4 段を始める。第 4 段でも 32 個の状態を保存し、同モデルの上位 3 個を仕上げて V16 で選ぶ。総焼きなまし反復数は SOTA と同じ。予測に注文処理を使わない。

仕上げは filler climb 50,000 回、再割当て 2 回、穴あけと最終再割当て。時間ガード、DesignStore、診断は親と同じ。生成は `solutions/deval-vselect/make_guided.py`。
