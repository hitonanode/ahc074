改良元: solutions/dcomp-screen-replay

可換な付け替えの最終並びGについて、列番号のsuffix最小値、列内の紙の位置bitset、最下部の位置を共有する。1枚挿入で列外に出るのは、挿入位置より上かつ挿入紙より深い列の紙だけ。この集合を列挙してcanonical recordsを復元し、旧fillersの優先順位も維持する。検証版では各shortcutを元のcanonicalizeと比較する。

予算・モデル値・合法性・選択順は不変。ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。
