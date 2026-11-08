# Task7 セッション継続用

作業開始 2026-11-08 04:03 JST。phase1のみ、締切13:00 JST。ユーザーの全条件はPROGRESS/READMEと会話参照。書込は新しいlns-*のみ、legal-*は一切読まない、コミットなし。注文処理はhelper-wideから一字も変更しない。研究評価 --no-record、ビルド/重分析 flock + nice、全ケースstandardrunner。

## 現在

- 設定選択は seed0–99 で予備測定中。seed500–999はまだ使っていない。
- baseline train500 replay = 20261108-040819_deval-helper-wide。
- 初期足場の0追加探索: GCC out200/200一致(041551_helper-wide/lns-star)。Clang normal200同点完了(043202_helper-wide/043203_lns-star)、ファイルidentity.pyの確認をまだ出していない。
- pilot結果は `pilot_table.py` / `pilot-table.json`、対応runは各 pilot*.json。詳細PROGRESS。
- 初期最良warm/coolの最終窓は100/100不変。スコア改善は再annealが主因。真の新近傍成功とは扱わない。
- 真の大きな変更は full star、初期に解放した全ペアを解放し続けるjoint、cutoff28+mapでの厳密増加路+マッチング引継ぎ(graph)、比較紙cut一括極性反転(cut)を試す。
- 共通ロックの待ちがかなり長い。別execのPID namespaceからps/--statusは所有者を見られず「なし」と誤表示することがある。共通flockは守る。lockファイルの最終記録だけではcompiler/分析の所有者は分からない。別agentのディレクトリを調べない。

## ソース生成

`make_source.py` が helper-wide + `.inc` から lns-star/main.cpp を作る。
`variant.py NAME --steps N --mode ...` が既定設定・config.json・日本語READMEを持つ研究版を作る。
現在の新規ソースは約550KB、サイズ制限無視可。
- mode1: star/subset window destroy, unconstrained regional map SA, pairing/columns repair, anneal, finish/V
- mode2: extra branches from shared prefix
- mode3: extra refinishes
- mode4: independent full original pipeline (new map RNG salt, shared+4branches+4refinishes)
- mode5: reheat best finished assignment, no window change
- mode6: fixed root assignment, invert polarities across one of31 sheet cuts, no map SA, pair/column repair
- LNS_MULTIPLIER default1 multiplies additional step count, so multipliers1,3,7 approximately2x,4x,8x design budgets.
- LNS_RELEASE_MODE 0 frees only pairs invalid after map;1 keeps initially broken pairs free;2 all pairs differing on region;3 all products.
- LNS_KEEP_COLUMNS keeps unchanged pairs/singles in unchanged-handle columns.
- LNS_MAP_EXACT repairs greedy shortages with Edmonds cardinality augmentation; LNS_CUTOFF28 expands map edge pool, LNS_MISSING2 lowers temporary deficit penalty. LNS_USE_MAP_MATCH passes map's chosen71 pairs to column repair.
- LNS_VERIFY_MATCH checks512 random small graphs against exact subset DP, executed throughnormalrunner, not directbinary.
- All original helper/request/perforation/V code between Helper tables and Design iteration counts is identical modulo blankline and inserted research dumper at end. Actual Solver::process never runs during design.

## Exports

LNS_DUMP_DIR root, LNS_DUMP_IDS comma IDs. Generated variants append their source name belowroot.
- 0..7 initial currentpipeline candidates.
-1000 incumbent before extra work;1001+j incumbent afterstepj
-2000+j bestcompleted candidate ofstepj
-3000+j raw candidate before finishing
-4000+j rawparent,5000+j finishedparent
- On repair failure exportedcandidate duplicatesparent with lns_export_failure=1.
`prepare_artifacts.py DIR --source RUN` writes metadata only inownedlns-notes. Then standardhelper-wide `--design-from ABS_DIR/candidate-NNN --orders8`. Do not use --extend forartifact sources.
`diagnostic_metrics.py TABLE --output FILE` computes within-case V r, split-half reliability/SpearmanBrown, slope, raw/finished improvements. Run underflock nice with OPENBLAS_NUM_THREADS=1.

## Ongoing/queued work (check logs/status/results)

- pilot-joint normal prefix042651 (joint2/open2/joint-long); replay batch session7766, log pilot-joint-replays.log. First2 replays043440/044642, third pending.
- pilot-control normal prefix043049 (map2/anneal2/fastbranch2), session54773. Replay batch session89835 waits thenruns.
- pilot-reheat normal043340_lns-reheat2 completed100; replay session47671.
- pilot8 normal044655 (warm-study/cool-study/joint-study/full-study), session47236, multiplier7 andexports underpilot8-dump. Replay session61366 waits normalthen4 replays.
- pilot-graph normal045302 (graph2/graph-warm2), session17302; replay session92463 waits.
- matching-check normal045736_lns-star session78538 (512DP checks x24 cases, actualgraphrepair); checkWA/assertions.
- pilot-cut normal run prefix inpilot-cut.log (source cut2/cut-cool2), session2026. Replay not yetqueued: readrunids first.
- Clang identity normal200 complete (session70932), fileidentity.py check needed.
- source generator has since addedcut/selftest andstats; snapshots ineach run areauthoritative. Onlyfinalfrozen source mustmatchacrossbudgets/test.

## Next

1. Finish reading fresh100 results andtime(allresearchno-record). Don't pickonrealorder0. A fewloads warned; repeatfinalmeasurement.
2. TestbesttrueLNS versusstrongestcontrolatlarge8x. Existing100 controlfull2 −.1576±.0350%; bestwarm/cool −.13% butunchangedwindows. Reheatcontrolimportantablation.
3. Decidealgorithm/settings on0–499 only, preferablyconfirmtraining500. Freezeownfinalsources/configs. For2/4/8 same-source comparison useexperiment.py with LNS_MULTIPLIER1/3/7. Measureactualdesign time ratios; makecontrolcomputeclose, notjustnominal.
4. Baselineheldout500–999 helper-wide from165305 thenfrozen LN/control normal +8-listreplays for500–999 at2/4/8. REPORTa,b,c pairedmoves/order+percent±SE. Goalphase1only, no2000casephase2.
5. Diagnostic candidate replay exports(usecurrentpilot8-dataifuseful; canrunfrozendiagnostic80heldout iftime). Countoldpairsdestroyed/newpairs, truepre/postfinishingandVaccuracy, winningwindowstructure. Showthatwarmimprovementswithoutwindowchangeareordinaryreannealing.
6. Gatefailif largestbudgetgain(LNSvscontrol)+2SE <.02moves/order; ~.05 stronggate. Intermediate: permillisecond comparison1–2x. Stopphase1andwriteJapaneseREPORT/PROGRESS, no phase2withoutuser.

## Tools

`run.py` importsstandardpahcer, wrapscompilerwithflock/nice andstrictsamehashcompilerflagsreuse. Now sys.dont_write_bytecode and PYTHONDONTWRITEBYTECODE=1 set toavoidsharedscriptcachewrites. It wasnotexplicitlysetbefore, cacheslikelyexisting; no sharedsourceedited.
`replay_batch.py` waits meta.status=ok, runshelper-wide8orders, stores tag.json.
`analyze.py` heavyunderflock outputs pairedmetrics+stagediagnostics. `structure.py` comparesDesignStore physicalwindowcodes/pairs. `identity.py` bytescomparesout.
`experiment.py TAG --lns NAME --control NAME --budget2/4/8 --seeds A-B --baseline REPLAY` normal3arms+2replays+metrics, fixedsourcehashrecord.

## 05:55 JST update (supersedes pending items above)

- Clang byte identity checked: 200/200. Matching-check512 DP percase24 allpassed.
- Reheat8 completed normal `20261108-051453_lns-reheat2`, replay `20261108-052305_deval-helper-wide`: fresh100 **−.04359±.00430moves, −.4351±.0429%**. Strong control. It used explicit LNS_STEPS49 because oldsource lacksmultiplier.
- graph2 replay052047: −.00826±.00246moves, −.0823±.0245%. graph-warm2 replaystillpending.
- controlmap replay051037 −.1617±.0672%; anneal051615 −.1352±.0537%; fastbranch053342 −.1067±.0331%.
- cut normal050158/050159 both100/100scoresidenticaltoSOTA, selectednone. Firstcutreplay053411complete, secondpending. Manyexactgraph-cardinalityfailures; seed0 viablecandidatesV+0.20–0.58.
- **pilot8 normal044655 ALL COMPLETE100, WA0,E0, outside.24core.** Freshreplaysinpilot8-replays.log pending. Typicaldesign8×; realscore0(notselection) warm−.247%,cool−.286%,joint−.082%,full−.421%. Do not chooseonlist0. Actualdesignstages queuedanalysis `pilot8-normal-metrics` session88858.
- `diagnostic-joint` session63670 waitingthenreplays12 artifactsets from pilot8-dump/lns-joint-study:0,1,2,3,1000,2000..2003,3000,4000,5000. It began artifactmetadata afterpilot8complete. log/table diagnostic-joint*. First4LNScompleted+baselinebranches Vranking, firststep truepre/postfinishing. `export_replays.py` orchestrates standardhelper-wide replays andflockanalysis. No requestsrunoutsidepahcer.
- `REPORT.md` now **explicit draft**, methodologyonly, nofinalgate. Needreplacefinaltable/conclusion.

### New source mechanisms (all owned .inc/make_source.py)

1. `LNS_TRANSFER_HOLES`: extra warm finish retaining genuine parent extra perforations mapped throughphysicalwindowindices. Rawpairholes excluded, newpair usesintersectionofoldextras, clippingtolegalaboveanchor. Alreadybuilt variants graph-warmhole/cut-warmhole beforeothernewsourcechanges.
2. `LNS_PREFERRED_PAIRS`8 in lns-preferred: choose disjointshortnewpairs notcompatibleinparent butacyclicoutsidechangedregion; rewardtheircompatibility .15 perpairinwindowrepair; validonespriorityinpairrepair. Actualfinalgraphmustbelegal. No old-pair loss screens.
3. `LNS_SOFT_PENALTY`1 inlns-soft: matchingduringwindowSAincludesincompatibleedgeswithfinitepenalty=max(1,oppositecomparisonarcs)*3600*weight; capped17bitkey. Returnbestvisitedfullycompatiblematchingpreferentially; final repair alwaysstrict realgraph. This removes large temporarypair-countwalls withoutallowinginvaliddesigns.
4. `LNS_MIN_WINDOWS`2/6 inlns-distinct2/6: recordbestwindowstate physicallydifferentfromparentbyatleastN windows. Proposalsnotrestricted. OriginphysicalcodescomputedfromparentDesignState, comparecurrentmask/polarityviainitialpermutation. Preventsrepairreturningoriginalwindowseverytime. Distinct2=2groups,nohandles,7steps; distinct6=fullstar+4handles,5steps.

Variant.py now accepts --preferred/--preferred-weight/--soft/--min-windows, --transfer inadditionpreviousargs. Evaluatedsnapshots remainauthoritative; oldvariantswerenotregenerated.

### New queued/running pilot jobs

Alltraining0–99, allnormalresearchno-record+save-design; allfreshreplayshelper-wide8lists.
- warmhole normal052019: graph-warmhole,cut-warmhole; replaybatch session45123.
- preferred normal052707_lns-preferred session44187; replaybatch91102.
- soft normal053221_lns-soft session56133; replaybatch18436.
- distinct normal053726_lns-distinct2/6 (baseline053725), session22832; replaybatch95618.
- long8 normal053758_lns-map8/lns-anneal8, session7162; replaybatch10941. Base-map7.8M /base-anneal226.95M, noextraLNS. Importantstrongestcontrolscreen.
- pilot8 replaybatch61366 (4arms).
- cut-normalanalysis56859, completed? checkJSON.
- pilot-controls-metrics2540 completed.

### New analysis tools

- `analyze.py` now addsreference stage means/ratio/pairedtimedelta (normalforcompute), max; oldJSONlackfields.
- `winning_changes.py` joinsphysicaldesigndeltaswithfreshscores; hashesoriginalinputbarcodes toDesignStore filenames; recordswindowchanges,pairs,extraholes,targetcolumn,modelparts. Descriptiveonly, notcausal.
- `collect_pilots.py` loopscompletedpilot*.json andcreatespilot-consolidated.json withnormalandfreshmetrics. Invokeunderflocknice; notrunyet.
- `pilot_table.py` includes allnewtags.
- `diagnostic_metrics.py` includesbase+LNSgroup, Vvsbase and4-listselectorvsbase onlists4–7, raw/finishedtrueimprovement. Alsoobserved/noisecorrectedSD. Notrunyetuntilartifactsreplayed.
- `PROGRESS.md` updated05:47. No heldout500–999usedyet. No frozenfinalsourcesyet. Continuewaitresults, no needmoreideasuntilpendingcomplete.

## 06:20 update

- pilot8 freshallcomplete: warm055116 −.3590±.0420%; cool055558 −.3242±.0325%; joint055948 −.1776±.0350%; **full061356 −.5320±.0550% (−.05330±.00551moves)**. Fullstrongestcontrolpointestimate. Warmvsreheat100pairedgainupper2SEonly.00084moves, farbelow.02gate, butneedfrozen500test.
- Newfresh: graphwarmhole055726 −.0869±.0252%; cutwarmhole0608490; preferred055328−.0002±.0120%; soft−.0563±.0260%; distinct2 060052−.0201±.0104%. Distinct6pending.
- pilot8-normal-metrics complete: baselinehelper_end1.070556; warm8.286517/full8.284131 exactlymatched(7.74×); cool8.024848; joint8.227995. Joint3500steps: destroy47.51, aftermapbroken13.58, free153.55, newfinish18.91, windowchanges7.68, map9.84→10.13, Vbetter3.54%. Warm/coolactualwindowchanges.0114/step. Globalproductregionexpansionjoint.34%, mostlyregionfixed.
- **Last new repair** lns-deepmap2/6 created, normal060218 (session44765), replaybatch68074. map150k, steps2×multiplier7=14; minchanged2/6,release1,keepcols1,AI2M,3finishes. Additionalfixed-prefixexports1002/1006/1014 underdeepmap8-dump; @lns_prefixrecordsdesignclockaftereachstep. Idea:20krepairunderoptimizedgobjby.29;testadequatelongrepairbeforegivingup. Source notsameasoldstudies; make_sourcecurrentincludesprefer/soft/mindistanceandprefixclocks. No phase2work.
- **Control audit surprise:** longmap8 manycases7800000iterationsbutonly~21000exactcandidateevaluations(map.27s vs7sothers). Allallowedcandidatescanbetabu; tabuusesacceptanceepoch, optionsareconsumed, noacceptancecannotexpiretabu ⇒ deadendwastesremainingdraws. RegionalLNSunscreeneddoesnotusuallyhaveemptyneighborhood.
- `lns-map-free8`: copiedlns-map8 onlyaddsresetifit-last_accept>=4*stall && !escape_valid: epoch+=kTabuAccepted+1,resetlastaccept,screen_dirty,path_active,escapefloor. Stillfixediterations,oldloss-screen/objective. Countermap_tabu_resets. **Onlycontrolaudit**, no2svariant/integration. Normal061226 helperwide/oldmap8/free8 (session16997), replays11164. Oldlong8run053758hadoutsideloadwarning.66core4.38max; repeataddressesit. Fresholdlongmap060743−.2480±.0674%, weakerthanfull. Fullcompile2sololdreused,newpending.
- Existingplainstar2(noinitialreleasedpairsretention)needs8×comparison, notnewalgorithm. EnvLNS_STEPS35 normal **061944_lns-star2** session43170, replayjustqueued. Oldsourcehasnomultiplier.
- `collect_pilots.py` queuedunderflock, createspilot-consolidated.json normalandfreshallcompleted. Re-runatendfornewdata. analyze.py now includesfailurecounts/allattemptmeanoldpairs, reference stage means/ratios.
- diagnostic-joint 12artifactreplays currentlyfirst4branchesdone:055121/055621/060010/061417; rest1000/2000–3/raw3000/parentraw4000/parentfinish5000pending. MetricsincludescompetitiveVwithin.05ofbase,andwithbase4-listselectorvsV,SDnoise correction. Somefunctionsaddedafterlaunchscriptbutdiagnostic_metricsloadedonlyafterallreplays.
- `REPORT.md` isdraftonly. PROGRESSupdated06:14(lastimportantfull8resultshouldappendsoon). No500–999dataused. Nothingfrozenyet. Needwaitdeepmap/star8/controlaudit, choosebestLNS+controlontrain, confirm400/500trainifuseful, freezeand2/4/8final500–999. Haveuntil13:00, current06:20, amplebutqueuelong.

## 07:03 JST continuation — SOURCES NOW FROZEN

- Settings frozen **06:53:55 JST** in `heldout-frozen.json` BEFORE reading any held-out result. DO NOT edit/tune these sources:
  - `lns-star-study`: new copy of old `lns-star2`, only multiplies LNS_STEPS by LNS_MULTIPLIER. Defaults5, so5/15/35steps. Primary authentic destroy variant, best training point estimate.
  - `lns-joint-study`: initialbrokenpairs remainreleased, same5/15/35. Stronger regionrelease ablation.
  - `lns-warm-study`: kick0, same5/15/35, mostly no windowchange; ablation, NOT claimed large-window success.
  - `lns-full-study`: mode4, extra1/3/7 complete independent pipelines. Strongest training control.
  - helper-wide SHA also recorded. Configs embedded in manifest.
- No further candidate settings are to be chosen from held-out results. Report all 3 LNS/ablation curves and main star versus full. Joint diagnostically strict release, though repair can expand productregion rarely; disclose this. Window region alwaysfixedoutside; globalcolumnanneal/finishing allowed afterrepair.

### New completed training results

- star8 normal061944_lns-star2, replay063335_helper-wide: **−.02000±.00372moves, −.1993±.0370%**. Better point thanjoint−.1776%, muchweakerfull−.5320%.
- deepmap2 normal060218, replay063232: **−.01133±.00303moves, −.1133±.0302%**.
- deepmap6 replay064440 nowcomplete: **−.00626±.00195moves, −.0623±.0194%**. Waspendingatfreeze, excludedbeforeseeingresult. Remains trainingtableonly.
- map-free8 repeatnormal061226, replay063448: **−.02878±.00637moves, −.2871±.0636%** vs originalmap8−.2480±.0674%. Do not integrate into2s; onlycontrolaudit.
- `pilot-winning.log` session79419 COMPLETE. JSONs `pilot-{warm,joint,full}-winning_changes.json` and `...-label_changes.json`.
  - warm:100/100samecomparatorwindows, +3.91newpairs, total−.03599; handlelabels−.03771, dig+.00382.
  - joint:17/100selecteddesignschangecomparatorwindows; conditionalmean6.53windows,15.47pairs, true−.04239moves. Whole100mean−.01781; handle−.01799, dig+.00391.
  - full:83/100changecomparatorwindows; conditionalmean50.72windows,54.01pairs,true−.06422. Whole100−.05330; handle−.05418.
  - Labels descriptive, notcausal. Windows metric is physical comparison group/polarity; column/handle order is a different change.
- Important correction in PROGRESS: joint `map_before` is post-destroy **220.2195**, afterrepair10.13365. 9.842639 is undestroyed warmbaseline startingobjective, NOT directlyrecordedjointparentvalue. Prior shorthandparent9.84wasapproximation. Reportaccurately.

### Active final pipeline / sessions

1. **Finalgrid session49252**, log`heldout-grid.log`, script`final_grid.py`.
   - Budgets2,4,8, **500–999**, normalcompare helper-wide +star +joint +warm +full, research`--no-record --save-design`.
   - 2x normalIDs **20261108-065356_{deval-helper-wide,lns-star-study,lns-joint-study,lns-warm-study,lns-full-study}**. As of07:00 waitingcompiler/evaluationlock.
   - Then4 helper-wide8-list replays, writes`heldout-b2-replay.json`, addsrecordto`heldout-runs.json`, heavyflocknice analyses normal/baseline/paired. Repeat4xthen8x. Sources checkedhashbefore/aftereachnormal.
   - Outcomes in`heldout-b{2,4,8}-{normal,baseline,paired}-metrics.json`. Paired reference isfullcontrol. Mainmetricsstar candidate−control. Gate improvement=negative ofthat; failif improvement+2SE<.02 at8x. All3LNS likelyfail; don't decideuntiltestdone.
2. **Heldoutbaseline session19506**, `heldout-base.log`, run**20261108-065042_deval-helper-wide**, fixeddesign165305,8lists500–999. Inqueue. Noheldoutresultsreadbeforefreeze.
3. **Finaldiagnostics session41612**, `final-diagnostics.log`, `final_diagnostics.py` waitsheldout-runslen3thenunderflocknice:
   - sourceauditallfrozen;
   - budget8 structurevsSOTA for4solvers;
   - starlabels vsSOTA andvsfullcontrol.
   - results`final-lnssolver-structure.json`, `final-star-labels-vs-base/control.json`.
4. **Cloneidentity session40356**, `identity-study.log` runs200casesGCCthen200Clang oldstar2vsstar-study withmultiplier1; researchno-record. NormalGCC**064701_lns-star2/star-study** inqueue.
   - `identity.py` now returnsnonzeroonmismatch; oldtestsremain200/200.
   - Results`identity-study.json`; verifiesbothcompileridentityfortheone-linebudgetmultiplieraddition. Do noteditclonesourcewhilequeued.
5. **Starcandidate diagnostics** normal session71917 run**20261108-064923_lns-star-study**, log`star-diagnostic-normal.log`. Fourstepsonly (fixedprefixof35), dumpsall20nativefinishes0..19into`star-dump`. Samefrozensource. No parameterschosenfromit.
   - orchestrator **6375**, `diagnostic-star.log`, script`star_diagnostics.py` waitsnormalcomplete;
   - `group_star_artifacts.py`: groups3finishes perLNSstep byrecordedV intoIDs2000..2003, bestoriginal8→1000, baseline4retained. Writes`star-grouped`, flagsfailedrepairifno3files.
   - Verifiesbyte-identicalDesignStatebody ofbaselineIDs0..3,1000 withjointdiagnostic artifacts100cases. Ifidenticalreuse5existingreplays; new4LNScandidatereplays viahelper-wide8lists.
   - Then`diagnostic-star.json` / `diagnostic-star-metrics.json` usingdiagnostic_metrics.py.
6. **Jointcandidate diagnostics session63670**, log`diagnostic-joint.log`, currently0..3,1000,2000..2002completed;2003/raw3000,parentraw4000,parentfinished5000pending.
   - Normal/source044655_lns-joint-study, dump`pilot8-dump/lns-joint-study`.
   - Scriptmetricsupdatedtoassertallorder_scores>0, includeexportfailurecounts, firststep truebefore/afterfinishing andsuccessful-onlyfraction.
   - all12replays→`diagnostic-joint-metrics.json`.
7. **Finalpilotcollector session5746**, log`collect-final-pilots.log`, waitingdeepmap6completionthenflocknice`collect_pilots.py`, then`render_training.py`→`TRAINING.md` all36ishpilots.
   - Oldcollector48980completed, oldreplaybatchesallprobablycomplete; do notduplicate.

### New scripts / validation

- `source_audit.py` verifiesexacttext forrequest/MDP/helper/perforation, DesignStore+main, column/rematchprimitives, andnowVbody. ExistingauditJSONfirst5sourcesidenticalrequests.
- `render_training.py` turnsconsolidatedcacheintoTRAINING.md withalltrialtime,gain,runids,repaircounts. Notatesttuningstep.
- `final_grid.py` manifestcontainsfrozenUTC andconfigJSON; allcaseexecutionsstillstandardpahcerthroughrun.py wrapper. `final_diagnostics.py` onlyanalysis.
- IdentitymetadataalreadycompletefootingGCC/Clang0extra200, Blossom512randomDP24cases, sourceauditunchangedrequests. Newidentityactual5stepGCC/Clangpending.
- `REPORT.md` STILL DRAFT. Needsfinaltesttables(a,b,c)permoves/%±SE, actualdesignsecondsratios, gateupper2SE, diagnosticsVranking+finishing, bestchangedcases/labels, fulltrainingtableslinkandlimitations, phase2recommendation. No2sphase2workor2000casecompare.
- Heavyanalyses/buildsflocknice, requestsallhelperwide, nolegal-*directoryreads, nootherfileedits. Sharedqueuelong; statuscannotseeotherPIDnamespaces, trustlockandcompletedmeta/resultonly. Lastactiveexternalevaluationbegan06:46, allowedwaituntil13deadline.

## 07:44 update — CRITICAL diagnostic-path issue fixed, frozen main evaluations valid

- All ORIGINAL artifact replays in `diagnostic-joint.json` and `diagnostic-star*.json` are INVALID: everycase score0, `design_store_error: no saved design /home/sato/ahc074/runs/candidate-NNN/design/hash.txt`. No V correlation/finishing statistic was everused; newpositive-scoreassert in diagnostic_metrics caughtit. Main normal/replaysuseordinaryrunsdirectories and arevalid. DO NOT useoldartifactreplayresults.
- Rootcause:standardpahcer design_source acceptsabsoluteartifactpath, butreturnsbasename; arm_env reconstructs runs/basename/design. `run.py` NOW wraps onlydesign_sourceforownedlnsartifacts tokeepabsoluteparentpath inmeta.design_from.run. Normalrunpathsunchanged. No sharedscriptorCPPmodified. `replay_batch.py` nowassertsallorder_scores>0 beforewritingrow.
- Correctedpathsmoke **20261108-074006_deval-helper-wide**,4cases×2orders artifact1000:allpositiveandSOTAexactscorematch. `artifact-smoke-check.json`.
- **Repairorchestrator session50610**, `repair-diagnostics.log`, `repair_diagnostics.py`: smokeverified,thenreplays12jointartifacts undernewtag`diagnostic-joint-fixed`, runsmetrics`diagnostic-joint-fixed-metrics.json`, then4starartifacts`diagnostic-star-fixed-new`, combineswith5 VALIDsharedbaselines into`diagnostic-star-fixed.json`, metrics`diagnostic-star-fixed-metrics.json`. ThesearetheONLY diagnosticmetrics to use. Expect~5minactualCPUrun plusqueue. Sourceartifactcontentsvalid; parsingpathwaswrong. Originalstarobserver6375 mayfailassertandexit; ignoreoldfailedmetrics, donotrestartit.
- Baselineheldout original065042hadoutsideload2.18coresmax12.33, so rerun**070629_helperwide** (session49839, done) clean. `heldout-base-identity.json`:500cases,4000stdoutbyteidentical, allscoresidentical. Use070629ascleanreferenceinreport; finalgridmanifest065042equivalent.
- b2 fresh500 complete:star071304 **−.00659905±.00112228moves,−.0656452±.01115996%**; joint072617 **−.00680190±.00121159,−.0677284±.0120645%**;warm072910 **−.01729883±.00151245,−.1722605±.0150488%**;full073202 **−.02532338±.00234206,−.2521891±.0232968%**. Allnormaldesignsources065356*. Mainfinalgrid49252currentlyflockanalysingb2 beforeb4normal. Stillfrozen, no parameterchanges.
- Sourcecloneidentity40356DONE:GCC200/200andClang200/200. `identity-study.json`.
- FinalClangfunctional session85370DONE, normal071531helper/joint/warm/full24cases,WA0. Outsideload1.6meansuseonlybuild/legality,nottimingorquality.
- Added `analyze.py --scores-only`:lightresultJSON-onlystats; fulltraceanalysesstillflocknice. `%`newcanonicalfields `pct_orders/pct_orders_se` averageperorderlogratios withineachseed. Existingpctislogofseedmeancost, retainedforcompatibility. Differences~.0002percentagepoints; movesunchanged. Reportcanonicalfield.
- `build_summary.py` NEW:afterall3heldoutmetricsdone, validatescurrentSHA,all500casesandnormalreal-score==replayorder0, generates FINAL_METRICS.json/FINAL_TABLES.md witha,b,c,allablationcurves,actualdesigntimes,gateupper2SE. Alsocompares8xLNSwith4xfullcontrolasrobustnessforfew%budgetrounding; thisismethodpredefinedbefore8xdata, nottuning. Runwhenready, ideallyflocknicealthoughlightJSONonly.
- `final_diagnostics.py` session41612waitsb8records thenstructureandlabelaudit. Unchangedandvalidordinaryrunpaths.
- `source_audit.py` nowalsoverifiesVbodyunchanged. `render_training.py` usescanonicalpct_orders afternewcollector. Collector5746DONE,TRAINING.md allpilotsnowupdated.
- PROGRESSupdated07:44includingbugdisclosure. REPORTstilldraft; needfinal3budgets+fixeddiagnosticresultsbeforefinishing. Deadline13:00, current07:44.

## 08:25 JST update

- Finalgrid49252 still running. b2 all analyses finished08:03. b4 normal COMPLETE, same compare500–999, IDs **080317_helper-wide/star-study**, **080318_joint-study/warm-study/full-study**. 500each WA0/E0, outside .30cores/max1.23. Freshreplayspending; first **20261108-081057_deval-helper-wide** (star) queued. Sharedqueue waits10–20min perturn, do notreadotheragentdirectories orduplicatejobs.
- Correcteddiagnostic orchestrator50610 has3 valid nativebranchsetsdone: candidate000 **074312**,001 **074744**,002 **080358**, allhelper-wide. Remaining9jointsets+4starsetsqueuedsequentially. Only `*-fixed` results valid. No final V/finishingmetrics yet.
- New **finish_report.py observer session23464**, logfinish-report.log: waitheldout-runslen3→flocknice `verify_replays.py`→waitb8pairedmetrics/fixedVdiagnostics/finalstructure+labels→lightJSONonly build_summary/render_diagnostics/render_report. It doesnotexecuteanysolver. ManualreviewrequiredaftergeneratedREPORT. Existingfinaldiagnostics41612unchanged.
- `verify_replays.py` reads all13 mainreplays (12model/budgets+cleanbase),500cases×8, checkspositiveorder_scores and tailself_wrong/op_label_errors/plan_failures/unsafe_plans all0,testerScorematches. Runsunderflocknice. Writesfinal-replay-audit.json.
- `diagnostic_metrics.py` NOW ALSO checks ALL @ops counts=sumScore for every8listartifactcase and all4safetycounterszero beforecorrelations; outputtrace_verified_requests. Correctedorchestratorloadsupdatedscriptwhenreplaysdone. Checkedcounterpresenceonsmokecase. NoCPPchanged.
- New **METHODS.md** precisealgorithm/scope/metrics. **render_diagnostics.py** writesDIAGNOSTICS.md fromfixedvalidmetrics. **render_report.py** generatesJapanesefinalREPORT fromFINAL_METRICS+fixeddiagnostics+structures+labels+audits. All6new/modifiedscriptsASTparsepasses. It hasprovisionalcalculatedconclusionviaactualgate, notpredeclaredoutcome. Needreviewfinalwordingagainstdata; addinterpretationandoutside-loadsummaryifneeded.
- FixedTRAINING.md rendererbug: replaycolumnhadentiremetricsdictbecausecollectoroverwroterunid. Collector now usesreplay_run; renderbackfillsfromtagtables. Allvaluesunchanged, nowreadable. Addedexplicitloadwarningcolumn(normal/replay). Do notusewarnedtimingsforsmallcomparisons. Frozen2/4comparisonsclean.
- `reproducibility.md` updatedwithfinalgridexactcommands/artifactpathbug. `PROGRESS.md` lastimportantupdate07:55 (b2pairedmetricsandstar20%productexpansion). Needupdateafterb4fresh/8data.
- MainCPPsourceshashcheckedagainallunchanged; all39ownedlnsdirsREADMEpresent. No legal-*reads, no sharedsourceedits, no commits.

## 09:43 JST — Phase 1 gate FAILED; finish diagnostics/report only

No new experiments or tuning. Frozen sources unchanged. Main seed500–999 fresh1–7 results are in PROGRESS.md and REPORT.md (main verdict already written). The full generated report will replace REPORT.md after the queued diagnostics finish. Primary star vs full control at 8× is +0.03657171 ±0.00275136 moves/order; improvement upper2SE −0.03106899, so FAIL. Recommend no phase2 and keep helper-wide. All 2×/4×/8× normal and main replays are complete; the normal 8× baseline analysis completed09:32, paired analysis still waiting.

Active sessions:49252 final_grid;41612 final_diagnostics;50610 repair_diagnostics;23464 finish_report. Do not duplicate evaluations. Star artifact2002 completed as091207; last2003 is092910, waiting shared lock. Joint fixed diagnostic is valid and complete. Original nonfixed artifact diagnostics were all invalid and must not be used. final-source-audit and final-replay-audit (52,000case-lists) done. clean-replay-checks done and all byte-identical.

Final star structure is complete:62/500 selected designs change comparison windows;438/500 same. changed group −0.04005±0.00597moves, samegroup−0.02128±0.00189. Windowchanged realwins50/500. Remaining joint/warm/full structures and two star label analyses waiting.

render_report.py now includes rounding mismatch (star3.61% less compute at8×), candidate SD, exact audit counts, broader tried approaches and interpretation of star's window changes. Syntax checks pass. Once watcher23464 renders REPORT.md, manually review all numbers, missing sections and wording, append final PROGRESS, ensure sessions end, then final Japanese table(a,b,c) and no-phase2 recommendation. Stop before13:00.

## 2026-11-08 10:23 JST — CLOSED

Phase 1 complete. All jobs (49252,41612,50610,23464,37808 and the earlier repeat watcher) exited successfully. REPORT.md is the final reviewed report, not the interim main-results version. Gate FAIL for all arms. No phase2/no more runs. Main source hashes unchanged. Final checks: all table/link/source/accounting checks pass; main and candidate load repeats byte-identical. See final PROGRESS entry.
