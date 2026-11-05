from pathlib import Path
import subprocess,sys,re,json,statistics,difflib,hashlib
work=Path(__file__).resolve().parent;p=Path('solutions/argon-req-ejecthelper');root=Path('/home/sato/ahc074/runs')
fixed_base,fixed_cand=re.findall(r'run-id: (\S+)',(p/'fixed-final.log').read_text())
names=re.findall(r'run-id: (\S+)',(p/'normal-final.log').read_text());assert len(names)==2
normal_base,normal_cand=names
for label,base,cand in [('fixed',fixed_base,fixed_cand),('normal',normal_base,normal_cand)]:
 with (p/(label+'-analysis.log')).open('w') as out:
  subprocess.run([sys.executable,str(work/'analyze.py'),base,cand,'--json',str(p/(label+'-results.json'))],stdout=out,stderr=subprocess.STDOUT,check=True)
 with (p/(label+'-metrics.log')).open('w') as out:
  subprocess.run([sys.executable,str(work/'metrics.py'),base,cand],stdout=out,stderr=subprocess.STDOUT,check=True)
with (p/'builds.log').open('w') as out:
 subprocess.run([sys.executable,str(work/'check_builds.py'),str(p)],stdout=out,stderr=subprocess.STDOUT,check=True)
with (p/'validation.log').open('w') as out:
 subprocess.run([sys.executable,'solutions/argon-req-oldvalue/check_final.py',normal_base,normal_cand,fixed_cand,str(p)],stdout=out,stderr=subprocess.STDOUT,check=True)
 assert (root/normal_cand/'src/main.cpp').read_bytes()==(p/'main.cpp').read_bytes()==(root/fixed_cand/'src/main.cpp').read_bytes()
 old=root/'20261106-030059_argon-req-completeeject-old';new=root/fixed_cand
 files=list((new/'out').glob('*.txt'))+list((new/'orders').glob('*/out/*.txt'))
 assert len(files)==4000
 for f in files:
  assert f.read_bytes()==(old/f.relative_to(new)).read_bytes(),f
 out.write('All 4000 final fixed stdout files equal the unsimplified prototype.\n')
 with (p/'trace-validation.log').open('w') as t:
  subprocess.run([sys.executable,str(work/'check_trace.py')],stdout=t,stderr=subprocess.STDOUT,check=True)
 assert 'All four builds passed with no warnings.' in (p/'builds.log').read_text()
 for run in [root/normal_base,root/normal_cand]:assert len(list((run/'design').glob('*')))==2000
 out.write('Four warning-free builds and 2000 saved designs in each normal arm confirmed.\n')
scratch=Path('/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/argon')
with (p/'judge-model.log').open('w') as out:
 subprocess.run(['/home/sato/ahc074/.venv/bin/python',str(scratch/'judge_model.py'),normal_base,normal_cand],stdout=out,stderr=subprocess.STDOUT,check=True)
f=json.loads((p/'fixed-results.json').read_text())[fixed_cand]
n=json.loads((p/'normal-results.json').read_text())[normal_cand]
assert f['seeds']==2000 and f['cases']==4000 and n['seeds']==2000 and n['cases']==2000
assert -f['score_log_pct']>=.005 and f['score_log_pct']+2*f['se_pct']<0 and n['score_log_pct']<0,(f['score_log_pct'],n['score_log_pct'])
assert n['judge']['mean']<=1.600 and n['judge']['p99']<=1.770,n['judge']
extra_req=n['means']['req_sec']-n['baseline_means']['req_sec'];rate=-f['score_log_pct']/n['judge_mean_delta'] if n['judge_mean_delta']>0 else float('inf')
assert n['judge_mean_delta']<=.01 or rate>.6,rate
for x in [f,n]:
 assert x['WA']==0 and x['means']['self_wrong']==0 and x['means']['op_label_errors']==0
base_text=(scratch/'BASE.md').read_text()
assert re.search(r'Current base \(SOTA\): `solutions/argon-req-completefast-v3`',base_text),'BASE changed: port and rerun before adoption'
before=(root/normal_base/'src/main.cpp').read_text();after=(p/'main.cpp').read_text();changes=list(difflib.ndiff(before.splitlines(),after.splitlines()));added=sum(x.startswith('+ ') for x in changes);removed=sum(x.startswith('- ') for x in changes)
rows=[]
for q in list((root/fixed_cand/'err').glob('*.txt'))+list((root/fixed_cand/'orders').glob('*/err/*.txt')):
 rows.append(dict((k,float(v)) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',q.read_text(),re.M)))
metrics={k:statistics.mean(row[k] for row in rows) for k in rows[0] if k.startswith('value_seed_')};(p/'local-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
real=f['baseline_means']['total_moves']-f['means']['total_moves']
def w(x):return '/'.join(map(str,x['wtl']))
table='\n'.join(f"| {label} | **{x['score_log_pct']:.6f} ± {x['se_pct']:.6f}** | {w(x)} | {x['baseline_means']['req_sec']:.8f}→{x['means']['req_sec']:.8f} | {x['req_ratio']:.6f} |" for label,x in [('固定2000×2',f),('通常2000',n)])
times='\n'.join(f"| {label} | {n['baseline_judge'][key]:.8f} | {n['judge'][key]:.8f} |" for label,key in [('平均','mean'),('p99','p99'),('最大','max')])
history=(work/'REPORT.md').read_text()
report=f'''# R2: 編集済み共同DP計画の追加eject

**採用候補: solutions/argon-req-ejecthelper。基準はPR #140のsolutions/argon-req-completefast-v3。採用条件を満たしたため、順次マージの指示に従ってここで停止する。コミットはしていない。**

## 指摘の現在の意味と変更

助言02-③の「整数のフィラー利得だけでは将来価値の良い候補を落とす」という指摘を継続した。PR #137と#140で価値付きDPを2種加えたが、初期値が僅かに負けた計画は、通常の候補編集まで済んでもejectを受けないことがある。`Request processing (process)`の`plan_cache`にその編集済み経路・状態が残っている。そこを再利用する。

抽出直後の積層価値を使う共同DPの計画に限り、現在の完成値との差0.5以内、別積層、未ejectの場合に既存の`polish_ejects`を適用する。DP・編集の再実行や中立探索の追加はしない。完成値を厳密に改善したときだけ採用する。既存計画・目的関数・設計・予算・乱数は変更せず、将来注文を参照しない。

修正後DPにも広げる案は2000×2で追加利得が約0.000635%しかなく、時間に見合わなかった。値差を0.25に狭める案は利得を約半分失い、追加ejectを1回だけにする案にも時間効率の改善は確認できなかった。詳細は下の試行表に残す。

## 最終比較

固定設計: `20261106-022300_argon-req-completefast-v3`。固定runは `{fixed_base}` / `{fixed_cand}`、2000×2。通常runは `{normal_base}` / `{normal_cand}`、2000 seeds、`--save-design`。通常runは記録し、両腕の2000設計を保存した。各最終比較前と報告時にBASE.mdを再確認した。

| 比較 | 平均log比 ± SE (%) | 勝/分/敗 | req_sec 基準→候補 | 比 |
|---|---:|---:|---:|---:|
{table}

通常比較のジャッジ時間モデル（提供されたjudge_model.pyでも照合）:

| 指標 | 基準 | 候補 |
|---|---:|---:|
{times}
| 2秒超え | {n['baseline_judge']['over2']} | {n['judge']['over2']} |

平均増分は{n['judge_mean_delta']:.8f}秒。固定比較の利得を通常比較のジャッジモデル平均増分全体で割ると **{rate:.3f}%/秒**。実用閾値0.005%、2SE、平均1.600秒・p99 1.770秒の時間枠を満たす。設計annealの予算を削る取引は不要だった。追加ejectの処理を専用の非インライン関数へ切り出し、通常経路のコードとスタックに低頻度の処理を置かない構造にした。

## 予測と実現、および悪化例

固定4000ケースの1ケース平均: 追加eject {metrics['value_seed_trials']:.4f}回、採用{metrics['value_seed_accepts']:.4f}回、完成評価値改善{metrics['value_seed_gain']:.6f}、採用時の即時手数差{metrics['value_seed_saved']:.6f}。実現した総手数差は{real:.6f}手で、完成評価値の予測の約{100*real/metrics['value_seed_gain']:.1f}%だった。

`observe.py cases / queries / state / stats --vs`と保存出力の再生で改善・悪化の両方を調べた（episodes.log）。試作と最終版のstdoutは全4000ケース一致している。

- seed1124、注文395: 12→11手。紙164の返却・再抽出を再利用へ変え、紙107をrepairで差し込む。以後、積層が再合流する注文492までの区間は11手改善。
- seed590、注文432: 両方10手だが残す紙が異なり、翌注文は12→13手。再合流する注文518までの区間は16手悪化。

区間には後続の別判断も含まれるので、全差を最初の選択の因果効果とは扱わない。局所の目的関数改善が各列の将来を完全には予測しないことを示す。全体では予測と実現の向きが合い、通常2000でも改善する。

## 正当性・解析機能・ビルド

- 固定4000ケース・通常2000ケースでWA / self_wrong / op_label_errorsはすべて0。
- 通常2000件の設計stdout部分と全@paperは基準と一致。候補の通常stdoutは固定比較の注文列0と2000件すべて一致。
- 整理前のcompleteeject-oldと最終版は全4000 stdoutが一致。200×2では@paper/@opsも一致。ejectcacheから専用関数版への分離は、通常200件のstdoutと全非時刻stderrが一致。
- 不要なplan_costを呼ばないためcf_value_hits/missesは変化する。ns_changed/ns_savedは追加処理を含む最終結果を数えるようにし、heavy traceも実際の最終経路を記録する。他の既存指標名・順序、ログ・スイッチ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStoreは維持。
- 関数分離前の整理版について、F3_HEAVY_TRACE=1の単独8 seeds確認は`20261106-032407_argon-req-ejectcache`。全#heavyの最終操作列とラベルをstdout/@opsに照合し、trace有無のstdoutも一致（trace-validation.log）。この短い実行の時間は性能判断に用いない。
- GCC/Clang、LOCAL_BENCH有無の4構成を`-std=c++23 -O2 -Wall -Wextra`でビルドし、警告0。
- {len(before.splitlines())}→{len(after.splitlines())}行、{added}行追加・{removed}行削除。変更段はRequest processingとmain: statisticsのみ。段の目印・目次・設計は変更しない。
- 最終main.cppは固定・通常runの保存ソースとバイト一致。SHA256: `{hashlib.sha256(after.encode()).hexdigest()}`。

## 再開時の残件

R2全体は閉じない。旧紙の完全な局所計画による重み付けは24×2の確認まで、第2紙集合の後処理での候補押し出し、およびseededit-wideの新基準での残余効果は未解決。採用後のBASE.mdから継続し、飽和の証拠を得てからR3〜R5へ進む。R3〜R5は未着手。

## 今回の全試行

{history}
'''
(p/'REPORT.md').write_text(report)
print('All adoption checks passed. Final Japanese REPORT.md written.',flush=True)
print('fixed',f['score_log_pct'],f['se_pct'],f['wtl'],'req ratio',f['req_ratio'],flush=True)
print('normal',n['score_log_pct'],n['se_pct'],n['wtl'],'req ratio',n['req_ratio'],'judge',n['judge'],'rate',rate,flush=True)
