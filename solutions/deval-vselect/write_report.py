"""Render the final, already-frozen evaluation evidence in Japanese."""
from pathlib import Path
import argparse,json
HERE=Path(__file__).resolve().parent
LABELS={
'finish4':'同じ焼きなまし結果から仕上げ4回', 'branch3':'前半共有3分岐、MAP 300k',
'map150k':'窓割当て150k', 'elites16':'最良途中状態16個から選別',
'refine32':'完成設計をVで局所改善32回', 'refine64fast':'短い焼きなまし＋V局所改善64回',
'refinebatch':'完成設計の変更をまとめてV選別', 'vmatch6':'Vで再割当て巡回を採否判定',
'local05':'局所7項モデルを目的値へ50%混合', 'current24':'現在状態24個から選別',
'guided8':'Vで各段の開始状態を選ぶ', 'current24warm':'現在状態24個、温度下限0.06',
'climb1':'filler climbの重み1.0', 'climbgrid':'仕上げの重みを4通りに変える',
'pool25':'途中状態25個を全部仕上げる（時間外の参考）',
'branch4tail':'最終1段を4分岐', 'branch4half':'後半2段を4分岐、元のV32',
'branch3tail':'最終1段を3分岐', 'targetmatch4':'V16で再割当てを採否判定',
'targetcurrent24':'現在状態24個、V16', 'col24':'完成した列の順序をVで改善',
'beam2':'軽い仕上げ予測で途中状態を2個に絞る',
'beam3cheap':'軽い仕上げ予測で3個に絞る', 'beam8ends':'前半1段共有、8終端から4個',
'beam6ends':'前半1段共有、6終端から4個', 'beam6long':'6分岐を長くしMAP 400k',
'beam8half':'前半2段共有、8終端から4個', 'beam4obj':'分岐ごとに局所目的値を変える',
'split4cool':'独立した1/4焼きなまし4個、開始温度0.5',
'split4base':'独立した1/4焼きなまし4個、開始温度2',
'generic13':'generic費用を1.3倍', 'genericcurve':'generic費用を回帰曲線で変更',
'reheat4':'4分岐、後発候補の開始温度4倍', 'reheat2':'4分岐、開始温度2倍',
'clean4':'4分岐、焼きなまし内側をSOTAと同じに整理',
'guided32':'第3段の途中32状態から次段を開始',
'perf4':'穴あけだけ4種類の重み', 'perfsalt4':'穴あけ以降だけ4回',
'mapelite2':'窓割当ての既存eliteを2個利用、焼きなまし1.4倍',
'mapelite4':'窓割当ての既存eliteを4個利用',
'pipeline8':'8分岐をclimb＋再割当てで一次選別',
'pipeline6':'6分岐をclimb＋再割当てで一次選別',
'screen12':'12分岐を再割当てだけで一次選別',
'screen12warm':'12分岐の一次選別、温度倍率1/2/4',
'mix15':'分岐ごとにgeneric費用の倍率を変更',
'mix15reheat':'generic倍率変更＋開始温度2倍',
'branch3early':'前半1段共有、3分岐、反復数約1.20倍',
'reheat6thin':'6分岐、climb25k＋再割当て1回',
'reheat8thin':'8分岐、climb12k＋再割当て1回',
'recip4':'4分岐、SIMD除算をNewton逆数に変更',
'kick2':'分岐前に列とhandleを2回入替え',
'screenpool12':'12候補を全部仕上げる（時間外の参考）',
'twins2x2':'長い2分岐を各2回仕上げる',
'twins3x2':'3分岐を各2回、仕上げ25k＋再割当て1回',
'funded105':'設計O3の短縮分で焼きなまし反復数を5%増加',
}

def effect(v):return f"{v['mean']:+.3f} ± {v['se']:.3f}%"

def main():
    p=argparse.ArgumentParser();p.add_argument('solution');a=p.parse_args()
    dest=Path(a.solution);d=json.loads((dest/'final_metrics.json').read_text())
    n=d['normal'];bt=d['time']['reference'];ct=d['time']['candidate']
    rows=json.loads((HERE/'analysis.json').read_text())
    test=d['replay_metrics']['test_500_999'];allq=d['replay_metrics']['all_0_999']
    text=f'''# Vによる設計選択の統合

採用解法は `{dest.name}`。seed 500–999 の新しい注文列1–7ではSOTA比 **{effect(test['lists1_7'])}**、通常2000ケースの同時比較では **{n['difference']:+.3f} ± {n['se']:.3f}%**。同時比較の平均judge-model時間比は **{d['judge_ratio']:.4f}**。

差はケースごとの `100 × log(候補の平均スコア / SOTAの平均スコア)` の平均。負が改善。±はケースを単位とする標準誤差で、95%区間ではない。注文列をまとめるときは、まずケース内のスコアを算術平均する。

## 採用した設計探索

窓割当てはSOTAのまま（MAP 450,000回、generic割当て133,000回）。4段の焼きなましの前半2段を共有し、その最良状態から後半2段を4候補へ分岐する。各分岐の反復予算は元の1/4で、前半と4分岐を合わせた総反復数は元とほぼ同じ。256反復ごとの終了判定による端数だけが増える。候補0は元の温度、候補1–3は分岐直後の温度を2倍にして、終端で元の温度へ戻す。分岐の乱数saltは固定する。

各候補をfiller climb 50,000回、Hungarian再割当て2回、穴あけ、穴あけ後の再割当てまで完成させ、V16が最小の設計を採用する。焼きなましの局所目的値はSOTAのまま。Vは完成候補の選択に用い、`Solver::process`による注文列の模擬はしない。

費用表の共有、未使用の実験経路の除去、GCCの局所的なO3指定で追加費用を抑えた。O3の対象は設計を中心とする関数群と共有のComparator・Interleave・ColumnMDP関数で、Solver本体は含めない。fast-mathは使わない。Clangはこのpragmaを使わず、標準のO2でビルドできる。

設定選択側では6回仕上げる案や反復数を5%増やす案も試した。4候補に対する差は、対応のあるケース間比較で標準誤差の2倍に届かなかった。6回仕上げる案の500ケース同時比較は時間比1.1045、4候補は1.0844だったため、時間の余裕を残す4候補を最終評価前に採用した。これは同等の候補間で真の最良を確定したという意味ではない。

具体的には、6回仕上げる案の追加改善は−0.0279 ± 0.0186%、反復数5%増加は−0.0167 ± 0.0241%。比較元は同じseed 0–499の`reheat2`。時間の同時比較は `20261107-061535_argon-des-perf-latew105` / `20261107-061535_deval-vtwins-o3` と、`20261107-060534_argon-des-perf-latew105` / `20261107-060534_deval-vbranch-o3`。

## 最終評価

ソースと設定を `FROZEN.json` に固定してから最終評価した。Task 2で新たに作った候補の設定選択とVの追加学習はseed 0–499だけを使い、下記のseed 500–999の結果で設定を選び直していない。Task 1の既存結果と、提供済みの半反復データは事前の参考資料として読んでいる。

通常比較はSOTAを先頭に置いた `--compare`。{n['n']}ケース、無効スコア {n['invalid']}件。誤表示の合計はSOTA {n['display_errors']['reference']} / 候補 {n['display_errors']['candidate']}件。

| 解法 | 平均スコア | SOTA比 ± SE | 勝 / 分 / 敗 |
|---|---:|---:|---:|
| argon-des-perf-latew105 | {n['base_mean']:.2f} | — | — |
| {dest.name} | {n['candidate_mean']:.2f} | {n['difference']:+.3f} ± {n['se']:.3f}% | {' / '.join(map(str,n['wtl']))} |

8注文列の保存設計リプレイ。SOTAが過去に実注文列で選ばれた影響を避けるため、主指標は列1–7。

| seed集合 | 件数 | 注文列1–7 | 全8列 | 実注文列0 |
|---|---:|---:|---:|---:|
'''
    for label,key in [('全体 0–999','all_0_999'),('設定選択側 0–499','train_0_499'),('最終確認側 500–999','test_500_999')]:
        q=d['replay_metrics'][key]
        text+=f"| {label} | {q['n']} | {effect(q['lists1_7'])} | {effect(q['all8'])} | {effect(q['real'])} |\n"
    text+='''
## 時間と提出時のガード

指定された `judge = 1.04 × helper_end_sec + 1.35 × req_sec + (end_sec − helper_end_sec − req_sec)` を、同時比較の各ケースへ適用した。設計にはhelper表の準備までを含める。通常比較ではLOCAL_BENCHにより注文の軽量化と追加の緊急打切りを無効にし、通常処理の費用を測る。

| 指標（秒） | SOTA 平均 / p99 / 最大 | 候補 平均 / p99 / 最大 |
|---|---:|---:|
'''
    for label,k in [('judge model','judge'),('設計＋準備','helper_end_sec'),('注文処理','req_sec'),('end_sec','end_sec')]:
        fmt=lambda t:' / '.join(f"{t[k][z]:.4f}" for z in ['mean','p99','max'])
        text+=f'| {label} | {fmt(bt)} | {fmt(ct)} |\n'
    text+=f"\n候補の `end_sec` が1.8 / 1.9 / 2.0秒を超えた件数は {ct['end_sec']['gt1.8']} / {ct['end_sec']['gt1.9']} / {ct['end_sec']['gt2']}。平均judge-model時間比は {d['judge_ratio']:.4f}。\n"
    text+=f"\n候補全体の平均内訳は、窓割当て終了まで{ct['map_end_sec']['mean']:.4f}秒、焼きなまし{ct['dv_anneal_sec']['mean']:.4f}秒、仕上げ{ct['dv_finish_sec']['mean']:.4f}秒、V評価{ct['dv_eval_sec']['mean']:.4f}秒。Vの1候補当たりは約{1000*ct['dv_eval_sec']['mean']/ct['dv_candidates']['mean']:.2f} ms（CLOCK_SCALE適用済み）。この内訳はhelper表の準備などを含む上の総設計時間とは区別する。\n"
    audit_path=dest/'audit.json'
    if audit_path.exists():
        audit=json.loads(audit_path.read_text())
        counts='、'.join(f"{k}候補を完成{v}ケース" for k,v in sorted(audit['completed_candidate_counts'].items(),reverse=True))
        text+=f"\n通常2000ケースでは{counts}だった。\n"
    text+='''
追加候補は設計経過1.12秒を過ぎたら開始しない。提出用では、残注文の比率をqとして1.84−0.12q秒から中立探索を省き、1.90−0.30q秒から最初の合法な通常計画を採用する。さらに窓探索0.85秒、窓climb0.90秒、設計anneal1.15秒、filler climb1.25秒を緊急打切りの目安とする。各ループの既存の最良状態への復元を通る。これらの緊急打切りと注文軽量化はLOCAL_BENCHでは無効。判定はすべてCLOCK_SCALEを通す。

ガード検査はLOCAL_BENCHを外し、CLOCK_SCALEを標準の1.1から2.2へ増やして時間不足を強制した通常評価。時計全体を一様に遅くするストレスであり、上の段別judge modelとは区別する。

| run | 件数 | end_sec 平均 / p99 / 最大 | 1.95秒超 / 2秒超 | 軽量化したケース / 強い軽量化 | WA / 誤表示 |
|---|---:|---:|---:|---:|---:|
'''
    for run,g in d['guard'].items():
        text+=f"| `{run}` | {g['n']} | {g['mean']:.4f} / {g['p99']:.4f} / {g['max']:.4f} | {g['gt195']} / {g['gt2']} | {g['light_cases']} / {g['hard_cases']} | {g['wa']} / {g['display_errors']} |\n"
    text+='''
## 試した方針

以下は設定選択用のseed 0–499。相互に同じ注文列を使う。多数の案から選んだ結果なので、採用効果の根拠は上の最終確認側と2000ケース比較に置く。設計時間は各通常runの `helper_end_sec` 平均で、別run間の細かい時間差には負荷・P/Eコアの配分の違いがある。最終の時間比は同時比較だけで判定する。

| tag / 方針 | 注文列1–7 ± SE | 全8列 ± SE | 実列 ± SE | 設計秒 |
|---|---:|---:|---:|---:|
'''
    half=HERE/'half_reference_500.json'
    if half.exists():
        q=json.loads(half.read_text())
        text+=f"| 半反復2候補をV32で選ぶ（既存データ） | {effect(q['lists1_7'])} | {effect(q['all8'])} | {effect(q['real'])} | 統合時間は未測定 |\n"
    for row in rows:
        if row['tag'].startswith('trainbranch'):continue
        q=row['quality'];t=row['time'];tag=row['tag']
        text+=f"| `{tag}` {LABELS.get(tag,tag)} | {effect(q['lists1_7'])} | {effect(q['all8'])} | {effect(q['real'])} | {t['helper_end_sec']['mean']:.4f} |\n"
    text+='''
各行の解法・環境変数・design/replay run-idは `../deval-vselect/experiments.jsonl` と `analysis.json` に残した。各実験用ディレクトリのREADMEと、`make_*.py` が具体的な差分を説明する。

実装上の変更は別の同時比較で確認した。下表のスコア差は各比較の親解法に対する実注文列の差。費用表の共有・未使用経路の除去・O3の比較では、同じ候補数を完成した場合の物理状態の一致も調べた。候補数が時間ガードで違ったケースは一致しない。個別の8列再評価は省き、採用した実装を含む全体を上の最終8列評価で確認する。

| 実装変更 | 件数 | 実列の差 ± SE | judge時間比 | 設計時間差（秒） | 保存状態の一致数 |
|---|---:|---:|---:|---:|---:|
'''
    backend=HERE/'backend_results.json'
    if backend.exists():
        for row in json.loads(backend.read_text()):
            if row['name']=='branch_time':continue
            q=row['normal'];tm=row['time'];same='—'
            if 'physical_states' in row:same=f"{row['physical_states']-len(row['physical_mismatches'])} / {row['physical_states']}"
            diff=tm['candidate']['helper_end_sec']['mean']-tm['reference']['helper_end_sec']['mean']
            text+=f"| `{row['name']}` | {q['n']} | {q['difference']:+.3f} ± {q['se']:.3f}% | {row['judge_ratio']:.4f} | {diff:+.4f} | {same} |\n"
    text+='''
費用表共有の不一致1件（seed 18）は旧版3候補・新版4候補で、最初のVは同じだった。表自体は全318クラス×720置換で方向別費用・正逆の和とも差0。未使用経路の除去は4候補を必ず完成させる設定で50/50設計が一致した。比較のrun-idと集計は `../deval-vselect/backend_results.json`。

## 得られたこと

- Vの評価そのものより、候補を作り、仕上げる費用が大きい。半反復の独立再始動は、選択益のかなりの部分を探索量の不足で失う。
- 前半を共有した4分岐の真の設計差の標準偏差は約0.0256操作/注文で、独立したanneal再始動の約0.040より小さかった。4列で選んで別の4列で測るoracleも、この集合ではSOTA比−0.136 ± 0.020%。単に独立4候補の−0.33%を期待できる集合ではない。
- 途中状態の安い予測、穴あけ前の一次選別、仕上げだけの再始動も実測した。候補数だけでなく、その平均品質と相互の似通いが重要だった。
- Vを完成状態の局所改善に直接使う案や、局所回帰項への目的値変更は、予測値の改善が実コストへ移らなかった。最終候補の選択にVを使う方針を保った。

4列で選ぶoracleは測定誤差を含む比較基準で、真の期待コストを知る数学的な上限ではない。Vがこの値を上回ることとは矛盾しない。4分岐の分散とoracleは、温度を変更する前の集合で測った値。

VはTask 1の32点モデルから、対象別の固定digital shiftと、不一致数を解析的に積分する補正を入れた16点モデルへ変更した。訓練0–399 / 検証400–499で選び、係数は0–499で再学習した142項の線形結合。検証の全7設計のケース内相関は元の0.8209に対して約0.8290。実注文の模擬は行わない。分岐の実データや、Vによる改善が外れた設計を加えた再学習も行ったが、検証上の上積みが小さく、最終候補には元のV16を使用した。モデルと検証結果は `../deval-vtarget/V.json`、`../deval-vselect/target_cv_qmc_16.validation.json`、`branch_refit_results.json`、`intervention_refit_results.json`。

汎用紙の厳密期待費用表の共有では、全318クラス×720置換で方向別の値と従来の正逆和を照合する。固定積分点は短いXOR基底から復元し、巨大な点列はソースに埋め込まない。

穴あけ前の12候補を安く選別するモデルも再学習した。seed 400–499で完成後のVを予測するケース内相関は、元のVの0.6195に対して再学習版0.6148で、採用しなかった。この実験の教師は完成後のVであり、実測操作数への相関ではない。`../deval-vselect/screen_fit_results.json`に残した。

## ソースと再現

'''
    text+=f"`main.cpp` は **{d['source_bytes']:,} bytes**。520,000 bytes以下、C++23で単独提出できる。SHA-256は `{d['source_sha256']}`。GCCによる標準評価ビルドとClang C++23/O2ビルドを確認した。DesignStoreは選んだ設計を保存し、@paper/@opsと段の目印を残した。係数の参照用JSONはこのディレクトリの `V.json`、ソース内には同じ係数を埋め込んでいる。\n\n"
    if audit_path.exists():
        text+='`audit.py`で、通常runと8列リプレイの実注文列が1000/1000ケース同スコアであること、各runの保存ソースが固定したソースと同じこと、60個の段の目印と目次が一致することを確認した。結果は `audit.json`。費用表の全置換検査は `value-table-check.log`、Clangのビルド記録は `clang-check.log`。\n\n'
    if test['lists1_7']['mean']>-.3:
        text+='目標の「独立確認側で0.3%以上の改善」には届いていない。今回の調査で確認できた改善として報告する。追加の候補数を増やすだけでは、候補を仕上げる時間と探索量の不足が制約になった。\n\n'
    text+=f'''最終run:

- SOTA通常比較: `{d['reference']}`
- 候補通常比較: `{d['candidate']}`
- 候補8列リプレイ: `{d['replay']}`
- リプレイのSOTA基準: `{d['replay_reference']}`

`../deval-vselect/run.py` は標準の `scripts/pahcer_run.py` を呼び、ビルドにも共有flockを付ける薄いラッパー。評価本体の排他制御・記録は標準スクリプトのまま。

```bash
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python \\
  solutions/deval-vselect/run.py --compare \\
  solutions/argon-des-perf-latew105 solutions/{dest.name} \\
  --seeds 0-2000 --save-design --no-record -c "V final comparison"

PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python \\
  solutions/deval-vselect/run.py solutions/{dest.name} \\
  --design-from {d['candidate']} --orders 8 --seeds 0-1000 \\
  --no-record -c "V final replay"

flock -x /home/sato/ahc074/runs/.lock env OPENBLAS_NUM_THREADS=1 \\
  /home/sato/ahc074/.venv/bin/python solutions/deval-vselect/summarize_final.py \\
  --reference {d['reference']} --candidate {d['candidate']} \\
  --replay {d['replay']} --solution solutions/{dest.name} \\
  {' '.join('--guard '+run for run in d['guard'])}

flock -x /home/sato/ahc074/runs/.lock env PYTHONDONTWRITEBYTECODE=1 \\
  /home/sato/ahc074/.venv/bin/python solutions/{dest.name}/audit.py
```
'''
    (dest/'REPORT.md').write_text(text)
    print(dest/'REPORT.md')
if __name__=='__main__':main()
