"""Insert the completed recorded comparison and frozen unseen replay into REPORT9."""
from pathlib import Path
import json
n=Path(__file__).resolve().parent
x=json.loads((n/'t9-final-stats.json').read_text());m=json.loads((n/'t9-final-runs.json').read_text())
argon,fix,nine,ten=x['runs'];rep=m['replay'];assert m['replay_real_list_identical']==500
r=json.loads((n/'t9-final-replay-metrics.json').read_text())['results'][rep]
def pct(s):return f"{s['mean']:+.5f} ± {s['se']:.5f}"
def ms(s):return f"{1000*s['mean']:+.2f} ± {1000*s['se']:.2f}"
def short(s):return s.split('_',1)[1]
def wtl(a):return '/'.join(map(str,a))
lines=['| 候補 | 基準 | seeds | 差 (%) | 勝/分/敗 |','|---|---|---|---:|---:|']
for c,b in [(nine,fix),(ten,fix),(ten,nine)]:
    for part in ['all','0-999','1000-1999']:
        q=x['comparisons'][c][b][part]
        lines.append(f"| {short(c)} | {short(b)} | {'0–1999' if part=='all' else part} | {pct(q['pct'])} | {wtl(q['wtl'])} |")
lines+=['','nine自身との比較は全件同点（0%、0/2000/0）。各runは2000件・WA0、記録あり。','',
        '| 解法 | judge平均(s) | argon比 | p99(s) | 最大(s) |',
        '|---|---:|---:|---:|---:|']
for rid in x['runs']:
    t=x['timing'][rid];j=t['judge_sec']
    lines.append(f"| {short(rid)} | {j['mean']:.6f} | {t['judge_ratio_argon']:.5f} | {j['p99']:.6f} | {j['max']:.6f} |")
lines+=['','| ten-fastの対応差 | helper_end(ms) | req(ms) | judge(ms) | p99差(ms)、paired bootstrap 95%区間 |',
        '|---|---:|---:|---:|---|']
for b in [fix,nine]:
    p=x['paired'][b];z=x['p99'][b]
    lines.append(f"| vs {short(b)} | {ms(p['helper_end_sec'])} | {ms(p['req_sec'])} | {ms(p['judge_sec'])} | {1000*z['difference']:+.2f} [{1000*z['ci95'][0]:+.2f}, {1000*z['ci95'][1]:+.2f}] |")
t=x['timing'][ten];e=t['end_sec'];above=t['end_above'];load=x['outside_load'][ten]
lines+=['',f"p99の区間は同じseedを組で再抽出した4000回bootstrap。最終比較の外部負荷は平均{load['mean_cores']:.3f} core、最大{load['max_cores']:.3f} core。",
        '',f"ten-fastのend_secは平均{e['mean']:.6f}s、p99 {e['p99']:.6f}s、最大{e['max']:.6f}s。1.8/1.9/2.0s超は{above['1.8']}/{above['1.9']}/{above['2.0']}件。時刻による処理変更なし。全2000件で完成候補数は10。候補9を選んだのは{t['chosen'].get('9',0)}件。",
        '', '### 未見500–999・8列の追加確認', '',
        f"基準nineの`{m['replay_reference']}`と、ten-fastの保存設計を同じlegal-tie-fastで再生した`{rep}`を比較した。凍結後の確認で、結果を設定選択に使っていない。実列0は通常比較と500/500一致。", '',
        '| 注文列 | 差 (%) | 差 (moves/order) | 勝/分/敗 |','|---|---:|---:|---:|']
for label,title in [('fresh','新規1–7'),('all','全8列'),('real','実列0')]:
    q=r['score'][label];mvs=q['moves']
    lines.append(f"| {title} | {pct(q['pct'])} | {mvs['mean']:+.7f} ± {mvs['se']:.7f} | {wtl(q['wtl'])} |")
fresh=r['score']['fresh']['pct']
if abs(fresh['mean'])<2*fresh['se']:
    lines+=['','新規7列の差は2SEに届かず、10候補目の未見リスト上の利得が確定したとは扱わない。']
elif fresh['mean']<0:lines+=['','新規7列でも10候補目の改善は2SEを超えた。']
else:lines+=['','新規7列では悪化が2SEを超えた。時間目標とは別に、候補追加の採用は再検討が必要。']
paired=x['paired'][nine]['helper_end_sec'];ratio=t['judge_ratio_argon']
if paired['mean']<=0 and ratio<=1.10:
    conclusion='10候補目を追加してもnineの設計時間以下に収まり、平均時間のargon比1.10以下も満たした。Task9の時間資金を作る目標を達成した。'
else:conclusion='今回の最終比較ではTask9の時間条件をすべて満たしていない。時間内候補としての採用は推奨しない。'
lines+=['','### 判定','',conclusion]
report=n/'REPORT9.md';s=report.read_text();begin=s.index('<!-- FINAL_START -->');end=s.index('<!-- FINAL_END -->')
s=s[:begin]+'<!-- FINAL_START -->\n'+'\n'.join(lines)+'\n'+s[end:]
score=x['comparisons'][ten][fix]['all']['pct'];inc=x['comparisons'][ten][nine]['all']['pct']
old='最終候補は **solutions/dcomp-ten-fast**。dcomp-nineの窓探索を出力同一で高速化し、Task 8のdcomp-ten-lateと同じ10候補目を加えた。高速化だけの再比較はhelper_end **−25.46 ± 2.57 ms**、10候補版でもnine比 **−22.50 ± 2.49 ms**（GCC既定、500件）。以下の最終2000件比較を確認して結論を確定する。'
new=(f"最終候補は **solutions/dcomp-ten-fast**。通常2000件でlegal-tie-fix比 **{pct(score)}%**、nine比 **{pct(inc)}%**。"
     f"10候補目を加えてもhelper_endはnine比 **{ms(paired)} ms**、judge平均はargon比 **{ratio:.5f}倍**。"+conclusion)
assert old in s;s=s.replace(old,new).replace('` t9-experiments.json`','`t9-experiments.json`')
report.write_text(s)
print(new)
