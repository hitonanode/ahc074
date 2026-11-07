## 試行名と変更内容

接頭辞は `deval-`。各候補のREADMEと保存ソースに固定値を残した。数値は後続の全試行表にある。

| 試行群 | 変更と判断 |
|---|---|
| trim6 / trim6b | 未使用関数、必ず上書きされる旧MDP分類、古いコメントを除く。GCC/Clang各250件で出力一致。容量確保であり速度改善とは数えない。 |
| linkload6 / filterprefix6 | linked-listの参照先取り、後処理filterの基準prefix保存。明瞭な短縮がなく不採用。 |
| helper-skip6 / pairskip6 | helper候補を作らない場面の走査・距離整列を省く。速度差が小さく不採用。 |
| divcorrect6 / divtable6 | annealの商を、補正付き近似・表引きへ変える。算術の単体一致は検証できたが通常比較は遅くなり不採用。 |
| reqtarget-pop / reqtarget-avx | requestの関数へ命令セット指定を付ける。短縮を確認できず不採用。 |
| ejectsimd6 / ejectsimd-seq6 | 修復紙の必要条件を4紙同時に検査。所有窓をstamp付きgather、または候補順配列で読む。必要条件・候補順は保つ。 |
| keypack6 | adaptive_next_costの完全cache keyを整数SIMDで詰める。キーの順と値、浮動小数点計算を保つ。 |
| canonicalstamp6 | canonicalizeの全配列クリアを世代stampへ置換。再構成したfillerの順・重複も保つ。 |
| branch3 / branch2 | 最初の焼きなまし枝を4から3/2へ削る。時間は減るが設計損失が大きく不採用。 |
| climb30 / gopt80 / anneal90 | climbを30k、窓matching climbを80k、annealを90%へ削る。時間資金としてprematch1を上回らなかった。 |
| prematch1 / prematch0 | 最初4枝の穴あけ前rematchを2回から1/0回へ削る。1回が最も損失の小さい時間資金だった。 |
| match-shift4 / match-shift8 / match-late2 | 穴あけ前のroundを後ろへ移す、または穴あけ後を2roundにする。設計損失と費用の点で単純なprematch1を上回らず。 |
| whole-unit / pairslots 系 | 単独/ペア構成・pair anchor色の制約を緩めるHungarianを仕上げの前後・warmに加える。whole-unitは悪化、pairだけの交換も改善に至らず。 |
| lateweights / latewarm2 / reanneal100,300 | 後半rematch係数の増加、warmだけ2round、仕上げ前の短い追加anneal。小幅な差か悪化で、費用に見合わず。 |
| v8 / cross32,64 | Vの積分点削減、annealの列間移動の頻度削減。品質低下があり不採用。 |
| cold-skip6 / cold-warm6 / cold-warm46 | cold再仕上げを省く、または穴を保持するwarmに変える。後続の出発点にも影響し、新規列で悪化。 |
| r6-ns3 / width4 / plans2 / short0 / post8 | requestの反復数・幅・本探索計画数・shortlist・候補数を増加。幅4とshortlistの小幅な拡張が主要な再投資先。 |
| r6-nmix75 / nextlow25,35 / charge60,80 / headvalue50,100,200 / genvalue75,100 | next costの重み、filler charge、列先頭のfiller価値、generic末端価値を変更。現行模型を明瞭に上回らず。 |
| helper-future / helper-equal | helperの最少generic距離の同点をfutureで選ぶ。さらに通常と同generic距離のhelperも許す。全候補追加は費用が大きい。 |
| helpeq1,2,3 / helpeq-screen / screen0 | 同距離の単独helperを見積り上位1/2/3件に制限、または通常のfix見積りで選別。上位1件が時間効率で有望。見積りでの強い選別は利得を落とす。 |
| helperplus1 / helper-rankfuture / pairfuture / helpeq-rank / mdp | generic距離が1長いhelper、futureやMDPを候補順位へ加える案。同距離上位1件を明瞭には上回らず。 |
| helper-staygoal / helper-retain / retain-model | below-genericでの再利用をgoal費用へ加える、旧fillerを正しいまま残す、残したcoverageを見積りにも反映。改善幅が小さくなるため不採用。 |
| helper3-eq1,2 / helpeq-tight / paireq-tight | 単独helper総数を3/2へ、pair総数を3へ絞る。単独3件は小さい損失で費用を減らすが、それ以上は利得も減る。 |
| paireq1 / paireq-screen / paireq-lazy | pair helperにも同距離上位1件を許す。改善はあるが費用が大きい。厳密な距離からgoalだけ遅延決定する案はGCCで明瞭な短縮なし。 |
| shortplus4,5 / shortgap100,150 | 1手長い計画も後処理する。重複紙に限定、全て許可、またはraw cost差≤1/1.5で制限する。後処理後の改善余地を買う予算として測定。 |
| equalwide6 / equalplus6 / equalshift6 / equalfund6 | helper候補拡張、幅4、shortlist拡張を併用。shift/fundはprematch1で資金を作る。fundはhelper総数3とgap1.5を使う。 |
| helper-half / helper-heavy | 単独helperの事前順位にある未被覆fix費用を0.5/1.5倍へ変更。0.5倍はwideより+0.00453±0.00113%、1.5倍は−0.00013±0.00091%で現行係数を保つ。 |
| helper-hash2 | 後処理memoの整数hashを2本の独立な積へ分ける。GCC250件で全stdout一致したがreq差−0.223±2.470msのため不採用。全successor配列の一致検査は保つ。 |
| *-fast / helper-fund / helper-gap1 / helper-wide / helper-one | 出力同一変更を併用。helper-fundは三つのrequest短縮を含む。gap1は追加後処理のraw gapを1へ絞った固定予算案。最終採否は記録付き2000件の時間と、凍結後replayで判断。 |

プロファイルは `20261107-175520_deval-prof6`、100ケース。計測入りの絶対時間は速度評価に使わず、対象箇所を選ぶためだけに使った。既存の上位3候補の選別についても、`20261107-174529_deval-rankprobe6` の学習側診断で改善余地が小さく、候補順位の学習を最終案には使っていない。
