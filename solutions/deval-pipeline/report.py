"""Render the frozen result and every completed training trial in Japanese."""
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent;root=P.parents[1];name=sys.argv[1];out=root/'solutions'/name
m=json.loads((out/'final-metrics.json').read_text());freeze=json.loads((out/'FROZEN.json').read_text())
for build_file in ['builds.json','builds-native.json']:
    builds=json.loads((out/build_file).read_text())
    assert len(builds)==2 and all(x['returncode']==0 and x['source_sha256']==freeze['sha256'] for x in builds)
normal=m['normal'];candidate=next(r for r in normal if r.endswith('_'+name))
ordered=next(r for r in normal if r.endswith('_deval-ordered8'));nofb=next(r for r in normal if r.endswith('_deval-vbranch-nofb'))
c=normal[candidate];score=m['paired_scores'][candidate+' vs '+ordered];fresh=m['replay']['fresh']
def number(v):return f'{v[0]:+.4f} ± {v[1]:.4f}'
lines=[f'# {name}: Task 5', '',
       f'未使用seed 500–999の新規注文列1–7で、ordered8に対して **{fresh["mean"]:+.4f} ± {fresh["se"]:.4f}%**。通常2000ケースは **{score["mean"]:+.4f} ± {score["se"]:.4f}%**。負が改善、±はケース単位の標準誤差。', '',
       f'judgeモデルの平均はold SOTA比 **{c["judge_ratio_old"][0]:.5f}倍**。p99は **{c["judge"]["p99"]:.6f} s**、同時比較のnofbは **{normal[nofb]["judge"]["p99"]:.6f} s**。ソースは **{m["audit"]["source_bytes"]:,} bytes**。時間不足による切り替えは加えていない。', '',
       '## 最終変更', '',
       (out/'README.md').read_text().strip(), '',
       '単独紙の色を動かせる理由は、列の両色が残る限り、従来の列費用が単独紙の色別枚数に依存しないためである。再割当ては紙slotの単独/ペア構成とペアのanchor色を保つので、列費用の枚数・ペア数・色別ペア数は変わらない。従来は不要な色固定で、ハンドルとfillerの経済性を改善する割当てを除外していた。色消失を巡回単位で棄却し、完成候補をVで選ぶことで、この余地を使う。', '',
       '## 測定と固定', '',
       f'設定選択はseed 0–499のみ。`{freeze["time"]}` にソースを固定した。SHA256は `{freeze["sha256"]}`。通常2000ケースと最終8列replayの保存ソースは、このソースとバイト単位で一致する。', '',
       '品質は各ケースで対象注文列のスコアを平均し、その比の自然対数×100を集計する。SEはケース間で計算し、注文列を独立ケースとして数えない。通常比較はseedごとのlog比である。', '',
       '通常評価は24並列、old / nofb / ordered8 / 固定候補の同時比較で、`--no-record`を付けずに記録した。judgeは `1.04 × helper_end_sec + 1.35 × req_sec + (end_sec − helper_end_sec − req_sec)`。replayの時間は通常実行の時間判定には使わない。', '',
       '## 通常2000ケース', '',
       '| 解法 | 平均スコア | 対old % ± SE | 対ordered8 % ± SE | 対ordered8 W/T/L |',
       '|---|---:|---:|---:|---|']
old=m['run_ids']['normal'][0]
for r,z in normal.items():
    a=m['paired_scores'].get(r+' vs '+old);b=m['paired_scores'].get(r+' vs '+ordered)
    af='—' if a is None else number([a['mean'],a['se']]);bf='—' if b is None else number([b['mean'],b['se']])
    w='—' if b is None else '/'.join(map(str,b['wtl']))
    lines.append(f'| {r.split("_",1)[1]} | {z["score_mean"]:.4f} | {af} | {bf} | {w} |')
lines+=['', '| 最終候補の比較先 | スコア差 % ± SE | W/T/L |', '|---|---:|---|']
for ref in [old,nofb,ordered]:
    z=m['paired_scores'][candidate+' vs '+ref]
    lines.append(f'| {ref.split("_",1)[1]} | {number([z["mean"],z["se"]])} | {"/".join(map(str,z["wtl"]))} |')
lines+=['', '| 解法 | judge平均 s | 対old平均比 ± SE | judge p99 s | judge最大 s |', '|---|---:|---:|---:|---:|']
for r,z in normal.items():
    j=z['judge'];rr=z['judge_ratio_old']
    lines.append(f'| {r.split("_",1)[1]} | {j["mean"]:.6f} | {rr[0]:.5f} ± {rr[1]:.5f} | {j["p99"]:.6f} | {j["max"]:.6f} |')
lines+=['', f'指定された平均・p99条件は満たす。judgeモデルで2秒を超えた推定は最終候補が {c["judge"]["over_2"]} / 2000件、nofbが {normal[nofb]["judge"]["over_2"]} / 2000件。最大は上表の通りで、全件2秒以内を保証した結果ではない。指示通り、時刻による軽量化・候補削減は入れていない。']
lines+=['', '| 解法 | end_sec平均 | p99 | 最大 | >1.8 / >1.9 / >2.0 s 件数 |', '|---|---:|---:|---:|---|']
for r,z in normal.items():
    e=z['end_sec'];lines.append(f'| {r.split("_",1)[1]} | {e["mean"]:.6f} | {e["p99"]:.6f} | {e["max"]:.6f} | {e["over_1_8"]} / {e["over_1_9"]} / {e["over_2"]} |')
lines+=['', '通常比較run: '+', '.join('`'+r+'`' for r in normal)+'.', '',
        '## 未使用500ケースの8列replay', '',
        '| 注文列 | ordered8比 % ± SE | 操作/注文の差 | W/T/L |', '|---|---:|---:|---|']
for key,title in [('fresh','新規1–7（主判定）'),('all','全0–7'),('real','実列0')]:
    z=m['replay'][key];lines.append(f'| {title} | {number([z["mean"],z["se"]])} | {z["moves_per_order"]:+.6f} | {"/".join(map(str,z["wtl"]))} |')
lines+=['', f'候補replay `{m["run_ids"]["replay"]}`、基準 `{m["run_ids"]["reference"]}`。候補の列0のstdoutは通常評価の同じ500ケースと全件一致した。', '',
        '## 最終候補の時間内訳', '', '| 段 | 平均秒 | ordered8との差 ms ± SE |', '|---|---:|---:|']
for k,v in m['stage_deltas_vs_ordered8'].items():
    lines.append(f'| {k} | {c["stage_mean"][k]:.6f} | {number([1000*v[0],1000*v[1]])} |')
lines+=['', '## 検査と再現', '',
        '通常2000ケースの全解法と候補の8列replayで、WA、表示誤り、自己検査誤り、操作ラベル不一致、計画失敗、unsafe planは0。最終replayの4000注文列・4,096,000注文についてstderrの検査値を確認した。DesignStoreは選んだ設計を保存し、列0の再生も一致する。', '',
        'GCC/ClangのC++23ビルドは `builds.json`、`-march=native`付きは `builds-native.json` にコマンド・ソースハッシュ・結果を保存する。時計は既存のCLOCK_SCALE付き関数を使い、候補数・探索量は固定。`@paper`/`@ops`、ログ、プロファイラ、実験スイッチ、段の目印と目次を保った。', '',
        '再現用は `../deval-pipeline/`。`batch.py` は通常500ケースと8列学習replay、`final_pair.py` は固定・記録付き通常2000ケース・時間条件だけの選択・最終500ケースreplayを順に行う。`run.py` は標準 `scripts/pahcer_run.py` を呼び、コンパイラをflockで保護する。`summarize.py`、`tables.py`、`final_metrics.py` が表と検査を再計算する。重い集計は共通flock下で実行する。', '',
        '通常比較の外部負荷: `'+str(c['outside_load'])+'`。', '',
        '## 学習で得た判断', '',
        '単独紙の色固定は再割当てに不要な制約だった。穴あけ後の再割当てだけを緩めるのが最も良かった。穴あけ前まで拡張したり、元の4枝を対象から外したりしても上回らなかった。係数1.25は1.05より学習の点推定が良いが、その差 −0.0131 ± 0.0095% 単独では有意と言わない。列MDPの需要分類と汎用紙の末端価値は、設計を固定した比較でも小さい改善があり、併用して確認した。', '',
        '色固定解除だけの診断（係数1.05、train500、新規列1–7）では、最初の256注文が −0.0247 ± 0.0142%、残り768注文が −0.0416 ± 0.0094%。起動時だけの改善ではない。fixは −0.00600手/注文だがfretは +0.00405、relevelは −0.00309で、総計は −0.00376手/注文だった。fix単独では過大評価する。元データは `20261107-130357_deval-ordered8` 対 `20261107-153129_deval-free-late`、再現は `attribute_moves.py`、集計は `move-attribution.json`。全7000注文列で@opsの総数とテスターのスコアが一致した。', '',
        '出力同一の主要変更（窓累積和とV色比較）はGCC/Clang各250件でstdout一致。追加の列移動特殊化・特徴量参照・popcountも、併用版の親に対してGCC/Clang各250件で一致した。単体では列移動が約3.87 ± 1.40 ms、静的特徴量が0.71 ± 0.13 ms短いが、追加群のGCC合算はjudge差 +4.02 ± 4.35 msで明瞭な総短縮ではない。短縮を単純に加算せず、最終2000件の時間で採否を決めた。', '',
        'プロファイル専用run `20261107-150436_deval-profile5`（200ケース）では、注文処理のexclusive時間はeval_filter 88 ms、eject 62.6 ms、nextcost 52.8 ms。焼きなましは394 msのうちcolumn_moveが266 ms、eval_holesが155 ms（後者は内包時間）。時計計測の負荷があるため、これは調査箇所の選択に使い、高速化の時間根拠には使っていない。', '',
        '代表紙の選び方・穴あけの多様化、generic割当ての局所探索、穿孔直後の候補追加、窓eliteを使った4枝目の置換は今回の採用には至らなかった。requestsのexact変更も、測定で速くならなかった案は取り込まなかった。採用した高速化と全試行は以下に残す。学習表は多数の試行からの選択を含むため、最終的な改善量は上の未使用ケースで判断する。', '',
        (P/'TRIAL_GUIDE.md').read_text().strip(), '',
        (P/'TABLES.md').read_text().strip(), '']
if (out/'time-selection.json').exists():
    selection=json.loads((out/'time-selection.json').read_text())
    position=lines.index('## 通常2000ケース')
    priority=' → '.join('`'+n+'`' for n in selection['priority'])
    text=['## 事前の採用規則', '',
          'Task4と同じ手順で、通常2000件の前に '+priority+' の順を固定した。平均judge比が1.10以下、p99が同じ比較のnofb以下である最初の候補を自動選択した。通常スコアは選択に使わず、未使用seedの8列replayは選んだ一案だけで実施した。全候補は独立した固定予算のソースであり、実行中に時刻で切り替えない。`FROZEN.json` と `time-selection.json` が事前規則と選択結果を保存する。', '',
          '| 固定した候補 | judge/old | p99−nofb ms | 時間条件 |', '|---|---:|---:|---|']
    for n in selection['priority']:
        rid=next(r for r in selection['normal'] if r.endswith('_'+n));z=selection['timing'][rid]
        text.append(f'| {n} | {z["ratio_old"]:.5f} | {1000*(z["p99"]-normal[nofb]["judge"]["p99"]):+.3f} | {"適合" if z["eligible"] else "不適合"} |')
    text+=[''];lines[position:position]=text
(out/'REPORT.md').write_text('\n'.join(lines))
print(out/'REPORT.md')
