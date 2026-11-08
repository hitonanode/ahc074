改良元: solutions/dcomp-screen-replay

next_costのcache keyの圧縮で、除外する7枚と、列外にある紙の重複しない総数を数える。走査済みの除外数が総数に達したら、残りはすべてkeyに入るためmemcpyする。keyの順序・全byte・hashと費用は不変。全16枚が残る中間blockもshuffleせずに写す。

通常と異なる役割配置は元のscalar処理を保持する。予算、ログ・実験スイッチ・DesignStoreは維持、時間fallbackなし。
