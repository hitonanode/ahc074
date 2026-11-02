from pathlib import Path
import json,statistics as st
p=Path(__file__).resolve().parent
report=(p/'REPORT.md').read_text()
comparison=json.loads((p/'comparisons.json').read_text())
def rows(label):return [json.loads(f.read_text())['metrics'] for f in sorted((p/'results'/label).glob('[0-9]*.json'))]
def table(labels):
 out=['|方式|件数|model_cost|列|穴|汎用|対の厳密汎用費用|模型差 ± SE|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for label,title in labels:
  rs=rows(label);d=comparison[label]['model_cost'];m={k:st.mean(r[k] for r in rs) for k in ['model_cost','model_col','model_hole','model_gc','pair_gc_mean']}
  out.append(f'|{title}|{len(rs)}|{m["model_cost"]:.5f}|{m["model_col"]:.5f}|{m["model_hole"]:.5f}|{m["model_gc"]:.5f}|{m["pair_gc_mean"]:.5f}|{d["delta"]:+.5f} ± {d["se"]:.5f}|')
 return '\n'.join(out)
# Add overlap and an explicitly reproducible example before the economic comparison.
overlap=json.loads((p/'window-overlap.json').read_text())
vertex=json.loads((p/'vertex-cycles.json').read_text())['summary']
insert=f'''最小除去集合に含まれる窓の重なりも数えた。各ケースで最多の窓は、平均{overlap['max_any_minimum_mean']:.5f}対の「いずれかの最小集合」に含まれる。しかし、その窓を単独で除くだけで整合する対は平均1.3125対に留まる。「切るべき窓の一部が共有される」ことと「同じ一窓だけで閉路が全て消える」ことは違う。全ての最小集合に必須の窓の最多共通数は平均{overlap['max_every_minimum_mean']:.5f}対（`window-overlap.json`）。

具体例は **seed 24、商品196と227、列7**。浅いハンドルの違いは0なのに汎用窓の違いは20個ある。最小除去は5窓で、その一つは物理窓 **1, 3, 5, 17, 31**。5個分は全て逆向き重複比較による長さ2の閉路から必要になる。この種の対が、ハンドル費用では得だが単窓救済では届かない対象である。

補助的に、比較器の紙を頂点として除く最小帰還頂点集合も数えた。不整合4182対のうち1/2/3頂点が必要なのは1115/2728/339対。平均{vertex['mean_vertex_feedback']:.5f}頂点。単に一枚の汎用紙の役割を二枚へ分割する構成では、同じ紙を通らない別の閉路が残る対が多い。これは固定した比較器に対する構造診断であり、印刷を全体で組み直す方式の不可能性を意味しない（`vertex-cycles.json`）。

'''
report=report.replace('### 2.3 得になる対と、単窓救済の限界',insert+'### 2.3 得になる対と、単窓救済の限界')
fees=json.loads((p/'fees-summary.json').read_text())
fee_lines=['### 2.4 次の復号器に必要な費用水準','',
'追加紙一枚も費用に入れた抽象模型。整合対の従来の費用は維持でき、不整合対に提示する3.0/3.4手はアクセス・配置・戻し等の全追加操作を含むと仮定する。実現可能な印刷の構成を証明した値ではない。全て64件。','',
'|対ごとの最小除去数|3.0手・追加紙なし|3.0手・追加紙1枚|3.4手・追加紙1枚|','|---|---:|---:|---:|']
for n in range(1,5):
 fields=[]
 for key in ['fee300p0','fee300p1','fee340p1']:
  x=fees[key][f'fas{n}'];fields.append(f'{x["delta"]:+.5f} ± {x["se"]:.5f}')
 fee_lines.append('|≤'+str(n)+'|'+'|'.join(fields)+'|')
fee_lines+=['', '表は基準との模型差（手/注文）。追加紙一枚、2窓を3.0手で救うなら約1.16%相当、3窓なら約1.87%相当の余地。1窓・3.0手では約0.40%相当、2窓・3.4手でも約0.41%相当しか残らない。**一窓だけの救済を多少広げるより、対ごとに異なる2〜3窓を3.0手前後で扱えることを目標にする。** 根拠は `fees-summary.json` と `data/fees*.jsonl`。','']
report=report.replace('## 3. 調べた復号器ごとの模型・数値・結論','\n'.join(fee_lines)+'\n## 3. 調べた復号器ごとの模型・数値・結論')
old='追試として、汎用窓とハンドル窓の交換をゲート変更と一つの手にまとめた `joint-detail.cpp` と、保護する比較窓を12個に減らした版を計測中。12個版は探索中に保護窓だけが保証する合法グラフを使い、完成後は全印刷からグラフを再構築して模型と模擬を評価する。'
new=['汎用窓とハンドル窓の交換をゲート変更と一つの手にまとめた版も計測した。以下は丸め、同点処理、相方の走査順を最終設計と揃えた `shared.cpp` の値。15窓・12窓の各64ケース全てで、探索側の選択対と最終 `Design::initialize` の初期対集合が一致することを実行時検査した（`decoder_matching_equal=1`）。1/4の提案に窓交換を含める。保護比較窓12個版では探索中に保護窓だけが保証する合法グラフを使い、完成後は全印刷からグラフを再構築して模型と模擬を評価する。対の再選択は同じ費用と選択規則で行う。','',table([('shared15','窓交換を含む・15窓保護'),('shared12','窓交換を含む・12窓保護')]),'',
'|方式|模擬のlog比 ± SE|勝/分/敗|模擬の汎用紙操作/注文|','|---|---:|---:|---:|']
for label,title in [('shared15','15窓保護'),('shared12','12窓保護')]:
 x=comparison[label]['sim_moves'];new.append(f'|{title}|{x["delta"]:+.4f}% ± {x["se"]:.4f}%|{"/".join(map(str,x["wtl"]))}|{st.mean(r["sim_generic"] for r in rows(label)):.5f}|')
new += ['', '基準の模擬は総手数10.39210、汎用紙操作1.27298手/注文。12窓保護版の総手数は10.37926。模型差は約−0.0024手で二標準誤差に届かず、模型の優劣は判定できない。模擬の差も約−0.12%に留まり、0.5%の採用条件には届かない。多候補を同じケースで選別した探索的比較なので、独立な採用確認とも扱わない。','',
'初期割り当ての `gobj_after` は両者とも9.85385。後段の0.65係数の目的は、15窓保護が'+f'{st.mean(r["decoder_obj_before"] for r in rows("shared15")):.5f}→{st.mean(r["decoder_obj_after"] for r in rows("shared15")):.5f}、12窓保護が{st.mean(r["decoder_obj_before"] for r in rows("shared12")):.5f}→{st.mean(r["decoder_obj_after"] for r in rows("shared12")):.5f}。12窓版の値は保護窓だけによる探索用距離。表の最終model_costは全印刷から再計算した距離を使う。','',
'局所的な改善だけを受理する制約も外した。`joint-sa.cpp` は温度0.05→0.00125で悪化を受理し、最良状態を保存する。ビームに非比較器窓を含む経路を一つ残す。16ケース（seed24〜39）×4本の追試では次のとおり。','',table([('joint-sa15','焼きなまし・15窓保護'),('joint-sa12','焼きなまし・12窓保護')]),'']
for label,title in [('joint-sa15','15窓'),('joint-sa12','12窓')]:
 x=comparison[label]['sim_moves'];rs=rows(label);new.append(f'- {title}: 模擬 {x["delta"]:+.4f} ± {x["se"]:.4f}%、勝/分/敗 '+ '/'.join(map(str,x['wtl']))+f'。悪化受理は平均{st.mean(r["decoder_uphill_accepted"] for r in rs):.3f}回。')
new+=['','悪化受理で平均16〜20回の変更を通しても0.5%改善は得られず、この追試は16件で打ち切った。全ての模擬で誤表示0。']
report=report.replace(old,'\n'.join(new))
# Tuning is an explicitly small screening set, not cherry-picked final evidence.
tuning=['七枚の探索が汎用費用の安い対へ寄りすぎる可能性も調べた。割り当てのハンドル差係数を基準の0.50から増やし、G=40と六枚から始める疎な6窓版も試した。seed24〜39の16件。','',table([('seven-h650','七枚・係数0.65'),('seven-h800','七枚・0.80'),('seven-h1000','七枚・1.00'),('seven-g40h650','七枚G40・0.65'),('sparse6h650','疎な6窓・0.65')]),'',
'全て基準より悪く、この調整でも採用条件を満たさなかった。模型で悪化した七枚方式には、長いオンライン模擬や提出時間内への最適化を追加しなかった。','']
report=report.replace('### 3.3 汎用窓の上の追加キャップ','\n'.join(tuning)+'\n### 3.3 汎用窓の上の追加キャップ')
forced=['狙った不整合対が部分ビームで落ちないよう、その一対を途中では必ず選ぶ `forced.cpp` も試した。完成した候補は強制を外し、最終設計と同じ対選択で採否を決める。12窓を保護し、4窓または8窓をまとめて変える。各128提案、seed24〜39の16件×4本。','',table([('forced4','一対を保持・4窓'),('forced8','一対を保持・8窓')]),'']
for label,title in [('forced4','4窓'),('forced8','8窓')]:
 x=comparison[label]['sim_moves'];rs=rows(label);forced.append(f'- {title}: 模擬 {x["delta"]:+.4f} ± {x["se"]:.4f}%、勝/分/敗 '+ '/'.join(map(str,x['wtl']))+f'。採用された提案は合計{int(sum(r["decoder_forced_accepts"] for r in rs))}回、最終の非比較器窓は全ケースで0。')
forced+=['','幅4のこの探索では、対象対の保持や窓群を8個に増やすことでも採用条件に届かなかった。全ての最終初期対集合が最終設計と一致し、模擬の誤表示は0。','']
report=report.replace('### 3.2 七枚比較器と疎な七枚目','\n'.join(forced)+'\n### 3.2 七枚比較器と疎な七枚目')
control=table([('six-control','移植した探索器を六枚で使用')])
x=comparison['seven-vs-six-control']['model_cost']
control_text='七枚用に移した探索器の差を調べるため、同じ候補列挙・重み・停滞脱出を六枚で動かす `six-control.cpp` も64件で比較した。'+ '\n\n'+control+'\n\n'+f'移植した六枚探索器と元の六枚版の差は二標準誤差未満なので、その優劣は判定しない。同じ移植探索器どうしで七枚−六枚の模型差は **{x["delta"]:+.5f} ± {x["se"]:.5f}手/注文**。七枚版の悪化を探索器の移植差だけで説明する結果ではない。ただし、任意の七枚方式を否定する比較ではない。'+'\n\n'
report=report.replace('### 3.3 汎用窓の上の追加キャップ',control_text+'### 3.3 汎用窓の上の追加キャップ')
validation=json.loads((p/'results/validation-shared/summary.json').read_text())
check=f'''### 正しさの検査

GCC 13.3.0とClang 18.1.3で、六枚模型・七枚模型・先着ゲート版を実際にコンパイルした。七枚の厳密費用表は100対で逆BFSと最大4.44e−16の差。疎な七枚目は40対で、全点対距離から求めた平均と逆BFSが完全一致。各1000本の経路の計7484移動も可視性を検査した（`verification.txt`）。

実際に学習された先着ゲートを含む8ケース（seed {', '.join(map(str,validation['seeds']))}）を公式 `/home/sato/ahc074/tools/target/release/tester` で実行した。さらに既存 `scripts/replay.py` を読み込み、**8192注文・{validation["replayed_moves"]}操作の再生、可視性、表示、得点の一致**を確認。WA=0、誤表示=0。これは選別した設計の正しさ検査であり、スコアの比較や時間内動作の検査ではない。`results/validation-shared/` に指標を保存した。

'''
report=report.replace('### 再現条件と保存物',check+'### 再現条件と保存物')
report=report.replace('最大8解法プロセス、テスター利用時は最大6組に制限。重い評価の組は直列に実行する。','主な評価は最大8解法プロセスで直列に実行。補助模型を同時実行するときは1解法プロセスのみ。実際のテスター検査は最大4組とし、テスターも数えた同時プロセス数を16以下に保った。')
report=report.replace('- `data/` にケース別模型と設計、','- 基準HEADは `61110efebdd01f08943eb8b4f431e837aa612ae2`。七枚の表と先着ゲートの距離球計算の移植元は PR76 の `cc718c1de52fe81c3c0c2724de276b51f5104317`。\n- `data/` にケース別模型と設計、')
cleanup=p/'cleanup-summary.json'
if cleanup.exists():
 stamp=json.loads(cleanup.read_text())['completed_jst']
 report += f'\n最終整理: {stamp}。指定終了期限2026-11-02 22:45 JSTより前に、実行ファイルと大きな中間出力を削除した。ソース・ケース別指標・集計・検算結果は保存した。\n'
else:
 report += '\n指定終了期限は2026-11-02 22:45 JST。最終整理で実行ファイルと大きな中間出力を削除し、ソース・ケース別指標・集計・検算結果を残す。\n'
(p/'REPORT.md').write_text(report)
