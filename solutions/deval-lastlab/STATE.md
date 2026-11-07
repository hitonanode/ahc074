# Task 6 checkpoint (2026-11-07 17:53 JST)

開始17:21、終了22:00。21:30までに凍結して最終評価へ。共有STATE/CLAUDE既読。Task6の書込みは新しいdeval-*だけ。no commit、trial_log等は触らない。コンパイルと重い分析はruns/.lock、評価はrun.py経由で標準pahcer_run.py。最終はrecordあり4解法2000件。時刻fallbackなし。上限522000 bytes。500–999は未使用、まだ凍結候補なし。

基準: flex125-plan3。設計165305、train8=164930、test8=170555。旧基準argon-des-perf-latew105、tail基準vbranch-nofb。

## スクリプト
run.py=標準runner+compiler flock+完全同一build再利用。batch.py=3基準とのnormal500保存、各候補train500x8。requests.py=165305固定design500x4。quick.py=学習seedだけ結果を即比較。summarize.py=manifestとspeedログから集計、flock下で実行。build_submission/nativeは後で最終両compilerチェックに使う。

## 済み
- deval-trim6: unused solve_edges/add_filler_features削除、521020 B。GCC/Clang各250 score全一致、stdout集計待ち。
- deval-trim6b: 古いMDP分類の上書き前の無駄な計算・古いコメント削除、519736 B。GCC/Clang250結果済み、stdout集計待ち。以後のベース。
- request budget (run172415、ref suffix -3): fresh3%±SE: ns3 −.002538±.000469、width4 −.008628±.000704、plans2 −.001323±.000475、short0 −.015502±.001346、post8 −.001968±.000582。時間は集計待ち。
- request value (172415、ref suffix -2): nextmix75 +.002951±.004269、filler charge.6 +.059940±.005458、.8 +.087675±.005211。不採用。

## 起動済み、全てflockで直列
- cuts batch (normal172749、現在各replay): branch3/2(追加candidateのid4–7維持)、climb30k、gopt80k、anneal90%。normal8解法500完了。設計の優劣はreplayで判断。
- units batch (normal173643完了、warm replay174441待ち): warm2回/last1回だけwhole-unit Hungarian。pair/single構成・pair色のslot固定を解除、列紙数は維持。最初のshadowingコンパイルエラーは修正済み、失敗run使用しない。
- headvalue request (173453): nextcostで既存filler utilityのhead合計を.5/1/2倍減算、現実行中。
- generic6 request (173453別suffix): generic future.75/1、helper未来tie、同距離helper許可。
- finish6 batch (normal173804待ち): d2 weight1.5/1.75/2、warm lateiter2。
- exact filter GCC250 (174108待ち): linkloadのprev/next先読み、filterprefixの共通操作列prefix再利用。後者は521258 B。Clang未起動。
- helper-skip GCC250 (174346待ち): generic distance0ならhelper探索即return。helper-equalとは同時採用不可。
- shortplus request (174529待ち): PLAN_SHORTLIST4/5=+1手まで追加計画許可、4は重複紙要件あり。
- rankprobe (174529待ち): neutral width12+HEAVY_PREDICT、train0–199×2。診断専用。heavycandからcheap ranking改善を検討予定。source deval-rankprobe6。
- summarize.py flock待ちのsession32778。完了時summary.log/json出力。

各driver/normal/replayログとrequests.jsonl/experiments.jsonlが根拠。未完result.jsonは使わない。sandbox PID namespaceのためstatusは他execの評価を見えず誤って空と言う。logと実ファイルを参照、flockは機能する。

## 未実施
最終候補、heldout、2000 normal、submission/native両compiler、REPORTは全て未実施。結果待ちが多いので新規大量queueを足さず集計を優先。


## 18:42 更新
- 共有STATE再読、最新17:18のまま。終了22:00、21:30までに凍結。heldout未使用、最終候補未確定。
- 全速度試行のGCC/Clang cleanup stdout各250一致。trim6b=519736 Bは空間確保のため採用可、速度改善主張なし。
- requests172415: width4 fresh -.008628±.000704%/req+13.89ms、short0 -.015502±.001346/+50.99ms、ns3 -.002538/+6.60ms。scalar nmix75,filler charge60/80は不採用。
- headvalue.5/1/2は +.001734/+.008085/+.020184%、不採用。
- helper-future (173453): fresh -.003020±.001096%、req+.326±1.408ms。Interleaveの同じ最少distanceのgoalをfuture優先、depth同点処理維持。
- helper-equal (173453): fresh -.018646±.002066%、req+39.132±1.516ms。同generic distanceの単独helperも許可。新しい有望方向だが費用大。
- genericbias75/100は差なし。shortplus5 (+1 move shortlist) fresh -.010927±.001059、shortplus4(繰返しpaper条件) -.001969。時間は次summaryへ。
- cuts: 3branch +.047219±.009376/−80.41ms design、2branch +.118979/−159ms、climb30 +.028221±.01155、gopt80 +.066042±.01561、anneal90 +.017660±.02594。最初4案不採用、anneal90は不確実。
- wholeunit warm/last (.017730/.006545%悪化, design+30.3/+16.1ms) 不採用。wholeunitをcold前半だけにしたunit-beforeは175940normal済→trainreplay待ち。
- lateweight1.50 +.046036%、1.75 +.121226%、2は最新quickへ。warm2のreplay183547進行中。
- V8(182508) fresh +.012320±.005832%、all+.013448%、real+.021345%、不採用方向。
- exact速度: linkload +.263ms req/filterprefix+6.867ms/helper-skip+1.376ms、各GCC250全stdout一致、不採用。pairskip180416も全score同点、summaryに追加済、段時間未集計。
- profile175520(100seed)終了: eval_holes~154ms、eval_filter/nextcost/ejectが重い。計測負荷あり、絶対時間は採否に不使用。
- division RCP+Newton+FMA/table+FMA: component分子0..65536/分母1..768の50,332,416組、GCC/Clangとも0不一致。ARITHMETIC.mdに丸め誤差の証明。GCC250compare182107は待ち、採否は速度次第。RCP版はTask3fastrecipで+8msだったことを後で発見、今回のtable版は新規。dirtyall/first/qtable等は過去遅かったため繰り返さない。
- rank_probe174529幅12 trace200seed×2完了。rank_fitで0–99学習/100–199確認。現在上位3はoracle12の利得の96%程度、単純weight変更にほぼ上積みなし。rank_fit.json/npz保存。コード変更なし。
- helpers6 prefix180311/180312、現在実行待ち: helper-future+equalのうち同距離のtop1/2/3、またはestimate screen。session88020。
- second6 normal175940完了: unit-before/reanneal100/300。cold前の通常anneal100k/300k追加。batchで各train8待ち。session28560。
- matchcuts6 normal180130済、prematch1 replay183002済。prematch0待ち。session7197。
- mapmix6 session65289: cross率1/16→1/32,1/64(他は通常window move)、固定予算でcrossの重さを減らす。0–499 normal+8、make_mapmix6.py。
- reqtarget6 session92353: Solver全関数にpopcntまたはavx2,popcntを指定(GCC既存push内、Clangattribute push/pop)。FMA/fastmathは増やさず。GCC250比較から。source519955/519965。reqtarget-gcc.log。
- summary session86924はflock待ち、pairskip/divログ追加済。reqtargetログはまだsummary対象外。
- 最終scriptsfinal_pair.py/final_metrics.pyは準備済み(未実行)。現時点新たに検証済best solverなし。既存ソース、shared/trial_logは未編集。


## 18:52 更新
- helper cap結果180312: fresh cap1 -.017231±.002069%/req+12.566±1.121ms、cap2 -.021257±.002322/+22.694ms、cap3 -.021556/+29.370ms。screen -.005870/+2.449ms。cap1のROIが良い。
- prematch1 fresh +.003919±.008874%、設計−19.565±1.866ms/finish−19.063ms。弱い損失で有望な資金。prematch0 +.029594±.012055%、設計−38.75msで損失大。
- unit-before fresh+.022152±.007197不採用。latewarm2 −.006884±.003180%の小幅利得、設計コスト未集計。latew200+.196530不採用。
- shortplus5のreq差+19.752ms、shortplus4−3.364ms。shortplus5は1手長い候補全部、4は繰返しpaper条件。診断F3_PLAN_TRACE=1でshortplus5の0–199×2を新たに起動、shorttrace6.log。新sourceではなく既存Task6独自版を標準runnerで使用。
- helperplus6 session76293: deval-helperplus1はgeneric+1まで許し、同距離以上は見積りbaseline−1以下・上位1だけ。helperrank6 session85310: helper-rankfutureは候補sortにもfuture×.5、pairfutureは2枚helperのgoalもfuture優先(優先perm順を一度作る)。各fixed500×4。
- matchshift6 session89460: pre1/late2 first4 (shift4)、pre0/late2all8 (shift8)、pre1/late2all8 (late2)。同じ回数を色自由の穴あけ後へ移す。batch500+8。
- pairslots6 session54867: wholeunitのうちpaired paperだけをpairslot間で動かす(last/warm)。singles固定、列の紙数/ペア数/targets数は固定。2色とvalidチェック。古いwholeunitに紛れたhead.rebuild後の余計なrefreshも除去(この版はreset率不変)。source520508/520478。
- reqtarget6はSolver全体popcnt/avx2,popcntのGCC250待ち、source519955/519965。Clang未。
- div182107はGCC250実行開始。過去同じRCP案遅かったためtable版が主。profile_report.py(100case集計)はsession4856待ち。
- tables.pyでTABLES.md自動生成可、現38行。summary.pyはreqtarget/pairskip/divも対象。次集計後tablesを再実行。
- 全新方向はここで一旦止め、既存queueの結果で併用候補を絞る。heldout未使用、freezeなし。終了22:00まで約3時間。


## 19:15 更新
- 全設定選択は0–499のみ、heldout未使用。凍結候補まだなし。終了22:00、21:20–21:30までにfinal開始。
- reqtargetのGCC250(184103): popcnt/avx2ともstdout250/250一致。req差+0.915±1.940ms/+2.204±1.819msで速度改善なし、Clang試行せず不採用。設計側popcnt版−6.79±2.97msだがlayout差程度、採用根拠にしない。
- div182107はRCP/tableともstdout250/250、anneal +7.879/+37.689ms、不採用。
- helperrank184554: futureを候補sortにも足すstrict版fresh−.003059±.001105%、pairfutureまで足す版−.002785±.001208%。元helper-futureの−.003020とほぼ同じ。等距離helper版(185946)は待ち。
- cross32 replay185845: fresh+.047665±.031459%、all+.055424、real+.109667%、不採用方向。cross64 replay190615待ち。
- shorttrace185215(0–199×2)完成。1手長い追加候補のgap≤1は呼出28%で診断改善量43–44%、≤1.5は呼出68%で79–80%。shorttrace-analysis.py/jsonに保存。これは局所model改善量で、実scoreの保証ではない。shortgap100/150を0–499×4で検証中(request driver83101)。
- equalshift6 normal185353完了: old judge1.59658/current1.72660/nofb1.71732/candidate1.76781、candidate比1.107未達。design1.04461 vs current1.06753、req.49420 vs.44587。500p99はcurrent1.93796/nofb1.86750/candidate1.95297、ばらつき大きい。train8replay190908待ち。
- combo6 185352 (equalwide6=helpeq1+width4、equalplus6=さらにshortplus5+ns3)は待ち。helpermdp6 185946 (helpeq1+future事前rank、さらにMDP差)待ち。helperscreen0 190153 (helpeq1+estimate<=baseline)待ち。
- pairequal6 driver90146: deval-paireq1/paireq-screenはhelpeq1にpair同距離も上位1許可。screenはestimate<=baseline。make_pairequal6.py。
- coldcuts6 driver94862: cold-skip6はcandidate6だけ省く7候補、cold-warm6は6をwarmに変更8候補、cold-warm46は4,6ともwarm8候補。Task5free-warm8/9は既試行だが今回は現行1.25モデルで時間資金として検証。make_coldcuts6.py。
- 新規方向の追加を止め、pendingのcombo/matchshift/pairslots/coldcuts/helperMDP/screen0から選ぶ。shortgap/pairhelperは最後の追加。
- summary再集計session42341はflock待ち。summary.logはredirectで空、以前のsummary.jsonは38行のままか確認。


## 19:28 更新
- combo6(185352) fixed500×4: equalwide6 fresh−.025692±.002163%、all−.027048、req+25.644±1.236ms。equalplus6 fresh−.037938±.002367%、all−.038852、req+54.076±1.227ms。
- equalshift6 replay190908 fresh−.034040±.008923%、all−.030759%、real−.007875±.020648%。品質はtarget程度だがnormal mean比1.107で不可。
- screen0 replay190153: fresh−.007757±.001563%、all−.009150。cap1から約.0095%損失、採用不利。
- cross64 replay190615 fresh+.070447±.031602%、design−74.3ms。cross32/64とも不採用。
- summary.json現在57行、summary.log再集計済。tables.py実行済。新規結果は後で再集計。
- helpercap6 driver60075: single候補全体6→3、equal上限1/2。deval-helper3-eq1/2、make_helpercap6.py。
- helperstay6 driver79354: deval-helper-staygoal、helper同generic距離goal選択にfuture×.5+genericより下に入る場合の既存filler_charge差を反映。make_helperstay6.py。
- exact eject追加: profileのeject exclusive67msに対し修復紙候補の必要条件をAVX2の4紙同時検査に。deval-ejectsimd6=masked gather(521372B)、deval-ejectsimd-seq6=候補順owned/stampを連続load(521471B)。候補・受理順・浮動小数点計算は維持。make_ejectsimd6.py/make_ejectseq6.py。GCC250比較は192253(driver79027)と192746(driver63115、実IDlog参照)、Clangはまだ未。speed根拠が出るまで採用しない。
- request-timing6 driver57969: old/nofb/current/helpeq1/equalwide6のnormal500(save-design,no-record)、0–499だけのtime frontier確認。
- helper属性分析 driver69428: attribute_helper.py、180311current vs180312helpeq1、0–499×新規1–3、@ops件数score照合、helper-attribution.json/logへ(まだ待ち)。
- REPORT-NOTES.mdは文章下書き、TABLES.md自動表。最終REPORT・sourcefreeze・2000compare・heldout・finalbuildsは全て未実施。

## 20:00 前後の引継ぎ
- 22:00終了。新方向を止め、21:15–21:25までに凍結する。Task6 heldout seed 500–999は未使用。
- 192415通常500: old judge1.59084、nofb1.71832 p99=1.90574、flex1.72617 p99=1.87421。helpeq1=1.73375(1.08983old),p99=1.89755、normal gain−.021742±.003344%。equalwide6=1.75847(1.10537old),p99=1.91247、−.031110±.003463%。後者は時間超過。
- 185353 equalshift6（prematch1+helpeq1+width4+shortplus5）: train8のfresh−.034040±.008923%、normal judge1.10725oldで時間超過。設計−22.918ms、req+48.330ms。
- 190916 paireq1: helpeq1に2枚helper同距離top1を追加、fresh−.024063±.002485%、req+32.153ms。paireq-screenは−.019254%、req+20.595ms。
- 190854 shortgap100/150: 1手長い計画をraw gap≤1/1.5だけ追加、fresh−.004491/−.008971%、req+7.049/+15.499ms。
- 192018 helper3-eq1/eq2: single上位6→3、同距離top1/2。fresh−.015998±.002067 / −.019616±.002277%、req+8.644/+18.228ms。helper-staygoal(192601)は−.016171±.002098%でhelpeq1を上回らず。
- speed: ejectsimd6 GCC192253 req−3.714±1.865ms、ejectsimd-seq6 GCC192745 req−2.822±2.610ms。stdout一致はsummarizeで確認（スコア250同点）。gather版Clang195123待ち、seq版は不採用候補。
- paireq-lazyはnormal generic goalなら両helperをdepth Mに置ける事実から、失敗したstrict検索をdistance=baseのplaceholderにして整列し、残った等距離候補だけgoalを詳細探索する。元paireq1とGCC194833、Clang195134各250のidentity/time比較待ち。
- keypack6はadaptive_next_costのkeyを16byte SSE、8lane圧縮tableで作る。role普通条件はinitで確認し例外にscalar path。GCC195331各250待ち。追加コード1640B、source521376B。
- helper-retain194347とretain-model194507待ち。旧fillersを全返却する制約を緩め、既に正しく対象列を隠さないbelow-generic fillersを残す。前者はfix見積り未変更、後者は残存coverageも引く。
- helpertight6待ち(新1955頃): helpeq-tight / paireq-tight、single総数2、pair総数3。各等距離top1。時間と品質を測る。
- coldcuts6 normal191024は6solver500が19:57前完了、skip6/warm6/warm46各train8待ち。match-late2のtrain8は194941が19:57開始。pairslots/shift4は改善なし、shift8はmanifestあり。
- summary.pyにpairlazy/keypack/ejectSIMDのGCC/Clangを登録。summary更新flock待ちsession11517。normal-frontier.json/logに上のnormal値あり。TABLES再生成はsummary後。
- REPORT-NOTES.mdに既検討と@ops解析。最終REPORTは未作成。新ソースの合成・予算判断・最終凍結が次。

## 20:21 更新
- fresh8 train: equalfund6 `201545` = −.0313616±.0088994%、all−.0281379、real−.0056564。prematch1 + single equal top1 / total3 + width4 + shortlist6 gap1.5。normal200401 judge1.743045/old1.582429=1.1015、p99 1.910692 vs nofb1.890599。SIMD併用前。
- cold-skip6 `195659` +.016416±.003547%、cold-warm6 `200459` +.011911±.004275%、cold-warm46 `200956` +.028686±.006622%。全て不採用。
- helper tight `195501`: single総数2、pair総数3。helpeq-tight fresh−.013453±.002139、req+8.016ms。paireq-tight fresh−.020140±.002550、req+23.757ms。狭くし過ぎ、主要候補には使わない。
- pairlazy GCC194833は250stdout同一、req−.139±2.513msで速度差なし。Clang195134はスコア250同点、stdout照合はsummary待ち。採用しない方向。
- eject gather Clang195123 stdout250同一、req−1.796±2.112ms。keypack GCC195331 stdout250同一、req−5.725±2.218ms。keypackのClangは単独を省き併用版で検証する。
- `merge_exact.py` は出力同一patchを合成し、呼出しのないfeature export2メソッド(1415B)と古いコメント84Bを削除。GCC/Clang併用identityが次。
- `deval-equalfund-fast` source521947B = fund6 + ejectSIMD + keypack −deadfeatures。GCC200829(親fund6)、Clang200834各250が待ち。
- 同じexact変更で `deval-equalshift-fast`521892B(fullshort+single6,prematch1)、`deval-equalwide-fast`521750B(requestonly幅4+singleeq1)、`deval-helpeq-fast`521750B(requestonly singleeq1)も作成。
- fast-frontier6.log通常500は201050 old/nofb/flex/shiftfast/fundfast/widefast/helpeqfast。driver session77800、まだcompile待ち。final候補の品質と時間を決める主要run。
- `deval-equalfund-gap1`521947Bはfundfastのgap1.5→1.0。fundgap6.logで親fund6と同じprematch1保存設計200401を500×8で比較、session63577待ち。summary/tableにcontrolled区分を追加済み。
- profile21msのcanonicalizeの配列全クリアをstamp化したdeval-canonicalstamp6 source520116B、GCC201259各250待ち。成功時だけClang/併用、追加は380Bなので522KBの容量調整が要る。epochs偶数+下位bitで旧fillerを印し、旧記録重複も保持する。新方向はこれで最後。
- final_pair.pyは混在priorityを扱えるよう `--request-only=<name>` を追加。各FROZEN.jsonに個別flag、選んだ案がrequestonlyなら保存design2000×4、設計変更ならheldout500×8。普通の最終比較は全候補を同じcompare、優先順と時間条件だけで一案選ぶ（スコア選択禁止）。
- write_report.py作成済み。最終JSONとTABLESから日本語REPORTを作る。ただしREPORT-NOTESの「現時点speedなし」などは最終前に直す。最終reportに全試行の変更説明のfamily表とfast-frontier表を加える必要あり。
- 全部まだtrain0–499だけ。ソース未凍結。22:00終了、21:10頃freezeを目標。主要候補のnormal/replay/identity/時間を待って絞る。

## 20:52 更新
- 未使用seedは未読、まだソース凍結なし。21:00頃に最終優先順位を固定し、7解法程度normal2000+選んだ一案のreplayを予定。22:00厳守。
- 最新normal500のhelper-fund(202405)はratio1.0950だがp99がnofbより29ms高い。gap1はratio1.0871、p99+14.5ms。設計削減の併用はtrain fresh8 -.03136/.02777%だがtail不適合。
- helper-wide(204516)=旧equalwideにcanonicalstampを加えたrequest-only、521712B。train fresh3 -.02569±.00216%。normal500ratio1.0931、p99+39ms。helper-one=width3、同521712B。fresh3 -.01723±.00207%、ratio1.0816、p99+8ms。500件p99は比較毎に振れるため、最終2000の同時比較で適合を見る。選択はスコアを使わず事前優先順+時間のみ。
- Nextmix .25/.35 (204050) は+.08250/+.03358%と悪化。採用しない。
- last_checks.py(session17796): newwide/one normal500済、GCC/Clang各200 identityとwide/one/gap1の提出/native両buildを直列中。source_auditも最後に実施。helper-fundの両build/nativebuildは済。
- native-gcc203310/native-clang203316: fund6対helperfund各200全score同点。バイトstdoutはidentity_extra.pyで集計予定。
- hash2-gcc204736: memo hashを2laneで独立乗算しdependencyを減らす試行、helperwide対hash2各250。request profileでeval_filter89msの内側。全配列照合を維持。結果待ち。
- helper-fixrank6(204846): request500x4、baseline/wide/half/heavy。順位の未被覆fix費用0.5/1.5倍を最後の模型試行として検証。結果待ち。これ以降新規方向は増やさない。
- 最終scriptsに提出/nativebuild+source audit一致のpreflightを追加。REPORT生成と全学習表の仕組み準備済。最終heldout後に再調整しない。

## 21:03 凍結・最終評価開始
- 21:02:26に4候補を同時に凍結。優先順位: helper-fund → helper-gap1 → helper-wide → helper-one。通常スコアでは選ばず、judge平均≤1.10old・p99≤nofbの最初の候補だけをreplayする。
- final_pair.py session36434、driver=final.driver.log。記録ありnormal7解法2000開始、prefix **20261107-210226** (old/nofb/flex/fund/gap1/wide/one)。ログはhelper-fund/final-normal.log。ここからソース変更・新しい調整なし。
- fund/gap1は設計変更なので選ばれたら500–999×8、wide/oneはrequest-onlyなので165305保存設計2000×4。未使用分500–1999を別報告する。ソース・優先順のFROZEN.jsonあり。
- 両compiler提出/nativebuildが4候補とも成功。source-auditも全てSHA一致。native fund6→fund GCC/Clang各200、default最後のstamp wide/oneのGCC/Clang各200、全stdout一致。
- 三つのexact変更のまとめ比較: **205534** raw equalwide6→helperwide GCC500、req −11.948±1.606ms、全500stdout一致。**205745** Clang250、−12.137±2.074ms、全250一致。24並列。identity-extra.json/EXTRA-TABLES.md参照。
- helperfixrankのhalfはwideより+.004531±.001132、heavy−.000133±.000913%。両方不採用。hash2も−.223±2.470msで不採用。新しい方向はこれで終了。
- refresh_report_data.pyとrender_extra.py完了。TABLES.mdは全学習、EXTRA-TABLES.mdはnormal training時刻と追加identity、EXACT.mdは不変条件。write_report.pyは選んだsolverのfinal-metrics.jsonができた後に実行し、REPORTを読んで仕上げる。

## Task 6 完了（最終結果）

採用候補 **solutions/deval-helper-one**。凍結後のソース変更なし。source **521712 bytes**, SHA256 **e545511e5604a7977cd95fe7632ab8dccd328422fe47a4270f5d6cd6f3ecda3f**。GCC/Clang C++23の提出用 / native build全て成功、clock52行・section61個を維持。no fallback、全2000件dv_candidates=8。

- 通常記録あり2000比較: prefix **20261107-210226**。refs=argon/nofb/flex125-plan3、候補=fund/gap1/wide/one。事前に固定した優先順で時間のみ判定。fund p99+19.735ms、gap1+7.842ms、wide+15.459msで不適合。oneだけ適合。
- one vs flex normal: **−0.015085983 ±0.001697033%**, W/T/L **1143/98/759**。平均score10277.385、flex10278.9355。
- one judge平均 **1.718382164 s**, old比 **1.082402275**。p99 **1.881012253 s**（nofb **1.8889500075**）、最大 **2.14722455 s**、>2s1件。end_sec平均1.523305685,p99 1.6590934,最大1.88202、>1.8s1件/>1.9s0/>2s0。全件含め、outlier除外なし。
- 最終replay: **20261107-211724_deval-flex125-plan3 / deval-helper-one**、保存design165305、2000seed×4lists。全新規1–3 **−0.015761702 ±0.000970463%**。全4列 **−0.015592208 ±0.000854569%**。
- 主評価、Task6未使用seed500–1999・新規1–3: **−0.015271816 ±0.001094973%**。500–999だけ **−0.016385197 ±0.001929662%**。1000–1999だけ **−0.014715125 ±0.001329540%**。
- **目標0.03%には未達。** 時間条件内で検証済みの改善は上記。最終データを見て予算・係数を再調整していない。
- 基準と候補ともreplay8,000列で@opsの総数=score、self_wrong/plan_failures/unsafe_plans/op_label_errors全て0。候補のnormal/replay列0stdoutは2000/2000一致、設計192行もflexと2000/2000一致。source hashは現行・normal保存・replay保存で一致。
- 指定judge_model.pyの再計算も一致。reference copyはdeval-lastlab/reference、元パス・SHAはsources.json（内容無変更）。
- REPORT.md（日本語、全学習試行397行程度）、README.md、REPRODUCE.md、FROZEN.json、final-runs.json、final-metrics.json、time-selection.json、builds*.json、source-audit.json、reference-audit.json、tail-audit.jsonは **deval-helper-one/**。
- 全評価・解析・build完了、実行中の自分の評価なし。主要session36434/2968/45626/6830はexit0確認。commitなし、既存solver/shared/trial_log/scriptsは編集していない。共有STATEの最新は再読時も17:18のまま。
