"""Assemble the Japanese report from verified final and training measurements."""
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent
S=Path(sys.argv[1])
extra=3 if S.name in ['deval-chain-seven','deval-seven-wide'] else 4
count=4+extra
request_settings='REPEAT_MIN=0.05, POST_CANDIDATES=5'+(', NEUTRAL_WIDTH=3' if S.name.endswith('wide') else '')
f=json.loads((S/'final-metrics.json').read_text())
ev=json.loads((S/'final-evaluation.json').read_text())
last=f['normal'][ev['normal'][-1]]
gain=f['replay']['results']['fresh']
ratio=last['time_comparisons'][ev['normal'][0]]['ratio']
v=f['verdict']
conclusion=(f"最終案は `{S.name}`。未使用seed 500–999、注文列1–7でnofb比 **{gain['mean']:+.4f} ± {gain['se']:.4f}%**、"
            f"同時2000ケース比較のjudge平均は旧SOTAの **{ratio:.4f}倍**。")
conclusion += ('平均時間・p99の条件を満たした。' if v['judge_mean_within_limit'] and v['judge_p99_within_limit'] else
               '時間条件の判定は下表の通りで、満たさなかった条件は未達として扱う。')
conclusion += ('0.10%改善の目標に到達した。' if v['gain_at_least_point_one'] else
               '改善は確認できたが、0.10%の目標には届かなかった。予定した作業時間で終了し、未使用seedを見てからの追加調整はしていない。')
intro=f'''# Task 3: 高速化と完成候補への再投資

{conclusion}

基準は `solutions/deval-vbranch-nofb`（PR #164）。時間の分母は `solutions/argon-des-perf-latew105`。11月7日07:20の更新と再開指示に従い、時間不足による軽い注文処理、設計段の時間上限、候補数の時間打切りを含めない。guard stress testも実施しない。実行不能な初期設計を検知する従来の処理は残るが、時間での切替えではない。

## 最終案

1. 窓割当て450k、窓climb133k、焼きなまし約11.2Mの共有前半2段と4分岐は基準と同じ。
2. 各分岐はfiller climb50k、Hungarian再割当て2回、穴あけ、穴あけ後の再割当てまで完成させる。穴あけの色サンプルは32から8へ減らす。完成V16で4候補を比較する。
3. 現在の最良完成配置を起点に、filler climb25k、再割当て1回、穴あけ8サンプル、穴あけ後の再割当てを{extra}回試す。各回のsaltは定数で変える。新しい完成Vが改善したときだけ、次の開始配置も更新する。
4. 最初の4完成候補を含む計{count}候補から、最小Vの設計を採用する。引き継ぐのは対象・列の配置で、物理的な穴は仕上げごとに再構築する。DesignStoreには採用した設計を保存する。
5. 注文処理は固定設定 `{request_settings}`。小さな改善後の再探索を省く一方、後処理で比較する候補を増やす。時間に応じた変更はしない。

V本体の係数・焼きなましの目的関数は変更していない。完成前のVだけで候補を絞る方式より、安く仕上げて完成後のVで選ぶ方式を採った。最終案の説明は[README.md](README.md)、単一ファイルの提出コードは[main.cpp](main.cpp)。

## 採用した高速化

| 対象 | 変更 | 出力を保つための扱い |
|---|---|---|
| Hungarian | 訪問済み列の配列、4列のAVX2緩和 | 同値の列順と更新順を維持 |
| 穴あけ | サンプルに依存しない被覆範囲を共有 | 供給紙と区間の列挙順を維持 |
| 穴あけDP | 1/5操作単位のint16_t、変化したサンプルだけを更新 | 期待値に戻す境界を明示し、GCC/Clangで実出力を照合 |
| 注文のfiller列 | 4要素を内部に保持し、超過時にvectorへ移す | 挿入・削除・コピーの順序を維持 |
| 注文の列価値 | 同じ列が連続する区間で順位と符号をレジスタに保持 | 浮動小数点の全体の加算順を維持 |
| 仕上げの確率 | 元の丸め済み確率差を先に作り、Bernoulliの最初の1段を直接初期化 | 残りの多項式更新順を維持 |
| 再割当て | 対象の穴・列、供給紙の被覆・色をrebuild単位で共有 | 数式と走査順を維持 |
| filler climb | 同じ幾何情報を交換する2ユニットだけ更新、作業領域を再利用 | 棄却時に復元し、乱数列を維持 |

穴あけDPの整数化は数値表現を変えるため、任意入力でのbit単位の算術同一性を主張するものではない。採用する根拠は費用が1/5単位であることと、両コンパイラの実出力一致検査である。高速化の検証は32サンプル・基準と同じ探索予算の `deval-climbcache` で行い、8サンプル化は別の品質変更として評価した。fast-mathは使っていない。

個別の時間差は末尾の全試行表に示す。組合せ全体の直接比較は次表。全て標準24並列の同時比較で、stdoutの全ファイルを比較した。中断前のguard付き基準では候補数打切りが変わったケースだけを区別し、再開後のnofb基準ではその例外はない。

| コンパイラ | 件数 | stdout一致 | 仕上げ秒差 ± SE | 注文秒差 ± SE | judge秒差 ± SE | run |
|---|---:|---:|---:|---:|---:|---|
'''
for tag,label in [('combined-gcc','GCC'),('combined-clang','Clang')]:
    d=json.loads((P/(tag+'.json')).read_text())
    def cell(key):
        x=d['time'][key]
        return f"{x['delta']:+.6f} ± {x['se']:.6f}"
    intro+=f"| {label} | {d['n']} | {d['n']-len(d['stdout_mismatches'])}/{d['n']} | {cell('dv_finish_sec')} | {cell('req_sec')} | {cell('judge')} | `{d['reference']}` / `{d['candidate']}` |\n"
intro+='''
## 探索配分の判断

候補の多様性には、焼きなましだけでなく仕上げの乱数も効いた。4分岐を全て十分に仕上げた後、完成配置の上位をもう一度仕上げる方が、全候補のclimbを最初から半分にするより良かった。仕上げを省いたVでの一次選別、climbの結果を共有して再割当てだけ増やす方式は、節約に対する改善が小さかった。

最良配置を更新するchain8は、調整用seedで列1–7が−0.0667 ± 0.0093%。chain10は−0.0744 ± 0.0094%にとどまり、時間が増えすぎた。独立の追加仕上げを10/12候補に増やした案も同様に時間条件で落とした。窓climbを133kから170kへ増やす案は、改善幅が不確かでp99も大きくなり採らなかった。

穴あけ32→8サンプル単独は列1–7が+0.0007 ± 0.0076%で、品質差を検出できなかった。注文の固定設定変更は保存設計500ケース×4列で−0.0007 ± 0.0009%。これらと高速化で得た時間を追加の完成候補に使う。最終案はこの組合せを固定して別のseedで検証したので、個別効果の足し算を最終改善率とはしていない。

## 検証と再現方法

設定の選択はseed 0–499だけ。未使用seed 500–999は最終ソースのSHA-256を`FROZEN.json`へ保存してから開いた。通常2000ケースは指定された3解法の同時比較で、`--no-record`を付けずに記録した。最終リプレイは、その通常比較で保存したnofbと候補の各設計を使った。旧o3のリプレイに混ざる候補打切りケースを比較の基準にしない。

再現用スクリプトは `../deval-speed/` にある。`run.py` は `scripts/pahcer_run.py` を呼び、ビルドにも共有flockを付ける薄いラッパー。24並列の評価・保存形式・記録は標準スクリプトのまま。重い分析と単体検査も同じflock下で行った。

```sh
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-speed/verify_combined_speed.py
```

最終評価は `final_evaluate.py solutions/解法名`。通常2000ケースの設計保存、基準・候補の未使用500ケース×8列を順に実行する。既存の最終記録を再集計する場合は次を実行する（`解法名`はこのディレクトリ名）。

```sh
flock -x /home/sato/ahc074/runs/.lock /home/sato/ahc074/.venv/bin/python solutions/deval-speed/summarize_final.py solutions/解法名
flock -x /home/sato/ahc074/runs/.lock /home/sato/ahc074/.venv/bin/python solutions/deval-speed/analyze_all_complete.py
```

Hungarianの同値を含む500行列とFillerListの10万操作をGCC/Clangで検査した（`../deval-speed/backend-unit.log`）。不採用の小vector案にも10万操作の単体検査をしたが、時間差が小さく採用しなかった。最終版は提出用のLOCAL_BENCHなしでもGCC 13.3・Clang 18.1のC++23ビルドが通った（`builds.json`）。ソース・注釈・DesignStoreの検査は`audit.json`。最終リプレイの全4000実行でself_wrongと操作ラベルの不整合は0。注文列0のstdoutも通常実行と500/500件一致した。

STATE.md付属の`judge_model.py`でも通常3runを集計し、同じ値を得た（`judge-model.log`）。

08:55の中断前後のrunは、`result.json`と完了状態を確認した。`interrupted-runs.json`に挙げた未完了runは結論に使っていない。元のedit4案はコンストラクタの暗黙変換によるinsertオーバーロードの誤りでWAとなり棄却した。修正版も速度改善がなく不採用。columnvalue案は浮動小数点の加算順を変えて1/500件の出力が変わり、出力同一の高速化から除いた。外部CPU負荷の警告がある速度測定は小差の採否に使っていない。

以下に最終評価と、中断前を含む全ての完了試行を記載する。±は全て標準誤差で、時間と品質の実験は分けて読む。

'''
validation_at=intro.index('## 検証と再現方法')
validation=intro[validation_at:]
intro=intro[:validation_at]
if S.name in ['deval-chain-wide','deval-seven-wide']:
    intro+=f'''最終版はさらに `NEUTRAL_WIDTH=3` を使う。2つの操作を置き換える後処理で保持する候補幅を2から3へ増やした。{count}完成候補の設計予算は保ち、残った時間をこの固定の注文探索へ使う。設定選択は調整用500ケースに限った。\n\n'''
if S.name in ['deval-chain-seven','deval-seven-wide']:
    intro+='''最終的にはp99の余裕を優先して、追加仕上げを3回にした計7候補を選んだ。8候補のGCC O3版は500ケースの複数回の比較でp99差の符号が変わり、時間余裕が確かではなかった。8候補と注文探索幅3の組合せは平均時間内でもp99を超えたので不採用。7候補は8候補の最初の7つと同じ集合で、設定を全ケース共通に固定する。時刻やケースの遅さで候補数を変える方式ではない。\n\n'''
if S.name=='deval-seven-wide':
    intro+='''7候補版の調整用比較ではjudge p99がnofbより約45ms低く、平均も約19ms低かったため、7候補と幅3の組合せを最後に確認した。保存した7候補版の同じ設計に対する500ケース×4列で注文処理だけの効果を測り、最終2000ケースでは組合せ全体の時間を確認した。\n\n'''
o3=P/'chain-final-o3.json'
if o3.exists():
    d=json.loads(o3.read_text())
    x=d['time']['req_sec']
    intro+=f"注文処理のGCC O3指定も比較した（fast-mathなし）。500件のstdout一致は{d['n']-len(d['stdout_mismatches'])}/{d['n']}、注文時間差{x['delta']:+.6f} ± {x['se']:.6f}秒。run: `{d['reference']}` / `{d['candidate']}`。このGCC O3指定は最終版にも採用した。\n\n"
algorithm_at=intro.index('## 最終案')
(S/'REPORT.md').write_text(intro[:algorithm_at]+(S/'FINAL_METRICS.md').read_text()+'\n'+intro[algorithm_at:]+validation+'\n'+(P/'EXPERIMENTS.md').read_text())
print(S/'REPORT.md')
