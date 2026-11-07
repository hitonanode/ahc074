# deval-edit4

改良元: solutions/deval-vbranch-o3。

編集の紙番号とanchorを4バイトの構造体へ詰める。紙番号は0〜191、anchorは−1〜191なので値は変わらない。LOCAL_BENCHの操作ラベルも保持する。

探索予算・浮動小数演算・時間ガードは同じ。
