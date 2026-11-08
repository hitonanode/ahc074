# Task 8 — 1倍の設計予算を有効に使う

## 2026-11-08 10:28 JST — 開始

- 基準はlegal-tie-fast（比較対象はlegal-tie-fix）。CLAUDE.mdとSTATE.mdを読み直した。注文処理は変更しない。読むlegal-*はコミット済みの上記2ディレクトリだけ。
- 書込は新しいdcomp-*のみ。既存ソース・共有ファイル・trial_log・STATEは変更しない。コミットなし。固定回数のみで、時間不足の切替なし。
- 最初に基準設計165305をlegal-tie-fastで0–499・8列再生する。tabu停滞の診断と同じ反復数での修正を500件で比較し、別に設計各段を計測する。
- 次に同じ設計時間での2窓探索・独立annealなどの配分を試す。方向の最初の公平な比較で改善がなければ深追いしない。プロファイルで明瞭な対象だけ出力同一高速化を行い、GCC/Clangで確認する。
- 20:00までに最終確認と報告を終了する。良い候補は通常4解法×2000件の時間・スコア比較と、凍結した未見500件の8列再生を残す。

## 10:45 — 最初の通常比較とプロファイル

- 基準8列リプレイ: `20261108-102842_legal-tie-fast`、seeds 0–499、500件完了・WAなし。設計元は165305、注文処理はlegal-tie-fast。
- 停滞比較: `20261108-103125_{legal-tie-fast,dcomp-audit,dcomp-unstall}`、各500件完了・WAなし。auditのスコアは500件すべて同じ。unstallは通常列で +0.00339 ± 0.00365%、2/495/3。設計の変化は少数。8列リプレイ104249と詳細発動数を確認して採否を決める。
- プロファイル: `20261108-103133_dcomp-profile`、200件完了。seed0では窓の関係更新48%、matching23%（inclusiveのサイクル比）。annealのeval_holes、finishingのclimb/rematchが主。詳細窓計測 `20261108-104044_dcomp-profile-deep` を待つ。初期列順DPは約0.4–0.6msなので優先しない。プロファイラ自体の時間は高速化の根拠にはせず、24並列の通常compareで測る。
- 配分比較: `20261108-103318_{legal-tie-fast,dcomp-two-anneals,dcomp-two-maps}`。前者は独立な半分長のprefix×2＋各2枝、後者は窓から半予算×2。それぞれ合計8完成候補、anneal総反復数は元と同じ。通常比較完了を確認して、legal-tie-fastで8列再生する。
- 依存するリプレイはreplay_train.pyから標準runnerを順に呼ぶ。ビルドと集計は共有flock＋nice。学習用0–499以外はまだ見ていない。

## 11:12 — 方向別の判定と高速化

- 停滞: auditはGCCのstdout 500/500同一。長い停滞は7/500ケース、平均2590反復/450k（最大443572）、climb側0件。修正の新規lists1–7は `104249` 対 `102842`、+0.00018 ± 0.00133%、全8列 +0.00058 ± 0.00118%。改善なしとして終了。
- 深さと多様性: `104718`（two-anneals）新規 +0.04197 ± 0.02527%、`104942`（two-maps）+0.18218 ± 0.03041%。いずれも同程度の設計時間で悪化。最初の公平な500件・8列評価で止める。
- プロファイル: `103133` 200件平均、map 478.7ms、anneal 396.4ms、finishing 214.3ms、V 20.9ms、初期列順0.56ms。finishing内climb68.9ms/rematch90.2ms/穿孔42.0ms。計測オーバーヘッド込み。`104044` は詳細窓計測。両者のGCC出力は基準と200/200同一。貪欲matchingは有効辺の約85%を走査するため部分ソートは見送った。
- 窓の関係費用cache `104939` は500件同一でhelper_end -7.25 ± 2.23ms。ただし5解法比較 `105525` で +7.79 ± 2.21msとなり、容量・配置を変えた3案も +5.7〜26.1ms。短縮が安定しないので採用しない。gatherを通常ロードに変えるexpandも +1.58 ± 1.86msで不採用。
- 取っ手費用の正確な表引き `110024` は500件スコア同一だがhelper_end +35.0msで不採用。
- filler climbの現在のtarget/donor寄与保存 `105401` はstdout 500/500同一、helper_end -18.98 ± 2.27ms。再比較 `110326` でも -16.80ms。覆う範囲のmemo追加は合計-19.53msで、単独追加の差は小さい。Clang native `110743` では両者のstdoutが200/200同一。
- 先頭候補の上界で寄与更新を遅延する `110906` はスコア同一だが現在の単純な寄与保存より少し遅い。これ以上の複雑化は採否を慎重にする。
- 次: 短縮した約20msの再投資を `111044` で比較中。map470kかgopt165kの2案で、完成設計をlegal-tie-fastで8列再生する。現時点で未見seedを使った設定選択は一切していない。

## 11:20 — 再投資の判定

- 窓への再投資: map470kは `111350` で +0.02814 ± 0.03043%（新規7列）、gopt165kは `111537` で −0.00454 ± 0.01331%。改善なし。helper_end差は −7.25ms / +0.95msなので予算を増やした試験ではない。この2案を拡大しない。
- 最後に、現在の20ms短縮で払える安い9番目の仕上げを測る。既存8候補を保ち、holesを引き継いだ最良割当を追加で1回だけ穿孔＋後段rematch、V選択。新規列で改善しなければ、出力同一高速化だけを検証済みの選択肢として残して終了する。
- 採用する寄与保存は、Clang native stdout200/200も確認済み。GCC nativeも追加確認中。未見seedはまだ設定選択に使っていない。

## 11:38 — 小さな改善の積み重ね

- 9候補 `112115_dcomp-nine` / replay `112306_legal-tie-fast`: 新規7列 −0.00644 ± 0.00222%、全8列 −0.00767 ± 0.00220%、実列 −0.01622 ± 0.00534%。helper_endは基準fastより −6.70ms。小さいが2SEを超えたので、この方向を一段だけ延長した。
- 10候補 `112915_dcomp-ten-late` / replay `113054_legal-tie-fast`: 新規7列 −0.01093 ± 0.00265%、全8列 −0.01196 ± 0.00257%、実列 −0.01918 ± 0.00651%。helper_end +3.81ms。追加の10番目は穿孔なし・後段rematchのみ。9候補からの増分も −0.00448 ± 0.00140% と2SEを超える。まだ目標0.03%には届かない。
- filler climb寄与保存のGCC native確認 `112116` はstdout200/200同一。Clang nativeの200/200、通常GCCの500/500と合わせ、両コンパイラで保持を確認した。
- さらなる時間資金として、プロファイルで合計54.9msあるrematchのdonor/targetの確率多項式を完全キーで保存する1案を `113533` で測る。q更新ごとに世代を変える。最初の公平な時間比較で得がなければ延長しない。設定選択はまだ0–499だけ。

## 11:44 — 設定選択の終了、凍結検証へ

- rematch多項式memo `113533`: stdout500/500同一だが、climb-cacheからhelper_end +7.56ms。不採用。このキャッシュ方向は延長しない。
- 6本の短い枝を未仕上げVで4本に絞るsuccessive halving `113929` / replay `114155`: 新規7列 +0.00153 ± 0.01966%、全8列 +0.00502 ± 0.01949%、実列 +0.02948 ± 0.03524%。改善なし。仕上げ前Vによる選別は、短縮した枝の損失を明瞭には返せなかった。半深さの最初の公平な試験で終了する。
- 4解法の予算比較 `113748`（0–499）: ten-lateはjudge平均1.75507s、argon比1.10241、p99 1.91177s（fix 1.90007s）、helper_endはfixより +5.00ms。0.03%に届かない追加利得で時間上限も超えるため、追加候補をこれ以上増やさない。
- 訓練だけで選んだ最良の時間内オプションはdcomp-nine。sourceをFROZEN.jsonに固定し、通常2000件の指定4解法比較と500–999の8列再生を行う。設定選択はここで終了。0.03%に届く候補を見つけたという扱いにはしない。

## 11:54 — 凍結版の通常2000件

- 指定4解法の通常比較 `20261108-114412` 完了、各2000件・WA0、記録あり。dcomp-nineはlegal-tie-fix比 −0.0144609 ± 0.0027563%、338/1434/228。0.03%には届かないが、小改善は明瞭。外部負荷は平均0.142 core、最大0.599 core。
- source hashは凍結時の2969698026bbdb76c0d345d921480068edf14bad3480c6e15fd6dc1a476b8169と一致。最終ソースのClang C++23 nativeビルドも成功。設定は変えない。
- 未見500–999の基準8列replayを実行中。これに続けて候補を同じlegal-tie-fastで再生し、時間のpaired集計と報告書を完成させる。

## 11:58 — 最終確認、終了

- judgeモデル（同じ114412比較）: dcomp-nine平均1.750748842s、argon比1.089390635。p99 1.953238243s、最大2.140132100s。fixのp99は1.968160400s。同一seed差helper_end −5.96675 ± 0.99060ms。p99差−14.92ms、paired bootstrap95%区間[-46.19,+27.70]ms。時刻切替なし。
- 未見500–999・8列: 基準 `20261108-115258_legal-tie-fast`、候補 `20261108-115455_legal-tie-fast`。新規1–7 −0.00347475 ± 0.00249543%、全8列 −0.00412916 ± 0.00236712%、実列 −0.008709996 ± 0.00510561%。新規列は2SEに届かず、改善確定とは扱わない。実列のスコアは通常runと500/500同一。
- 通常2000件の分割: 0–999 −0.0124641 ± 0.0036929%、1000–1999 −0.0164577 ± 0.0040937%。すべて凍結後の確認。結果を見た追加の設定選択なし。
- 0.03%に届く候補は見つからなかった。成果は小改善候補dcomp-nineと、出力を変えず約17–20ms短縮するdcomp-climb-cache。tabu、予算分割、raw V選別、窓への再投資は初回の公平な試験で止め、候補追加は時間上限で止めた。
- REPORT.mdと再現スクリプトを作成。GCC/Clang確認済み、dv_candidatesは2000件すべて9、保存・再生一致、source hash不変。共有ファイルの手動編集・commitなし。ここで終了する。

# Task 9

## 2026-11-08 12:03 — 開始

- 基準dcomp-nineとTask8の全ソルバを凍結のまま保つ。追加・変更は新規dcomp-*、notesはTask9用の新規ファイルと本節だけ。注文側M1やcombo-m1-nineは読まず、注文処理はlegal-tie-fastのまま。
- 目標: 出力同一でhelper_endを15–25ms以上短縮し、既存ten-lateの10候補目を払う。固定反復数・時計の倍率・ログ・実験スイッチを保持。build/重い解析は共有flock＋nice、実行は標準runner、通常runを記録。
- Task8のprofileを再確認: column_move約260ms、内包するeval_holes約161ms。dirty groupを個別に分岐して省く案はTask3で遅かったので繰り返さない。差分配列の構築と評価を融合し、SIMDレジスタの寿命とstack往復を減らす案から測る。受理時だけ新countsを再計算する版も比較する。

## 12:23 — 最初の出力同一案

- `20261108-120548`、GCC既定・500件・24並列: fusedはhelper_end +7.65 ± 1.87ms、anneal +5.13 ± 0.83ms。deferredはhelper_end −1.50 ± 1.84ms、anneal −2.27 ± 0.82ms。両方スコア500/500同一だが、必要な短縮に届かないので延長しない。byte一致を別途集計中。
- 窓の互換一覧差分更新(livepairs、120857)、費用配列の非ゼロだけ更新(sparserel、121546)を測定済み、lock内集計待ち。直接bit packing(packrel、121724)、single同士の交換で不変な列費用の省略(singlecost、121935)、方向bitのSIMD直接展開(arcflags)も独立に測定する。
- 次は明瞭な短縮のある部品だけ組み合わせ、再比較で再現性を確かめる。最初のfused比較の外部負荷は平均0.23 core・最大1.18 core。既存ソースは変更なし。

## 12:32 — 約38msの短縮、再検証へ

- `20261108-122540` の500件: bitlive単体はhelper_end −7.87 ± 2.07ms、map −11.43 ± 1.81ms。疎な費用更新と組み合わせたsparsebitsはhelper_end **−37.76 ± 2.11ms**、map **−39.30 ± 1.81ms**。両方stdout 500/500 byte一致。外部負荷平均0.13 core、最大0.27 core。
- 単純リスト併合のlivepairsは+52.41ms、sparserelでも+18.75msだった。bitsetからの順序付き列挙で、予測しにくい併合分岐をなくすと改善した。direct packing −0.77ms、singlecost +5.77ms、arcflags +12.15msはいずれも採用しない。
- `dcomp-nine-fast`はsparsebitsと完全に同じソース。`dcomp-ten-fast`はその窓高速化と、凍結ten-lateの追加候補だけを組み合わせた。9→10変換を旧nineへ適用すると旧ten-lateと文字列単位で完全一致することをassert。窓以降のコードは、それぞれの親と完全一致（t9-source-audit.json）。
- 次: default GCC500件で再測定、GCC native/Clang native各200件の同一性。速さが再現すれば、指定4解法・通常2000件を記録して最終確認する。新たな探索・注文ポリシーは変えない。

## 12:39 — 凍結・最終比較開始

- 同一性: GCC既定500、GCC native200、Clang native200すべて親nineとstdout byte一致。ten-fastは旧ten-late(112915)の500件ともbyte一致。
- 123149再比較: nine-fastはhelper_end −25.46ms、ten-fastは−22.50ms（いずれもnine比）。GCC nativeではnine-fast −22.24ms。Clang nativeは出力同一だが+80.30msで、性能改善はGCC側に限定される。この差は報告に明記する。GCC/ClangともLOCAL_BENCHなしの提出形式でもビルド成功。
- `20261108-123401`の診断200件: first 9の完成DesignState全値、raw unit割当、RNG、cur/Vのbit表現が1800/1800完全一致。全件で選択は最初のargmin V。10候補目を選ばない175件のstdoutも完全一致、選ぶ25件はVが厳密に改善。
- 12:39:24にten-fastを凍結: SHA256 b30828b092bd40a0bd1164380046d6cf0b695a789874e37106a42b9c5ac10303、533860 bytes。指定4解法2000件 `20261108-123924` を--save-design付き、記録ありで開始。以後設定変更なし。
- 最終比較の後、nineの既存未見replay115455に対してtenの500–999を8列再生し、平均注文リストでの増分も参考確認する。依存関係をtask9_finish.pyで順に実行、重い集計はlock＋nice。最終が通ればそこで終了し、選別段の新実験には入らない。

## 12:50 — 最終2000件: 時間目標は達成、10候補目の得点増分は未確認

- `20261108-123924`は4解法各2000件・WA0、記録ありで完了。nine vs fixはTask8と同じ −0.0144609 ± 0.0027563%、338/1434/228。ten-fast vs fixは−0.0147087 ± 0.0032786%、430/1247/323。ten vs nineは−0.0002478 ± 0.0017422%、128/1747/125で2SEに届かない。
- judge平均: argon1.630006s、fix1.782543s、nine1.772792s、ten1.750662s。ten/argon=1.0740216。p99はfix1.960380s、nine1.940552s、ten1.941841s（nine比+1.29ms）。tenのhelper_end対応差はnine比−20.69596 ± 1.07578ms。10候補を払ってもnineより短いという時間目標は達成。
- 未見500–999・8列のten replay `20261108-124817_legal-tie-fast`を実行中。比較基準はnineの115455。追加候補の得点が改善したと通常比較だけでは主張しない。時間部品としてのnine-fast（出力同一）も残しており、注文側への時間再配分に使える。

## 12:52 — Task 9終了

- 未見500–999・8列 `20261108-124817_legal-tie-fast` 対nineの115455: 新規1–7 -0.0032976 ± 0.0014459%、全8列 -0.0030900 ± 0.0014001%、実列 -0.0016361 ± 0.0037719%。新規列の小改善は2SEを超えた。一方、通常2000件でnine比−0.0002478±0.0017422%は未確定であり、区別して報告。
- 最終p99: ten−fix = −18.54ms（paired bootstrap95% [-59.98,−2.25]ms）、ten−nine = +1.29ms（[-33.64,+20.01]ms）。平均judge 1.07402×argon、helper_end −20.70±1.08msで10候補を払った上でもnineより短い。end_sec平均1.544045s、p99 1.711994s、最大1.852230s、1.8/1.9/2s超2/0/0件。
- REPORT9.md、再現スクリプト、source audit、同一性JSON、from-dcomp-nine.patchを完成。GCC既定500/native200、Clang native200の出力同一、先頭9候補1800件の完全一致、旧ten-lateと500件同一、提出形式GCC/Clangビルドを確認。
- 凍結SHA、旧nine/ten-late/legal-tie-fastのSHA、最終run全件完了・record=true、保存設計replay実列500/500一致を再確認。M1統合は別担当へ渡す。任意の新選別実験は行わず、最終確認完了で早期終了する。

# Task 10

## 11-08 13:04 — 開始・コンパイラの条件を分離

- 目標: combo-m1-nineから通常2000件で0.03%以上、GCCのjudge平均≤1.10×argon、p99はcomboと同等以下、Clang nativeもcomboより遅くしない。
- CLAUDE.md、STATE.md、committed legal-notes/PROGRESS.mdを確認。M1既試行のcache拡大・部分canonicalize・取り出し無効判定は再試行しない。
- dcomp-combo-ten: Task 9のsparsebitsはGCCだけ、Clangでは旧窓探索。10候補目はten-fastの追加差分そのもの。注文処理はcomboのまま。以前の解法は変更しない。
- task10_run.pyは標準runnerのprepare/compileだけを拡張し、arm別コンパイラを正しくmetaに保存する。コンパイルはflock+nice、バイナリはruns内。評価・24並列・記録は標準runnerのまま。
- 次: comboのGCC native/Clang native500件同時比較、要求処理800出力の同一性、ten-fastとの設計一致。それと並行してpost_optimizeの実装を調べ、プロフィールで大きい試行評価に絞って高速化する。

## 13:20 — 基準と最初の出力同一高速化

- コンパイラの同時500件 `20261108-130056`: 同じcomboソースのClang nativeはGCC native比でhelper_end −74.43±1.69ms、req −21.50±1.28ms、end −95.87±2.31ms。Clangの平均はhelper1.016932s、req0.455420s、end1.487669s。既存の親自体が両コンパイラで199/500出力異なり、seed1は設計も異なる。コンパイラごとの親との同一性を基準とするか、ユーザーに確認中。新変更の検証は継続。
- `dcomp-combo-ten`: GCC通常500件 `20261108-130114` はcombo比helper_end −31.25ms、得点 −0.00356±0.00335%（未確定）。ten-fastの設計と500/500一致。固定設計200×4 `130439` はcomboと800/800 stdout一致。Clang native通常200 `130540` は旧窓経路でhelper_end +11.71±3.18ms、end +13.80±4.35ms。10候補の支払いをClang側でも回収する必要がある。
- `dcomp-screen-links` (`130508`, 固定200×4): 表示screenで作ったGのリンクを1回のspliceで再利用。800/800 byte一致、req −11.37±0.99ms。検証版も800/800一致（最終リンクと表示の検査不一致なし）。Clang検証を投入。
- 現在のprofile (`130508`): post_optimize423.7ms incl、evaluate280.2ms incl、filter71.7ms、replay64.0ms、next_cost63.8ms、canonicalize25.6ms。計測によるreq増分97.7msがあるので絶対値を通常版の時間とは混同しない。screen準備31,971回/ケース、表示で518,474試行を省く。
- 失敗は深追いしない: canonicalizeのgen_seen→cur=-1は800同一だがreq +0.33±0.99ms、2つのmemchrをAVX2で一括探索は800同一だが+2.65±0.94ms（`130711/130712`）。不採用。
- Clangのsparsebitsを分解 (`130904`, 診断100件): SIMD本体は450→397 Mcyclesと速いが、疎なlookupが95→267、valid列挙97→173で遅い。追加した間接indexループだけvectorize/interleave/unrollを止めて検証する。
- 次: screenの可換性を使った合法性再生の共有、候補sortで大きなStateを移動しない案、Clang間接ループの確認。採用できる短縮を合成した後に予算を配り直す。

## 13:53 — 約27msの注文短縮を両コンパイラで確認、追加資金を探索

- `dcomp-screen-replay`の確定ソース（未準備rankを参照しないガード付き）: GCC500×4 `133217` は2000/2000 stdout一致、req −27.48±0.55ms。Clang200×4 `132834` は800/800一致、req −27.07±0.96ms。Clangの元リンク版だけは−14.62±0.96ms。完全な旧再生で合法性・操作列・ラベルを検査する版も800/800一致。
- 失敗した出力同一案: neutral候補をindexでsort −1.73±1.00ms（`131225`、2SE未満）、gen_seen除去 +0.33ms、二IDのAVX検索 +2.65ms。除算のNewton＋FMA残差補正は0..256の全16,974,593組でGCC/Clangともbit一致、solverもGCC500/Clang200出力一致だがhelper_end +10.86±2.68/+9.84±3.62ms（`132826`,`133019`）で不採用。
- 窓の追加: Clangの疎な間接ループのvectorize等を止めても+76.17±4.67ms (`131908`)。費用/valid走査の統合はClang +54.90/+52.75ms (`132343`)、GCC +51.56/+7.15ms (`132508`)。いずれも出力一致だが採らない。Clangは元の窓経路を維持。
- ejectの上位2層を、常に3層目以下の未操作紙を除いた列で計算する案 (`133748`): 完全再生の検証を含め800/800出力一致、しかしreq −0.17±0.88msで効果なし。終状態memoを旧filler優先順の完全keyで呼出し間共有する案 (`134406`): 800一致、hitは24,358→27,883回に増えたがreq +1.38±0.83ms。両案とも深追いしない。
- 再投資A (`133211`, 訓練500×4、screen-replay比): alternate gap .25 / eject2は−0.01077±0.00085%、+27.97±0.59ms。gap .75 / eject2は−0.02817±0.00149%、+64.67±0.60ms。eject4にしても−0.02822%、+64.81msで実益なし。REPEAT_MIN=0は−0.00681±0.00094%、+22.63±0.64ms。最大の得は目標に近いが、特にClang側の資金が不足。
- 次: 幅6・追加候補8・rwf・短いgapでのshortlist解除・alternate gap .5を単独測定中。next_costのkeyについて、除外紙をすべて通過した後のsuffixをそのままコピーする出力同一案も確認する。まだ最終設定・最終2000件は凍結していない。

## 14:28 — 取り出し修復の共有とrematchの整数SIMD

- 再投資B (`134801`, 訓練500×4、screen-replay比): NW6 −0.002735±0.000489%、req +5.90±0.58ms; EXP8 −0.001268±0.000359%、+2.66±0.58ms; RWF −0.002800±0.000537%、+13.69±0.60ms; shortlistをgap .25に置換すると+0.009910±0.000833%、−11.55msで不採用。alternate gap .5は−0.019665±0.001217%、+46.21±0.57ms。
- 失敗した追加案: next keyの除外完了後memcpy (`135015`) +0.37±0.93ms、全16枚block直コピー付き−1.35±0.95msで未確定。表示Blockをwrong-color maskにする案 (`135426`) +1.63±0.93ms。どれも800/800 stdout一致だが採らない。
- 窓restrict (`140033`, Clang200) −2.25±2.61msで効果なし。64要素paddingは初回Clang−6.37±2.54msだが、500件再測定`140410`に外部負荷1.11 coreの警告があり時間の採否には使わない。GCC500 `140538` は500/500一致、−2.67±2.55msで未確定。
- canonical recordsを可換G＋1挿入のsuffix最小値/bitsetから作る案 (`140540`) は800/800一致、元canonicalizeとの検証も一致。しかしreq +4.43±0.94msで不採用。準備の費用を回収できない。
- `dcomp-eject-screen` (`141014` GCC200×4): 取り出しのanchor群でも共有再生を使う。800一致、req −3.01±0.86ms。さらに取り出しが既に構成したGと表示を直す区間を再利用する `dcomp-eject-known` はClang200×4 `141414`で800一致、req **−9.44±0.88ms**（screen-replay比）。完全再生によるリンク・表示・合法性・操作/ラベルの検証版も800一致。GCC500×4も評価済み、集計待ち。
- `dcomp-donor4` (`141438`, GCC500): rematch donorの修復可能handle集合だけを4 targetずつSIMD計算。確率多項式・加算順は同じ。500/500 stdout一致、helper_end **−16.32±2.71ms**。target側への拡張とClang同時比較を投入。
- next_costの再profile (`140829`, 100×4): key11.1ms、列内scan28.4ms、holes12.0ms、MDP11.3ms（計測版の値）。元のdouble途中和と整数状態を64/128枚prefixで保存する正確なcacheを検証中。
- 追加で検証中: ejectの区間が空な候補では残りのorderを構成しない、窓費用の無効要素を初期化せずlive一覧コピーを受理時に延期、Hungarianのway更新の4分岐をmask storeにする案。再投資はalternateの手数filter/上位1候補/1対1修復を訓練500×4で比較。まだ最終設定は凍結していない。

## 14:46 — exact短縮の合成を開始

- donorの4target整数SIMDを再確認: GCC500 `143356` −14.14±2.63ms、Clang native500 `142404` −8.43±1.60ms（helper_end、各500/500 stdout同一）。target側まで広げるhead4はGCCでdonorより約2.5ms遅く、Clangの差も小さいのでdonorのみを合成する。
- `dcomp-eject-known` GCC500×4 `142007`: screen-replay比req −10.32±0.57ms、2000/2000同一。空の修復区間では尾部を作らないgeometry (`142027`) はさらに−3.70±1.07ms、800/800同一。独立完全区間検証も一致。Clang版を実行中。
- next_costの正確な64/128 prefix (`141638` GCC200×4): req −5.76±0.86ms、800/800同一。全cache外れを旧関数で再計算したdouble bit検証も一致。Clang、64/160 checkpoint、cache容量と単一checkpointを比較中。
- Clangのvalid-only窓 (`142228`、500): loose +51.39±2.67ms、費用とbitsetを統合したunified +0.71±2.11ms、各500同一。Clangで採る根拠なし。GCCは追加試験。
- alternateの予算を絞る試験 (`141843`, 訓練500×4): gap .75全候補 −0.02817±0.00149%、+65.77±0.59ms。手数で絞るshort −0.01715±0.00106%、+44.88ms、上位1候補top1 −0.01873±0.00118%、+38.91ms、1対1修復one −0.00232±0.00205%、+58.86ms。oneは不採用、主軸は全候補。
- `dcomp-stack-nine`は窓GCC専用＋screen replay＋eject known/geometry＋next prefix＋donor4を合成し、候補数9で純粋な出力同一性を測る。`dcomp-stack-ten`は同じ短縮と10候補目を保存。`dcomp-stack-alt75`は9候補の時間をALT .75/eject2、NW6、EXP8に再配分。まず訓練500通常GCC/Clang同時比較で合成時の時間を確認する。最終設定はまだ凍結していない。

## 15:08 — 合成の通常500件、追加資金とALT frontier

- `dcomp-stack-nine` GCC通常500 `144454`: comboと500/500 stdout一致。helper_end −49.98±2.27ms、req −44.38±1.47ms、end −94.10±2.93ms。ALT .75＋NW6＋EXP8の同時比較は−0.03341%（訓練500）、helper −47.36ms、req +11.03ms、end −35.79ms。GCCでは余裕があるがClangが制約。
- Clang通常500 `145325` は全件完了・meta status ok・正のscore500件を確認。stack-nineのスコアは全件同点、ALT版は約−0.029%。単純な平均実時間ではexact版−44ms、ALT版+4ms。対応差とbyte一致は集計中。worker終了時のInterrupted tracebackがあるが、result.jsonのケース欠落・WAはない。
- Hungarian (`144645` Clang native500): mask版helper_end −7.79±1.64ms、blend版−8.73±1.67ms、各500/500 stdout一致。GCCはmaskが−13.60±2.48ms (`142734`)。合成の最終版ではGCCにmask、Clangにblendを使う候補を考える。
- prefix (`143415` Clang200×4): 64/128は−10.28±0.94ms、64/160は−8.17±0.89ms。各800同一、元の関数とのbit検証も一致。prefixのway増加/64checkpoint除去 (`144302`) はGCC−0.08/−0.86msで未確定。列MDP cache 64/128 (`144409`) も+0.18/−0.83msで未確定。どちらも追加追試なし。
- 窓valid-only unifiedのGCC500 `144740`: helper_end +0.06±2.36ms、500同一。Clangも改善なしなので不採用。元のGCC sparsebitsのみ残す。
- ALT gap1.0は訓練500×4 (`143744`) −0.03403±0.00162%、eject-known版比req +63.66±0.61ms。PLAN_LIMIT=3は2000出力同一、NS4は−0.000145±0.000095%、効果が薄い。slack.5は−0.002835±0.000500%、+8.54ms。gap1/1.25/1.5とgap1＋NW6/EXP8を、合成高速化版で再測定中 (`144941/144942`)。
- 残りの明確なprofile targetを2案だけ確認: VのDPはdp[lo]が増える位置だけを試す（元の全DPのbit/選択照合付き）。next_costの穴費用は各項が整数/1024で正確なので4項をSIMD計算し、一般の途中和には元の順で加える（元のnext_costとのbit照合付き）。Clangの数ms不足を埋める目的。新しい予算設定はまだ凍結していない。

## 15:31 — 採用範囲の得点、Clangの資金を窓sortで確保

- 最終予算の訓練500×4 `151147`: ALT gap1、width5は−0.03403±0.00162%、width6は−0.03695±0.00170%、width6＋EXP8は−0.03720±0.00170%。width6からEXP8への上積みは約0.00025%だけで2.8msかかり、採る価値が薄い。gap1.25/1.5は−0.03668/−0.03857%、req +73.5/+82.5ms (`144941/144942`) と高価。
- GCC通常500 `151716`: pure `dcomp-hole4` はcomboと500/500 byte同一、helper −61.52±2.12ms、req −51.05±1.32ms、end −112.83±2.62ms。ALT1/width5は−0.03625±0.00297%、end −51.59ms。ALT1/width6は−0.04099±0.00311%、end −46.24ms。
- Clang通常500 `152049`: pureは500/500同一、helper −4.14±1.36ms、req −51.49±1.30ms、end −55.90±2.11ms。しかしALT1/width5はend +6.50±2.00ms、width6は+11.55±1.94ms。GCCだけの余裕では採用しない。
- 穴費用の整数/1024 SIMDはGCC200×4 `150503` req−4.31±0.91ms、Clang200×4 `151125` −1.20±0.86ms（未確定）、各800 byte同一、旧関数とのdouble bit検証一致。V DPのstrict-rise省略 `150150` は全200出力・全DP検証一致だがdv_eval +1.20±0.21msなので棄却、深追いしない。
- **Clang窓sortの新しい資金** (`151728/151729`, 500): 安定radixの8+9bitを6+11へするとhelper −23.10±1.57ms、map −20.43±1.26ms、500/500同一。7+10はhelper−20.04±1.60ms、9+8は−3.72±1.54ms（map差は−0.58±1.15ms）。GCCでも確認中。6bit＋ALT1/width6の合成をClang500で再確認する。
- ソートレコードを費用17bit＋pair番号15bitのuint32へ圧縮する独立案 (`152702`, Clang500): helper −18.39±1.34ms、500/500同一。greedyでのみ16bitのu/v表を1回読む。radix6との効果の重なりを測る（6bit版を対照に32bit recordの6/7bitと、64bit recordの5bitを試す）。正確なsortだから設定によらず得点は同じ。最終2000件はまだ始めず、seed500以上は未使用。

### Task 10 / 15:52: 最終版の固定

- GCC sortの再測定 `20261108-154335`: radix7はhelper −1.620±2.526msで明瞭な改善なし、32bit/radix7は+42.231±2.837ms。GCCは既存の64bit/8+9を採用。Clangは32bit/7+10を採用（153241、64bit/6+11からさらに−4.443±1.379ms、500/500出力一致）。
- 拡大予算での旧実装対照checker: `153706` Clang、`153946` GCC。両方200×4=800/800 stdout一致、内部のリンク・合法性・double bit照合も不一致0。要求側tenのClang固定replay `151652` も800/800一致。
- `dcomp-combo-fast` は9候補・元の要求予算の完全高速化対照、`dcomp-combo-alt1` はそれにNS_ALTERNATE=1/GAP=1.0、alternate eject最大2回、NEUTRAL_WIDTH=6を加える。POST_CANDIDATES=6を維持。設定選別は0–499のみ。
- 最終sourceを15:50:48に固定。alt1 SHA256 `8fae7ff4cbfa331797ef8f3f6835cf6ad912f04fa5a94f3fa084e11a563f97c6`。ソートはコンパイラ別だが並び順・設計予算・要求予算は共通。残りはGCC nativeの同一性、Clang native500件、通常2000件、未見注文列の確認。

### Task 10 / 15:55: 最終 native 比較を通過

- 凍結版 `dcomp-combo-fast`: GCC native200 `155138` で200/200 stdout一致、helper −60.880±4.202ms、req −54.827±2.159ms、end −116.830±5.059ms。Clang native500 `155242` で500/500一致、helper −23.849±1.459ms、req −53.461±1.345ms、end −77.493±2.144ms。
- 同じClang500比較の `dcomp-combo-alt1`: score −0.034880±0.003278%、331/20/149。helper −24.303±1.384ms、req +11.316±1.404ms、end **−12.576±2.157ms**。Clang側でも再投資後に親より速い。
- LOCAL_BENCHなしの提出形式でGCC native / Clang native / Clang plainのC++23 -O2ビルド成功。バイナリは/tmp、直接実行なし。
- `task10_final_run.py` により凍結ソースの通常2000件4者比較（記録・設計保存あり）を開始。その設計の2000件一致を確認してから、同じcombo9設計の2000×4 replayを実行する。新規列1–3を別集計する。最終検証で設定は変更しない。

### Task 10 / 16:06: 通常2000件の最終比較

- `20261108-155517_{argon-des-perf-latew105,legal-tie-fix,combo-m1-nine,dcomp-combo-alt1}`、全arm2000件、WA0、記録あり。最終alt1はcombo比 **−0.035241±0.001661%**、1331/110/559。0–999は−0.035957±0.002253%、1000–1999は−0.034525±0.002442%、選別に使わなかった500–1999は−0.033323±0.001955%。legal-tie-fix比−0.070650±0.003305%。
- judge平均argon1.623486s、fix1.776826s、combo1.779743s、alt1 **1.742437s / argon比1.073269**。p99はfix1.958409、combo1.975643、alt1 1.979913s。comboとの差+4.269ms、paired bootstrap95%区間[−38.557,+31.836]ms（4000回）で、差は測定のばらつきの範囲。
- alt1のcombo対応差: helper **−57.837±1.145ms**、req +16.618±0.716ms、end −40.809±1.429ms、judge−37.306±1.629ms。end平均1.530021、p99 1.729219、max1.917520s、1.8/1.9/2.0超8/1/0件。外部負荷mean0.135/max0.464core。
- 親と最終版の設計は **2000/2000 byte一致**。通常run末尾のworker終了処理にInterrupted tracebackが出たが、親プロセスは正常完了し、全meta status ok・全result正の2000件・pahcer記録済みを確認。欠損したrunとして扱わず、根拠と確認を残す。
- `20261108-160428_{combo-m1-nine,dcomp-combo-alt1}`で上記comboの9候補設計を共用する2000×4 replayを実行中。新規列1–3はこれまで設定選別に用いず、実列0の再現も確認する。最終採用条件の通常比較とClang時間は通過。追加replayの記録・報告を終えて停止する。

### Task 10 / 16:12: 最終replay・停止

- 凍結後replay `20261108-160428_{combo-m1-nine,dcomp-combo-alt1}`、2000×4、全件完了・正のscore。全4列 **−0.035391±0.000833%**、新規列1–3 **−0.035441±0.000945%**（−0.0035527±0.0000948 moves/order）。未選別seed500–1999の新規列は **−0.035793±0.001077%**。新規列の改善も0.03%を超えた。
- DesignStoreの実列0再現: combo、alt1とも通常runと **2000/2000 stdout byte一致**。最終normal/replay/Clangすべてのstatus、件数、source hashを`t10-final-audit.json`に保存。最終ソースhashは凍結時のまま。
- `REPORT10.md`を確定。通常2000件の−0.03524%、judge平均argon比1.07327、p99差+4.27ms（95%区間は0を含む）、Clang native end−12.58±2.16msにより採用条件を満たす。以後の探索・予算変更はしない。最終候補は`dcomp-combo-alt1`、完全同一の高速化部品は`dcomp-combo-fast`。指定の10候補部品は`dcomp-combo-ten`に保存。
- 単独の小さいオプションとしてREPEAT_MIN=0、RWF、slack.5を報告したが、ALT版との組合せは未測定なので推奨版には足さない。コードサイズは指示どおり無視。no fallback、固定予算、共有ファイル編集・commitなし。
