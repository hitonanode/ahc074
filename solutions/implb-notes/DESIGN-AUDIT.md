# stack1 設計モデル定数の監査（実装B、2026-11-09）

更新: この表と16版screenは11:35時点のstack1を対象にする。12:25相当のユーザー更新でcovered_gain返却0.8は撤回され、以後の基準はsolutions/d30a-reset6（返却0.6）になった。screen通過のheadreset=6とperfreset=6だけを、新基準で再評価する。

基準は solutions/d30a-stack1。A担当の reset_strength=6、covered_gain の返却0.8、その勾配・穿孔DPへの展開（fret-full）、V の fitted coefficients は変更しない。新しい時計・打切り・fallback は加えない。以下の行番号は変更前 stack1/main.cpp。

## 実際の注文処理との対応

`20261109-104153_d30a-stack1` の2000件を `scripts/observe.py stats ... --attr role --cross role` で集計。全文は stack1-stats.txt。誤表示0、10.013手/注文。dig 2.840、fix 1.483、fret 1.241、gen 1.214、lift .906、repair .694、ret .663、fill .411、relevel .215、fdig .147、reuse .097、help .075、hdig .026。generic紙の移動1.248、pair紙6.739、single紙2.026。後処理削減3471.48手/ケース、secondary削減152.60。model_col 2.94864、model_hole 3.77512、model_gc 1.36075、dv_best 10.0384。

モデル項と最終操作ラベルは一対一ではない。例えば穴直しはfixだけでなくrepair/fill/fdig/fret等にも分散し、後処理が複数段の操作を消す。したがって平均値の比をそのまま係数に代入せず、介入によるpaired V/得点で検査する。

|場所・定数|注文側でモデル化する量|現在のずれと判断|
|---|---|---|
|2674,2752 kHoleWeight=.38、4倍した有効係数1.52|独立な先頭色の不一致を直す限界手数（約2*.38=.76/不一致）|複数filler、helper、後処理で共有される。全体の修復手数と直接一致はしない。上下screenする。|
|2692 reset_strength=6|商品返却が列先頭色を多数派に戻す頻度|Aが検証済み。変更禁止。|
|2736–2750 colcost: least_depths2*.5、同色pair補正2、違反罰1e5|pair需要2・single需要1で重み付けした掘り出し深さ、両色先頭の制約|モデル2.949対dig2.840。reuse/後処理や動的挿入で回避可能。総倍率のみscreen。需要2・両色制約は構造的なので維持。|
|2764 gc: pairの平均費用*2、2817 gcost表|一様な汎用層順序から両商品を作る平均操作数|pair需要2は構造的。実際gen1.214、generic紙1.248に対してモデル1.361。補助紙・積み残し・後処理によるずれ候補。表全体の倍率をscreen。|
|2818,2833 initialize .65*handle差+2*gcost+.04*全差|ペアの穴修復・汎用層費用・模様距離の正則化|後段のannealとVで大きく再最適化される初期値。map側の.5とも不一致だが初期値だけの効果は弱いと判断し今回はscreen対象外。|
|2888 initialize cap/(c+1.5)、2905 leftoverの.5/.5/3|列サイズの深さ依存と色均衡、初期掘り/穴費用|静的初期値。最後の3は色均衡の強い経験罰。後段で可変なため優先度低。|
|2675,3718,10912 climb proxy=.5|列先頭の最良fillerが将来減らす修復手数|covered_gainの返却0.8とreset6で基準目的が変化。proxy平均.411→.415、採用17.45回。旧最適値をscreen。|
|3607 climbの先頭色reset=2、3853/3885 ProbabilityHeadのstrength=2|返却後の列先頭色の定常確率|コスト側reset6に対し確率側2が残る。1.4と6をscreen。A担当reset_strength自体は変更しない。|
|10734/10866 rematch weight=1.0/1.25|初回/穿孔後Hungarian再割当でのfiller利益|後期の利益は.47987→.48615、モデル費用8.10558→8.111。受理上の利益と費用の釣り合いを同倍率でscreen。|
|3940付近 probability_gradientの.6|covered_gainの先頭色確率微分|現行covered_gain=.8と数式不一致。ただしAのfret-full担当なので変更しない。|
|10831 perforation weight=.7|自分に穴を足す費用に対するdonor/owner改善価値|owner補正・複数filler DP導入後の旧係数。穴7.636、donor gain .011404、owner補正.003364。上下screen。|
|9599/9886 perforationの2*demands|追加穴の色費用と先頭色確率|ここもreset2が残る。費用・確率両側を同時に1.4/6へ変更。穿孔DP価格8/5=1.6はA担当なので維持。|
|1501/1578 map gobj=.5*handle差+両商品汎用費用+.04*全差、未成立pair罰10|窓割当でペア作成の将来費用を予測|完成設計前の粗い目的。後処理・holecost変更を反映しない可能性はあるが、窓全体が変わり500件の感度が低い。今回の8系統には含めない。|
|10041 initial-column DPの需要1、穴需要1、add_filler_demand（kFillerDemandWeight=.25、最小需要.25）|初期列順から最初の注文を出す費用|注文側と同じ需要関数を再利用。主に初期過渡、1024注文に希釈。今回は固定。|
|10915以降候補選択|完成候補をV最小で選択|独自の線形混合重みはない。4枝+5回仕上げの探索配分は費用係数ではなく、今回固定。V回帰係数も固定。特徴量生成側のreset強度2・DP価格1.6等も、回帰時の定義と一組なので固定。|

## Screen と過去の試行との違い

8系統×2値、16候補をstack1と同一compare（500件）で測る。hole .266/.532、generic .7/1.4倍、column .7/1.4倍、climb .35/.7、rematch .7/1.4倍、perforation .49/.98、head probability reset1.4/6、perforation reset1.4/6。

trial_log.md:450–453では11/4の模型は実操作とほぼ整合し、残差補正は不採用。496では旧climb=.5最良、rematch/perforation等も既存値が最良。1505では仕上げごとの重み混合に利益なし。今回の新しい根拠は、reset6・返却.8への変更が有意に成功したstack1で、残りの項との相対的な釣り合いが変わったこと。過去の探索を無視した再提案ではなく、変更済み基準への再較正である。

hole=.532では古い枝刈りコメント「4*kHoleWeight<2」が偽になるが、実際の安全条件64*64*4*kHoleWeight+22<10000は成立する。枝刈り閾値・乱数消費は維持し、static_assertで検査する。columnはscalar/int40/SIMDの3式を同じ倍率へ変更する。安価な6系統はLOCAL_BENCH環境変数を追加し、hot constexprの2系統はコンパイル定数を維持する。

判定は得点とpaired dv_best（.01 V≈.14–.21%）を併記。screenの多重選択による楽観を避け、最後に独立のstack2通常2000件比較で増分と時間課金を判断する。

係数を変えるscreenでは `model_cost` 自体の尺度も変わる。model_costの減少を改善とは解釈せず、全armで定義が同じ `dv_best` と実得点を使う。

## reset6での再確認

`20261109-122453_d30a-reset6`対`20261109-122454_d30b-r6-headreset` / `d30b-r6-perfreset`、500件。headreset=6はΔV −0.00026±0.00077で改善が消失。perfreset=6はΔV −0.00322±0.00048、得点−0.0285±0.0226%でscreenを通過。stack2には後者だけを採用して2000件で確認する。したがって「残る2を一律6へ揃える」という結論にはしない。
