改良元: solutions/argon-des-perf-latew105

保存済み設計に対する列モデルの計測。通常のcolumn MDPの最後の相対価値反復の
正規化量に列の事象頻度を掛け、d2_column_average（全被覆列の和、手/注文）を出す。
8反復の近似値であり、実処理のフィラーや列外状態は含まない。
d2_column_rateは被覆列の事象頻度、holesは全列のハンドル穴需要、weightsは紙の適応重みの和。
既存MDPのF/Hや注文処理は変えない。--design-fromを使用する。
既存ログ・スイッチ・プロファイラ・DesignStore・段の目印を保持する。
