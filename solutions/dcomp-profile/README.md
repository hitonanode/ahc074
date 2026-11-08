改良元: solutions/legal-tie-fast

出力を変えずに設計段を測定する研究版。既存 DESIGN_PROFILE/AS_PROFILE/AF_PROFILE を有効化し、8 候補それぞれの finishing ログを @dcomp_finish に保存する。dc_climb_sec は filler climb の時間。プロファイラのオーバーヘッドがあるため、時間制限を超える研究実行は --no-record とする。

注文処理は改良元と同一。固定反復回数で動作し、時間による省略はしない。
