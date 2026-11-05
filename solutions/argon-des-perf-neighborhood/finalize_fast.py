"""Final adoption check for identical DP values stored contiguously."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
load=lambda n:json.loads((H/n).read_text())
b,c=load('fast-2000.json');m=lambda r,k:r['metrics'][k]['mean']
assert b['n']==c['n']==2000
rate=-c['score']['mean']/(c['judge']['mean']-b['judge']['mean'])
assert c['score']['mean']<-2*c['score']['se'] and c['score']['mean']<-.005
assert c['judge']['mean']<=1.6 and c['judge']['p99']<=1.77
assert c['judge']['mean']-b['judge']['mean']<=.01 or rate>.6
identity=load('fast-identity2000.json');assert identity['stdout_identical']==identity['stderr_identical']==2000
name='argon-des-perf-stratafast';folder=H.parent/name
audit=json.loads((folder/'final-audit.json').read_text());assert audit['previous_designs_identical'] and audit['design_metrics_identical']
wtl='/'.join(map(str,c['wtl']));diff=f"{c['score']['mean']:+.6f} ± {c['score']['se']:.6f}%"
section=f'''## PR #140 上の最終採用版: 値だけの連続キャッシュ

穿孔の層別32標本だけを移植したv2は、得点が改善してもjudge平均1.603557/p99 1.781163秒で不採用だった。
`argon-des-perf-stratafast` は `QueryCache::value` だけを連続配列 `cache_value` にも保存する。
不変な目標では大きなDPレコードの参照を省き、DP再構築時に値も同時に更新する。
値の加算順と受理式を維持し、結果を変えずに時間を削る。

500件の3者比較は `20261106-030225_argon-req-completefast-v3` /
`20261106-030615_argon-des-perf-strata32-v2` / `20261106-030615_argon-des-perf-stratafast`。
高速化の前後は全得点、stdout、時刻以外のstderrが500/500一致した。
穿孔時間は29.382→28.100 ms、judge平均は1.614807→1.602092秒。
局所の時間差は約1.3 msであり、全体の約12.7 ms差にはコード配置などの影響も含まれる。
連続配列だけで全体差の全てを説明したとは主張せず、最終の両側同時比較で時間枠を判断した。

最終は基準 **`{b['run']}`**、候補 **`{c['run']}`** を2000件へ延長した。
両側2000設計を保存、記録あり。BASE.mdはPR #140のままであることを延長前に再読した。

- **{diff}**、勝/分/敗 **{wtl}**、{-c['score']['mean']/c['score']['se']:.2f} SE。
- req_sec **{m(b,'req_sec'):.6f}→{m(c,'req_sec'):.6f}**、helper_end_sec **{m(b,'helper_end_sec'):.6f}→{m(c,'helper_end_sec'):.6f}**、
  end_sec **{m(b,'end_sec'):.6f}→{m(c,'end_sec'):.6f}秒**。
- judge平均 **{b['judge']['mean']:.6f}→{c['judge']['mean']:.6f}**、p99 **{b['judge']['p99']:.6f}→{c['judge']['p99']:.6f}**、
  最大 **{b['judge']['max']:.6f}→{c['judge']['max']:.6f}秒**。2秒超え {b['judge']['over2']}→{c['judge']['over2']}。
- 追加judge平均 **{1000*(c['judge']['mean']-b['judge']['mean']):.3f} ms**、改善効率 **{rate:.3f}%/秒**。
- 穿孔時間 {m(b,'perforation_sec')*1000:.3f}→{m(c,'perforation_sec')*1000:.3f} ms、
  穴数 {m(b,'perforation_holes'):.3f}→{m(c,'perforation_holes'):.3f}。
- GCC/Clang × LOCAL_BENCH有無の4構成で警告0。WA・self_wrong・op_label_errorsは全件0。
- 旧v2の通常2000件ともstdout・時刻以外のstderrが **2000/2000一致**（`fast-identity2000.json`）。
  旧基準の層別版とも保存設計・前段のmodel/gobj/proxyが全2000件一致した。
- `final-audit.json` は評価ソースとビルドSHA、段の保持、全件の正当性を照合する。
  ビルド用実行ファイルは/tmpで作り、削除済み。

**マージ対象は `solutions/{name}`。新基準で採用条件を満たしたため停止する。**
基準との差は+18/−6行、`Handle perforation` の標本数・標本生成・DP値の保存だけ。
採用済み注文処理、全ログ・profiler・switch・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次は保持する。
D2は未完了。再開後は層別16/64などの時間効率、新標本数での係数・非head候補、前段への穿孔の影響を続ける。
D3〜D5は未開始。新しいBASE.mdを読んで再開する。
'''
old=(H/'REPORT.md').read_text();body=old[old.index('## 助言と現行コード'):]
body=body.split('## PR #140 上の最終採用版:')[0]
lead=f'''# D2 続き: 穿孔の色標本の分散とDP値キャッシュ

**最終マージ対象: `solutions/{name}`（PR #140上）。**
通常2000件で **{diff}**、勝/分/敗 **{wtl}**。
judge平均 **{c['judge']['mean']:.6f}秒**、p99 **{c['judge']['p99']:.6f}秒**、改善効率 **{rate:.3f}%/秒**。
採用条件を満たしたため停止してマージを待つ。D2自体は未完了。
採用版の[REPORT](../{name}/REPORT.md)、全比較の[MEASUREMENTS](MEASUREMENTS.md)。
探索はPR #139から始め、基準更新後にPR #140へ移植した。時間条件を満たさなかった版も下に記録する。

'''
(H/'REPORT.md').write_text(lead+body+'\n'+section)
(folder/'REPORT.md').write_text(f'''# D2 採用候補: 層別32標本とDP値キャッシュ

改良元: `solutions/argon-req-completefast-v3`（PR #140）。
助言01-1「穿孔処理とフィラー評価の対象拡大」を検証する中で、色標本の選択誤差を抑える変更を得た。
詳細な比較・不採用案・診断は[調査REPORT](../argon-des-perf-neighborhood/REPORT.md)、
全runの時間は[MEASUREMENTS](../argon-des-perf-neighborhood/MEASUREMENTS.md)。
独立32標本も有意に改善しており、層別化だけの寄与は分離して確定していない。

'''+section)
p=H/'MEASUREMENTS.md';text=p.read_text().split('## PR #140 移植と高速化')[0]
text+='## PR #140 移植と高速化\n\n'
for title,rows in [('層別32だけ、2000件・時間超過で不採用',load('rebase-2000.json')),('高速化の対照、500件',load('fast-500.json')),('最終、2000件',[b,c])]:
    text+=f'### {title}\n\n| run-id | n | 差 ± SE (%) | 勝/分/敗 | req | helper end | judge平均 | p99 | 最大 | >2秒 | 穴数 | 穿孔時間 |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        j=r['judge'];text+=f"| {r['run']} | {r['n']} | {r['score']['mean']:+.6f} ± {r['score']['se']:.6f} | {'/'.join(map(str,r['wtl']))} | {m(r,'req_sec'):.6f} | {m(r,'helper_end_sec'):.6f} | {j['mean']:.6f} | {j['p99']:.6f} | {j['max']:.6f} | {j['over2']} | {m(r,'perforation_holes'):.3f} | {m(r,'perforation_sec'):.6f} |\n"
    text+='\n'
p.write_text(text)
print('final candidate',name,'score',diff,'judge',c['judge'],'gain per second',rate)
