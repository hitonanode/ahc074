改良元: solutions/legal-tie-fast

Task 8の設計予算配分と高速化の研究記録。注文処理はlegal-tie-fastに固定する。通常の2秒ソルバは記録し、プロファイルなど時間超過の研究版だけ --no-record にする。実行は標準pahcer runner、ビルドと重い分析は共通flockとniceを使う。

進捗はPROGRESS.md、最終結果はREPORT.md。設定選択はseed0–499、凍結確認は500–999、最終通常比較は2000件。
