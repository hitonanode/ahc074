"""Finalize the reports after the selected source and decisive run pass the audit."""
import json
import hashlib
from pathlib import Path
here=Path(__file__).resolve().parent
candidate=here.parent/'argon-des-perf-latew105'
audit=json.loads((candidate/'final-audit.json').read_text())
assert all(audit['criteria'].values())
rows=json.loads((here/'upper-restore2000.json').read_text())
b,c,w110,restore=rows
f=lambda row,key:row['metrics'][key]['mean']
d=c['judge_delta'];score=c['score']
diagnosis=json.loads((here/'upper-restore-diagnosis2000.json').read_text())
diag=next(x for x in diagnosis if x['run']==c['run'])

report=f'''# D2：穿孔後再割当のフィラー係数1.05

**マージ対象はこのディレクトリ `argon-des-perf-latew105`。**
基準はPR145 `solutions/argon-des-perf-rematch-v2`。
通常2000 seedで **{score['mean']:+.6f} ± {score['se']:.6f}%**、
勝/分/敗は **{'/'.join(map(str,c['wtl']))}**。全採用条件を通過したため確定し、マージを待つ。

## 変更と検証した指摘

外部助言01-1「穿孔処理とフィラー評価の対象拡大」から発展した、穿孔後再割当を継続検証した。
`design_papers: perforation-aware reassignment`の`rematch_probability`呼出しで、
フィラー係数だけを1.0→1.05に変更する（+1/−1行）。
費用−係数×フィラー価値という目的関数で、穿孔済みの穴に適応する際のフィラー価値を少し重くする。
回数は従来どおり1回。前段の4回の再割当、穿孔、その他の設計・注文処理は同じ。
元のログ・プロファイラ・スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次をすべて保持した。
新しいスイッチや指標はない。

0.70/0.85へ下げると、モデルの穴費用は減るがフィラー価値をより大きく失い、
500件で+0.086541±0.014566% / +0.037793±0.011257%悪化した。
0.95も改善せず、上側1.05/1.10を調べた。
2回・4回への増量は2000件で+0.003109±0.002561% / +0.001940±0.003076%。
追加時間13.22/26.43 msに見合わず、1回を維持した。

## 決定比較

基準runは `{b['run']}`。
候補runは `{c['run']}`（今後の保存設計として利用可能）。
対照は `{w110['run']}` と `{restore['run']}`。
通常2000件、全群設計保存・pahcerへの記録あり。延長前にBASE.mdがPR145であることを再確認した。

| 候補 | 差 ± SE (%) | 勝/分/敗 | judge平均 | p99 | 最大 | 2秒超 |
|---|---:|---:|---:|---:|---:|---:|
'''
for row in rows:
    j=row['judge'];v=row['score']
    report+=f"| {row['run'].split('_',1)[1]} | {v['mean']:+.6f} ± {v['se']:.6f} | {'/'.join(map(str,row['wtl']))} | {j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} |\n"
report+=f'''
1.05のjudge平均差は **{1000*d['mean']:+.3f} ± {1000*d['se']:.3f} ms**、
p99差は **{1000*d['p99_difference']:+.3f} ms**。共有予算15 msと時間差の条件を満たす。
外部負荷は初回500件0.14/0.36コア、延長1500件0.14/0.38コア（平均/最大）、警告なし。

| 平均時間 (秒) | 基準 | 1.05 |
|---|---:|---:|
| req_sec | {f(b,'req_sec'):.6f} | {f(c,'req_sec'):.6f} |
| helper_end_sec | {f(b,'helper_end_sec'):.6f} | {f(c,'helper_end_sec'):.6f} |
| end_sec | {f(b,'end_sec'):.6f} | {f(c,'end_sec'):.6f} |

judge = end_sec + 0.04×helper_end_sec + 0.35×req_sec。
最終モデル費用は基準{f(b,'d2_model_final'):.6f}→{f(c,'d2_model_final'):.6f}、
フィラーproxyは{f(b,'d2_filler_final'):.6f}→{f(c,'d2_filler_final'):.6f}。
両設計を係数1.05で評価した予測差は{diag['predicted_moves']['mean']:+.6f}手/注文、
実測差は{diag['actual_moves']['mean']:+.6f}±{diag['actual_moves']['se']:.6f}手/注文。

## 正当性と差分の監査

- GCC/Clang、C++23 -O2 -Wall -Wextra、LOCAL_BENCH有無の4構成で警告0。
- 全2000件でWA・self_wrong・op_label_errorsは0。
- ソースの差は指定した係数1箇所だけ。保存ソース・ビルド結果のSHAも照合した。
- 全2000件で、窓割当・焼きなまし・climb・前段Hungarian・穿孔の非時刻指標は基準と一致。
- 全2000保存設計で列・頻度・汎用層・capが不変。元の穿孔後・再割当前の保存設計
  `20261106-054641_argon-req-ejectstats-v2`から固定追加穴を独立に抽出し、
  新しい所有目標の印刷式と照合した。
- ビルド実行ファイルは/tmpで作り削除済み。`final-audit.json`と`build-results.json`に結果。

## 再開後の残件

採用版ごとに止める指示に従い、ここでマージを待つ。D2を閉じたわけではない。
係数1.05周辺の飽和、既存穴の復元の診断、穴の追加も含む交互最適化が残る。
whole-unit列移動は発火したが予測と実測が逆だった。多数色反転なしの481/500件でも悪化し、
頭の色確率の不連続な切替だけでは説明できない。フィラーの重なりと列費用モデルの診断を残す。
D1は終了。D3（長い列のMDP）、D4（汎用層の価値）、D5（rollout）は未着手。
全実験は[調査報告](../argon-des-perf-late-study/REPORT.md)と
[測定表](../argon-des-perf-late-study/MEASUREMENTS.md)。コミットはしていない。
'''
(candidate/'REPORT.md').write_text(report)

text=['# D2継続の測定表','','差は同時比較の先頭群に対する平均logスコア比（負が改善）。時間は秒。',
      'judge = end_sec + 0.04×helper_end_sec + 0.35×req_sec。全て通常比較・記録・設計保存あり。','']
for file,title in [('grid500.json','回数と係数下側・500件'),('iterations2000.json','回数・2000件'),
                   ('whole500.json','whole-unit・500件'),('upper-restore500.json','上側係数と復元・500件'),
                   ('upper-restore2000.json','上側係数と復元・2000件')]:
    text += [f'## {title}','','| run-id | n | 差 ± SE (%) | 勝/分/敗 | req | helper_end | end | judge平均 | p99 | 最大 | >2秒 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in json.loads((here/file).read_text()):
        j=row['judge'];v=row['score']
        text.append(f"| {row['run']} | {row['n']} | {v['mean']:+.6f} ± {v['se']:.6f} | {'/'.join(map(str,row['wtl']))} | {f(row,'req_sec'):.6f} | {f(row,'helper_end_sec'):.6f} | {f(row,'end_sec'):.6f} | {j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} |")
    text.append('')
(here/'MEASUREMENTS.md').write_text('\n'.join(text))

path=here/'REPORT.md'
marker='\n## 最終判定：係数1.05を採用\n'
contents=path.read_text().split(marker)[0]
contents+=marker+f'''
マージ対象は[argon-des-perf-latew105](../argon-des-perf-latew105/REPORT.md)。
通常2000件で **{score['mean']:+.6f}±{score['se']:.6f}%**、{'/'.join(map(str,c['wtl']))}。
judge平均差{1000*d['mean']:+.3f}±{1000*d['se']:.3f} ms、p99差{1000*d['p99_difference']:+.3f} ms。
全採用条件・4構成警告確認・全紙の独立照合を通過した。
採用版ごとに止める指示に従ってマージを待つ。D2は未終了、D3–D5は未着手。
全測定値は[MEASUREMENTS.md](MEASUREMENTS.md)。
'''
path.write_text(contents)
names=['late-study','late2','late4','latew70','latew85','latew95','latew105','latew110',
       'restoreonly','whole','wholeplain','wholehalf']
dirs=[here.parent/('argon-des-perf-'+name) for name in names]
assert all((d/'README.md').read_text().startswith('改良元: solutions/') for d in dirs)
for directory in dirs:
    for file in directory.rglob('*'):
        if file.is_file():
            with file.open('rb') as handle:
                assert handle.read(4)!=bytes([127,69,76,70]),str(file)
assert hashlib.sha256((candidate/'main.cpp').read_bytes()).hexdigest()==audit['source_sha256']
(here/'packaging-check.json').write_text(json.dumps({'readmes':len(dirs),'elf_binaries':0,
    'final_source_sha256':audit['source_sha256'],'reports_written':True},indent=2)+'\n')
print('Finalized adoption reports',candidate,score,d)
