Task4開始11:36、締切約14:40〜15:00。基準seven-wide。Task4学習基準8-listは113720_seven-wide (0-499)。テスト500-999は112011、設計保存111153。テストはまだ触らない。
編集はTask4で新設したdeval-*のみ。共有STATE/trial_log/scripts/既存solverには書かない。flockビルド/重分析。run.pyはpahcerのビルドにもflockを付け、同一SHA/flags/compilerの完了binaryを再利用。全部通常pahcerで24並列。
11:50時点: diversity1(batch.py) normal113953の10solvers500cases完了。7候補replay順次実行中。mix-climb開始114657、他はexperiments.jsonl参照。batchsession66799。
速度GCC250case比較:
 map-speed 114420: gather/expand/triangle/key (session4542)
 req-speed 114532: cap-late/cap-once/eject-right (85759)
 perf-copy114653: 穴あけvector取消しをstackarray (42659)
 key-speed1149xx: key-pack/key-mask/mdp-cache (46739)
 profile114428 next-prof96case (33589)、既存DESIGN_PROFILE3/COLFAST_PROFILE1/AF_PROFILE1。
全てキュー待ち/実行中。result/meta完了を確認してから使う。生成scriptは各make_*.py、README全候補あり。
窓closure4展開をgather or tableへ、最初三角閉路で早return、整数matching鍵cache。capは表示正しい後に検査/重複検査省略。eject-rightは色マスクhoist。key-packはbranchless、key-maskはgeneric/capもextra[]に入れる、mdp-cacheは列ごとの正確系列cache16→64。
日本語進捗60秒程度。subagent禁止。最終3者old/seven/candidate + nofb tail比較推奨、記録2000+save-design。凍結後500-999 replay8。REPORT日本語、GCCとClang出力一致最低200、source<=520000。時間固定・fallback禁止。

12:09更新:
- 品質train: mix-climb -0.00774±0.00766%、mix-match +0.01818±0.00730%、mix-perf +0.04103±0.00650%。残り4案replay待ち。基準113720。
- 完了GCC出力250/250一致: cap-late, cap-once, eject-right, perf-copy, eject-simd, filler-pack。速度は全て有意な短縮なし/悪化。summary.log/json参照。まだClang確認していない。勝ちそうなものだけまとめてClang200以上。
- map-speed114420(4solvs)はコンパイル完了、評価待ち。key-speed114857(3solvs)も待ち。map-bits1154xx(2solvs)も待ち。
- 新規exact: eject-simd115122 (vector必要条件4枚、全一致、req差-0.00029±.00214で不採用)、filler-pack115152(全一致、req+3.53ms)。map-bits(表展開→可変シフト),map-pending(さらに空pending store省略)。
- 近似逆数anneal: reciprocal batch normal115015(old/seven/nofb/recip)完了、replay待ち。make_anneal_recip.py、session4664。
- warm batch(session22187): warm9(base7+穴保存再仕上げ2回)、warm7(追加j1のみ穴保存、他普通)、warm10(追加6回、通常/穴保存交互)。make_warm.py。自然マスクをperforation.allowedに戻して穴の復元も可能に。climb/Hungarian前半を省き、前の物理穴をunit→dedで移す。
- req-search(session32185) 500×4設計固定、7者比較。plan3/plan4(PLAN_SHORTLIST3/4),anchor3(ONE_ANCHORS3),slack125/PROMISING_SLACK1.25,slack040/.4,round3(NS_ROUNDS3)。ログreq-search.log。
- req-value(session81345)500×4設計固定7者: end90/end95(kEndWeight),next25/next75(COLMDP_NEXTMIX),demand15/demand35(kFillerDemandWeight)。ログreq-value.log。設計に影響しない。
- summary.pyは完了したspeedログを集計しstdout完全一致確認、experiments.jsonlからfresh/all/realと同時通常time計算。flock下で再実行するとsummary.json/logが更新される。profile_summary.py修正済みcfprof_*_exc/_inc出す。profile-summary2.log。
- 軽いquick.pyは500未満のみ、JSON集計(<0.2CPU秒)なので直実行可。重い分析と出力一致検査はflock。キューは多いが全てflockで24並列評価と重ならない。
- プロファイルcurrent96cases: request exclusive filter .0898,eject .0649,next_cost .0551,replay .052,evaluate .048,post .0415; map cycles ev_simd480/total1646、pending221、key144、sort162。既存Task3badblock/blockbadは表示誤色マスク先計算を試済み・効果なしなので再試行しない。
- GCC arch pragmaを付けるだけではjudgeの-march=nativeでは得しないため試していない。実仕事を減らす速度改善を優先。

12:42更新:
- gatherのみ有望なexact speed: GCC114420窓-9.797±2.346ms、Clang121916窓-12.433±2.155ms。stdout両方250/250完全一致。summary.json参照。
- 他speed全250/250だが短縮なし: mapkey(+11ms),mapbits(+9),mappending(+29),mapcyclic(+34),mapdefer(+50),req各案,perfcopy,Vint/skipDP。Vcapacity(25特化、shiftsは63のまま)123236比較キュー。
- design train113720比較: mix-climb -0.00774±.00766、mix-match+.01818、mix-perf+.04103、mix-finish+.04159、kick2+.00582、kick6+.00960、beam+.00096、anneal-recip+.03038(速度なし)。experiments.jsonlに全runとnormalrefs。
- old warm試験: warm9追加2warm -0.02032±.00381、warm7(j1warm置換) -0.01447±.00513、warm10(通常/warm交互6extra) -0.03454±.00590%。normal115814: helperdelta+26.75/-12.77/+42.85ms。**穴復元のバグ**あり: paper=旧穴付きでPerforation.allowedだけ自然マスクに戻したためinstallは復元不能、旧穴黒色も0。出力合法だが意図と違う試験、finalには採らない。報告で区別。
- warm-fixed batch37712 normal122923: warmfix9/7/10はphysical natural紙を保ち、h_opqだけ旧穴にしてPerforation開始、allowed自然maskなので復元が正しく物理反映。warmadd9は旧physical紙を保ち、allowed=oldopacityなので追加穴だけ、復元なし。全結果待ち。
- late batch87921 normal122720: late9/12はbase7+late Hungarianのみ2/5回。latemix10はfull,warm,full,late3。**latemix10 mode2はoldwarmbugを含む**、採用時要修正。late9/12には復元バグなし。
- initial batch54317 normal122419: 最終V選択後の列内初期順序の最適化2種。MDPは完全状態のF最小type列、同typeはfiller込みweight順。rankは色内weight順と2色interleave小DP(次注文cost)。DesignStore前に物理紙IDとded更新、replayは再計算なし。source518041/518090。結果待ち。
- req-search115919完了: plan3全4=-.009382±.000950、req+10.90ms; plan4はmode4が2と同条件なので完全同点; anchor3+.000716; slack125-.000230; slack040+.002310; round3-.003184±.000469、req+4.07ms。req-value120658(6variants)実行中。
- 新 terminal1/4/16: 最後h注文でfuture_discount=min(1,remaining/h)、filler chargeとend next価値両方へ。orders_doneは提出も有効、時間と無関係、探索予算同一。session96044、terminal.log、make_terminal.py。500×4保存設計で比較。
- summary.py最終requestログにterminal追加、speedログにvcap-speed追加が必要。summarizeはflock下。最終2000用集計はquick.pyではなく別script(quickはseed<500固定)。最終凍結test500-999は未着手。
12:53補足: 初期順序normal122419はMDP -0.04595±.00640%、rank -0.04567±.00653%(元の列)。追加時間MDP9.60ms/rank0.481ms。MDP replay124609はfresh-0.03672±.00248%、rank124912待ち。sourceパターン保持とded対応check_initial_designs.py、最初何注文で効いたかanalyze_initial_prefix.pyをflock待ち。
組合せordered batch32455 normal124749: warmfix7/9 +gather+initial-rank =>ordered7/9、518020bytes。ordered8 batch60814 normal~1250: warmfix7 extra4, warm j%2==1、518022bytes。
terminal初回はRがmain-localなためcompilefailed。total_ordersメンバとmain読込Rの代入で修正、再run124904/session58608。compile失敗runはpahcerが自動削除。combine.pyも修正済み。
Vcapacity123236は外部負荷平均1.107coreあり、かつV時間+0.17msで改善なし。不採用。summary/reportに警告を付ける。
final_metrics.pyはnormal2000(ref old,sevens/nofb/candidate)とtest500-999×8の集計、sourcehash/DesignStore stdout一致、全4000リプレイ注釈error検査。normal source凍結後に使う。final未着手。
12:59: initial-rank replay124912 fresh -0.0366697±.0025197%、MDPとの差+.0000516±.0007042%。rankを採用方向。初期順序normalの改善はfirst16:-1.550手、16–64:-2.062、64–256:-1.070、256–1024:-.014、合計-4.696±.670手。check_initial_designsで両案500/500: 列ごとの紙模様multiset、ded target紙模様、他designstate全一致。
late9 replay125253 fresh-.003120±.001996%、追加2lateの効率小。正常timing122720 helper+~.012、late12+~.037。oldwarm*とlatemix10のREADMEに復元不反映の注記追加。
run.pyの未使用DEVAL_GUARD_TEST/STRESS分岐を削除(今回未使用、通常のcompiler flagsは不変)。
13:22重要更新:
- ordered8 replay130357 fresh -0.0594303±.0056318%、all-.0606129、real-.0688616±.0126595。Normal125001old,125001seven,125002nofb,125002ordered8: judgeold1.581962956、candidate1.708792786 =>1.08017、p991.8703266 vsnofb1.8922603。source518022。candidates8固定500/500。dv_chosen {7:181,5:114,6:64,4:60,3:24,0:21,1:19,2:17}。warm2候補59%。
- ordered7 replay130834 fresh-.0468671±.0053561%。normal124749judge1.6940/old1.5876 =>1.067、p991.8580<nofb1.87167。ordered9はnormal1.7375/1.5876=>1.0944だがp991.8951>nofb1.87167なので除外。
- warmfix9 replay130134 fresh-.0249968±.0036802%、修正後も効く。warmfix7 replay131027完了。warmfix10/warmadd9 replays待ち。oldwarmバグ版は採らない。
- terminal1/4/16 fixed設計compare124904完了。全4列 -0.0000776±.0000394 / -.0000922±.0000646 / +.0004236±.0001574%。実質効果なし、**全部不採用**。terminal-prefix検査scriptはまだ実行しなくてよい(不採用)。
- 最後の追加確認: deval-ordered8-plan3 (518083bytes)、ordered8にF3_PLAN_SHORTLIST=3だけ追加(単独測定で-.00938%、req+~11ms)。plan3_combo.py session39109、normal131957(old,seven,nofb,candidate)500と、125002ordered8保存設計からordered8/candidate同時500×8を順次。plan3-combo.*ログ。完了時experiments.jsonlへnormalrefs+request_referenceを記録。もしp99/meanが足りなければordered8採用。**まだソース凍結・test500-999・最終2000は未着手**。現状有力ordered8。
- 最終normalは old,seven,best,nofb の2000、--save-design、**--no-record無し**。まず時間条件を確認してから500-999×8replayを開始(112011seven比較)。最終再評価前にsourceSHAをfreeze.jsonへ。READMEは最終内容を日本語で具体化してからsnapshot。
- final_metrics.py: normal2kとtest500–999×8集計、sourcehash/normal-replay stdout500一致、全4000のself_wrong/op_label_errors等0assert。実行はflock。render_report.pyがfinal-metrics.json+EXPERIMENTS.mdからREPORT生成、実際のGCC/Clang提出build成功は別途必要、builds.jsonに残す。
- summarize.pyはvcap-speed/terminal追加済、outside_loadも保持、report_tables.pyは外部負荷†。完了残りすべてを反映してflock summarize → report_tablesを再実行。
- 全作業はTask4新規dirsだけ。sharedSTATE/trial_log等編集無し。userに日本語進捗~60sec。Task4開始11:36、目安14:40〜15:00、13:22時点まだ1h20ほど残り。達成milestone(.05+最終確認)なら早く停止。

13:50 最終完了（追加実験不要）:
- 採用版はdeval-ordered8。source 518022bytes、SHA256 4d20a050f699138fc26b3eb52d3bbd83cc4a46a9782be03a5750342745fb0d37。13:31:30凍結後、main.cpp変更なし。
- 記録済み通常2000件比較20261107-133130: argon-des-perf-latew105 / deval-seven-wide / deval-ordered8-plan3 / deval-vbranch-nofb / deval-ordered8。全件完了、外部負荷0.116/0.375core、E/不正表示0。
- 事前に定めた時間条件だけで選択。plan3のp99 1.876289秒 > nofb 1.869711秒のため不採用。ordered8のjudge平均1.709060秒、old比1.0768009、p99 1.865724秒で合格。最大2.033501秒、2秒超え2/2000件。全8候補固定、時間fallback無し。
- 通常2000件score差: seven-wide比 -0.0635826±0.0066055%、1194/24/782。old比 -0.2874448±0.0163258%、1303/10/687。
- 未使用500–999×8再評価20261107-134239_deval-ordered8、基準20261107-112011_deval-seven-wide。fresh1–7 -0.0587166±0.0057983%、moves/order -0.00590179、355/2/143。all8 -0.0563059±0.0056343%。real0 -0.0395210±0.0126521%。0.05% milestoneと時間条件を達成。
- DesignStore normal/replayの列0 stdout500/500完全一致。最終normal/replay/currentのsource一致。全4000 replayの表示誤り/注釈不整合0。
- 採用speedのgather: GCC250/250、Clang250/250 stdout完全一致。map短縮9.797±2.346ms / 12.433±2.155ms。
- 提出ビルド GCC13.3 / Clang18.1.3、C++23 -O2、さらに-march=nativeも全て成功。各ビルドflock、実行は無し。builds.json/builds-native.json、ログ保存。生成binary削除済み。
- 最終REPORT/README/metrics/build/source auditはsolutions/deval-ordered8内。全試行・再現scriptはこのdeval-next内。共有STATEは13:45:58に再読、最新11:45で変更なし。共有STATE/trial_log/scriptsは編集せず、commitなし。
