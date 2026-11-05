改良元: solutions/esw-clean

設計の焼きなまし4区間のうち、第2区間の直後に Hungarian 再割り当てを2回行う。
最後の再割り当ては2回とし、合計4回、焼きなましの温度と候補数は維持する。
一括の目標交換が作った状態から、後ろ2区間で列・ハンドル順も適応させる。

FRAME_MID_ROUNDS（既定2、0で基準の順序）と FRAME_MID_AFTER（既定2、1～3）で位置を指定できる。
追加指標 frame_mid_iterations / cycles / changed / decrease / sec は途中の再割り当て。
従来の match_* は最後の分で、回数は両者を合わせる。その他のログ・設定・プロファイラは維持する。
