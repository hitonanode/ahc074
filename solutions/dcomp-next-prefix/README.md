改良元: solutions/dcomp-screen-replay

next_costの列内走査で64枚・128枚目までのkey、途中のdouble和、rank/first/MDP codeを完全keyで保存。共通prefixがあればその同じ途中状態から残りだけを走査する。加算の順序は変えず、近似やfast-mathも使わない。検証版はcacheに頼らない元の全走査とdouble bitを比較する。

固定探索予算、ログ・実験スイッチ・DesignStoreを維持し、時間fallbackなし。
