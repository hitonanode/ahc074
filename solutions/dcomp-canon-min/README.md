改良元: solutions/dcomp-combo-ten

canonicalizeの下からの走査で、汎用紙を見た状態をcur=-1で表す。列に残る条件はc<=curの1個となる。外れる紙は必ずc>curなので、levelのmin(cur,c)を省き、max(cur,0)で同じ値を作る。

探索・予算・浮動小数点の加算順は変更しない。ログ・実験スイッチ・DesignStoreを保持し、時間fallbackは使わない。
