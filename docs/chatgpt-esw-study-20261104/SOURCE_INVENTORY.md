# 元成果物・証拠の所在

このPRは研究報告と評価データの保存であり、提出用C++の変更を導入しない。以下はPR作成時に会話の添付から実在を確認したファイルのSHA-256。ZIP内の対応ソースとも照合した。巨大なZIP・C++本体はこのPRに追加していないため、下記ファイルは元の会話添付から取得する。ChatGPT内でのみ有効なsandboxリンクをGitHub上の永続的なソースURLとしては使わない。

## アーカイブ

| 添付名 | bytes | SHA-256 | 内容 |
|---|---:|---|---|
| ahc074_research_bundle.zip | 6991689 | `2d82057528c8cfeb2b4c8c7c21fcb5057e4eb85d8ca31ddd4cf8fd15e4aefa09` | 初回の実行予算制御・列MDP・OverlapReassignなど |
| ahc074_no_fallback_sources.zip | 674713 | `4719e13b4ee64d3664fe34fd0cac21a3598a8502e29c7f25d666329dd84087aa` | 第2回のソース、説明、評価スクリプト、主要CSV |
| ahc074_no_fallback_research.zip | 57410599 | `8ec68edeb35809ebe98fb78a30fe6a80d38fd162e571dc827603e7befc825f1c` | 第2回の全入力・操作列・ログ。320出力を今回再生検証した対象 |

小さいsource ZIPのルートは `ahc074_no_fallback_sources/`、大きいresearch ZIPのルートは `ahc074_no_fallback_research/`。初回ZIPのルートは `ahc074_research/`。

## 確認できた単体C++

| 会話添付名 | SHA-256 | アーカイブ内の所在・役割 |
|---|---|---|
| eject-single-window.cpp | `5f58f1c24f8a643c589124bad0b93d29c35d029a2c7d6ca9f2964726ff7b4bdd` | 初回 `baseline/eject-single-window.cpp`、第2回 `src/original-eject-single-window.cpp`。今回の比較基準 |
| anytime-controller.cpp | `901335c8d66b67da14cc6a57973c9a1184dee4c24c82c92c78c05c821fefec32` | 初回 `src/anytime-controller.cpp`。通常処理の予算予約 |
| column-mdp-anytime.cpp | `74178ac05b3f1dc9d53db3ca78878d2bb7fe856c024289f153ee8bddf25c48af` | 初回 `src/column-mdp-anytime.cpp`。時間制御＋列MDP |
| ahc074-research.cpp | `e2412bdfa4a6ea5fd6a2dafd8249bb5ea350ca5f041831f17f8c933cef4dd63b` | 初回 `src/research.cpp`。保存設計、MDP、重複を考慮した再割当て |
| batch-prefix.cpp | `561a0528b0ccc8fe0a53f8b8859c52659280f65b461f1f8fde7ceba366e92e2a` | 第2回 `src/batch-prefix.cpp`。前方紙の一括再挿入 |
| column-mdp-reuse-four.cpp | `0735e72de6e82651115bd806fbb0adcd4d58127ab67f061e09c6a69a162f635e` | 第2回 `src/column-mdp-reuse-four.cpp`。MDP＋旧商品紙再利用＋4系統後処理 |
| two-window-cap.cpp | `96aae2d95dc75e0f5911592210f92f6dc15e6e081829423d91b37b046f8a020f` | 第2回 `src/two-window-cap.cpp`。二窓capの試作 |
| ahc074-no-fallback-lab.cpp | `c2ac73a422cbfd54e28cea1f8d3dad78a24baacb0e2af0e8cbcfd60b6b981330` | 第2回 `src/research-lab.cpp`。各種試行・保存設計 |
| ahc074-eval.cpp | `9471fb7184dbd9ecc9b285d704e60cd505ccf055639394702c80a91d3669385c` | 両ZIPの `src/judge.cpp`。独自生成器兼独立チェッカー |

第2回ZIPにはさらに次のソースがある。

```text
src/baseline-no-fallback.cpp
  9c1940e83a3803e22c235a91d2870059f97a91ada880a44638f895df360c09ed
src/cap-portfolio-full.cpp
  524291ea06bbc2baefabe3540f36e707fa6bbb580b226ad69a8487f212fa46fe
src/cap-portfolio-light.cpp
  8149c16e4fdb8b8f444556c23285272d5a98490cf4294fa04c5c550b9970e56e
src/count-triples.cpp
  6cba18c04af6745d2ef631b2a6f54395a15d68df27dcbb5d15447e2fb0c137d4
```

`cap-portfolio-full.cpp` は異なる構造の候補を選ぶ第2回の方式。最終回に説明した独立初期値4設計の `design-portfolio.cpp` と同じではない。名前の似た別ソースを、0.4694%の評価済みソースとして代用しない。

## 確認できた報告書とCSV

| 元添付名 | SHA-256 |
|---|---|
| ahc074_report_ja.md | `bf81d3c87ec26fbfe9ccb0dd5c6df5ec6e675a7b4f582f014302b1fe57572580` |
| ahc074_no_fallback_report_ja.md | `7fccd4283cf4dcfe191b56e36dd9aecfc7fbb5927a492d38e382706e29912529` |
| ahc074_deeper_design_report_ja.md | `7c63df7e7c27c7baf1efa2deedb38756a6e477e96467e1bc42968484e7edf67b` |
| ahc074_no_fallback_paired64.csv | `11354f736e7b83c67e6ed83808fa7b1978abd486323eeb52bb67eac3c82e384e` |
| ahc074_no_fallback_summary.csv | `d1ac3c6c807b2230ef88c9b7445f5ef6a73d04640d9a6e64ea66ab5ee0e1789b` |
| ahc074_results_summary.csv | `90842fd5bf77c916c28f2d61685e49046887289a99a0e4e1c6f3ff3462461e5d` |
| ahc074_design_portfolio_confirmed_results.csv | `973d132c034e42e7ecd94350b7fef00726c642f92f0debc1bc8c7c5fe39b10d6` |

これらの数値は総合報告へ統合し、CSVは `results/` に収録した。最後のCSVの元ファイル名にはconfirmedとあるが、このPRでは証拠の状態を明確にするため `portfolio-reported32.csv` とした。元ファイルのラベルだけで今回の再現確認済みと判断しない。

## 最終回の成果物に関する重要な制約

以下は前回回答で案内されていたが、今回アクセスできた添付、既存ZIPの内容、および会話ファイル検索から実体を確認できなかった。

```text
design-portfolio.cpp
soft-pair-audit.cpp
seed-design-lab.cpp
ahc074_deeper_design_research.zip
```

最終回の残存報告書には、次のコンパイル失敗も記録されている。

```text
cc1plus: fatal error: /mnt/data/deep3/src/design-portfolio.cpp: No such file or directory
compilation terminated.
```

したがって、最終回のソースが今回ビルドできた、追加32ケースが完了した、過去32ケースの生ログから再検証した、という主張はしない。残存する集計は過去の中間実験報告として保存する。低手数のsoft-pair改善も未確認。失われた実装を復元した場合は、新しいソースhash・新しい同一ケース比較を取り、旧集計とは別に記録する。

## 今回の再検証の範囲

`audit_archive.py` は上記57MBアーカイブをhashで限定し、保存された独立C++チェッカーを一時ディレクトリでビルドする。64ケース×5方式の保存出力について可視性・表示・手数・hash・設計一致・fast_requestsを再確認する。スクリプト自身をこのアーカイブに実行し、320出力が全て通り、再計算統計が先行する再生検証と一致することを確認した。

これは新規ソルバー実行、公式Rust tester、Clangビルド、現在のmainとの成績比較ではない。元のチェッカーはGNU用ヘッダーを使うため、この監査の既定コンパイラはg++である。
