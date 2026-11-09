"""Write the final gbias decision from recorded paired comparisons."""
import hashlib,json
from pathlib import Path
notes=Path(__file__).resolve().parent;root=notes.parents[1]
read=lambda n:json.loads((notes/(n+'.json')).read_text())
screen=read('gbias-screen-500');gcc=read('gbias-screen-2000')[0];clang=read('gbias-clang-2000')[0];identity=read('gbias-logcheck')
rows=[('GCC λ=0.001',screen[0]),('GCC λ=0.002',screen[1]),('GCC λ=0.001',gcc),('Clang λ=0.001',clang)]
assert all(x['wa']==[0,0] for _,x in rows)
assert identity['same']==identity['n']==20 and identity['wa']==0
loads=[screen[0]['outside_load'][0],gcc['extensions'][0][0]['outside_load'],clang['outside_load'][0]]
assert all(x['mean_cores']<.5 and x['max_cores']<3 for x in loads), 'Comparison timing needs a clean repeat'
for name,info in read('final2-files').items():
 assert hashlib.sha256((root/'solutions/final2-reset6'/name).read_bytes()).hexdigest()==info['sha256']
pm=lambda x,n=4:f"{x['mean']:+.{n}f} ± {x['se']:.{n}f}"
metric=lambda x,key:pm(x['metrics'][key]['difference'],6)
passed=lambda x:x['score_pct']['mean']<=-2*x['score_pct']['se'] and x['net_score_pct']['mean']<=-2*x['net_score_pct']['se']
if passed(clang):
 status='Clang条件で成功です。' + ('GCCでも採用条件を満たしました。'if passed(gcc)else'GCCでは2 SE未満で、改善は未確定です。')
else:status='改善未確認のため不採用です。GCC・Clangとも、時間換算後の2 SE条件を満たしません。'if not passed(gcc)else'GCCでは成功ですが、Clangでは採用条件を満たしません。'
link=lambda label,path:f'[{label}]({root/path})'
lines=[f"**gobj-handle-biasは{status}** 実装は {link('d30a-gbias','solutions/d30a-gbias/main.cpp')} にあります。final2-reset6は変更しておらず、既存の再検査スクリプトも保持しています。",
 '以下の±は標準誤差、scoreは平均log(候補/基準)の百分率です。負なら改善。全評価でWA 0でした。',
 f"GCCの基準は `{gcc['base']}`。λ=0.001は `{gcc['candidate']}`（500→2000件）、λ=0.002は `{screen[1]['candidate']}`（500件）です。Clangの基準／候補は `{clang['base']}` ／ `{clang['candidate']}`（各2000件）です。",
 '|条件|件数|score % ± SE|W/T/L|dv_best差 ± SE|補正前gobj差 ± SE|\n|---|---:|---:|---|---:|---:|']
for name,x in rows:lines.append(f"|{name}|{x['n']}|{pm(x['score_pct'])}|{'/'.join(map(str,x['wtl']))}|{metric(x,'dv_best')}|{metric(x,'gobj_after')}|")
lines += ['500件ではλ=0.001だけがdv_bestの2 SE条件を通過しました。λ=0.002はVの改善が2 SE未満で、補正前gobjの悪化も0.02を超えたため打ち切りました。',
 '対応する時間差（候補−基準、ms）と、指定の換算率によるscore補正値です。設計100 msを0.03%、注文100 msを0.055%として加算し、短縮は逆向きに換算しています。補正値のSEもケースごとの差から計算しました。',
 '|条件・件数|helper_end差 ms|req差 ms|end差 ms|時間換算後 % ± SE|\n|---|---:|---:|---:|---:|']
for name,x in rows:
 times=[pm(x['metrics'][k]['difference'],3)for k in ['helper_end_sec','req_sec','end_sec']]
 lines.append(f"|{name}・{x['n']}|{'|'.join(times)}|{pm(x['net_score_pct'])}|")
lines += ['2000件比較のp99です（基準→候補、ms）。', '|ビルド|helper_end|req|end|\n|---|---:|---:|---:|']
for name,x in [('GCC',gcc),('Clang',clang)]:
 lines.append('|'+name+'|'+'|'.join(f"{x['metrics'][k]['base_p99']:.3f} → {x['metrics'][k]['candidate_p99']:.3f}"for k in ['helper_end_sec','req_sec','end_sec'])+'|')
b=screen[0]['design_bias'];m=gcc['metrics']
lines += [f"機構は働いています。500件のλ=0.001では、ハンドルの偏りBが{b['B']['base_mean']:.3f}→{b['B']['candidate_mean']:.3f}、少数色割合が{100*b['minority_share']['base_mean']:.3f}%→{100*b['minority_share']['candidate_mean']:.3f}%になりました。GCC 2000件ではmodel_hole差 {pm(m['model_hole']['difference'],6)}、model_gc差 {pm(m['model_gc']['difference'],6)}。穴費用の改善と汎用層の費用増が同時に起きています。",
 '実装は旧as6-gproxyと同じ **gobj−λB** です。S項は使わず、対の整数キー・枝刈り・キャッシュ・反復回数を保持しました。LOCAL_BENCHの `D30A_GBIAS` でλを指定できます。新しい時計読みや時間打切りはありません。',
 '初版の新設ログには、山登りで最良状態を復元した後も最後に受理した状態のhmを読む問題がありました。探索・得点・dv_bestには影響しません。診断を最良maskからの計算に修正し、表の補正前gobjは保存設計のBと補正後目的から復元しました。',
 f"動作確認は `20261109-132134_d30a-reset6` と同時刻の `d30a-gbias`／`-2`／`-3`（λ=0／0.001／0.002）、各20件WA 0。λ=0はstdoutも20/20一致。診断修正後は `{identity['candidate']}` で20件WA 0、修正前 `{identity['base']}` とstdoutが20/20一致しました。",
 'Clang比較は `-O2 -std=gnu++23 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero` にLOCAL_BENCHとCLOCK_SCALE=1.1を付けています。手元のClang 18.1.3による検査です。',
 '外部負荷（平均／最大コア）は、GCC 500件・追加1500件・Clang 2000件の順に '+ '、'.join(f"{x['mean_cores']:.3f}／{x['max_cores']:.3f}"for x in loads)+'で、いずれも基準内でした。',
 f"詳細は {link('PROGRESS.md','solutions/impla-notes/PROGRESS.md')} とgbias-*.json、差分は {link('gbias.patch','solutions/impla-notes/gbias.patch')}。{link('REPORT.md','solutions/impla-notes/REPORT.md')} に追記し、同文を {link('REPORT-gbias.md','solutions/impla-notes/REPORT-gbias.md')} に保存しました。コミットは作成していません。"]
text='';table=False
for line in lines:
 next_table=line.startswith('|')
 if text:text+='\n'if table and next_table else'\n\n'
 text+=line;table=next_table
text+='\n';(notes/'REPORT-gbias.md').write_text(text)
p=notes/'REPORT.md';marker='\n\n---\n\n2026-11-09 追加評価: gobj-handle-bias\n\n';p.write_text(p.read_text().split(marker)[0]+marker+text)
p=notes/'PROGRESS.md';marker='\n\n### gobj-handle-bias 最終判定\n\n';p.write_text(p.read_text().split(marker)[0]+marker+text)
print(text)
