改良元: solutions/argon-req-ejectstats-v2

通常の穿孔を終えた紙に対し、追加穴を紙の位置に固定してHungarianによる目標再割当を行う。
追加穴の実際の色別需要を穴コスト・頭の色確率に入れ、フィラーの模様にも含める。
再割当で新しいペアが自然に同じ穴を持つ場合は二重に数えない。追加穴はその紙自身の
ハンドルより上だけなので、列と自身のハンドルは保持できる。ペアの汎用層整合も従来どおり。
列・窓割当は変更しない。再割当後の所有目標で紙を印刷し直す。未来の注文は読まない。

追加段のフィラー係数は1.0。ARGON_D2_LATE_ITERSは追加Hungarian回数（既定1、0で同一性確認）。
元のHungarianは追加穴なしの従来モデルのまま。元のmodel/proxy/perforation指標は追加段の前。
d2_rematch_*は追加段の回数・受理cycle・変更unit数・モデル改善・時間、
d2_extra_remainingは自然なペア穴と重複しない追加穴数。
ログ・@paper/@ops・プロファイラ・予算スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStoreを保持。
新しい段の目印と目次項目design_papers: perforation-aware reassignmentを加える。

追加段のモデル費用とフィラーproxyの開始・終了値をd2_model_initial/final、
d2_filler_initial/finalで出力する。受理済み状態の値を保存するので、表示のための再構築は行わない。
