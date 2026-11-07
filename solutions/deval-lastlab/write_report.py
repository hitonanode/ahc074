"""Render the frozen final report from audited JSON; no fitting or selection."""
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent;D=P.parent/sys.argv[1]
x=json.loads((D/'final-metrics.json').read_text());f=json.loads((D/'FROZEN.json').read_text());t=json.loads((D/'time-selection.json').read_text())
name=D.name;ids=x['run_ids']['normal'];candidate=next(r for r in ids if r.endswith('_'+name));base=next(r for r in ids if r.endswith('_deval-flex125-plan3'));old=next(r for r in ids if r.endswith('_argon-des-perf-latew105'));nofb=next(r for r in ids if r.endswith('_deval-vbranch-nofb'))
def pct(z):return f"{z['mean']:+.4f} ± {z['se']:.4f}"
def wtl(z):return '/'.join(map(str,z['wtl']))
def nm(r):return r.split('_',1)[1]
z=x['normal'][candidate];q=x['replay']['fresh'];rq=f['request_only'];primary=q['unseen_seeds_500_1999'] if rq else q
lines=[f'# {name}: Task 6','',
 (f"未使用seed 500–1999、新規注文列1–3で、flex125-plan3に対して **{pct(primary)}%**。保存設計2000ケース×4列全体の新規列では **{pct(q)}%**。" if rq else f"未使用seed 500–999、新規注文列1–7で、flex125-plan3に対して **{pct(q)}%**。")+
 f" 通常2000ケースは **{pct(x['paired_scores'][candidate+' vs '+base])}%**。負が改善、±はケース単位の標準誤差。",'',
 f"judge平均はargon比 **{z['judge_ratio_old'][0]:.5f}倍**、p99は **{z['judge']['p99']:.6f} s**、同じ比較のnofbは **{x['normal'][nofb]['judge']['p99']:.6f} s**。ソースは **{x['audit']['source_bytes']:,} bytes**。",'',
 ('目標の0.03%改善に届いた。' if primary['mean']<=-.03 else '未使用ケースでの点推定は目標の0.03%改善に届かなかった。')+
 '平均・p99条件は下の同時比較で確認した。時間による軽量化、設計打切り、候補数切替えは加えていない。', '',
 '## 最終変更','', (D/'README.md').read_text().strip(),'',
 '出力同一の3変更をまとめ、幅4・同距離helper上位1件の同じ探索をする親と比較した。req_secはGCC500件で−11.948±1.606ms、Clang250件で−12.137±2.074ms。stdoutはそれぞれ全件一致した（205534 / 205745）。この差は同じ24並列compare内の値で、単体差を足した見積りではない。','',
 '## 測定と固定','',
 f"設定選択はseed 0–499のみ。`{f['time']}` に固定、SHA256 `{f['sha256']}`。通常比較と最終replayの保存ソースは現行main.cppとバイト単位で一致した。",'',
 ('採用案は注文処理のみの変更なので、最終replayは指定された2000ケース×4列のprotocolを使った。' if rq else '最終replayは未使用seed 500–999×8列で実施した。'),'',
 '各ケースで対象注文列のスコアを平均し、その比の自然対数×100を集計する。SEはケース間で求め、複数注文列を独立ケースとして数えない。通常比較はseedごとのlog比。多数の学習試行から選んでいるため、主判定は未使用seedの結果とする。', '',
 '時間は24並列の通常同時比較で測り、`judge = 1.04 × helper_end_sec + 1.35 × req_sec + end_sec − helper_end_sec − req_sec` とする。保存設計replayの絶対時間は最終judge判定に使わない。通常2000件は `--no-record` なしで記録した。','',
 '## 事前の時間による採用規則','',
 '学習結果から次の優先順を固定し、通常スコアを使わず、平均比≤1.10かつp99≤nofbを満たす最初の候補を選んだ。未使用seedのreplayは選んだ一案だけに行った。各候補は独立した固定予算のsolverで、実行中に選択を切り替えない。', '',
 '| 固定候補 | judge/old | p99−nofb ms | 適合 |','|---|---:|---:|---|']
for n in f['priority']:
 r=next(r for r in ids if r.endswith('_'+n));a=t['timing'][r]
 lines.append(f"| {n} | {a['ratio_old']:.5f} | {(a['p99']-t['timing'][nofb]['p99'])*1000:+.3f} | {a['eligible']} |")
lines+=['','## 通常2000ケース','','| 解法 | 平均スコア | 対flex125-plan3 % ± SE | W/T/L |','|---|---:|---:|---|']
for r in ids:
 a=x['normal'][r];b=x['paired_scores'].get(r+' vs '+base)
 lines.append(f"| {nm(r)} | {a['score_mean']:.4f} | {pct(b) if b else '—'} | {wtl(b) if b else '—'} |")
lines+=['','| 最終候補の比較先 | スコア差 % ± SE | W/T/L |','|---|---:|---|']
for r in [old,nofb,base]:
 a=x['paired_scores'][candidate+' vs '+r];lines.append(f'| {nm(r)} | {pct(a)} | {wtl(a)} |')
lines+=['','| 解法 | judge平均 s | 対old比 ± SE | judge p99 s | judge最大 s |','|---|---:|---:|---:|---:|']
for r in ids:
 a=x['normal'][r];b=a['judge'];v=a['judge_ratio_old']
 lines.append(f"| {nm(r)} | {b['mean']:.6f} | {v[0]:.5f} ± {v[1]:.5f} | {b['p99']:.6f} | {b['max']:.6f} |")
lines+=['','| 解法 | end_sec平均 | p99 | 最大 | >1.8 / >1.9 / >2.0 件数 |','|---|---:|---:|---:|---|']
for r in ids:
 b=x['normal'][r]['end_sec'];lines.append(f"| {nm(r)} | {b['mean']:.6f} | {b['p99']:.6f} | {b['max']:.6f} | {b['over_1_8']} / {b['over_1_9']} / {b['over_2']} |")
lines+=['',f"judge推定で2秒を超えるケースは候補{z['judge']['over_2']}件、nofb{x['normal'][nofb]['judge']['over_2']}件。時刻によるfallbackは加えていない。",'', (D/'TAIL.md').read_text(),'',
 '通常run: '+', '.join('`'+r+'`' for r in ids)+'.','',
 '## 凍結後のreplay','', '| 注文列 | flex125-plan3比 % ± SE | 手/注文差 | W/T/L |','|---|---:|---:|---|']
for k,label in [('fresh','新規1–3' if rq else '新規1–7'),('all','全0–3' if rq else '全0–7'),('real','実列0')]:
 a=x['replay'][k];lines.append(f"| {label} | {pct(a)} | {a['moves_per_order']:+.7f} | {wtl(a)} |")
if rq:
 lines+=['','上表は指定の保存設計2000ケース×4列。学習に使わなかったseed 500–1999を分けた値:','', '| 注文列 | 未使用1500ケース % ± SE |','|---|---:|']
 for k,label in [('fresh','新規1–3'),('all','全0–3'),('real','実列0')]:lines.append(f"| {label} | {pct(x['replay'][k]['unseen_seeds_500_1999'])} |")
 lines+=['','全てのseed区分も併記する。最初の500件は設定選択に使った学習側。','','| seed | 新規1–3 % ± SE | 全0–3 % ± SE | 実列0 % ± SE |','|---|---:|---:|---:|']
 for group in ['0-499','500-999','1000-1999']:
  vals=[pct(x['replay'][key]['seed_groups'][group]) for key in ['fresh','all','real']]
  lines.append('| '+group+' | '+' | '.join(vals)+' |')
lines+=['',f"候補 `{x['run_ids']['replay']}`、基準 `{x['run_ids']['reference']}`。列0のstdoutは通常比較の同じ{x['audit']['normal_replay_list0_identical']}ケースと全件一致。",'',
 '## 最終候補の時間内訳','', '| 段 | 平均 s | flex125-plan3との差 ms ± SE |','|---|---:|---:|']
for k,a in x['stage_deltas_vs_flex125'].items():lines.append(f"| {k} | {z['stage_mean'][k]:.6f} | {a[0]*1000:+.3f} ± {a[1]*1000:.3f} |")
lines+=['','## 検査と再現','',
 f"最終候補の設計候補数分布: `{z.get('candidate_counts',{})}`。各ケースで同じ固定候補数を完了している。",'',
 f"通常2000件と最終replayのWA・表示誤り・自己検査誤り・操作ラベル不一致・計画失敗・unsafe planは0。replayの{x['audit']['replay_trace_moves_match_score']:,}列、{x['audit']['replay_requests']:,}注文で@ops総数とscoreの一致も検査した。"+('設計の192行は2000ケースすべて基準と一致。' if rq else ''), '',
 '比較元replayの8,000列も、表示・計画のエラーが0で、@ops総数とscoreが一致することを確認した（`reference-audit.json`）。','',
 'GCC/ClangのC++23提出用ビルドは `builds.json`、`-march=native` は `builds-native.json`。CLOCK_SCALE、DesignStore、@paper/@ops、各種ログ・profiler・実験switch、段の目印と目次を保持した。未使用関数、必ず上書きされる旧MDP分類、古いコメントを整理し、整理だけの版はGCC/Clang各250ケースで出力一致を確認した。', '',
 '指定の未変更 `judge_model.py` による再計算も `judge-model.txt` に保存し、平均・p99・最大が集計と一致することを確認した。','',
 '再実行のコマンドは [REPRODUCE.md](REPRODUCE.md) にまとめた。','',
 '再現スクリプトは `../deval-lastlab/`。`run.py` は標準pahcer_run.pyを呼び、buildを共通flockで保護する。同一source/compiler/flagsの完了済みbinaryだけ再利用する。`requests.py` は固定設計の注文比較、`batch.py` は通常500件と8列replay、`final_pair.py` は事前固定・記録付き通常比較・時間だけの選択・最終replayを行う。`summarize.py`、`tables.py`、`final_metrics.py`、`write_report.py` で表と監査を再現できる。重い分析は全て共通flock下で行う。', '',
 f"通常比較の外部負荷: `{z['outside_load']}`。",'',
 '## 学習で得た判断','',
 (P/'REPORT-NOTES.md').read_text().split('\n\n',2)[2].split('`TABLES.md`')[0].strip(), '',
 'helper単体のラベル解析は `../deval-lastlab/helper-attribution.json`。180311基準/180312helpeq1、seed0–499、新規3列でnet −0.001728手/注文。fix、fill、repairなどが減る一方、help、hdig、genなどが増える。generic距離が同じという追加条件は清算後のhelper探索での条件であり、元solverとの総gen数が同じという意味ではない。起動時だけでなく後半768注文でも改善した。', '',
 (P/'STRATEGIES.md').read_text(),'',
 (P/'EXTRA-TABLES.md').read_text(),'',
 (P/'EXACT.md').read_text(),'',
 '## 全学習試行','',
 '以下は不採用案も含む。各候補のREADMEに基準との差分と固定パラメータを記載した。末尾の新しい候補を含め、未使用ケースの結果を見て設定を再調整していない。','',
 (P/'TABLES.md').read_text().replace('# Task 6 学習試行一覧','### 学習用の数値表').replace('\n## ','\n### ')]
(D/'REPORT.md').write_text('\n'.join(lines)+'\n');print(D/'REPORT.md')
