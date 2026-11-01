# imp-combo

改良元: solutions/astra-search3

solutions/astra-search3（Astra。窓の割り当ての「1 窓を別の組へ」の手で、移動先を閉包から直接選ぶ）に、solutions/imp-seg の変更（設計の焼きなましを 4 区間に分け、区間ごとに最良の状態から再開）を当てただけ。2 つはコードの別の部分（assign_windows と Design::anneal / Annealer::run）を変える。どちらも単独では 2000 件で有意でなかった（imp-s2hd 比 −0.032 / −0.038%）ので、合わせて有意になるかを確かめる。中身は 2 つの README を参照。
