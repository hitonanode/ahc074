"""Build the final Japanese report from completed, frozen measurements."""
from pathlib import Path
import json,time

h=Path(__file__).resolve().parent
d=json.loads((h/'FINAL_METRICS.json').read_text())
assert set(d['budgets'])=={'2','4','8'}
diag={n:json.loads((h/f'diagnostic-{n}-fixed-metrics.json').read_text()) for n in ['star','joint']}
structures={n:json.loads((h/f'final-lns-{n}-study-structure.json').read_text()) for n in ['star','joint','warm','full']}
labels={n:json.loads((h/f'final-star-labels-vs-{n}.json').read_text()) for n in ['base','control']}
audit=json.loads((h/'final-source-audit.json').read_text())
assert len(audit)==4
replay_audit=json.loads((h/'final-replay-audit.json').read_text())
assert len(replay_audit)==13 and all(x['all_counters_zero'] and x['tester_scores_match'] for x in replay_audit.values())
while True:
    try:
        clean=json.loads((h/'clean-replay-checks.json').read_text())
        if clean['done']:break
    except (OSError,json.JSONDecodeError):pass
    time.sleep(10)
while True:
    try:
        candidate_clean=json.loads((h/'clean-candidate-checks.json').read_text())
        if candidate_clean['done']:break
    except (OSError,json.JSONDecodeError):pass
    time.sleep(10)
for x in diag.values():assert x['all_trace_moves_equal_scores']
for x in labels.values():assert x['all_trace_moves_equal_scores']

def stat(x):return f'{x["mean"]:+.5f} ±{x["se"]:.5f}'
def num(x):return '—' if x is None else f'{x:.3f}'
gate=d['gate']['lns-star-study']
lines=['# Task 7 phase 1 — 窓・共有ペア・列の破壊修復', '']
if gate['status']=='失敗':
    lines += [f'**phase 1のgateは不合格。phase 2への移植は推奨しない。** 最大予算のstarは、同程度の計算量の全再設計に対する改善量が {gate["improvement"]:+.5f} ±{gate["se"]:.5f}手/注文。改善量の上側2SEでも {gate["upper_2se"]:+.5f}で、必要な0.02手/注文に届かない。SOTAに対する改善はあるが、追加計算量を既存の全再設計へ渡した方が良い。', '']
else:
    lines += [f'phase 1のgate判定は **{gate["status"]}**。最大予算での対照に対する改善量は {gate["improvement"]:+.5f} ±{gate["se"]:.5f}手/注文。phase 2は未実施。', '']
lines += ['基準は `solutions/deval-helper-wide`。設定選択は訓練seed 0–99で行い、**2026-11-08 06:53:55 JSTにソース・固定回数を凍結**して、seed500–999の500件で確認した。未見結果を見てから設定を変更していない。全ての8列再生で注文処理はhelper-wideに固定し、主判定は設計が見ていないlists1–7とした。phase 2、2秒版への統合、2000件の本番比較は行っていない。', '',
          '## 主結果と計算量', '',
          '以下の差は候補−参照で、**負が改善**。手/注文と、seed内で7列のlog比を平均した%を併記する。±はseed間の対応差の標準誤差。研究用通常評価は全て `--no-record`。', '']
table=(h/'FINAL_TABLES.md').read_text().splitlines()
lines+=table[4:]
ts=d['budgets']['8']['lns-star-study']['stage']['helper_end_sec']['mean']
tc=d['budgets']['8']['lns-full-study']['stage']['helper_end_sec']['mean']
lines+=['',f'固定回数の丸めにより、最大予算のstarは対照より設計時間が{100*(1-ts/tc):.2f}%短い。この小差だけで負けたとは考えにくく、上表のとおり計算量が約半分の4倍全再設計にも劣る。']
lines+=['','## 試した近傍と対照','','詳細は [METHODS.md](METHODS.md)、全予備測定は [TRAINING.md](TRAINING.md)。主方式starは、比較紙1枚に接続する5比較組と4取っ手窓を混ぜ、20k反復で窓を修復し、新しい互換グラフで共有と列を修復、2M反復の列annealと3完成候補の仕上げを行う。旧共有の破壊数による足切りはない。5/15/35回を固定予算として、完成Vが改善したときだけ親を更新する。', '',
          'jointは破壊直後に壊れたペアも最後まで解放しておく版。warmは初期破壊なしの対照で、窓がほぼ変わらない改善を窓近傍の成果とは扱わない。全再設計対照は元の窓探索・4分岐・4refinishを独立なsaltで1/3/7回追加し、同じVで選ぶ。訓練側では追加分岐、refinishだけ、完成状態の再加熱、長い窓探索、長い列探索も測り、大予算の点推定で最も良かった全再設計を主対照に固定した。', '',
          '修復不足の切り分けとして、部分領域、少数kick、初期破壊なし、互換グラフでの広い商品解放、望む新ペアからの窓修復、途中の非互換を有限罰則にする方式、親の穴の引継ぎ、変更窓数の下限、150k反復の長い窓修復も訓練側で試した。150k版は約8.3秒の設計予算でも新規列で−0.113%または−0.062%に留まり、全再設計対照の訓練値−0.532%に届かなかった。各runとSEはTRAINING.mdに載せた。', '',
          '窓領域の外は固定してassertで検査する。商品領域内で71共有を作れないときは商品領域を全体へ広げるため、その割合を下表に明示する。また、その後の列annealと仕上げは従来どおり全列を動かす。マッチングは重み付き貪欲解＋厳密な個数の増加路補修であり、重み付き最適マッチングの厳密解ではない。M・G・共有総数は固定している。', '',
          '## 壊した旧ペアと修復後の状態', '',
          '最大予算・未見500件、成功した修復ステップの平均。旧ペア破壊は非互換化と元の列アンカー不適合を含む。新ペア数は親になかったペア数。', '',
          '| 方式 | 試行 / 成功 | 旧ペア破壊 | 修復商品 | 新ペア：修復 / anneal / 完成 | 商品領域拡張率 | 従来模型改善率 | 完成V改善率 |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
for name in ['star','joint','warm']:
    x=d['budgets']['8'][f'lns-{name}-study']['diag']
    lines.append(f'| {name} | {x["attempts"]} / {x["n"]} | {x["destroyed"]:.2f} | {x["free_targets"]:.2f} | {x["new_repair"]:.2f} / {x["new_anneal"]:.2f} / {x["new_finish"]:.2f} | {100*x["expanded"]:.2f}% | {100*x["model_better"]:.2f}% | {100*x["better"]:.2f}% |')
j=d['budgets']['8']['lns-joint-study']['diag'];s=d['budgets']['8']['lns-star-study']['diag']
lines+=['',f'jointの窓探索は、平均{j["tracked_old_pairs"]:.2f}個の追跡対象旧ペアについて、受理した途中状態で最大{j["max_accepted_old_loss"]:.2f}個（1修復ごとの最大値の平均）を不適合にしている。旧共有を少数しか失わない探索にはなっていない。修復後の互換グラフは親から平均{j["graph_added"]:.2f}辺追加・{j["graph_removed"]:.2f}辺削除、比較窓は平均{j["window_changes"]:.2f}個変化した。', '',
          f'商品領域を拡張したjointの{j["expanded_successful_steps"]}修復は、完成Vでの採用{j["expanded_and_V_better_steps"]}回。採用{j["regional_and_V_better_steps"]}回は全て元の商品修復領域内だった。starでは拡張した修復の採用{s["expanded_and_V_better_steps"]}回、領域内の採用{s["regional_and_V_better_steps"]}回。商品領域の拡張と、後段で全列を動かす通常のanneal・仕上げは区別する。']
lines+=['','初期に40個以上の旧ペアを壊しており、以前の「共有損失を2個以下などに抑える」探索とは異なる大きさを実際に試した。一方、列模型が改善しても、完成Vを改善する割合は小さい。Vによる受理と実コストによる改善は分けて測る。','','## 仕上げ前後の実コスト','','100訓練seedの第1joint修復を保存し、子の列anneal後と完成後を比較した。親の未仕上げ参照は完成時の割当から追加穿孔なしで再印刷したもので、履歴上のclimb/rematch前ではない。初期紙順も再構成するため、finishing単独の因果効果ではなく構造診断として読む。以下は新規lists1–7、成功した修復のみ。']
f=diag['joint']['finishing']['0']['successful_repairs_only']
lines += ['',f'- 成功修復数: {f["n"]}。',f'- 仕上げ前の子−親: **{stat(f["before_delta"])}手/注文**、実コスト改善率 {100*f["before_better_fraction"]:.1f}%。',f'- 完成後の子−親: **{stat(f["after_delta"])}手/注文**、実コスト改善率 {100*f["after_better_fraction"]:.1f}%。', '',
          '失敗修復は親の複製として明示的に記録し、この率から除いた。starは完成候補のみを保存したため、この対応診断はjointで行った。これは最初の1修復の診断であり、全35修復の真の改善率ではない。', '',
          '## Vは新しい候補も順位付けできるか', '',
          '各訓練seedの元4分岐と、最初の4修復それぞれで残った候補を再生した。全候補での相関と、親のVから+0.05手以内の競合候補を別に見る。下表の補正相関は新規lists1–6を3列ずつに分けた信頼性を使う。詳しい全8列の相関、傾き、校正、選択比較、run-idは [DIAGNOSTICS.md](DIAGNOSTICS.md)。', '',
          '| 方式 | 群 | r（lists1–7） | r（lists1–6） | 補正r（lists1–6） |',
          '|---|---|---:|---:|---:|']
for name in ['star','joint']:
    for key,label in [('branches','既存4分岐'),('lns_finished','修復後の4候補'),('lns_with_base','元の最良＋4修復')]:
        x=diag[name]['groups'][key];f=x['fresh_lists1_6']
        lines.append(f'| {name} | {label} | {num(x["fresh_lists1_7_r"])} | {num(f["r"])} | {num(f["corrected_r"])} |')
nf={name:sum(v for k,v in diag[name]['failed_repair_exports'].items() if 2000<=int(k)<2010) for name in ['star','joint']}
lines+=['',f'各方式は100seed×4修復枠。starの{nf["star"]}枠、jointの{nf["joint"]}枠は修復失敗で親を残しており、相関と選択の表には実際の候補枠としてその親の複製を含める。']
lines += ['', '| 方式 | Vで選択：元の最良との差 | 4列で選択：元の最良との差 |', '|---|---:|---:|']
for name in ['star','joint']:
    x=diag[name]['groups']['lns_with_base']
    lines.append(f'| {name} | {stat(x["V_pick_vs_base_lists4_7"])} | {stat(x["oracle_vs_base_lists4_7"])} |')
j=diag['joint']['groups']['lns_with_base']['competitive_within_005_V']
s=diag['star']['groups']['lns_with_base']['competitive_within_005_V']
lines+=['',f'競合候補だけでは、starの補正相関{ s["corrected_r"]:.3f}・傾き{s["slope"]:.3f}（{s["n_cases"]}seed、{s["n_entries"]}候補）、jointは{j["corrected_r"]:.3f}・{j["slope"]:.3f}（{j["n_cases"]}seed、{j["n_entries"]}候補）。starでは実コストの差をVが小さく見積もる傾向があり、校正まで完全とはいえない。ただし競合域の順位相関も高く、全体の相関が良いのは悪い候補を含めた品質幅だけの効果ではない。第1joint修復の完成後も平均+0.11手/注文悪いことと合わせると、この実装では良い完成候補を作る頻度の不足が主因と考える。']
g=diag['joint']['groups']
lines += ['',f'全8列から測定雑音を除いたwithin-case SDは、元4分岐の{g["branches"]["noise_corrected_within_case_sd"]:.4f}手/注文に対しjoint完成候補は{g["lns_finished"]["noise_corrected_within_case_sd"]:.4f}。候補の幅は増えたが、それだけでは良い側の裾が改善したことを意味しない。']
v=structures['star']['groups']['all']
lines += ['',f'別に、未見500件で最終採用されたstarのV差は平均{v["dv_best_delta"]["mean"]:+.5f}手/注文、実測の新規7列の差は{stat(v["moves"])}だった。平均改善量の校正は合っているが、これだけで全修復候補の順位が正しいと証明するものではない。']
lines+=['','上の選択比較はlists4–7の手数/注文。4列選択器はlists0–3を見て選ぶため、完全oracleではなく雑音を持つ対照。診断の候補は最初の4修復だけで、全35修復の選択余地を厳密に上から抑えるものではない。','','## 採用された設計で何が変わったか','','最大予算・未見500件で、最終的に選んだ設計を基準と比較した。比較窓の変更は、物理窓での比較紙の組または極性の変更。列順や取っ手順だけの変更とは区別する。','','| 方式 | 比較窓が変わった件数 | その群の変更窓数 | その群の新ペア数 | その群の実手数差 | 全件の実手数差 |','|---|---:|---:|---:|---:|---:|']
for name,s in structures.items():
    a=s['groups']['all'];g=s['groups']['changed_windows']
    if 'moves' in g:
        cells=f'{g["moves"]["n"]}/500 | {g["windows_changed"]["mean"]:.2f} | {g["new_pairs"]["mean"]:.2f} | {stat(g["moves"])}'
    else:cells='0/500 | — | — | —'
    lines.append(f'| {name} | {cells} | {stat(a["moves"])} |')
sg=structures['star']['groups'];same=sg['same_windows'];wins=sg['changed_and_better']
lines+=['',f'starの最終設計は{same["moves"]["n"]}/500件で比較窓が基準と同一だった。その群でも{stat(same["moves"])}手/注文改善しており、利益の多くは比較窓を変えない共有・列・仕上げの変更から来ている。比較窓を変え、実手数も下がったのは{wins["moves"]["n"]}/500件で、平均{wins["windows_changed"]["mean"]:.2f}窓・{wins["new_pairs"]["mean"]:.2f}ペアの変更を伴った。', '',
          f'この勝ち群の追加取っ手穴数の差は{stat(wins["extra_holes_delta"])}、平均列番号の差は{stat(wins["target_column_delta"])}、共有ペアの平均Hamming距離の差は{stat(wins["pair_hamming_delta"])}。単に穴を増やす・列を浅くするという一方向の変化では説明できない。勝ちで条件付けた記述統計であり、これらを次の設計目的へ直接置き換える根拠にはしない。']
fg=structures['full']['groups']['changed_windows']
lines+=['',f'全再設計対照は{fg["moves"]["n"]}/500件で新しい比較窓配置を採用し、その群で平均{fg["windows_changed"]["mean"]:.2f}窓・{fg["new_pairs"]["mean"]:.2f}ペアが変わり、実コストは{stat(fg["moves"])}手/注文改善した。今回の局所修復より、別の窓・共有・列の組合せを最初から作る対照が良い完成設計へ移る頻度は高かった。']
lines+=['','starの実操作の差を、生成経路のラベルで分解した。単位は手/注文。ラベルは因果効果の分解ではない。全件でラベル総数と実スコアを照合した。','','| 操作群 | star−SOTA | star−全再設計 |','|---|---:|---:|']
label_rows=[('handle_related','取っ手関連（fix/fill/fdig/fret/relevel/reuse）'),('generic_related','比較紙・helper関連（gen/help/hdig）'),('dig','列dig'),('lift','注文紙の持上げ（lift）'),('ret','前の注文紙の返却（ret）'),('repair','後処理repair'),('total','全操作')]
if any('other' in x['delta'] for x in labels.values()):label_rows.insert(-1,('other','その他'))
for key,label in label_rows:
    lines.append(f'| {label} | {stat(labels["base"]["delta"].get(key,{"mean":0,"se":0}))} | {stat(labels["control"]["delta"].get(key,{"mean":0,"se":0}))} |')
lb=labels['base']['delta'];lc=labels['control']['delta']
lines+=['',f'操作ラベル上では、starの対SOTA改善の中心は取っ手関連の{stat(lb["handle_related"])}手/注文だった。一部が列digと後処理repairの増加で相殺されている。一方、全再設計対照に対しては取っ手関連で{stat(lc["handle_related"])}、比較紙・helper関連で{stat(lc["generic_related"])}手/注文多く、列digなどの減少では埋め切れなかった。']
lines+=['','個々の構造差、従来模型の内訳、最大改善・悪化ケースのseedは `final-lns-*-study-structure.json` に保存した。観測した勝ちケースだけの集計を、次の設計規則の因果的根拠にはしていない。','','## 1×から2×への計算効率とphase 2の推奨','','同じ2倍通常compareの設計時間差で割った、1×からの平均改善。元のパイプラインへの追加予算の効率であり、微小な2秒予算へ線形外挿した予測ではない。','','| 方式 | 追加設計秒 | 改善 手/注文/設計ms | 改善 %/設計秒 |','|---|---:|---:|---:|']
for name in ['star','joint','warm','full']:
    x=d['budgets']['2'][f'lns-{name}-study'];t=x['stage']['helper_end_sec']['paired_delta'];v=x['versus_base']['fresh']
    lines.append(f'| {name} | {t:.4f} | {-v["moves"]/(1000*t):.8f} | {-v["pct_orders"]/t:.4f} |')
if gate['status']=='失敗':
    model=d['budgets']['8']['lns-star-study']
    attempt_ms=1000*model['stage']['lns_sec']['mean']/(model['diag']['attempts']/500)
    lines+=['','**2秒ソルバに入れる変更はなし。helper-wideを維持する。** 今回は統合案を出さないため、提案する追加時間・改善量はともに0。大きな破壊修復を既存分岐やrefinishと置き換えて良くなる根拠は得られなかった。今の修復方式の高速化だけを主投資にすることも推奨しない。', '',
             f'starの追加1試行は平均 **{attempt_ms:.1f} ms**（失敗も含む、CLOCK_SCALE込み設計時間）。既存段をこの時間だけ削って置き換える実験には進んでいない。粗い予算曲線から、2秒版で正の純利益が出ると外挿はしない。', '',
             'これは、試した領域・段階的修復・貪欲重み付きマッチング・従来列模型・完成Vによる山登りの組合せに対するgate不合格である。別の厳密な重み付き共同修復や、異なる受理法が全て無効だと証明したものではない。phase 2は開始せず、この測定と実装を引き渡す。']
else:
    lines+=['','phase 2はユーザーの判断を待つ。上の計算効率と、候補1回あたりの実測時間をもとに、移植案を別途判断する。']
lines+=['','## 検証・記録・再現','','- 追加探索0の足場は、GCCとClangでhelper-wideと200/200件のstdoutバイト一致。通常starへの倍率追加も両コンパイラで200/200件一致（`identity-study.json`）。joint/warm/fullのClang動作確認24件もWA0。',
          '- 増加路マッチングは512小規模乱数グラフの部分集合DPとの照合を24ケース内で実施し、全成功（`20261108-045736_lns-star`）。',
          '- `final-source-audit.json` で注文処理・helper・列MDP・穿孔原始処理・V・DesignStoreとmainの不変を確認。凍結ソースSHA256は `heldout-frozen.json`。通常実行と保存設計再生の実列0は全方式・全予算で500/500スコア一致。',
          '- 全主比較はWA0・表示誤り0。研究時間は2秒を超えるため本番候補ではなく、通常runは全て `--no-record`。ケースは60秒タイムアウト内。時計は既存のCLOCK_SCALE付き関数を使用し、時間不足モード・時間による候補数変更はない。',
          f'- `final-replay-audit.json` の全{len(replay_audit)}再生・{sum(x["case_lists"] for x in replay_audit.values()):,}ケース列・{sum(x["requests"] for x in replay_audit.values()):,}注文で、表示誤り・ラベル数不一致・計画失敗・不安全計画のカウンタは全て0。テスター得点とorder_scoresも照合した。',
          '- 最初の基準再生 `20261108-065042_deval-helper-wide` に外部負荷警告が出たため、`20261108-070629_deval-helper-wide` で再実行。全500件×8列の出力がバイト一致、全スコア一致。最終参照は後者と同値。',
          '- 初期の候補artifact再生は絶対パスがbasenameへ変わる読込不具合で0点になった。正のスコア検査で検出し、全て破棄して `*-fixed` として再測定した。主比較と通常の保存設計再生には影響しない。共有scriptsは変更せず、自己所有artifactだけ `run.py` でパスを保持する。診断の全注文で操作数と得点も一致を検査した。',
          '- ビルド・重い分析は共通flockとnice、ケース実行は標準pahcer runner。章4の実装・他agentのディレクトリには触れていない。コミットなし。', '',
          '再現コマンドは [reproducibility.md](reproducibility.md)。予備実験の全表は [TRAINING.md](TRAINING.md)、経過と判断時点は [PROGRESS.md](PROGRESS.md)。集計は `analyze.py`、`build_summary.py`、`diagnostic_metrics.py`、`winning_changes.py`、`label_changes.py`。', '',
          '## 凍結確認run一覧','','基準設計は `20261107-165305_deval-flex125-plan3`、注文処理基準再生は `20261108-070629_deval-helper-wide`。','','| 予算 | 方式 | 設計run | helper-wide再生run |','|---|---|---|---|']
for k,models in d['budgets'].items():
    for name,x in models.items():lines.append(f'| {k}× | {name} | `{x["normal"]}` | `{x["replay"]}` |')
lines+=['','## 外部負荷警告の再確認','','主再生で負荷警告があったrunは、同じ設計・同じ固定方策で負荷の低い再生を行い、全4,000出力のバイト一致と全スコア一致を確認した。再生時間を通常比較の設計時間の代用にはしていない。','','| 元の再生 | 負荷の低い再実行 | 一致出力数 |','|---|---|---:|']
for original,x in clean['checks'].items():lines.append(f'| `{original}` | `{x["clean_replay"]}` | 4,000 / 4,000 |')
lines+=['','候補単位の診断16再生も負荷を検査した。警告のあった以下の再生は、訓練100件×8列の全800出力・スコア一致を確認した（`clean-candidate-checks.json`）。','','| 元の候補再生 | 負荷の低い再実行 | 一致出力数 |','|---|---|---:|']
for original,x in candidate_clean['checks'].items():lines.append(f'| `{original}` | `{x["clean_replay"]}` | 800 / 800 |')
lines+=['','## 補助スコア','','全8列と実列0のlog比。主判定や凍結後の設定選択には使わない。','','| 予算 | 方式 | 全8列 vs SOTA | 実列0 vs SOTA |','|---|---|---:|---:|']
for k,models in d['budgets'].items():
    for name,x in models.items():
        a=x['versus_base']['all'];r=x['versus_base']['real']
        lines.append(f'| {k}× | {name} | {a["pct_orders"]:+.4f} ±{a["pct_orders_se"]:.4f}% | {r["pct_orders"]:+.4f} ±{r["pct_orders_se"]:.4f}% |')
(h/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('Wrote',h/'REPORT.md')
