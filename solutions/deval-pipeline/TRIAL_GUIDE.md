## 試行名と変更内容

全行の接頭辞は `deval-`。詳細な固定パラメータは各解法のREADMEと保存ソースにある。下の数値表は不採用案も含む。

| 試行群 | 変更と判断 |
|---|---|
| head-jitter15/50、head-all1/0 | 穴を保持する再仕上げの代表紙を変更。価値への固定ハッシュの揺らぎ、単独紙を含む選択を試したが採用に至らず。 |
| warm-s16/32 | 穴あけの色状態サンプルを8から16/32へ増加。時間に見合う品質差なし。 |
| gref500/3000/12000 | 汎用紙の比較窓の局所再最適化。変更できるケースも利得も少なく不採用。 |
| anchor-high/low、free-anchor | ペアの固定側を合法な相手の多い/少ない方にする。単独紙の色自由化との併用も、それ単独を上回らず。 |
| free-color、free-late/all/extra/extra-all/body | 単独紙の色固定を解除する場所を比較。warmだけ、全8候補の穴あけ後、穴あけ前も含む、追加4候補だけ、代表紙以外だけ。全8候補の穴あけ後を採用。 |
| free-warm8/9 | coldの再仕上げを1回へ減らしwarmを3/4回にする。元の2cold＋2warmの構成を上回らず。 |
| prelate10/16/chain | 穴あけ直後、最終再割当て前の状態もVの選択肢にする。中間状態を次の再仕上げへ渡す案も含む。上積みが小さく不採用。 |
| elite-branch/close | 同じ汎用窓集合を持つ別の窓割当てをelite poolから取り、4本目の枝を置換。不整合ペアを修復。窓目的/修復ペア数で選ぶ2案とも不採用。 |
| free-head/flip | 色を変える際の旧色の次点代表紙、新色の代表紙昇格をHungarianの線形提案費用へ反映。単純な色自由化との差がなく不採用。 |
| free-price85/125/pricemix | 穴あけ後のfiller価値の係数を0.85/1.25、またはwarmごとに変える。1.25を併用候補へ進めた。単独差の有意性は主張しない。 |
| genlook、genone50、genbias25/50/100 | 汎用紙6枚の順序の将来価値を同手数選択・末端費用へ追加。12反復の価値より安い、既存の1注文先平均×0.5を採用。 |
| mdp-rate50/75/depth | fillerが吸収する需要を見込み、列MDPのハンドル需要を一律/深さ別に減らす。改善せず。 |
| mdp-cluster、mdp-quant4/quant4x2 | 紙の4分類をfiller込みの需要に合わせる。色ごとの2群を採用。4群を2色へ自由配分し、元の状態数の1倍/2倍以内にする案は採用せず。 |
| free-mdp/gen/both、flex8系 | 上記注文項を新しい保存設計でも確認し、設計変更・高速化と併用。最終flex125系はさらに係数を1.25とする。 |
| plan3、ns1/ns1-plan3 | 同手数計画も後処理するモードを採用。neutral rewriteを2反復から1反復へ削る案は、時間短縮に対して品質低下が大きく不採用。 |
| hash-next/end/both、cache-next/end/both | 完全キー照合を残したキャッシュの整数ハッシュ並列化・容量変更。明瞭な速度差なし。 |
| sort-msd、sort32、msd-lazy、radix16 | 窓割当ての整列をMSD化、32bit化、必要bucketだけ遅延整列、上位histogramの縮小。速くならず。 |
| radix-prefix、prefix8 | 既存radix sortのhistogram累積和をAVX2整数演算へ。キー上限の追加仮定を要しないprefix8を採用。 |
| target-delta/plane | 焼きなましのtarget移動の差分式や2列同時計算を変更。速くならず。 |
| column-kind | column_moveを移動方向別に特殊化。採用。 |
| vheads/vdraw/vfast、vstatic | Vの不要なdonor候補を省略、色マスク比較を整数SIMD化、特徴量参照の検索をループ外へ。source量と測定からvdrawとvstaticを採用。 |
| exact5、flex8-fast | 採用する出力同一変更をまとめ、親との出力一致をGCC/Clang各250件で確認。後者には汎用紙評価のpopcount命令指定も含む。 |
| mdp-dag、filter-mask、eject-range | MDPの削除DAG伝播、表示検査の重複削減、書換え候補の連続区間処理。速度改善が確認できず不採用。 |
| flex8-arrays/matrix/dense | 仕上げの二次元表を固定配列/連続配列へ変更。allocation削減より時間増加が見られ、不採用。 |
