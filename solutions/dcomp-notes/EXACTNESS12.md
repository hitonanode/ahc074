# Task 12: 出力同一性の条件

## whole-post memo

`dcomp-t12-postmemo` は、同じ注文内の通常 `post_optimize` だけを再利用する。注文の始点 `initial`、注文バーコード、紙の設計、設定は、その注文内で不変である。`process` の開始ごとにepochを進めるので、異なる注文では一致させない。

keyは現在の192枚の順序、top_d、順序を含む全filler記録(paper,lvl,hi)、eject/delete_only/secondaryフラグ、全操作の紙と挿入深さ、LOCAL_BENCHでは全ラベルを含む。hashは32entryの位置を選ぶだけで、epoch・長さ・key全byteが一致した場合だけ再利用する。浮動小数の値を近似する処理はない。

hitでは終状態・操作列・ラベル・last_post_operatorを戻す。外側の反復の停止判定に使われるeject_acceptsの差を再現し、post_savedも元と同じ増分にする。その他の探索回数の指標は実行した仕事を数える。neutral_collectは候補poolへの副作用を持つためキャッシュ対象外。trace/predict/plan_trace、およびF3/COLFASTの計測buildでも元の処理を実行する。

`POST_MEMO_CHECK` 版はhitでも元のpostを実行し、終状態、操作、ラベル、last_post_operator、eject_accepts差が全て一致するかを検査する。通常・検査版ともGCC/Clang各200×4で800出力が親とbyte一致した（213308/213514）。GCC通常版のclean再試験214102は500×4の2000出力が一致した。速度の採否は各コンパイラの同時比較で別に決める。

`dcomp-t12-postcompact` は同じ条件のkeyを512 bytesに置く。操作数≤64、filler数≤32、LOCAL_BENCHのラベル数≤64ならkey長は最大489 bytes、8byteに丸めても496 bytesである。これを超える入力は元の同一postを実行する。時計・探索予算の条件分岐ではない。

## replay-prefix の無効化

prefixはpostの操作列の共通接頭辞を再生済み状態から始めるための作業省略である。無効時は同じ初期状態から同じ操作を再生する。候補順、予算、評価式は変えない。元の実験スイッチを保持する。

## helper増加の調査

204122のGCCバイナリでは、assign_windows本体はalt1/dual25とも19311 bytesで3551命令。関連lambdaの命令数も一致し、正規化した逆アセンブルの差はPC相対参照先の配置のみだった。これは仕事量が増えた証拠ではない。一方、アラインメントを変えた212334の試験では時間を回収できなかった。配置の影響を疑うことと、実行時間差の原因を特定することを区別する。

## 追加の同一性確認

compact memoはGCC既定/Clang nativeの各500×4で2000/2000 byte一致(214646/215406)。GCC nativeの通常200件も200/200一致(221614)、req差−5.063±2.222ms、end差−3.116±6.163ms。Clangのprefix無効単体は500×4の2000/2000一致(215710)。GCCではprefixの無効化を採用しない。
