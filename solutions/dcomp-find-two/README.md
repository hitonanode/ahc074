改良元: solutions/dcomp-combo-ten

後処理の可視性再生で、移動する紙とanchorの位置をAVX2の同じ走査で求める。別々のmemchrで同じ192枚を調べる負担を減らす。負のanchorは従来のtop挿入。

探索・予算・浮動小数点の加算順は変更しない。ログ・実験スイッチ・DesignStoreを保持し、時間fallbackは使わない。
