"""Render the Task10 report from the frozen final measurements."""
from pathlib import Path
import hashlib
import json
import re

N = Path(__file__).resolve().parent
ROOT = N.parents[1]
final = json.loads((N/'t10-final-normal.json').read_text())
replay = json.loads((N/'t10-final-replay.json').read_text())
clang = json.loads((N/'t10-final-clang.json').read_text())
native = json.loads((N/'t10-final-gnative.json').read_text())
argon, fix, combo, candidate = final['runs']
name = lambda s: s.split('_', 1)[1]
fmt = lambda s, scale=1, digits=3: f"{s['mean']*scale:+.{digits}f} ± {s['se']*scale:.{digits}f}"
wtl = lambda s: '/'.join(map(str, s))
source = ROOT/'solutions/dcomp-combo-alt1/main.cpp'
sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert sha == final['source_sha256'][candidate] == replay['hashes'][1]
assert sha == '8fae7ff4cbfa331797ef8f3f6835cf6ad912f04fa5a94f3fa084e11a563f97c6'
summary = final['comparisons'][candidate][combo]['all']
t = final['timing'][candidate]
clang_name = next(k for k in clang['results'] if k.endswith('_dcomp-combo-alt1'))
cc = clang['results'][clang_name]
parts = []

parts.append(f'''# Task 10: 両コンパイラで時間を空け、別プランの再編集に回す

最終候補は **`solutions/dcomp-combo-alt1`**。凍結後の通常2000件でcombo-m1-nine比 **{fmt(summary['pct'],digits=5)}%**、勝/分/敗 **{wtl(summary['wtl'])}**。GCCのjudge平均 **{t['judge_sec']['mean']:.6f}s、argon比{t['judge_ratio_argon']:.5f}倍**。p99は{t['judge_sec']['p99']:.6f}s（comboは{final['timing'][combo]['judge_sec']['p99']:.6f}s）。Clang native500件でもendは **{fmt(cc['metrics']['end_sec']['paired'],1000)}ms** で、再投資後も親より速い。

設計はcomboと同じ9候補。窓・rematch・後処理・next_costを出力同一で短縮し、`NS_ALTERNATE=1`、`NS_ALTERNATE_GAP=1.0`、alternate側の取り出し修復最大2回、`NEUTRAL_WIDTH=6`に時間を回した。`POST_CANDIDATES=6`、`NS_ROUNDS=3`、`NEUTRAL_SLACK=.35`を維持する。別プランは通常の編集が既に作った状態を再利用し、取り出し修復後に逆転する候補を拾う。既存機能を固定予算で有効にしたもので、時刻を見て予算を変えない。

## 測定条件・凍結

- 選別はseed 0–499だけ。ソース固定は2026-11-08 15:50:48 JST。固定後の設定変更なし。
- 全ケース実行は`task10_run.py`から標準`pahcer_run.py`を呼ぶ。24並列。同一seedで各armを続けて実行する同時比較。通常runは記録あり、replayは標準仕様で記録なし。ビルドと重い解析は共通flock＋nice。
- 割合はseedごとの`100 log(candidate/reference)`の平均±1SE。複数列ではseed内で先に平均する。勝/分/敗の勝は候補のスコアが小さいケース。
- 時間はローカルstderrの値で、`CLOCK_SCALE=1.1`込み。壁時計換算は表の値を1.1で割る。judgeは`end_sec + .04×helper_end_sec + .35×req_sec`。
- 提出用も固定反復。時間不足のlight mode、設計cap、時刻による候補数変更なし。既存のログ・metrics・@paper/@ops・trace・profiler・実験スイッチ、段の目印と目次、DesignStoreを保持。
- 最終ソース{source.stat().st_size:,} bytes。SHA256 `{sha}`。サイズは今回の指示どおり制約にしない。バイナリはrunsまたは/tmpだけに置いた。LOCAL_BENCHなしのGCC native、Clang native、Clang plainのC++23 -O2ビルド成功。

以下の短いrun群表記にはすべて日付`20261108-`が付く。完全なrun-id・コマンドは`t10-*.log`と各runのmeta.json、計算結果は`t10-*.json`に保存した。
''')

parts.append('''## 出発点とコンパイラの違い

指定の出発点 `dcomp-combo-ten` も作成した。Task 9のsparsebitsはGCCだけ、Clangは旧窓経路を使う。10候補目はten-fastと同じlate-rematchのみ。GCC通常500件 `130114` の設計はten-fast `123924` と500/500 byte一致。最初の9候補のsalt・予算・生成順・V選択は変更しない。要求側は固定200×4でGCC `130439`、Clang native `151652` ともcomboに800/800 stdout一致。

tenはGCC helper −31.25ms、Clang nativeでは+11.71±3.18ms（`130540`）。Task 9最終の10番目だけの得点増分は−0.0002±0.0017%だったので、最終版では9候補を維持し、資金をより効いた要求探索に回した。tenは独立した部品として残す。

### 元のcombo、GCC native対Clang native（要求された500件比較）

`20261108-130056`。ソースはbyte同一。GCC 13.3.0とClang 18.1.3、いずれも`-std=c++23 -O2 -march=native -DCLOCK_SCALE=1.1 -DLOCAL_BENCH`。ソース中の既存最適化指定も維持。

| 指標 | GCC native(s) | Clang native(s) | Clang−GCC(ms±SE) |
|---|---:|---:|---:|
| helper_end | 1.091365 | 1.016932 | −74.433±1.693 |
| req | 0.476922 | 0.455420 | −21.502±1.283 |
| end | 1.583537 | 1.487669 | −95.868±2.314 |

**親combo自体がGCC/Clang間で199/500 stdout異なる**。seed1では設計も異なり、新しい変更に由来する差ではない。同一ソースhashを確認した。したがって本報告の「出力同一」は、それぞれのコンパイラでビルドした親とのbyte一致を指す。文字通りのGCC対Clangの全出力同一は未達であり、元の差を修正したとは主張しない。元のコンパイラ間の得点差−0.01348±0.00988%は2SE未満で、Clangの得点が良いという根拠には使わない。

## プロファイルから選んだ出力同一高速化

M1のprofileを読み、試行評価・next_costを中心に調べた。再計測 `130508` の計測版ではpost_optimize 423.7ms(inclusive)、evaluate 280.2ms、filter 71.7ms、replay 64.0ms、next_cost 63.8ms、canonicalize 25.6ms。計測自体にreq約97.7msの増分があるので、これを通常版の絶対時間とは扱わない。next_cost内の再profile `140829` はkey11.1ms、列内scan28.4ms、holes12.0ms、MDP11.3msだった。

下表は各段階の対照版からの対応差で、個別のmsを加算して最終効果とはしない。括弧内はケース数×注文列数。同一性はすべてstdoutのbyte比較。恒等変形の証明と検証スイッチは[EXACTNESS10.md](EXACTNESS10.md)。

| 変更 | GCC | Clang native | 同一性 | run群 |
|---|---:|---:|---|---|
| 可換anchor群のリンクと合法性再生を共有 | req −27.48±0.55ms | req −27.07±0.96ms | 2000/2000、800/800 | 133217,132834 |
| ejectが既に持つ終状態と表示条件を再利用 | req −10.32±0.57ms | req −9.44±0.88ms | 2000/2000、800/800 | 142007,141414 |
| 空の修復区間では順序の末尾を作らない | req −3.70±1.07ms | req −1.77±0.88ms | 各800/800 | 142027,144107 |
| next_costの正確な64/128枚prefix cache | req −5.76±0.86ms | req −10.28±0.94ms | 各800/800、旧関数とのdouble bit一致 | 141638,143415 |
| rematch donorの整数maskを4対象ずつ計算 | helper −14.14±2.63ms | helper −8.43±1.60ms | 各500/500 | 143356,142404 |
| Hungarianの前駆更新をmask store | helper −13.60±2.48ms | helper −7.79±1.64ms | 各500/500 | 142734,144645 |
| 穴費用の4項を同時計算、加算順は維持 | req −4.31±0.91ms | req −1.20±0.86ms | 各800/800、旧関数とのdouble bit一致 | 150503,151125 |
| Clangの安定radixを8+9から6+11bitへ | GCCは+23.22±2.56msで不採用 | helper −23.10±1.57ms | 各500/500 | 153050,151728/151729 |
| 上記Clangを32bit record・7+10bitへ | GCCは+42.23±2.84msで不採用 | helperさらに−4.44±1.38ms | 各500/500 | 154335,153241 |

prefixは完全なkeyを照合し、途中のdouble和も保存する。一般の浮動小数点和は元の順序を保つ。穴費用だけは整数/1024で正確に表せるため4項同時計算ができる。donorは整数の集合演算だけをSIMD化した。fast-mathは不使用。

窓のsparsebitsはTask 9のものをGCCでのみ使う。ClangではSIMD部分こそ速いが、疎なlookupとvalid列挙が遅い（`130904`: 450→397、95→267、97→173 Mcycles）。Clangのsortには32bitレコード＋7/10bit radix、GCCには従来の64bit＋8/9bitを使う。費用順・同点順はどちらも同じ。

拡大したALT1/width6予算でも、リンク・表示・合法性・操作列・ラベル・next_cost double bitを旧実装で再計算するcheckerが、Clang `153706`、GCC `153946` の各200×4で不一致0、stdout 800/800一致した。

### 明瞭な利益がなく止めた高速化

| 案 | 対応時間差・判断 | run群 |
|---|---|---|
| canonicalizeの世代stamp除去／2紙IDのAVX探索 | req +0.33±0.99 / +2.65±0.94ms | 130711,130712 |
| neutral候補をindexだけでsort | −1.73±1.00ms、2SE未満 | 131225 |
| Clang sparseのvectorize等停止／窓走査統合 | +76.17ms／+52–55ms | 131908,132343 |
| 除算のNewton＋残差補正 | 全16,974,593組でbit一致だがhelper GCC+10.86、Clang+9.84ms | 132826,133019 |
| 常に上位2層へ射影／終状態memoを呼出し間共有 | req −0.17±0.88 / +1.38±0.83ms | 133748,134406 |
| next keyのtail memcpy／blockコピー | +0.37±0.93 / −1.35±0.95ms | 135015 |
| wrong-color block／可換Gからcanonical recordsを生成 | +1.63±0.93 / +4.43±0.94ms | 135426,140540 |
| 窓restrict／64要素padding | 有意な再現なし。140410は外部負荷1.11coreで時間判定から除外 | 140033,140538 |
| donorをtarget側まで4対象化 | GCCでdonorのみより約2.5ms遅い | 143356,142404 |
| 窓valid-only統合 | GCC+0.06±2.36、Clang+0.71±2.11ms | 144740,142228 |
| prefix160／way増加／64 checkpoint除去 | 128版を超える明瞭な効果なし | 143415,144302 |
| MDP cache 64/128 | +0.18±0.93 / −0.83±0.94ms | 144409 |
| VのDPでstrict-rise位置だけ試す | 全DP bit一致だがdv_eval +1.20±0.21ms | 150150 |
| GCC radix7 | 再測定−1.62±2.53msで不確定、従来分割を採用 | 154335 |
| Clang radix5 | radix6より+10.98±1.40ms | 153241 |

全出力は各試験で同一だったが、得点を変えない以上、明瞭に速くならない案は追加しなかった。細分化した試験の全経過・run-idはPROGRESS.mdのTask 10に残した。
''')

parts.append('''## 再投資の選別（0–499、固定設計4列）

固定設計は`20261107-165305_deval-flex125-plan3`。得点の対照はcomboと同じM1要求方策。時間欄は対応する出力同一高速化版からのreq増分であり、異なる段階の時間をそのまま差し引かない。replayの時間は相対費用の選別用で、最終judge時間には通常比較の値だけを使う。ALT gapは元の計画費用の差、ejectは最大2回。

| 設定 | 差 %±SE | req追加(ms) | run群 |
|---|---:|---:|---|
| ALT gap .25 | −0.010773±0.000848 | +27.97 | 133211 |
| ALT gap .5 | −0.019665±0.001217 | +46.21 | 134801 |
| ALT gap .75 | −0.028166±0.001490 | +65.77 | 141843 |
| ALT gap 1.0（最終高速化上） | −0.034026±0.001618 | +60.39 | 151147 |
| ALT gap 1.25 | −0.036675±0.001717 | +73.53 | 144941/144942 |
| ALT gap 1.5 | −0.038566±0.001736 | +82.52 | 144941/144942 |
| ALT .75、手数で対象を絞る | −0.017149±0.001063 | +44.88 | 141843 |
| ALT .75、上位1候補だけ | −0.018725±0.001179 | +38.91 | 141843 |
| ALT .75、1対1修復 | −0.002316±0.002050 | +58.86 | 141843 |
| NEUTRAL_WIDTH 5→6のみ | −0.002735±0.000489 | +5.90 | 134801 |
| POST_CANDIDATES 6→8のみ | −0.001268±0.000359 | +2.66 | 134801 |
| NEUTRAL_SLACK .35→.5のみ | −0.002835±0.000500 | +8.54 | 143744 |
| RWFのみ | −0.002800±0.000537 | +13.69 | 134801 |
| REPEAT_MIN .05→0のみ | −0.006809±0.000940 | +22.63 | 133211 |
| shortlistをgap .25へ置換 | +0.009910±0.000833 | −11.55 | 134801 |
| PLAN_LIMIT 2→3 | 0、2000/2000 stdout同一 | −0.60±0.57 | 143744 |
| NS_ROUNDS 3→4 | −0.000145±0.000095 | +0.05±0.57 | 143744 |
| **ALT1 + width6（採用）** | **−0.036945±0.001704** | **+66.66** | **151147** |
| ALT1 + width6 + POST_CANDIDATES8 | −0.037195±0.001699 | +69.44 | 151147 |

ALTの修復回数を4へ増やしても実益はほぼなかった。ALT1+width6へPOST_CANDIDATES8を足す効果は約0.00025%に縮むので採らない。単独利得を足し算せず、組合せを再測定した。訓練通常500件 `151716` のALT1+width6は−0.040994±0.003111%、GCC end−46.24ms。一方、Clangは窓sortの追加前には+11.55ms遅く、sortの追加で最終時間条件を満たした。
''')

parts.append(f'''## 凍結後の通常2000件（記録あり）

run群`{argon.split('_')[0]}`。4armとも2000件完了・正のscore、WA0。worker終了時のInterrupted tracebackがログに残るが、親プロセスは正常完了し、全meta status ok、全resultの2000件、pahcerへの記録を確認した。comboと最終候補の先頭192設計行は **2000/2000 byte一致**。9候補という設計予算は変えていない。

| 候補 | 比較先 | seed | 差 %±SE | moves/order差±SE | 勝/分/敗 |
|---|---|---|---:|---:|---:|
''')
for cand in [combo,candidate]:
    for ref in [fix,combo]:
        if cand==ref: continue
        for label in ['all','0-999','1000-1999','500-1999']:
            q=final['comparisons'][cand][ref][label]
            parts.append(f"| {name(cand)} | {name(ref)} | {label} | {fmt(q['pct'],digits=5)} | {fmt(q['moves'],digits=6)} | {wtl(q['wtl'])} |\n")
parts.append('\n| 解法 | judge平均(s) | argon比 | p99(s) | 最大(s) |\n|---|---:|---:|---:|---:|\n')
for rid in final['runs']:
    q=final['timing'][rid]
    parts.append(f"| {name(rid)} | {q['judge_sec']['mean']:.6f} | {q['judge_ratio_argon']:.5f} | {q['judge_sec']['p99']:.6f} | {q['judge_sec']['max']:.6f} |\n")
parts.append('\n| 最終候補の対応差 | helper_end(ms) | req(ms) | end(ms) | judge(ms) |\n|---|---:|---:|---:|---:|\n')
for rid in [fix,combo]:
    q=final['paired'][rid]
    parts.append('| vs '+name(rid)+' | '+' | '.join(fmt(q[k],1000) for k in ['helper_end_sec','req_sec','end_sec','judge_sec'])+' |\n')
pq=final['p99'][combo]
parts.append(f"\np99のcomboとの差は{pq['difference']*1000:+.3f}ms、paired bootstrap 95%区間 [{pq['ci95'][0]*1000:+.3f}, {pq['ci95'][1]*1000:+.3f}]ms（同じseedを対で再標本化、4000回、乱数seed20261109）。最終候補のend_secは平均{t['end_sec']['mean']:.6f}s、p99 {t['end_sec']['p99']:.6f}s、最大{t['end_sec']['max']:.6f}s、1.8/1.9/2.0s超は{t['end_above']['1.8']}/{t['end_above']['1.9']}/{t['end_above']['2.0']}件。外部負荷は平均0.135 core、最大0.464 core。全armの詳細を`t10-final-normal.json`に保存した。\n")

parts.append(f'''## 最終ソースのnative時間と同一性

GCC nativeの`{native['reference'].split('_')[0]}`は200件、Clang nativeの`{clang['reference'].split('_')[0]}`は500件。同時比較の親は各コンパイラでビルドしたcombo。

| コンパイラ・版 | 件数 | helper差(ms) | req差(ms) | end差(ms) | stdout一致 |
|---|---:|---:|---:|---:|---:|
''')
for label,d,n in [('GCC native',native,200),('Clang native',clang,500)]:
    for rid,q in d['results'].items():
        ident=q['identity']
        parts.append('| '+label+' '+name(rid)+f' | {n} | '+' | '.join(fmt(q['metrics'][k]['paired'],1000) for k in ['helper_end_sec','req_sec','end_sec'])+f" | {ident['same']}/{ident['total']} |\n")
parts.append('''
alt1は探索予算を変えるため、stdout一致は要求しない。出力同一の対照はfast。GCC既定の合体版は`151716_dcomp-hole4`で500/500一致（最終版のGCC経路は同じ）。helper −61.52±2.12ms、req −51.05±1.32ms、end −112.83±2.62msだった。Clang最終fastは500/500、GCC native最終fastは200/200一致した。各単独変更の比較と内部旧実装checkerも上表のとおり。
''')

parts.append(f'''## 未見注文列での凍結後確認

通常比較のcombo保存設計`{combo}`を両solverで読み、2000 seed×4列を再生。基準`{replay['reference']}`、候補`{replay['candidate']}`。列0は実列、列1–3は新しい列。設計は通常比較で同一確認済み。実列0のstdoutも通常比較と両solverそれぞれ2000/2000 byte一致した。設定の再選別には使わない。

| seed | 列 | 差 %±SE | moves/order差±SE | 勝/分/敗 |
|---|---|---:|---:|---:|
''')
for group in ['all','500-999','500-1999','1000-1999']:
    for lists in ['all','new','real']:
        q=replay['groups'][group][lists]
        parts.append(f"| {group} | {lists} | {fmt(q['pct'],digits=5)} | {fmt(q['moves'],digits=6)} | {wtl(q['wtl'])} |\n")

parts.append('''
## 採用案・小さい選択肢・引き継ぎ

推奨は`dcomp-combo-alt1`。高速化だけを先に使うなら`dcomp-combo-fast`。10候補の指定部品は`dcomp-combo-ten`に残したが、最終版には積まなかった。

今回の0.03%未満の単独オプションはREPEAT_MIN=0（−0.00681%、req+22.63ms）、RWF（−0.00280%、+13.69ms）、slack.5（−0.00283%、+8.54ms）。いずれも訓練500×4で元のM1比、最終ALT版へ積んだ増分は未確認。Clangの余裕を消費するため無条件には推奨しない。次に進めるなら、まずこの最終版を基準に固定設計replayで相互作用を測り、値段が下がっている案を切る。今回は指定された採用床と時間条件の確認で止める。

## 再現・ファイル

最終ソースの親との差分は各解法の`from-combo-m1-nine.patch`。`task10_release.py`は測定済みの各部品から最終2版を生成する。既存ディレクトリがある場合は上書きを拒む。元のcombo・Task 8/9のソルバは編集していない。共有scripts・trial_log・CLAUDE・STATEの編集、commitはしていない。

```sh
python3 solutions/dcomp-notes/task10_run.py --compare \\
  solutions/argon-des-perf-latew105 solutions/legal-tie-fix \\
  solutions/combo-m1-nine solutions/dcomp-combo-alt1 \\
  --seeds 0-2000 --save-design -c "Task10 final reproduction"

DEVAL_CXX=clang++ DEVAL_NATIVE=1 \\
python3 solutions/dcomp-notes/task10_run.py --compare \\
  solutions/combo-m1-nine solutions/dcomp-combo-fast solutions/dcomp-combo-alt1 \\
  --seeds 0-500 -c "Task10 Clang native reproduction"
```

`task10_run.py`は標準runnerのビルドをflock/niceにし、コンパイラとnative指定を選べるだけで、評価方式は変更しない。GCC nativeは`DEVAL_NATIVE=1`。同じソース・コンパイラ完全version・flagsのビルドだけ再利用し、そのrun-idをcompile.logに記録する。

`task10_final_run.py`はhashを検査し、通常比較・統計・2000設計一致・固定設計replayを順に実行した。`task10_final_stats.py`は分割得点・judge時間・paired p99を、`task10_replay_stats.py`はseed単位の新列/実列を集計する。重い集計は必ずflock＋niceで呼ぶ。`task10_report.py`がこれらのJSONから本報告を生成する。
''')
report=re.sub(r'\n+(?=#{2,3} )', '\n\n', ''.join(parts))
(N/'REPORT10.md').write_text(report)
print('REPORT10.md', len(report.encode()), 'bytes')
