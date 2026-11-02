from pathlib import Path
import collections,json,math,statistics as st
p=Path(__file__).resolve().parent
models=json.loads((p/'model-summary.json').read_text());cycles=json.loads((p/'cycle-summary.json').read_text());relax=json.loads((p/'relax-summary.json').read_text())
def metric_rows(label):
 return [json.loads(f.read_text()) for f in sorted((p/'results'/label).glob('[0-9]*.json'))]
def comparison(label,reference='base-detail'):
 rr=metric_rows(label); out={}
 for k in ['model_cost','sim_moves','sim_generic']:
  vals=[];delta=[]
  for r in rr:
   f=p/'results'/reference/f"{r['seed']:04d}.json"
   if not f.exists():continue
   b=json.loads(f.read_text())['metrics'];a=r['metrics']
   if k not in a or k not in b:continue
   vals.append(a[k]);delta.append(100*math.log(a[k]/b[k]) if k=='sim_moves' else a[k]-b[k])
  if vals:out[k]={'n':len(vals),'mean':st.mean(vals),'delta':st.mean(delta),'se':st.stdev(delta)/len(delta)**.5 if len(delta)>1 else 0,'wtl':[sum(x<0 for x in delta),sum(x==0 for x in delta),sum(x>0 for x in delta)]}
 return out
labels=['gate128','compare128','seven400','sparse4','sparse8','sparse12','seven-h650','seven-h800','seven-h1000','seven-g40h650','sparse6h650','joint15','joint12','joint-sa15','joint-sa12','shared15','shared12','forced4','forced8','six-control']
comparisons={x:comparison(x) for x in labels if metric_rows(x)}
comparisons['seven-vs-six-control']=comparison('seven400','six-control')
(p/'comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
base_moves=10.392103125
lines=['# 比較器の整合の値段を取る汎用層の研究','', '## 1. 要約','',
'対象は `solutions/as6-cap38p0`。計測は seed 24〜87 の64ケースを基本とする。**採用条件を満たす案がなく、提出候補は作らなかった。**','',
f'- 整合しない近い対を、基準とほぼ同じ汎用費用2.46手/対の注文で使える模型は **−0.53351 ± 0.00493手/注文**。基準の模擬10.39210手に対して約 **−5.13%相当**。3.0手でも −0.28705 ± 0.00423手（約−2.76%相当）。',
f'- この模型の不整合な選択対は、整合に平均 **{cycles["mean_fas_incompat"]:.3f}窓**の除去が必要。共通1窓を最善に選んでも平均 **{cycles["shared_removal_means"]["1"]:.4f}対/ケース**しか救えない。単窓救済の件数が増えても得が小さい理由を定量化した。',
'- 先着ゲート602種の2〜4窓同時変更と、毎回の厳密費用による対の組み直しを実装した。15比較窓を保護した128手の探索では、模型・4本の注文列による模擬とも0.5%改善に届かなかった。',
'- 七枚比較器と疎な七枚目は、専用紙が一枚減る費用も含めて評価した。七枚版と疎な4・8・12窓版は全て模型で悪化した。',
'- 二枚目の固定キャップは、全費用と実際の挿入位置制約を数えると悪化した。共通窓を無料で外す模型と、実装可能なキャップを区別した。','',
'以下の ± はケースごとの対応差の標準誤差。模型から換算した%は、テスターのケース別logスコア比ではない。汎用費用の「厳密」は一様な全順序から部分表示を作る最短合法手数の平均であり、実際の注文後の定常分布を一様と証明したものではない。','',
'## 2. 整合を外したモデルが選ぶ対の性質（謎への答え）','',
'### 2.1 現行系譜での整合の値段','',
'`model.cpp` は現行版への `COMPAT_FREE`、`COMPAT_GX`、`MODEL_ONLY` の移植。最初の窓割り当てを揃え、その後の対・列・ハンドル順の探索で制約を外した。`model_cost` は列の掘り、ハンドルの穴、汎用層の和で、持ち上げと前紙の戻し約1.75手を含まない。数学的な最適値や上限の証明ではなく、同じ探索回数で到達した費用の差である。','',
'|不整合対の費用/目標|model_cost|列|穴|汎用|基準差 ± SE|不整合対/71対|','|---|---:|---:|---:|---:|---:|---:|']
for key,title in [('base','許可しない'),('free230','2.30'),('free246','2.46'),('free260','2.60'),('free300','3.00'),('free340','3.40'),('free380','3.80')]:
 r=models[key];m=r['mean'];lines.append(f'|{title}|{m["model_cost"]:.5f}|{m["model_col"]:.5f}|{m["model_hole"]:.5f}|{m["model_gc"]:.5f}|{r["delta"]:+.5f} ± {r["delta_se"]:.5f}|{m["pairs_incompat"]:.3f}|')
lines += ['', '窓割り当て段階の `gobj_after` は全行で9.85385。基準の対の汎用費用は2.45695手なので、2.46を同価格の比較とする。近い対の判定は現行版どおり、キャップを除いた63ビット上で距離26以下。','',
'### 2.2 閉路の構造と共有できる窓','',
'六枚の全720順序について、要求と逆になる窓集合を列挙した。その最小要素数が、窓単位の最小帰還辺集合の大きさとなる。同じ紙の組を比較する窓が重複しても一窓ずつ数える。順序を反転すると比較器の全表示が補色になるので、この除去集合は対の両側に共通して有効。','',
f'以下は同価格の `free246` の選択4544対の分布（うち不整合{cycles["incompatible"]}対）。','',
'|最小除去窓数|対数|','|---:|---:|']
for n,count in cycles['fas_hist'].items():lines.append(f'|{n}|{count}|')
lines += ['',f'- 不整合対の最小除去数は平均{cycles["mean_fas_incompat"]:.5f}。1窓だけでは{cycles["fas_hist"]["1"]/cycles["incompatible"]*100:.2f}%しか救えない。',
f'- 逆向きの重複比較、すなわち長さ2の閉路だけでも平均{cycles["mean_two_cycle_lower"]:.5f}窓の除去が必要。{cycles["two_cycle_explains_optimum"]}/{cycles["incompatible"]}対ではこれだけで最小除去数を説明できる。長い閉路だけの問題ではない。',
f'- 全対で共有する窓を最適に選んだ場合、救える不整合対は共通1窓で{cycles["shared_removal_means"]["1"]:.5f}、2窓で{cycles["shared_removal_means"]["2"]:.5f}、3窓でも{cycles["shared_removal_means"]["3"]:.5f}対/ケース。窓集合を全列挙した値。',
f'- 最初の一窓ずつを15比較組の証人として保護すると、残りの窓を自由に変えても救済の可能性が残るのは{cycles["protected_rescuable"]}/{cycles["incompatible"]}対。これは除去だけの可否であり、実際に良いゲートを印刷できることまでは保証しない。','',
'### 2.3 得になる対と、単窓救済の限界','',
'|選択対の平均|基準|整合なし・2.46手|','|---|---:|---:|',
f'|自分の列以浅のハンドルでの違い|{models["base"]["mean"]["pair_shallow_hd"]:.5f}|{models["free246"]["mean"]["pair_shallow_hd"]:.5f}|',
f'|汎用窓での違い|{models["base"]["mean"]["pair_generic_hd"]:.5f}|{models["free246"]["mean"]["pair_generic_hd"]:.5f}|','',
'**得になるのは、違いを汎用窓へ多く寄せ、浅いハンドルの違いを減らせる対である。** 一つの共通窓でたまたま救える対の数を増やしても、この集合を広く取れるようにはならない。','',
'対ごとに自由に選んだ窓を切れる理想的な復号器を、費用2.46手/目標で追加する緩和も測った。新しい紙の費用はここでは含めない。','',
'|許す不整合対|model_cost|基準差 ± SE|採用する不整合対|','|---|---:|---:|---:|']
for key,title in [('fas1','最小除去数≤1'),('fas2','≤2'),('fas3','≤3'),('fas4','≤4'),('shared1_free','共通の一窓だけ無料除去')]:
 r=relax[key];m=r['mean'];lines.append(f'|{title}|{m["model_cost"]:.5f}|{m["delta"]:+.5f} ± {r["delta_se"]:.5f}|{m["pairs_incompat"]:.3f}|')
lines += ['', '共通1窓の0.031手に対して、対ごとに異なる1窓を選べれば0.176手、2窓なら0.334手ある。したがって、多窓の閉路と、対ごとに必要な窓が散っていることの両方が障壁。資料は `pair-cycles.json`、`cycle-summary.json`、`relax-summary.json`。','',
'## 3. 調べた復号器ごとの模型・数値・結論','',
'### 3.1 先着ゲートの2〜4窓同時変更','',
'`gates.cpp` / `gate_search.inc`。白・黒を両方含む全602印刷を使う。失敗集合から2〜4窓を選び、一度まとめて制約を外して、幅4のビームで埋め戻す。部分状態の602候補を可否と暫定費用で絞り、上位候補は全対の厳密費用を再計算する。完成候補の採否は新しい価格順で対を組み直して決める。対の距離26による打ち切りをせず、最終設計と同じ全256商品対、同じ0.65×ハンドル差＋両側の汎用費用＋0.04×全差、貪欲法と長さ3の増加路を使う。最適matchingを保証するものではない。','',
'15比較窓を保護した版では合法移動グラフが従来と一致する。比較器30種だけに制限した同じ探索を対照とした。各128提案、設計反復数固定、64件×注文列4本。','',
'|方式|模型の差 ± SE（手/注文）|模擬のlog比 ± SE|勝/分/敗|','|---|---:|---:|---:|']
for label,title in [('gate128','全602印刷'),('compare128','比較器30印刷のみ')]:
 if label not in comparisons:continue
 a=comparisons[label]['model_cost'];b=comparisons[label]['sim_moves'];lines.append(f'|{title}|{a["delta"]:+.5f} ± {a["se"]:.5f}|{b["delta"]:+.4f}% ± {b["se"]:.4f}%|{"/".join(map(str,b["wtl"]))}|')
lines += ['', '全602版の模型は8.64210（列3.07635、穴4.20142、汎用1.36432）。対の注文一件あたりの一様開始からの厳密汎用費用は2.45962手。初期の `gobj_after` は9.85385、後段の設計と同じ0.65係数の目的は11.08382→11.07951。二つの目的値は係数が違うため、そのまま差し引かない。','',
'128提案のうち採用は平均0.40625回、2窓以上を変えた採用は64件で5回、残った非比較器窓は平均0.171875個。複数窓を試しても、得のある変更はまれだった。全602版も比較器のみの対照も二標準誤差に届かず、0.5%の採用条件を満たさない。全模擬の誤表示は0。','',
'追試として、汎用窓とハンドル窓の交換をゲート変更と一つの手にまとめた `joint-detail.cpp` と、保護する比較窓を12個に減らした版を計測中。12個版は探索中に保護窓だけが保証する合法グラフを使い、完成後は全印刷からグラフを再構築して模型と模擬を評価する。','',
'### 3.2 七枚比較器と疎な七枚目','',
'`seven.cpp`。七枚の全2045非同型半順序の厳密費用表を既存PR76の実装から移植。固定キャップ、現行の列・ハンドル探索、穴埋め探索を使う。七枚への拡張では21比較組が必要なため、六枚専用の32ビット表現を使わず、7×7関係行列で候補を列挙する。窓・ハンドル交換、色反転、比較組の交換・移動、1/16の複合交換、損失0/1/2への4/2/1の重みと停滞脱出を実装した。同一の高速化コードではなく、同じ近傍を七枚へ移した研究版である。','',
'疎な版は、現行の六枚設計を作ってから一部窓の比較相手を七枚目へ付け替える。元の六枚の各比較組を一窓以上残し、七枚目を使う窓数を固定して探索。**六枚の印刷を残したまま七枚目を足す方式とは違う。** 後者は既知の一枚補助紙の不可能性に当たり、不整合対の両側を救えない。','',
'探索中の七枚完全グラフによる価格は疎な版の下界だが、最終の `Design::initialize` には、実際の印刷から作った合法な5040状態の有向グラフと逆BFSによる厳密平均を渡す。紙は6→7、専用紙は185→184、対は71→72。模型の列・穴・汎用費用は全てこの紙数で評価。','',
'|方式|件数|model_cost|列|穴|汎用|対の厳密汎用費用|gobj_after|模型差 ± SE|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for label,title in [('seven400','七枚'),('sparse4','疎な七枚目・4窓'),('sparse8','8窓'),('sparse12','12窓')]:
 rr=metric_rows(label)
 if not rr:continue
 good=[x for x in rr if 'model_cost' in x['metrics']]
 if not good:continue
 m={k:st.mean(x['metrics'][k] for x in good) for k in ['model_cost','model_col','model_hole','model_gc','pair_gc_mean','gobj_after']};c=comparisons[label]['model_cost']
 lines.append(f'|{title}|{len(good)}|{m["model_cost"]:.5f}|{m["model_col"]:.5f}|{m["model_hole"]:.5f}|{m["model_gc"]:.5f}|{m["pair_gc_mean"]:.5f}|{m["gobj_after"]:.5f}|{c["delta"]:+.5f} ± {c["se"]:.5f}|')
lines += ['', '通常の二秒制限ではなく、固定反復による構造の診断。七枚版は割り当てだけで倍率込み平均22.31秒を使った。この時間を提出可能な実行時間とは扱わない。七枚の厳密費用表100対を別の逆BFSと照合し、最大差4.44e−16。1000本・3713移動の最短経路を可視性検査した（`verification.txt`）。','',
'### 3.3 汎用窓の上の追加キャップ','',
'`relax_probe.cpp`。既存の窓63のキャップに加え、汎用窓wに白または黒のキャップを置く。対ごとのDの印刷を四通り、Dの挿入位置を三通り列挙し、両目標を表示できる対だけ許す。二つの窓の色を独立に選べるとは仮定しない。キャップの順序も両方試す。汎用窓wの比較を除いた正確な汎用費用を使い、専用紙一枚減・72対を含めた。wが比較組の唯一の可視性保証となる候補は除外する。','',
'全w・二色・二順序を初期模型で順位付けし、上位4候補を各2000万反復で仕上げた。各ケースでこの4候補の最良を採る、候補側に有利な比較でも次の結果。','',
'|model_cost|列|穴|汎用|対の厳密汎用費用|基準差 ± SE|','|---:|---:|---:|---:|---:|---:|']
r=relax['cap2_best'];m=r['mean'];lines.append(f'|{m["model_cost"]:.5f}|{m["model_col"]:.5f}|{m["model_hole"]:.5f}|{m["model_gc"]:.5f}|{m["pair_gc_mean"]:.5f}|{m["delta"]:+.5f} ± {r["delta_se"]:.5f}|')
lines += ['', '初期窓割り当ての `gobj_after` は基準と同じ9.85385。自由な一窓除去の得0.031手を、紙数と二キャップの表示制約が上回る。試した固定キャップ構成は不採用。任意の動くキャップや、別の復号器一般を否定した結果ではない。','',
'## 4. 実装した候補の詳細（あれば）','',
'提出候補 `main.cpp` / `cand2/main.cpp` は作らなかった。模型で−0.5%以上、かつ回数固定の模擬で悪化しないという条件を満たす案がないため。研究用のソースを完成候補として置き換えない。採用条件を通過しなかったため、候補向けの通常ビルドの最大 `end_sec ≤ 1.75` と64件の交互テスター比較は実施していない。これは提出版の性能・時間を確認したという報告ではない。','',
'### 再現条件と保存物','',
'- 全ソースと出力は本ディレクトリ内。既存ファイル、git状態、共通評価履歴には書き込まない。`scripts/pahcer_run.py` は未使用。',
'- C++の計測ビルドは `g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1`。模擬には `-DSIM_HARNESS` を足す。固定モードのみhelper構築の時間打切りとオンラインの軽量化を解除。',
'- `MAP_ITERS=400000, GOPT_STEPS=100000, ANNEAL_ITERS=20000000, CLIMB_ITERS=60000`。焼きなましの実回数はバッチ境界により20000768。乱数seedはソース内の定数。',
'- 模擬は各ケース4本×1024注文。各列のseedは1000003×(列番号+1)。直前の商品を除く255商品から一様に生成する、元版の模擬器を使用。テスト入力末尾の未来注文は使わない。',
'- `run_models.py` と `run_relax.py` が初期模型。`analyze.py` が帰還辺集合を全列挙。`bench.py` がその他の模型・模擬・テスター用。最大8解法プロセス、テスター利用時は最大6組に制限。重い評価の組は直列に実行する。',
'- `data/` にケース別模型と設計、`results/<label>/` にケース別指標と条件、`comparisons.json` に対応比較を保存。本文の件数を満たした結果だけを結論に使う。','',
'## 5. 捨てた案と、次に試すべき案','',
'1. 一つの固定窓を救う追加紙やキャップの拡張は優先しない。全対で共有できる窓の少なさと紙数の費用が同時に効く。',
'2. 六枚の元の比較器を残したまま疎な補助紙一枚を足す方式は、不整合対の両側を救えない。救済するには既存比較そのものを変えるなど、定理の前提を外す構成が必要。Dの非対称化だけで救えるとは仮定しない。',
'3. 次の復号器の目標は「整合する対の総数」ではなく、**対ごとに異なる2〜3窓の逆向き重複比較を、全追加操作込みの汎用費用3.0手前後で切れること**。理想模型の費用差と、実際の追加操作・追加紙数を必ず比較する。',
'4. 先着ゲートの保護窓を減らす場合は、可視性の低下も模型に入れる。今回の15窓保護・同時変更が弱いことを、一般の先着ゲートの不可能性と読み替えない。','']
(p/'REPORT.md').write_text('\n'.join(lines))
