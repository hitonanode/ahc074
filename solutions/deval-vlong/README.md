# deval-vlong

改良元: `solutions/deval-vbranch-o3`。

GCCの設計関数の最適化で短縮した時間を使い、焼きなまし反復数を11,175,000から11,733,750へ5%増やす。前半2段共有、後半4分岐、後発候補の温度2倍、V16での選択、仕上げ予算と時間ガードは親と同じ。

提出用は `main.cpp` 1ファイル。Vの係数はseed 0–499で学習済み。DesignStoreは選択済みの設計を保存する。診断項目は親と共通。再生成は `../deval-vselect/make_long.py`。`FROZEN.json` に設定とソースハッシュを記録する。
