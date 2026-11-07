# deval-recip

改良元: solutions/deval-vbranch-o3。

焼きなましの穴費用のfloat除算を逆数近似・Newton補正・FMA残差補正に置き換える。入力は小さな非負整数で、到達可能な全ての穴数とresetの組合せについて元の除算とのビット一致をGCCとClangで確認する。fast-mathは使わない。探索予算・乱数・時間ガードは同じ。
