改良元: solutions/combo-m1-nine

設計は同じ9候補を生成・選択する。窓のsparsebitsはGCCでだけ使い、Clangでは元の関係走査。互換ペアの安定sortはGCCで64bitレコードと8+9bitのradix、Clangで32bitレコードと7+10bitのradixを使う。費用順・同点順は同じ。rematch donorの修復可能maskを4対象ずつ計算し、Hungarianの前駆列を同じmaskで更新する。

注文処理では、後の手と交換できるanchor群のリンク・合法性再生を共有し、取り出し修復が既に持つ終状態と表示条件を再利用する。空の修復区間では深い順序を構成しない。next_costは先頭64/128枚の正確な途中状態を完全keyで保存し、穴費用の4項だけを同時計算する。浮動小数点の加算順は保ち、fast-mathは使わない。

空いた時間を別プランの再編集に配る。NS_ALTERNATE=1、NS_ALTERNATE_GAP=1.0、alternateの取り出し修復は最大2回。NEUTRAL_WIDTH=6、POST_CANDIDATES=6、NS_ROUNDS=3、NEUTRAL_SLACK=.35。元のF3_*環境変数の実験設定を優先する。

全予算は固定回数。時間不足の軽いモード、設計cap、時刻による候補数変更はない。DesignStoreは選択した設計を保存する。段の目印と目次、ログ・metrics・@paper/@ops・trace・profiler・実験スイッチを維持する。検証手順と式の根拠は ../dcomp-notes/EXACTNESS10.md、実測結果は ../dcomp-notes/REPORT10.md。
