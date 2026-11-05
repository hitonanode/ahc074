"""Write reports only after the saved-result audit has passed; run when idle."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
candidate = here.parent/'argon-des-perf-rematch-v2'
audit = json.loads((candidate/'final-audit.json').read_text())
assert all(audit['criteria'].values())
rows = json.loads((here/'rematch-final2000.json').read_text())
b, c, plain, fifth = rows
f = lambda row,key: row['metrics'][key]['mean']
score = c['score']; dt = c['judge_delta']; bj = b['judge']; cj = c['judge']
ratio = -score['mean']/dt['mean'] if dt['mean'] > 0 else float('inf')

text = f'''# D2：穿孔済みの穴を使う目標再割当

**マージ対象はこのディレクトリ `argon-des-perf-rematch-v2`。**
基準はPR #144 `solutions/argon-req-ejectstats-v2`。
通常2000 seedで **{score['mean']:+.6f} ± {score['se']:.6f}%**、
勝/分/敗は **{'/'.join(map(str,c['wtl']))}**。
全採用条件を満たしたため、この版を確定してマージを待つ。

## 助言の検証から得た変更

外部助言01-1の「穿孔処理とフィラー評価の対象拡大」を検証した。
`Handle perforation`の`best_heads`が列・色ごとに1枚を固定し、
第2候補もフィラーになるという指摘は正しい。
ただし32層化標本で非headを追加しても、2000件の差は
−0.000832 ± 0.001397%に留まり、時間も増えた。
露出を0にしても穴が選ばれ、利益予測をowner側が支配していた。
係数0.65/0.75/0.80の近傍にも採用できる改善はなかった。

検証を前段へ広げると、`Filler climb`と`ProbabilityHead`は解析的な期待値なので
少数標本を使う偏りはないが、最適化している模様・穴費用・頭の色確率は穿孔前だった。
そこで、穿孔済みの穴を紙の位置に固定し、目標と紙の組合せを最後に選び直す。
窓、汎用比較層、列、各紙の頻度と自身のハンドルは変えない。

## 実装と整合性

- `ProbabilityHead`は任意の追加穴配列を受け取る。通常の先行4回は配列なしで従来どおり。
  追加段では、各紙の自然なペア穴に固定追加穴を加え、色別需要と色確率を作り直す。
  ペアの穴と追加穴が重なる窓は二重に数えない。
- donorとownerのフィラー価値、色確率の勾配、Hungarianの費用行列、受理時の正確な目的関数に
  同じ追加穴を使う。`ProbabilityHead::diff`はこの段では自然なペア穴と追加穴の和集合になる。
  Singletonのキャッシュも、追加穴のある位置では別に計算する。
- 係数1.0でHungarianを1回実行する。従来同様、各ペアの片方をanchorとして固定し、
  比較層と整合する組合せだけを許す。受理は穴を含むモデル費用−フィラーproxyの改善。
- 新しい所有目標の模様で商品紙を印刷し直し、元の追加穴を除く。
  列と各紙の自身のハンドルは固定なので、追加穴がアクセス用のハンドルを壊さない。
  `state.ded`も新しい所有目標に合わせる。未来の注文は使わない。

追加した段と目次項目は `design_papers: perforation-aware reassignment`。
新しい予算スイッチは `ARGON_D2_LATE_ITERS`（既定1、0で追加段なし）。
`d2_rematch_*`は回数・受理cycle・変更unit数・予測改善・時間、
`d2_model_initial/final`と`d2_filler_initial/final`は目的関数の内訳（手/注文）。
`d2_extra_remaining`は新しい自然なペア穴と重ならない追加穴数。
既存のmodel/proxy/perforation指標は追加段の前を示す。

元のログ、@paper/@ops、全プロファイラとスイッチ、CLOCK_SCALE、LOCAL_BENCH、
DesignStore、既存の段を保持した。DesignStateとrequest側のインターフェースは変更しない。
main.cppの差は+118/−25行。

## 決定比較

run-idはすべて `20261106-054641_`。基準は`argon-req-ejectstats-v2`、
採用候補は`argon-des-perf-rematch-v2`、対照は`argon-des-perf-rematch-plain`と
`argon-des-perf-match5`。通常2000 seed、全群設計保存・記録あり。
開始前、延長前、終了後にBASE.mdがPR144であることを確認した。

| 候補 | 差 ± SE (%) | 勝/分/敗 | judge平均 (秒) | p99 (秒) |
|---|---:|---:|---:|---:|
| 基準 | — | — | {bj['mean']:.6f} | {bj['p99']:.6f} |
| 穿孔後の穴を考慮 | **{score['mean']:+.6f} ± {score['se']:.6f}** | {'/'.join(map(str,c['wtl']))} | {cj['mean']:.6f} | {cj['p99']:.6f} |
| 穴を残して評価だけ無視 | {plain['score']['mean']:+.6f} ± {plain['score']['se']:.6f} | {'/'.join(map(str,plain['wtl']))} | {plain['judge']['mean']:.6f} | {plain['judge']['p99']:.6f} |
| 穿孔前のHungarianを5回へ | {fifth['score']['mean']:+.6f} ± {fifth['score']['se']:.6f} | {'/'.join(map(str,fifth['wtl']))} | {fifth['judge']['mean']:.6f} | {fifth['judge']['p99']:.6f} |

単にHungarianを1回足すより、穿孔後の模様を評価することが効く。
採用版は平均{f(c,'d2_rematch_cycles'):.4f} cycle、{f(c,'d2_rematch_changed'):.4f} unitを変更。
自然なペア穴と重ならない追加穴数は初期{f(c,'perforation_holes'):.4f}から{f(c,'d2_extra_remaining'):.4f}で、追加穿孔は行わない。
モデル費用は{f(c,'d2_model_initial'):.6f}→{f(c,'d2_model_final'):.6f}、
フィラーproxyは{f(c,'d2_filler_initial'):.6f}→{f(c,'d2_filler_final'):.6f}、
差し引きの予測改善は{-f(c,'d2_rematch_decrease'):.6f}手/注文。

| 時間・正当性 | 基準 | 採用版 |
|---|---:|---:|
| req_sec | {f(b,'req_sec'):.6f} | {f(c,'req_sec'):.6f} |
| helper_end_sec | {f(b,'helper_end_sec'):.6f} | {f(c,'helper_end_sec'):.6f} |
| end_sec | {f(b,'end_sec'):.6f} | {f(c,'end_sec'):.6f} |
| judge最大 | {bj['max']:.6f} | {cj['max']:.6f} |
| judge 2秒超え | {bj['over2']} | {cj['over2']} |
| WA / self_wrong / op_label_errors | 0 / 0 / 0 | 0 / 0 / 0 |

judge = end_sec + 0.04×helper_end_sec + 0.35×req_sec。
平均増分は **{1000*dt['mean']:.3f} ± {1000*dt['se']:.3f} ms**、
p99増分は{1000*dt['p99_difference']:.3f} ms。
改善効率は **{ratio:.3f}%/judge秒**で0.6%/秒を超える。
共有予算25 msとp99の差分条件を満たす。
外部負荷は初回500件0.35/1.24コア、延長1500件0.15/0.51コア（平均/最大）で警告なし。
`20261106-054135_*`は平均0.55コアの負荷警告があったため採用判定から除外した。

## 検証

- 追加段0回のPR143対照: `20261106-052425_argon-req-filterblocks-v2` /
  `20261106-052601_argon-des-perf-rematch`、通常200件でstdout・非時刻stderrが200/200一致。
- 最終2000件のgobj、anneal、climb、match、model、穿孔の全非時刻指標は基準と一致。
  既存の設計はそのままで、追加段だけが新しい紙を作る。
- 全2000保存設計で、窓・列・汎用紙・cap・各紙の頻度が不変であることと、
  新しい所有目標からの印刷式と追加穴の保持を独立に再構成して照合した。
- GCC/Clang、C++23 -O2 -Wall -Wextra、LOCAL_BENCH有無の4構成で警告0。
  ビルド実行ファイルは/tmpで作り、削除済み。ソースSHA、保存ソース、ビルド結果を照合。
- 変更範囲は再割当関連と穿孔後の追加段、および新しい目次項目だけ。
  `final-audit.json`、`build-results.json`に検証結果を保存した。

## 再開後

これはD2全体の終了ではなく、採用版ごとに止める指示に従う区切り。
新基準で追加再割当の回数・係数の近傍、再割当後に既存穴を再評価する範囲を検証する。
今回は1回・係数1.0までで、これらの飽和はまだ確かめていない。
D1は閉じたまま。D3（長い列のMDP）、D4（汎用層の価値）、D5（rollout）は未着手。
全D2継続の実験と不採用案は[調査報告](../argon-des-perf-s32-neighborhood/REPORT.md)、
全群のreq_secと時間分布は[測定表](../argon-des-perf-s32-neighborhood/MEASUREMENTS.md)。
コミットと共有ファイルの編集はしていない。
'''
(candidate/'REPORT.md').write_text(text)

tables = ['# D2継続の全測定値', '',
          '差は各比較の先頭群に対する平均logスコア比。負が改善。時間は秒。',
          'judge = end_sec + 0.04×helper_end_sec + 0.35×req_sec。採否と診断はREPORT.md。', '']
for file,title in [
    ('grid500.json','32層化標本の係数、500件'), ('grid2000.json','係数、2000件'),
    ('nonhead500.json','PR142 非head追加段、500件'), ('mix500.json','PR143 一巡化、500件'),
    ('mix2000.json','非head追加段・一巡化、2000件'),
    ('diagnosis500.json','owner対照と穿孔後再割当、500件'),
    ('rematch-v2-500.json','PR144 初回（外部負荷警告、採否から除外）'),
    ('rematch-final2000.json','PR144 決定比較、2000件')]:
    group = json.loads((here/file).read_text())
    tables += [f'## {title}', '', '| run-id | n | 差 ± SE (%) | 勝/分/敗 | req | helper_end | end | judge平均 | p99 | 最大 | >2秒 |',
               '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in group:
        j=row['judge'];m=row['metrics'];v=row['score']
        tables.append(f"| {row['run']} | {row['n']} | {v['mean']:+.6f} ± {v['se']:.6f} | {'/'.join(map(str,row['wtl']))} | "
                      f"{m['req_sec']['mean']:.6f} | {m['helper_end_sec']['mean']:.6f} | {m['end_sec']['mean']:.6f} | "
                      f"{j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} |")
    tables += ['']
tables += ['## 未評価の移植', '',
           '`argon-des-perf-nonhead32-v2`はPR143への移植のみ。比較には1/8のwide-v2を使った。',
           '実装の元のnonhead32（1/16）はPR142で500件を評価している。', '']
(here/'MEASUREMENTS.md').write_text('\n'.join(tables))

report = here/'REPORT.md'
contents = report.read_text()
marker = '\n## 最終判定：穿孔後の再割当を採用\n'
if marker in contents: contents=contents.split(marker)[0]
contents += marker+f'''
マージ対象は[argon-des-perf-rematch-v2](../argon-des-perf-rematch-v2/REPORT.md)。
通常2000 seed（全群 `20261106-054641_*`）で
**{score['mean']:+.6f} ± {score['se']:.6f}%**、{'/'.join(map(str,c['wtl']))}。
追加judge平均{1000*dt['mean']:.3f}±{1000*dt['se']:.3f} ms、p99差{1000*dt['p99_difference']:.3f} ms、
効率{ratio:.3f}%/秒。全採用条件と全紙の独立照合を通過した。
対照の穴無視は{plain['score']['mean']:+.6f}±{plain['score']['se']:.6f}%、
穿孔前5回は{fifth['score']['mean']:+.6f}±{fifth['score']['se']:.6f}%。
穿孔後の目的関数へ変えることに効果がある。

採用版ごとに止める指示に従って、ここでマージを待つ。
再開後は新基準で追加再割当の回数・係数・穴の再評価を調べ、飽和したらD3〜D5へ進む。
D1は完了、D3〜D5は未着手。全runの時間は[MEASUREMENTS.md](MEASUREMENTS.md)。
'''
report.write_text(contents)
print('Reports finalized:', candidate, score, dt)
