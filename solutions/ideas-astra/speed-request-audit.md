# Task 15: 要求処理と出力同一高速化の監査

09:20 JST 更新。既存のファイルは編集せず、実行・コンパイルは親 agent が直列に行う。基準は `solutions/dcomp-combo-dual30/main.cpp`。以下の行番号は同ファイル。

## 優先候補

### 1. `ret-duplicate-skip` — 同じ返却モードの「採点」も一度にする

- 分類: 3（出力同一高速化）+4（古い前提）。試作 `solutions/ia-ret-skip`。
- 変更: `process` の options loop（8967–9002）、ret_mode=2 を `kTopPenalty==0` のとき省く。現状の RepeatedPlan は模擬だけを再利用するが、表示・filler到達性・plan_cost・record_future（mergeと再plan_costを含む）を再度行う。
- 根拠: adaptive_insert（5310付近）の mode1/2 の差は0の top penaltyのみ。mode2と全フィールド一致するmode1が先にあり、両collectorとbestの更新は厳密な `<`。同じ候補が一度 pool から落ちた場合も閾値は単調改善なので再挿入できない。mode2にはvalue_fillers/complete_valueがなく、weighted_rawの副作用もない。mergeはpathを変えるだけ、他の副作用は診断回数。
- 既往: trial_log 549 の colmdp-fast で模擬共有は導入済み。今回はその後の二重移動結合（Task11）の費用まで重複するようになった後の、残った再採点を省く。Task12のraw copy省略とは異なる。
- 予測: req −3〜15ms、設計へ戻した場合 −0.001〜−0.005%。単独採用床を狙う案ではなく、小改善の束の部品。出力同一なら固定反復スコア差0。
- 工数: 0.15h実装 + 0.3h検証。最安probeは固定設計100〜200件でstdout全byte一致と対応時間。Clang judge flags/GCC双方で200件、最終は通常2000件のbyte一致、対応速度差が2SE以上、他の部品と合成後も速ければ採用。
- probe: GCC固定設計200件 `20261109-091447_ia-ret-skip` はstdout200/200一致、WA0、req差 −2.828 ± 1.861ms。Clang judge相当（libc++/LTO/zero/native）の200件 `20261109-091731_ia-ret-skip` は200/200一致、req +1.504 ± 1.820ms。どちらも2SE未満で、現時点で高速化の根拠は得ていない。
- リスク: counters/cache履歴は変わる。cacheが正確なら出力へ影響しないが、全byteを照合する。将来kTopPenaltyを戻すなら条件を残す。

### 2. `endmemo-context` — 同じ filler 優先順の別 post pass で終状態メモを共用

- 分類: 3（出力同一高速化）。試作 `solutions/ia-endmemo`。
- 変更: EndMemo（7173–7182）、post_optimize_impl入口（7295）、合法性を通った後のmemo（7640–7700）、process入口（8858）。postごとの世代を、同じ注文内で同じ旧filler紙ID列に共用する。表の位置は最終順序のhash、衝突照合は全192byteで維持。
- 根拠: canonicalize（6678–6730）はtop_d/lvl/hiを再構成し、入力状態から参照するのは旧fillerの紙ID順のみ。今の終状態memoは全passで破棄されるため、別path・別passから同じ終状態へ至る重複を拾えない。whole-post memoは入力path全体一致だけなので補完的。
- 既往: Task11はmemoを可視性再生の後へ移し、Task12はwhole-post入力一致を追加。postをまたぐ、正確なcanonicalizeコンテキストは未探索。
- 予測: req −0〜30ms（未実測）、設計再投資 −0〜−0.009%。固定反復score0。context lookupとcache汚染で遅くなる可能性あり。
- 工数: 0.4h実装 + 0.4h検証。最安probeは旧local missのうち別passで既出な終状態の件数。試作は実際にmemoを拡張し `ia_endmemo_cross_hits` を出す。`IA_ENDMEMO_CHECK` で全hitを旧計算し、canonical records、到達性、charge/nextのdouble bit一致を検査。表128/1024を固定設計200件、GCC/Clangで比較。通常2000件byte一致、合成後対応速度差2SE以上。
- probe: check `20261109-091254_ia-endmemo` は100/100 stdout一致、全hitの再計算照合完了、WA0。GCC固定設計200件 `20261109-091447_ia-endmemo` は128表でreq +1.601 ± 1.942ms、`ia-endmemo-2` は1024表で +1.136 ± 1.752ms。cross-pass hitは3921/6011回/ケース。Clang judge相当200件 `20261109-091731_ia-endmemo`（1024）は +2.912 ± 2.051ms。各200/200 stdout一致、WA0だが速度利益なし。ここで打ち切るのが妥当。
- リスク: コンテキストには旧filler紙の「集合」でなく「順番」が必要。浮動小数加算と後続計画のfiller順を守るため。注文境界を超える再利用は禁止。可視性はpath依存なので一切省かない。

### 3. `generic-action-memo` — 汎用6枚の同じ (目標,初期順列) の操作を再利用

- 分類: 3（出力同一高速化）。未実装。
- 変更: Solver::set_generic（4686–4733）、init_lookahead（4740–4758）。通常穴集合の場合だけ、(u,s0)をkeyにbest到達順序と元Comparator::pathが返す操作列をlazy保存。order_indexはgeneric_biasと同じLehmer rankへ置換できるが、まずcacheだけを測る。helperの変則穴では既存経路を保つ。
- 機序: sat[u]/futureは設計固定後不変。複数候補が同じu/6枚順列へ戻り、最小distance探索とpath復元（各手M*M走査）を繰り返す。表を全256*720先行計算するのでなく、訪れたkeyだけ作る。
- 根拠: コードの純粋依存、過去imp-glaの同点規則（trial_log257）をそのまま保存できる。現在tail cacheは返却後の192枚全体一致のときだけ共有（6280–6320）なので、generic6枚だけ同じ別候補には効かない。REPORT8–12/READMEをgrepした範囲ではこのcacheの試行なし。
- 予測: req −0〜8ms、設計再投資 −0〜−0.0024%。上限は小さく、安いprofileで5ms未満なら打ち切り。
- 工数: 0.4h + 検証0.3h。最安probeはset_genericのcall数、異なる(u,s0)数、sat探索回数を100seed計数。試すなら固定設計200件GCC/Clang、stdout全byte一致、対応reqが2SE以上。最終は上2案と合成した通常2000件。
- リスク: M=6を固定配列にする場合はemergencyなどMが変わる経路を保つ。holes==gmask&~paper[ded[u]].opaque条件を満たす時だけ使う。bestのtie順を変えない。メモリ/初期化費用が得を消す可能性。


### 4. `record-cost-once` — 二重移動の結合で長さ不変なら再採点しない

- 分類: 3（出力同一高速化）。試作 `solutions/ia-record-cost`、親へ渡し済み。
- 変更: process::record_future（8932–8943）、`cost=plan_cost(ops.size())` を `if(ops.size()!=raw_ops.size())cost=plan_cost(ops.size());` にする。
- 機序・根拠: 全callerが同状態のplan_costを渡す（通常8989、chain9014、helper6928）。merge_double_movesはpathだけを変え、終状態・top_d・fillersを変えない。長さが不変なら元と同じ費用で、再計算が無駄。長さが変わる時は元関数を呼び、浮動小数の加算順を保つ。
- 既往: dcomp-t12-rawcopyはsave/restore/copyを減らす案で、再採点は残る（README「候補の順と費用計算は変えない」）。この1行の条件化は別の削減。
- 予測: req −0〜8ms、再投資 −0〜−0.0024%。工数0.1h実装＋0.3h検証。固定設計200件GCC/Clang judge flagsでstdout完全一致・時間差2SEを条件に小部品として残す。parentが後で実行する。
- 最安probe: 試作そのものの100〜200件比較。未実行。cache hit/missと診断call数のみ変わる可能性。
- 実装の次の候補: process 9051–9054、9070–9074、9090–9104、9127–9129にも同じplan_costの連続呼び出しがあり、stateを変えない区間でconst doubleにまとめられる。ただしまず最も明瞭なrecord_futureだけを測る。

### 5. `column-view-cache` — 旧研究に残る列内順のcacheを限定移植

- 分類: 3。今回未実装・低順位。
- 候補箇所: dual30 adaptive_insert（5270付近）、column_top（5625）、set_handle（5672）、restore（6731）とshift（5610）。192枚を繰り返し走査する所を列内順cacheにする。
- 既往: `solutions/astra-endval/fast.cpp` 2866–2958 は旧as6で同じ案を実装済み。REPORT.md67で64設計×4列の設計/手数/全内訳/合法性一致を確認。ただし正式速度測定も本流移植もない。現在はbyte order/memchrなので位置cacheは逆効果になりうる。列内viewだけに絞り直す理由はある。
- 予測: req −0〜25ms、再投資 −0〜−0.0075%。工数1.0〜1.5h＋検証0.5hで、時間に余裕がある時だけ。`restore`、top_d/filler変更、直接order代入の全てで失効が必要。
- 上限資料: 既存Clang profile `20261108-162556_dcomp-t11-profile` seed0はinsert inclusive21.43/exclusive16.55ms（63636calls）、plan_tail exclusive7.55ms。時計費用込みなのでそのまま節約量へは使えず、100ms級の案にはならない。
- 最安probe: 現行の列走査回数/走査長と部品のexclusive時間を100seed計数し、理想的に半減して5ms未満なら止める。今は上の軽い3部品を優先する。

## advice-1107-02 の要求処理に関係する部分

- §2の15比較窓保護を外すdecoder共同設計は新しいが、現行Comparator::complete/planと汎用層可視性の保証を丸ごと置き換える。2.5hの実装・2000case検証枠には入らない。少なくとも720合法状態graph、全商品satと最短path、ペア再選択、汎用費用と設計評価の整合が必要。旧一般印刷602種類は15窓保護だったので、科学的には未否定。
- §3の印刷+取出し兼務は未探索の組合せだが、変更紙の別商品でのアクセスとfiller価値・回収まで含めた実状態の反例が必要。数列模型だけで採用しない。現状の要求側を少し変える試作には落ちないため今回順位外。
- §4の異なる窓割当候補は設計担当へ。2本半予算はTask8で負けており、同じ提案をそのまま再評価しない。
- §5の比較器の分割・共有は助言自身の模型で合法移動が重く、新しい理由なしに試さない。

## 今回繰り返さないもの

- next_value cacheの1024化/compact化: Task12、GCC −1ms程度・Clang +0.6ms、確定利益なし。
- 小shiftのinline/同位置早期return: Task12でClang +3.94/+0.55ms。OOB修正は最終版に既に別理由で入る。
- 2紙の位置をAVX一括検索: Task10で+2.65ms。
- 表示/可視性等のscalar早期終了一式: argon-req-earlyscan、trial_log1054でreq+0.8%。
- canonicalizeを最終リンクから直接構成: Task10で+4.43ms。
- 既存探索幅の無条件拡大: Task11/12でほぼ0.02〜0.05%/100ms、安い設計時間との交換利益は小さい。slack.35は小さな有効部品だが既知案。
- 全計画の選択学習/将来モデル係数: near-tie以外はTask11/12で無益・悪化。再学習を単独の有望案とは数えない。

## 09:28 追加監査: cache key の過剰な区別

### `nextkey-normalize` — 次状態費用の filler 順・実質同じ水準を区別しない

- 分類3。試作 `solutions/ia-nextkey`。`IA_NEXTKEY_MODE=1` は末尾の `(paper,lvl)` だけsort、`=2` はさらに見せる不透明maskが同じ水準を共通keyへ、`=0` は親のkey。まだ未評価。
- dual30変更箇所: adaptive_next_costのキー末尾（5072–5092）、参照関数（4950付近）、stay_tableの構築（4875–4907）。
- 機序: 列内の紙ID列は加算順に必要なのでそのまま。現在のkey末尾はbelow-generic fillersをリスト順に入れるが、nextcost本体のfiller依存はextra/availableのbool設定とcoveredの要素ごとのmaxのみ。順序を変えても実際の演算結果は同じ。水準も `shown = h_opq[paper] & ~low_bits(lvl)` が同じならcover成分が同じで、actual recordを変えずkeyだけ正規化できる。
- 具体例: 紙のハンドル2,3が穴なら、その紙のlvl2とlvl4は同じshown mask。アンカー位置は違ってもnextcostの被覆率は同じ。従来は別keyだった。
- 正確性: filler_chargeは別計算で、こちらのkey正規化は触れない。浮動小数の非結合性を避けるためin_place部分の順は一切変更しない。`IA_NEXTKEY_CHECK` でhitでも元referenceを実計算し、double全bit一致を確認する。missでも既存NEXT_PREFIX_CHECKが照合する。
- 既往: next_value cache増量・縮小、4本hash、prefix、部分MDPcacheは試行済み。今回の順序/level同値類のキー化は未試行で、cache容量は変えない。
- 予測: req −0〜15ms（未検証）、再投資 −0〜−0.0045%。工数0.3h実装+0.4h検証。gainの上限は現在のcf_value_miss数、go/no-goは200固定設計のhit増分とGCC/Clang judge flagsの対応時間。各stdout全byte一致、check完走、速度差2SEを条件にstackへ。
- リスク: 追加sortの費用で逆に遅くなる、汎用層内外が違えば共有不可。above-genericは末尾から除外する元条件を保つ。代入するのはkeyのlevelのみ。

### 早期棄却下界を上位案にしなかった理由

- `moves + 0` 型の下界は、列内の重み付きdepthという不可避な数手を丸ごと落とすため緩い。鋭くするにはcanonicalize後の残紙集合と各列の最小depth/最低色修正費用を求める必要があり、計算量がnextcost自身へ近づく。
- 下界は単なるbest_scoreとの比較では不十分。evaluateは直接不採用の候補も中立探索へbest+.30または+.75まで保存し、value<best+1e-8ならmergeでさらに短縮する（7692–7790）。この副作用まで含めた安全な棄却が必要。
- 固定列MDPのFは非負でも、同じtype数の順列全体でminを取ると0になりやすく、安い一般下界の追加分は弱い。2.5h枠では上記exact keyの方を優先する。

## 09:30 追加レビュー: `mdp-types`（root 実装）

- 現行の `COLMDP_NEXTKEEP=1` では `colmdp_next_drop=0`。partial MDP が exact paper-ID keyとone_stepを計算する理由がなく、対応列のtype codeだけでFを取れる。rootの `ia-mdp-types` は通常scanへcode生成を広げ、非対応列をdecode前にskipする2箇所の変更。source差分を読み、妥当と判断した。
- **同案の既往あり:** `solutions/nogen-true-demand/README.md`、main.cpp4666/4904。11/06の別構造で背景列の需要が0になったとき、同じfull-or-drop0条件と非対応列skipを導入している。trial_log1272、同REPORT.mdの130407 runは需要修正との合成で、当該高速化単体の正式速度は測っていない。今回の新理由は、本流Task11のpartial-cacheが「one_stepのためpaper IDが必要」という旧条件を保持していたこと。
- bit同一性の条件: 対応列だけをc昇順に加算し、外側 `cost += term` のgroupingを保つ。対応列は≤14紙なので32bit leading1+2bit codeで一意、逆順rankは元のpartialと一致。非対応長列のuint32 overflowは定義済みで、そのcodeをdecodeしない。partialは元と同じ+0から開始（root実装済み）。デフォルトの有限・非負係数なら `weight*F - 0*one_step` は `weight*F` と同じ。
- prefix cacheが保存するmdp_codeも新しいmdp_scan条件に従い初回から構築されるため、古いmodeのentryが混ざらない。NEXT_PREFIX_CHECKのreference側は元のfull-only条件のままで、partialでは旧colmdp_next_termを独立対照にできる。scoreや速度の結論はrootのprobe待ち。

## SearchConfig 定数化の重複確認

rootから候補に挙がったSearchConfig全体のconstexpr化は、`solutions/deval-fixedcfg`で既に試行されていたため、指定どおり新しい`ia-static-config`の作成は止めた。`deval-seven-wide/REPORT.md:148` の `20261107-070201_deval-fixedcfg` はGCC200件、req差 **+4.516 ± 2.824ms**。stdout199/200一致、残る1件は当時の候補数の時間打切り差で、その他の出力差0。Task11の2bool template化より前に、全SearchConfig fieldをstatic constexprへ変えている。Clang judge flagsでの単体測定は当該表にないが、全体定数化を未試行案とは扱わない。

## SearchConfig: 再試験の限定理由と試作

rootが、旧GCC結果を現行へ転用できない理由を指定し、一度だけの再試験へ進む。新しい理由は、dual30でALT・追加親・whole-post memo等のhot branchが増え、最終judgeのClang/libc++/LTO/zero-initでは定数伝播・コード配置の効果が異なり得ること。これを受け `solutions/ia-static-config` を作成した。既往を無視した未試行案としては扱わない。

`IA_STATIC_CONFIG=1`（試作の既定）でsearch_env固定lookup/get/numberとSearchConfig objectをconstexprにする。各fieldのmode依存の初期化式はそのまま、直接getenv lookupするneutral設定も同じconstexprへ。`=0` なら親の実行時F3_*設定経路を保つ。設計のスイッチには触れない。生成のみ完了、コンパイル/評価はrootがGCC100・Clang judge flags200件で一度行う。利益がなければ終了する。

## 09:43 `generic-action-memo` の具体化と既往補足

追加grepで、`gpt6pro-09-01-legal-dist/main.cpp:2262` に旧Comparator::planの1entry memoがあると分かった。trial_log85の総合結果は他の設計改良との合成。本流imp-fastのREADMEではtail全体の共有だけを導入しており、imp-gla（trial_log257）以降のfuture/sat到達先選択にはmemoがない。従って完全な未試行アイデアではなく、現行へ移っていない既往部品を安く再評価する案として扱う。

`solutions/ia-generic-memo` に試作を作成。通常経路の `(u,holes,4bitずつ詰めた汎用順序)` を1entryだけ保持し、hitではlocal vectorの生成、order_index、sat探索、path復元、pathコピーをまとめて省く。大きな256×720表は不要。init_lookaheadで失効、例外の穴/M>16は旧経路。`IA_GENERIC_CHECK` は全hitの親操作列を再生成して完全照合し、`generic_memo_hits/misses`を出す。未compile/未評価でrootへ渡した。

予測利得は以前の0〜8msのまま。単体0.03%は狙わず、部品合成の候補。100件check、200件固定設計GCC/Clang judge flagsでstdout同一と対応時間を確認する。以前のClang profile seed0のplan_tail exclusive7.55msが上限の手掛かりだが、時計費用込み・run_jointも別なので真の速度上限とはしない。
