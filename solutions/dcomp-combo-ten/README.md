改良元: solutions/combo-m1-nine

combo-m1-nineにTask 9の10候補目を加える。窓探索のsparsebits高速化はGCCだけで使い、Clangでは元の全走査を使う。注文処理はcombo-m1-nineのまま。

反復数、既存9候補の生成・選択、実験スイッチ、ログ、DesignStoreを維持する。時間による打切りや軽いモードは使わない。fast-mathは使わない。
