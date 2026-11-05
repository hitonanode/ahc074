"""Record the decisive comparison against the updated BASE.md."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
b,c=json.loads((H/'rebase-2000.json').read_text());m=lambda r,k:r['metrics'][k]['mean']
assert b['n']==c['n']==2000
rate=-c['score']['mean']/(c['judge']['mean']-b['judge']['mean'])
assert c['score']['mean']<-2*c['score']['se'] and c['score']['mean']<-.005
assert c['judge']['mean']<=1.6 and c['judge']['p99']<=1.77
assert c['judge']['mean']-b['judge']['mean']<=.01 or rate>.6
name='argon-des-perf-strata32-v2';folder=H.parent/name
audit=json.loads((folder/'final-audit.json').read_text())
assert audit['previous_designs_identical'] and audit['design_metrics_identical']
wtl='/'.join(map(str,c['wtl']));diff=f"{c['score']['mean']:+.6f} ± {c['score']['se']:.6f}%"
section=f'''## PR #140 上の最終採用判定

最終確認時にBASE.mdが `solutions/argon-req-completefast-v3`（PR #140）へ変わったので、
新しい `solutions/{name}` に標本生成の変更だけを移植した。
旧基準の解法のまま採用とはせず、新基準を基準側に置いて通常比較を取り直した。

基準 **`{b['run']}`**、候補 **`{c['run']}`**。
500件で−0.011 ± 0.009%、245/14/241だったため、同じrunを2000件へ延長した。
両側2000設計保存、記録あり。

- **{diff}**、勝/分/敗 **{wtl}**、{-c['score']['mean']/c['score']['se']:.2f} SE。
- req_sec **{m(b,'req_sec'):.6f}→{m(c,'req_sec'):.6f}**、helper_end_sec **{m(b,'helper_end_sec'):.6f}→{m(c,'helper_end_sec'):.6f}**、
  end_sec **{m(b,'end_sec'):.6f}→{m(c,'end_sec'):.6f}秒**。
- judge平均 **{b['judge']['mean']:.6f}→{c['judge']['mean']:.6f}**、p99 **{b['judge']['p99']:.6f}→{c['judge']['p99']:.6f}**、
  最大 **{b['judge']['max']:.6f}→{c['judge']['max']:.6f}秒**。2秒超えは両側0。
- 追加judge平均 **{1000*(c['judge']['mean']-b['judge']['mean']):.3f} ms**、改善効率 **{rate:.3f}%/秒**。
- 穿孔時間 {m(b,'perforation_sec')*1000:.3f}→{m(c,'perforation_sec')*1000:.3f} ms、
  穴数 {m(b,'perforation_holes'):.3f}→{m(c,'perforation_holes'):.3f}。
- GCC/Clang × LOCAL_BENCH有無、4構成で警告0。WA・self_wrong・op_label_errorsは全件0。
- 変更は+11/−4行。採用済みの注文処理を含め、穿孔以外の段・全ログ・profiler・switch・段の目印・目次は基準と同じ。
- 旧候補strata32と保存設計が2000件全て一致し、gobj・model_cost各項・proxyも一致した。
  `final-audit.json`で評価ソース、ビルドのSHA、全件の正当性と照合した。ビルド用実行ファイルは/tmpから削除済み。

**マージ対象は `solutions/{name}`。新基準で全採用条件を満たしたため停止する。**
D2の残る方向は、層別16/64などの時間効率、新しい標本数での係数・非head候補、前段への穿孔の影響。
D3〜D5は未開始。次回は更新されたBASE.mdから再開する。
'''
old=(H/'REPORT.md').read_text();body=old[old.index('## 助言と現行コード'):]
body=body.split('## PR #140 上の最終採用判定')[0]
body=body.replace('## 最終比較、採用条件、引き継ぎ','## 旧基準での採用条件と基準更新')
lead=f'''# D2 続き: 穿孔の色標本の分散

**最終マージ対象: `solutions/{name}`（PR #140上）。**
通常2000件で **{diff}**、勝/分/敗 **{wtl}**。
judge平均 **{c['judge']['mean']:.6f}秒**、p99 **{c['judge']['p99']:.6f}秒**、改善効率 **{rate:.3f}%/秒**。
全採用条件を満たしたため停止してマージを待つ。D2自体は未完了。
採用版の[REPORT](../{name}/REPORT.md)、全比較の[MEASUREMENTS](MEASUREMENTS.md)。
以下の探索はPR #139上、末尾がPR #140への移植と最終比較である。

'''
(H/'REPORT.md').write_text(lead+body+'\n'+section)
readme=f'''# D2 採用候補: 穿孔の層別32標本（PR #140上）

改良元: `solutions/argon-req-completefast-v3`。
助言01-1「穿孔処理とフィラー評価の対象拡大」の継続検証で見つけた色標本の選択誤差を抑える。
`Handle perforation` の `Perforation::kSamples` を8→32、`rebuild`の色標本を層別抽出に変える。
受理係数0.7、owner条件付け、利益上限、差分キャッシュは維持。変更は+11/−4行。
他の段とログ・profiler・switchは不変。

詳細な検証・不採用案・診断は[調査REPORT](../argon-des-perf-neighborhood/REPORT.md)、
各比較の時間は[MEASUREMENTS](../argon-des-perf-neighborhood/MEASUREMENTS.md)。
旧基準PR #139では−0.021836 ± 0.004853%だったが、BASE更新を確認し、この版で採用判定を取り直した。
独立32標本も有意に改善しており、層別化だけの寄与は分離して確定していない。

'''+section
(folder/'REPORT.md').write_text(readme)
p=H/'MEASUREMENTS.md';text=p.read_text().split('## PR #140 最終2000件')[0]
text+='## PR #140 最終2000件\n\n| run-id | n | 差 ± SE (%) | 勝/分/敗 | req | helper end | judge平均 | p99 | 最大 | >2秒 | 穴数 | 穿孔時間 |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
for r in [b,c]:
    j=r['judge'];text+=f"| {r['run']} | {r['n']} | {r['score']['mean']:+.6f} ± {r['score']['se']:.6f} | {'/'.join(map(str,r['wtl']))} | {m(r,'req_sec'):.6f} | {m(r,'helper_end_sec'):.6f} | {j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} | {m(r,'perforation_holes'):.3f} | {m(r,'perforation_sec'):.6f} |\n"
p.write_text(text)
print('final candidate',name,'score',diff,'judge',c['judge'],'gain per second',rate)
