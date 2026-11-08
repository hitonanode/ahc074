改良元: solutions/dcomp-stack-b

next_costの穴費用の4色分をAVX2で計算し、元の順にcostへ加える。穴需要率と残留カバー率はいずれも整数/256、係数は.25、深さは整数なので各項が整数/1024として正確に表せる。積や差の丸めがなく、FMAの有無に左右されない。一般の途中和への加算順は変更しない。検証版は旧next_costで全missを再計算しdouble bitを照合。

予算・列挙順・ログ・DesignStore・実験スイッチはそのまま。時間fallbackなし。
