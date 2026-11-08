改良元: solutions/dcomp-screen-replay

出力同一の短縮で空けた時間を注文探索へ配る試行。固定の既定値: NS_ALTERNATE=1, NS_ALTERNATE_GAP=.75、次点の取り出しを4回。

設計は10候補のまま。環境変数による実験設定を優先し、時計による候補数変更やfallbackはない。設定はseed 0〜499の固定設計・4注文列で選ぶ。ログとDesignStoreを保持する。
