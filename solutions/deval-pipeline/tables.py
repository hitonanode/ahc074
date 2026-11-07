"""Render completed training trials and exact-output checks from summary.json."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=json.loads((P/'summary.json').read_text())
def f(v,scale=1,n=4):return f'{v[0]*scale:+.{n}f} ± {v[1]*scale:.{n}f}'
def short(run):return run.split('_',1)[1]
lines=['## 学習用の全試行','', '設定選択はseed 0–499のみ。負が改善、±はseed単位の標準誤差。品質は各seedの対象注文列の平均スコアのlog比×100で測る。設計変更の基準は`20261107-130357_deval-ordered8`。時間は同じ24並列の通常比較。','', '### 設計の変更','', '| 候補 | 新規1–7 % ± SE | 全8列 % ± SE | 列0 % ± SE | 設計時間差 ms ± SE | judge/old | p99 候補/nofb 秒 | 設計run / replay |','|---|---:|---:|---:|---:|---:|---:|---|']
for r in rows:
 if r['kind']!='quality':continue
 lines.append(f"| {r['tag']} | {f(r['fresh'])} | {f(r['all'])} | {f(r['real'])} | {f(r['design_delta'],1000,2)} | {r['judge_ratio_old']:.4f} | {r['judge_p99'][0]:.4f} / {r['judge_p99'][1]:.4f} | `{r['design']}` / `{r['run']}` |")
lines+=['', '### 注文処理のみ','', '500ケース×4列の同時比較。保存設計は通常133130_ordered8、free-*併用は142620_free-color、flex8/NSの配分は161041_flex8-fast。各行に比較元replayを併記する。req_sec差はreplay内の比較であり、通常実行のjudge時間の代用にはしない。','', '| 候補 | 全4列 % ± SE | 新規1–3 % ± SE | 列0 % ± SE | req差 ms ± SE | run / 比較元 |','|---|---:|---:|---:|---:|---|']
for r in rows:
 if r['kind']=='request':lines.append(f"| {short(r['run'])} | {f(r['all4'])} | {f(r['fresh3'])} | {f(r['real'])} | {f(r['req_delta'],1000,2)} | `{r['run']}` / `{r['ref']}` |")
lines+=['','### 出力同一の高速化','', 'stdoutをバイト単位で照合。時間差は候補−親、local scaled秒。fast-mathなし。不採用案はGCC段階で閉じ、採用する変更はClangでも同じ確認を行う。','', '| 候補 | compiler | 段 | 段の差 ms ± SE | judge差 ms ± SE | stdout一致 | run |','|---|---|---|---:|---:|---:|---|']
for r in rows:
 if r['kind']!='speed':continue
 name=short(r['run']);stage='req_sec'
 if any(t in name for t in ['sort','radix','prefix','msd-lazy']):stage='map_end_sec'
 if any(t in name for t in ['target-delta','target-plane','column-kind']):stage='dv_anneal_sec'
 if 'exact5' in name:stage='map_end_sec'
 if any(t in name for t in ['vheads','vdraw','vfast','vstatic']):stage='dv_eval_sec'
 if 'flex8-fast' in name:stage='helper_end_sec'
 if any(t in name for t in ['flex8-arrays','flex8-matrix','flex8-dense']):stage='dv_finish_sec'
 if 'mdp-dag' in name:stage='colmdp_sec'
 lines.append(f"| {name} | {r.get('compiler','—')} | {stage} | {f(r[stage],1000,2)} | {f(r['judge_delta'],1000,2)} | {r['identical']}/{r['n']} | `{r['run']}` |")
(P/'TABLES.md').write_text('\n'.join(lines)+'\n')
print(len(rows),'rows')
