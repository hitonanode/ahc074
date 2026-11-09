**Task 15 — dual30への改善提案と安い検証（2026-11-09）**

**0.03%以上の改善を確認した案はありません。残す品質仮説は、既存の窓探索が保存した「異なる汎用窓集合のelite」を第4枝へ使う案です。** 候補の存在と窓目的値の近さは確認しました。完成設計への統合と得点の改善は未検証です。速度側では部分MDPと穴あけの無駄を減らせましたが、小さく、合成後の全実行時間では2SEに届いていません。

保存先：[IDEAS.md](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ideas-astra/IDEAS.md)。基準・行番号はすべて [dual30/main.cpp](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/dcomp-combo-dual30/main.cpp)。以下の±は1標準誤差、時間は倍率込みのpaired差です。GCC13.3とClang18.1.3で測定しました。Clangは `-O2 -std=gnu++23 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero`。ジャッジのClang21そのものではありません。ケース実行はすべて標準pahcer経由、100–300件、共有ロック下で実施しました。提出版の実装・既存ソルバー／共通スクリプト／trial_logの編集・commitはしていません。

**1. 順位付き提案**

順位は追加作業の優先度です。1は条件付きの研究案、2–3は合成用の小部品、4以下は今回のprobeから優先度を下げた案です。高速化案の固定反復スコア差は0であり、記載する改善幅は時間を探索へ戻せた場合の仮説です。

**1位 `different-map-elite` — 既に探索した別の窓集合を第4枝へ渡す。分類1：設計品質。**

- 機構・変更：`assign_windows` の `Elite`／`record_elite`（2165–2197行）を終了時2599行で保存し、共有prefix後の第4枝（10918行）へ1候補だけ渡す。主mapの探索量を減らさず、汎用窓とhandle窓の分け方が違う完成候補を作る。新しい座標でペア・列を修復し、元と同じ枝のanneal回数で仕上げる。`finish`（10716行）とrefinish（10929行）には枝ごとのComparatorとpermutationも渡す。
- 根拠：旧 `20261107-150327_deval-elite-branch/close` の500件では、8枠中、別集合が平均6.324個、500/500件に存在。現行の診断 `20261109-095836_ia-map-elites` も100/100件に存在し、平均6.26個。最良別集合の窓目的値差は **+0.00915±0.00090**、交換窓組数は **2.34±0.17**。seed0は目的値差0.0018662、5組交換。診断のstdoutは100/100一致、WA0。
- 既往との差：`elite-branch/close` は異なる窓集合を明示的に除外し、同集合のedge/polarityだけを使用した（trial_log:1552）。その効果は−0.0018/−0.0037±約0.004%。独立半予算2mapsの+0.18218±0.03041%（500件、新規7注文列、Task8 REPORT）とも違い、今回は窓探索を分割しない。
- 期待改善：**0〜0.05%を狙う仮説域。得点の予測としては未成立で、悪化もあり得る。** 既存候補の数だけから0.03%を約束しない。統合のpaired時間は未測定。新グラフ初期化の旧実測はClang約5ms（SHARES13.md、20261108-231826）で、修復込み追加5–15msを仮置きする。診断版のend差−2.58±7.52msは統合の費用ではない。
- 工数：統合全体は1.5–2.5時間の見積り。ただし今回の診断コードからelite保存・物理handle対応・不適合判定を流用できるため、残り実装1.2–2.0時間＋評価0.3–0.5時間が目安。2.5時間枠の上限に近い。
- 最安probeの結果：`20261109-100609_ia-map-repair-audit`、100件でstdout全一致・WA0。最良別集合へ移す際、比較不整合pairは平均8.50、新handle異色pairは2.19、解放unitは23.63、商品は **37.33±2.79**。解放商品の中央値27、90%点71、最大144（seed27）。窓cost差≤0.02かつ解放48商品以下の別候補が84/100件にある。修復規模は試作可能だが、修復成功率と品質は未実証。seed0は13pairが比較不整合、8pairがhandle異色で、重複を除く解放対象は40unit／62商品。
- 評価：まず通常100件で修復成功率、変更したunit数、完成V、候補選択率、時間を確認。修復費用が15msを大きく超える、または良い完成候補にならないなら中止。通過時はdual30先頭の通常compareを500件ずつ、最大2000件。最終採用はlog比が−0.03%以下かつ改善が2SE以上、時間版でも悪化しないこと。設計を変えるので `--design-from` だけでは判定しない。
- リスク：共通prefixの最適化を壊すこと、修復のための列単色化、座標の取り違え、refinishのframe混在。完成候補を増やすだけの追加計算案へ変質させない。

**2位 `mdp-types` — 差引き係数0なら部分MDPも種類列だけで計算。分類3・4：出力同一高速化／古い前提。**

- 機構・変更：`adaptive_next_cost` の5112・5217行、`colmdp_next_scanned` 5420行。既定の `COLMDP_NEXTKEEP=1` ではone-step項に最後に0を掛ける。紙ID列とその費用を作る必要がないため、対応列だけ種類列cacheを使う。全列版／部分列版はtemplateで分ける。試作は [ia-mdp-types](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ia-mdp-types/README.md)。
- 根拠：固定設計200件中、部分MDPの25件でreqが **GCC −38.01±7.56ms、Clang −21.83±6.17ms**。全体平均は−3.42±3.07／−4.05±2.57ms。通常Clang200件では **−5.60±2.43ms**。CHECK100件と各比較のstdoutは全件一致。run-idは後述のG1/C1/N1。
- 既往との差：`nogen-true-demand` に同じ条件分岐がある（trial_log:1272）が、別の需要模型との合成だった。本流のpartial-cacheには「one-stepのため紙IDが必要」という前提が残り、この部品単体の現行Clang測定はなかった。
- 期待改善：時間再投資で0〜0.003%程度。固定反復は0%。工数0.2–0.4時間。対象条件への高速化は確認したが、単独で0.03%には届かない。
- 評価・最安probe：`NEXT_PREFIX_CHECK`付き固定設計100件は完了。合成する場合のみ固定設計500件、さらに通常2000件を500件単位で出力一致・時間確認。採否は全体時間と合成全体の得点で決める。リスクは加算順、+0/−0、32bit種類列の長さ、非zero差引き設定を誤って短縮すること。

**3位 `perf-lazy` — 穴あけで不変の紙・行・列を計算しない。分類3：出力同一高速化。**

- 機構・変更：`Perforation::refresh_cache` 9711行、`total_profit` 9759行。変更紙以外のhead署名を再計算せず、非owner同列・dirty sampleなしの行をgeometry構築前に飛ばす。穴追加時の旧owner geometryは変更handleの1列だけ作る。試作は [ia-perf-lazy](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ia-perf-lazy/README.md)。
- 根拠：通常200件N1でstdout全件一致。finishは **GCC −10.72±0.64ms、Clang −5.51±0.81ms**。一方Vは+0.77／+1.12msとなり、Clang endは+1.61±4.80msで短縮未確認。段の短縮を全体の短縮と取り違えない。
- 既往との差：`deval-geometry` のsample間共有、`deval-perfsparse` の差分DP更新が入った後も、変更sampleがない行のgeometry等を作っていた。その残りを省く。
- 期待改善：0〜0.002%程度。工数0.2–0.4時間。最安probeの通常GCC/Clang200件は完了。以後は単独延長せず、合成した通常2000件で出力一致・全体時間・時間版の得点を確認する。リスクはownerをskipすること、穴の復元にも1列だけの旧geometryを使うこと、将来の複数穴同時変更へ誤用すること。

**4位 `generic-action-memo` — 同じ目標と汎用6枚順序の操作を再利用。分類3。**

- `set_generic` 4689行と `init_lookahead` 4739行に、商品・穴mask・6枚順序の1entry cacheを置く。到達先選択とpath復元を省く。試作 `ia-generic-memo`。
- C1で平均2590hit／569miss、82%hit、stdout200/200一致。ただしreqはClang −2.65±2.44ms、通常GCC N1でも−0.95±2.45msで利益未確認。旧 `gpt6pro-09-01-legal-dist` のplan memoの類例はあるが、imp-gla以降のfutureによる同点選択込みの経路は本流に未移植（trial_log:85,249,257）。
- 期待改善0〜0.002%の小部品、工数0.2時間。最安probeは実施済み。追加するなら `IA_GENERIC_CHECK` 100件の後、固定500件でClangが2SE以上速いことを要求し、合成通常2000件で確認。現状は見送り。sat/futureの更新時の失効、offsetをcacheへ混ぜないこと、同点の最初の候補を変えないことが注意点。

**5位 `future-key-normalize` — 同じ被覆を作るfiller記録を同じcache keyへ。分類3。**

- `adaptive_next_cost` 5072–5092行でkey末尾のfillerだけ紙ID順へ整列し、水準を最初の不透明窓へ正規化する。実状態と列内紙順は変えない。`stay_table` 4875行の依存はshown maskだけ。試作 `ia-nextkey`、`IA_NEXTKEY_MODE=2`。
- G1ではcache missが119596→114408、4.34%減った。CHECK100件・GCC/Clang200件で全出力一致。ただしreqはGCC +1.97±2.66ms／Clang −0.80±2.53ms。過去のcache容量・hash・prefix調整とは違う同値keyだが、sort費用を回収できていない。
- 期待改善0〜0.002%、工数0.3時間。最安probeは完了。再開するならsort不要の同値keyを先に作り、固定500件で2SE以上短縮→合成通常2000件。現実装は見送り。filler_chargeとの混同、汎用層の上下、浮動小数加算順の変更がリスク。

**6位 `record-cost-once` — 操作結合で長さ不変なら再採点しない。分類3。**

- `process::record_future` 8932–8943行。callerが渡した費用を使い、`merge_double_moves` 後に長さが変わった場合だけ再計算する。終状態は元と同じ。試作 `ia-record-cost`。
- G1/C1の各200件で全出力一致、reqはGCC −2.77±3.11ms／Clang +3.67±2.51ms。Task12のraw-copy削減は費用計算を残した別案だった。こちらも速い証拠なし。
- 期待改善0〜0.002%、工数0.1時間。最安probeは完了。9051–9054等の連続plan_costもまとめる場合に限り固定500件を再測定し、速ければ合成通常2000件。現状は見送り。長さが変わる場合の費用を差引きで済ませると加算順が変わるので、元関数を呼ぶ。

**7位 `extra-mask-lazy` — 通常SIMD経路で未使用の除外配列を作らない。分類3。**

- `adaptive_next_cost` 5055行の `extra[192]` を例外scalar経路内へ移し、`colmdp_next_partial` 5454行の未使用引数を除く。検査用には別に構築する。試作 `ia-extra-lazy`。
- G1/C1各200件で全出力一致。reqはGCC −4.19±2.80ms／Clang −0.53±2.72ms。既存NOINITは配列初期化を省く別の対処で、この案は設定loopと配列自体を通常経路から除く。ただし現行finalへの追加利益は別途必要。
- 期待改善0〜0.001%、工数0.1時間。最安probe完了、速度利益未確認で見送り。finalのNOINIT込みで固定500件の2SE短縮が出た場合だけ合成通常2000件へ。例外role配置とCHECKの配列を消してしまうことがリスク。

**8位 `static-search-config` — 固定設定をコンパイル時定数へ。分類3・4。**

- `search_env` 6959行、`SearchConfig` 6973行、直接読むneutral設定をconstexpr化。試作 `ia-static-config`。不要な探索分岐を定数伝播で消す。
- `deval-fixedcfg` は既試験でGCC200件+4.52±2.82ms（20261107-070201）。再試験した新しい理由はdual30のhot branch追加とClang/libc++/LTO。今回G1/C1は全出力一致、req −3.15±2.54／−1.39±2.85msで再び未確認。
- 期待改善0〜0.002%、工数0.2時間。最安probeは完了、これ以上の単体再試験は勧めない。別変更で構造が変わって再開するなら両compiler固定500件→合成通常2000件。環境設定を黙って無視すること、Clang専用prefix既定値、コード肥大がリスク。

**9位 `inline-moves` — 短い操作列の動的確保を減らす。分類3。**

- `Solver::Moves` 4571行を16操作までinline、長い列はvectorにする。copy/move/resize/appendの意味を維持。試作 `ia-moves-inline`。既存のFillerList小配列とは対象が違い、このMoves容器の現行測定は見つからなかった。
- C1/N1で各200件の全出力一致。Clang req +1.38±2.48ms、通常GCC −1.07±2.79ms。alloc削減と、pair配列の初期化・candidate sortでのcopy増が相殺した可能性がある。
- 期待改善0〜0.002%、工数0.5時間。最安probeと境界レビューは完了、現実装は見送り。容量変更だけの再掃引は勧めない。新たなallocation profileで十分な上限が出た場合に固定500件→通常2000件。自己範囲のinsert、overflow後の再利用、vector moveより高いcopy費用がリスク。

**10位 `perforation-screen` — 穴あけの事前棄却が本当の目的値を落としていないか。分類1・4。**

- `Perforation::run` 9944行の単独利益screenを影で全評価する。区間DPの代替donorとowner補正があるため、単独利益差が厳密な棄却上界とは限らない。試作 `ia-perf-screen`。
- `20261109-092025_ia-perf-screen`、100件でstdout全一致。114420棄却中138件、63seedで受理可能な変更が漏れ、11件は穴の復元。選択済み候補で漏れた模型gainの和は平均0.000141手/注文、約0.00141%相当。9候補の最大をseedごとに選ぶ指標でも約0.00784%。これらは探索経路と重複を無視した規模で、得点の上限ではない。
- 既往の2pass・複数穴・sample調整（trial_log:371,930–1008）とは違う棄却規則の監査。漏れ自体は発見したが小さい。期待改善0〜0.01%の仮説、影評価のGCC finish費用+10.55±1.12ms、Clang未測定。工数0.5–1.5時間。
- 最安probeは完了し、今日の追加実装はno-go。再開するなら `IA_PERF_SCREEN_BYPASS=1` の通常100件でVと費用を先に確認し、その後通常500→2000件。利益が費用を回収しなければ止める。cache_dirty・owner条件付けと探索経路変更がリスク。

**2. 上位3案の実装手順**

**different-map-elite**

```text
assign_windowsを元の予算で実行
  → poolからgeneric集合の違うeliteを保存（探索中のpoolは変更しない）
主Designで共有prefixを元どおり実行
第0〜2枝は元どおり
第3枝:
  e = 別集合eliteの窓cost最小（同点は交換窓組数、pool番号）
  old physical handleが新mapでもhandleなら同じ列に残す
  失われた列に新handleを昇順で割り当てる
  eのgeneric/pol/whichからA、Comparator、permutationを再構築
  新座標で不適合なpairと、handleが替わる列の全unitを解放
  LnsMatching/lns_repairを使い、71対と各列両色を修復
  第3枝の元の後半2区間だけanneal → finish → V
bestのrefinishでは、bestのedge/polarity/permutationも復元
```

診断の保存・座標対応・不適合判定は [ia-map-repair-audit](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ia-map-repair-audit/README.md) から流用できます。修復の移植元は [lns-star-study/main.cpp](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/lns-star-study/main.cpp:4094) のLnsMatchingと4134行のlns_repair。既存処理の `handle=old.handle` は新座標用に直す。最初は1elite、追加の前半annealなし、候補数増加なし、最良窓cost順だけで選ぶ。全8eliteで32640対ずつ初期化しない。cap63は固定。Designだけ取り替えてfinishの捕捉したComparator/permutationを残す誤りと、warm穴を別frameへ持ち込む誤りに注意する。修復・座標・refinishの正しさを先に確認し、100件の小さい得点差で採用しない。

**mdp-types**

```cpp
mdp_scan = colmdp_next && (all_columns || colmdp_next_drop == 0);
// 元の列順・紙順のscan中に leading-1 + 2bit/type のcodeを作る
if (mdp_scan)
    cost += all_columns ? scanned<true>(codes, cost)
                        : scanned<false>(codes, cost);
else
    cost += original_partial(...);

// scanned<false>: term=+0; c昇順、!colmdp[c].okはskip
// scanned<true>: 元の -drop*cost から開始
// 各列のF取得は既存の正確な16entry code cache
```

対応列だけdecodeする。長い非対応列のunsigned codeのwrapを使ってはいけない。非zeroのdropは旧経路へ残し、加算の括り方も維持する。`NEXT_PREFIX_CHECK` は元のpartial式を独立対照として全bit比較できる。差分は小さいので、時間版へファイル丸ごと置換せず、既存のpacer・NOINIT・境界修正を保持して移す。

**perf-lazy**

```text
total_profit(k): opacityが変わるのはkの1bitだけ
  non-ownerで同列ならdirty=0
  otherwise: kだけのbefore/after署名を比較
  non-owner差分loopは owner または dirty_samples==0 を先にskip
refresh_cache(!all): dirty sampleなしならgeometryを作らない
owner補正:
  穴追加 → old_geometry[changed_handle]だけ作る
  穴復元 → 元どおりold_geometry全体を作る
```

整数DPとownerのdouble加算順は変えない。old_geometryを部分構築する条件は「穴追加」に限定する。新しい複数穴operatorと併用するなら、1紙1bit差という証明を再確認する。

**3. probeの読み方と、合成の結果**

固定設計は `20261108-224255_dcomp-combo-dual30` を使用。各比較は同じcompilerのdual30に対する値です。

|記号|run-idと条件|
|---|---|
|G1|`20261109-093426_*`、GCC、固定設計200件|
|C1|基準・nextkeyは `20261109-094534_*`、他候補は `20261109-094535_*`、Clang、固定設計200件|
|N1|`20261109-094911_*`、通常200件。GCC基準はdual30、Clang基準はdual30-2|
|S1|`20261109-095348_*`、未使用seed200–499の通常300件。GCC基準はdual30、Clang基準はdual30-2|

S1の `ia-speed-stack` はmdp-types＋perf-lazyだけを合成した固定反復の試作です。**両compilerで300/300 stdout一致、WA0、得点差0±0%、勝/分/敗0/300/0。** 時間は次のとおりでした。

|compiler|finish差 ms|V差 ms|req差 ms|end差 ms|
|---|---:|---:|---:|---:|
|GCC|−9.28±0.53|+0.77±0.14|+1.08±1.95|+3.08±3.96|
|Clang|−3.67±0.56|+1.03±0.14|−3.08±1.97|−5.76±3.24|

GCCではmapが+9.17±3.14msとなり、仕上げの節約を相殺しました。Clangの全体短縮も2SE未満です。**この合成を「確認済み高速化」「0.03%に達する合成」とは扱いません。** 単体の段ごとの節約を足した値も採用根拠にしません。G1/C1/N1/S1の外部負荷は平均0.337/0.377/0.268/0.167コアで警告基準内。別のClang焼きなましprobe `20261109-092248_*` は平均1.55コアのため速度判断から除外しました。

次担当の2000件確認は、1run最大500件を守って4分割し、全seedのlog比から平均・SEをまとめます。出力同一部品だけなら固定反復の得点差は常に0なので、得点改善の採否は時間管理版への移植・時間再配分後の通常比較が必要です。

**4. advice-1107-02を構成ごとに判定**

|構成|既試験／残る新条件|今日の2.5時間枠|
|---|---|---|
|15保護を外す602印刷|`free-code` が実施済み。seed24–27、元開始8条件は改善0、均衡／乱数開始は+1.040/+1.323手/対。trial_log:361。設計元 `20261103-033246_as6-canon` の模型研究で、正式runではない|見送り|
|商品対・証拠順序・印刷の交互最適化|`latent-code` が24条件、各10k反復で実施。最良差0〜+0.03859手/対、改善0条件|見送り|
|5辺の比較木だけ保護|その限定条件は未確認。残り33窓も制約を作るため木だけで71対の実現は保証されない|合法距離・helper・設計の統合に6–12h以上の見積りで不適合|
|実可視性の720状態合法グラフ|free-code／latent-code／sparse-sixで既試験。sparse-sixの500件は+0.03517±0.05378%、250/0/250（20261104-012947）|新しい理由なし|
|2–4窓の一般印刷、12保護|astra-decoderに既往。12保護＋窓交換の模擬は−0.1240±0.0440%だが選別後の独立検証なし|統合費用が重く、今回の数字だけで復活させない|
|実192枚で印刷＋操作を局所共同合成|回収・他列filler利益を含むこの限定条件は未確認。小型非三角moduleは既試験で負（trial_log:365）|まず成功例の合成が必要。4–10h見積りで不適合|
|独立な窓設計を複数作る|追加予算なら改善。同予算2mapsは悪化|そのまま再提案しない|
|既払eliteの異なる窓集合を使う|同集合eliteは既試験。異集合を除いていたことと今回の候補計数が新しい根拠|上記1位のみ条件付き。統合＋検証は時間枠の上限|
|比較器分割・共有頂点・7枚目・補修紙|既往か助言自身の実合法距離実験で費用増|見送り|

助言全体を未検討として再実装することは勧めません。今回残したのは、中心の602印刷ではなく、異なる窓集合のeliteを既存探索から取り出す限定案です。

**5. 検討して見送ったもの**

- 別post間の終状態memo共有：cross hitが3921–6011/ケースあっても、表1024でGCC +1.14±1.75／Clang +2.91±2.05ms。各200件全出力一致、`20261109-091447_ia-endmemo-2`／`20261109-091731_ia-endmemo`。
- ret_mode2の重複採点省略：GCC −2.83±1.86／Clang +1.50±1.82ms、各200件一致、同prefixの `ia-ret-skip`。速度利益なし。
- annealの不可能列早期棄却：GCC100件−2.35±2.02msで確認できず、`20261109-092025_ia-anneal-reject`。
- annealの不変8lane群skip：GCC100件+10.46±2.26msと遅い、同prefixの `ia-dirty-groups`。
- tabu freeze解放：Task8で500×8注文列、未見列+0.00018±0.00133%、7/500件だけが対象。trial_log:1676。
- reset demandの毎手更新：reset-exactに既往。trial_log:369。
- cap窓の入力依存選択：既存2000件で利益なし。trial_log:1338–1342。
- Vの再学習・間隔模型・late前の追加候補：既往の独立検証で改善が小さいかなし。trial_log:1419–1443、Task5 REPORT。
- 9候補finishで巨大な不変表を毎回再構築している疑い：Comparator距離、MDP、Interleaveは最終選択後に1回、VのPoset/Sobolも共有済み。100ms級の重複は見つからなかった。
- singleton Hungarian行の共有：高価なtarget値は既cache。残りは0–2ms規模の未実測案で、今回は実装しない。

詳細な証明・既往・集計は [設計監査](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ideas-astra/design-audit.md)、[設計速度監査](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ideas-astra/design-speed-audit.md)、[注文処理監査](/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/solutions/ideas-astra/speed-request-audit.md) と同ディレクトリのJSON／logに保存しています。全試作は `solutions/ia-*/` にREADME付きで残しています。
