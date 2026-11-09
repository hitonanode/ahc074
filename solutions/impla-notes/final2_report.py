"""Finalize the reviewable submission report from recorded check results."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[2];notes=Path(__file__).resolve().parent;solver=root/'solutions/final2-reset6'
read=lambda s:json.loads((notes/f'final2-{s}.json').read_text())
checks={s:read(s) for s in ['identity','identity_final','bounds','pattern','normal','stretch','judge']}
files={name:{'bytes':len((solver/name).read_bytes()),'sha256':hashlib.sha256((solver/name).read_bytes()).hexdigest()}for name in ['main.cpp','submit.cpp']}
assert files==json.loads((notes/'final2-files.json').read_text())
assert files['submit.cpp']['bytes']<=524288
sha=files['main.cpp']['sha256']
for suite,data in checks.items():
 for i,r in enumerate(data['runs']):
  assert r['wa']==0 and not r['traps'],(suite,r['run'])
  count=2000 if suite=='normal' else 50 if suite=='judge' else 200
  assert r['n']==r['end_sec']['n']==count
  if suite!='identity' and not(suite=='normal' and i==0):assert r['source_sha256']==sha
 if 'identity' in data:assert all(x['same']==x['n']==200 for x in data['identity'])
assert all(r['end_sec']['max']<=1.92 for r in checks['stretch']['runs'])
log=(notes/'final2-submit-check.log').read_text();assert 'all identical' in log and log.count('only in submit.cpp: none; only in main.cpp: none')==2
# Exactly the authorized reset parameter and measured schedule may differ from fix2.
parent=(root/'solutions/final-time-pace-fix2/main.cpp').read_text();main=(solver/'main.cpp').read_text()
block=r'static constexpr Boundary boundaries\[\] = \{.*?\n    \};'
normalized=re.sub(block,re.search(block,parent,re.S).group(),main,flags=re.S)
normalized=normalized.replace('// Reset6 weights: GCC default and Clang judge flags, 200 cases each. Finite work','// Common weights for both compilers, measured on 200 cases each. Finite work')
reset='''#ifdef LOCAL_BENCH
    inline static const double reset_strength = env_real("D30A_RESET", 6.0);
#else
    static constexpr double reset_strength = 6.0;
#endif'''
assert reset in normalized
normalized=normalized.replace(reset,'    static constexpr double reset_strength = 2.0;')
assert normalized==parent
link=lambda label,path:f'[{label}]({root/path})'
pm=lambda s:f"{s['mean']:+.4f} ± {s['se']:.4f}"
comparison=checks['normal']['comparison'];score=comparison['score_pct'];wtl='/'.join(map(str,comparison['wtl']))
if score['mean']<=-2*score['se']:decision='通常比較でも改善を確認できました。'
elif score['mean']>=2*score['se']:decision='通常比較では有意な悪化があり、採用判断に注意が必要です。'
else:decision='通常比較の差は2 SE未満で、得点の優劣は未確定です。'
lines=[f"{link('final2-reset6/submit.cpp','solutions/final2-reset6/submit.cpp')} を作成しました。指定した全検査は合格です。fix2 に reset6 と測定に基づく設計時間比率を統合し、設計予算1.22秒、pacerの1.88／1.92秒、NOINIT、2件の範囲外参照修正を保持しました。",
 f"通常の2000件比較は **{pm(score)}%**、勝/分/敗 **{wtl}**、両案WA 0です。{decision} ±はケースごとのlogスコア比の標準誤差です。",
 '|ファイル|bytes|SHA-256|\n|---|---:|---|']
for name,x in files.items():lines.append(f"|{link(name,'solutions/final2-reset6/'+name)}|{x['bytes']:,}|`{x['sha256']}`|")
lines += ['提出上限524,288 bytes以内です。`unexpand --first-only -t 4` だけで作成し、trim_toolによる短縮は使っていません。',
 '固定反復・各200件の出力一致は、次の3条件すべてで200/200一致、WA・trapとも0です。時間比率の更新前後で確認しました。LOCAL_BENCHでは全注文effort 0でした。',
 '|条件|reset6基準 run-id|更新前 final2 run-id|最終 final2 run-id|一致|\n|---|---|---|---|---:|']
for label,old,new in zip(['GCC既定','Clang提出相当（LTO含む）','GCC native'],checks['identity']['identity'],checks['identity_final']['identity']):
 lines.append(f"|{label}|`{old['base']}`|`{old['candidate']}`|`{new['candidate']}`|200/200|")
lines += ['時間比率は、同じ境界計測を持つfix2の固定反復をdual30側の段別対照として測定しました。GCCの `20261109-122337_final-time-pace-fix2` と Clangの `20261109-122337_final-time-pace-fix2-2`、対応するfinal2各200件を使用しました。helpersは20.31092→18.49998 ms（−8.916%、対応差 −1.81094 ± 0.31591 ms）。c1_print、c1_perforation、c4_print、c5_printと合わせて5段が3%を超えたため、Task 13と同じく両コンパイラの平均を等重みで合算し、全66段の比率を再計算しました。総予算は維持しています。',
 f"全段の測定値と新旧比率は {link('final2-shares.md','solutions/impla-notes/final2-shares.md')} にあります。",
 '|検査|条件|run-id|件数|WA / trap|end最大 s|\n|---|---|---|---:|---|---:|']
for suite,labels in [('bounds',['Clang libc++ HARDENING_MODE_DEBUG','GCC _GLIBCXX_ASSERTIONS']),('pattern',['Clang NOINIT_EMPTY＋pattern初期化']),('stretch',['PACE_SIM=1.35','PACE_SIM=2.0']),('judge',['Clang 本番相当','GCC 本番相当'])]:
 for label,r in zip(labels,checks[suite]['runs']):lines.append(f"|{suite}|{label}|`{r['run']}`|{r['n']}|0 / 0|{r['end_sec']['max']:.5f}|")
pi=checks['pattern']['identity'][0]
lines += [f"pattern初期化版も、ゼロ初期化側の `{pi['base']}` と200/200件で出力が一致しました。両伸長試験の最大endは1.92秒以下でした。",
 '本番相当50件はLOCAL_BENCH・CLOCK_SCALEを付けず、指定されたGCC／Clangのnative＋zero初期化フラグで実行しました。この2ビルドは指定どおりLTOなしです。',
 '本番相当検査の外部負荷は平均0.830・最大1.239コアでした。WAの確認に用い、得点差の判定は低負荷の通常2000件比較（平均0.125・最大0.330コア）に基づきます。',
 '通常比較は以下の2 run です。LOCAL_BENCHの全力処理で測定し、end_secはCLOCK_SCALE=1.1を適用した値です。',
 '|run-id|件数|end平均 s|p99 s|最大 s|>1.8 / >1.9 / >2.0|WA|\n|---|---:|---:|---:|---:|---|---:|']
for r in checks['normal']['runs']:
 e=r['end_sec'];counts='/'.join(str(e['over'][k])for k in ['1.8','1.9','2.0'])
 lines.append(f"|`{r['run']}`|{r['n']}|{e['mean']:.6f}|{e['p99']:.6f}|{e['max']:.5f}|{counts}|0|")
lines += ['同じ通常比較での時間差（final2−fix2）です。差は平均 ± SE、p99は各案の分位点です。',
 '|指標|対応差 ms|fix2 p99 s|final2 p99 s|\n|---|---:|---:|---:|']
for key in ['helper_end_sec','req_sec','end_sec']:
 delta=comparison['times'][key];a,b=checks['normal']['runs']
 lines.append(f"|{key}|{delta['mean']:+.3f} ± {delta['se']:.3f}|{a[key]['p99']:.6f}|{b[key]['p99']:.6f}|")
lines += ['提出ファイルの `-E -P` トークン列は、LOCAL_BENCHなしのGCC・Clang両方でmain.cppと一致しました。GCCは1,589,294 tokens、Clangは1,590,318 tokens。`-Wall` の警告はmain/submitともGCC 4件、Clang 3件で差0です。',
 f"検査ログは {link('final2-submit-check.log','solutions/impla-notes/final2-submit-check.log')}。",
 '計画上の変更は、指定条件に該当した時間比率の再計算です。三方向マージの競合はなく、ソース差分もreset係数・その試験用スイッチ・時間比率だけであることを機械的に確認しました。手元はGCC 13.3／Clang 18.1.3で、ジャッジのClang 21実機による検証ではありません。',
 f"全runの結果・コンパイル条件・外部負荷は {link('PROGRESS-final2.md','solutions/impla-notes/PROGRESS-final2.md')} と同ディレクトリのfinal2-*.jsonに保存しています。コミットは作成していません。同文の {link('REPORT-final2.md','solutions/impla-notes/REPORT-final2.md')} を保存しました。"]
# Adjacent table rows stay adjacent; paragraphs retain blank separation.
text='';previous_table=False
for line in lines:
 is_table=line.startswith('|')
 if text:text+='\n' if previous_table and is_table else '\n\n'
 text+=line;previous_table=is_table
text+='\n';(notes/'REPORT-final2.md').write_text(text)
(notes/'final2-final-audit.json').write_text(json.dumps({'files':files,'authorized_diff_only':True,'all_current_source_checks_pass':True,'normal':comparison},ensure_ascii=False,indent=2)+'\n')
progress=notes/'PROGRESS-final2.md';old=progress.read_text();marker='\n## 最終検査の記録\n'
old=old.split(marker)[0]
detail=[marker]
for suite,data in checks.items():
 detail.append('\n'+suite+'：')
 for r in data['runs']:
  load=r['outside_load'];e=r['end_sec']
  detail.append(f"- `{r['run']}`: n={r['n']}, WA={r['wa']}, trap={len(r['traps'])}, end平均/p99/最大={e['mean']:.6f}/{e['p99']:.6f}/{e['max']:.6f} s、外部負荷={json.dumps(load,ensure_ascii=False)}。コンパイル: `{r['compile_command']}`")
 if 'identity' in data:
  for x in data['identity']:detail.append(f"- 出力一致 `{x['base']}` → `{x['candidate']}`: {x['same']}/{x['n']}。")
detail.append('\n通常比較の対応差: '+json.dumps(comparison,ensure_ascii=False)+'\n')
progress.write_text(old+'\n'.join(detail))
print(text)
