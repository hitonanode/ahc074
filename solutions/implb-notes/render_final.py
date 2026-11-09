from pathlib import Path
import json
root=Path(__file__).resolve().parents[2];notes=root/'solutions/implb-notes'
def link(label,path):return f'[{label}]({root/path})'
def load(file):return json.loads((notes/file).read_text())
def fs(x,d=4):return f"{x['mean']:+.{d}f} ± {x['se']:.{d}f}"
ks=['helper_end_sec','req_sec','end_sec']
stages=[]
def add(label,file,index=0):
 d=load(file);name,z=list(d['comparisons'].items())[index];stages.append((label,d['base'],name,z));return z
h=add('R-H','r6-500.json',0);p=add('R-P','r6-500.json',1)
s5=add('S500','stack2-500.json');sg=add('S2000','stack2-2000.json');sc=add('SC2000','stack2-clang2000.json')
pc=add('PC','perfcost-500.json',1);inc=add('PC増分','perfcost-increment-500.json')
text=f'''実装Bの最終報告（2026-11-09、追加評価は12:52 JSTに終了）

最終判定は **below-floor finding、採用なし** です。13:05相当のユーザー判断に従い、最終版は solutions/d30a-reset6 単独を維持します。以下は solutions/d30b-stack2 の検証結果です。基準 solutions/d30a-reset6 に対し、GCC通常2000件で **{fs(sg['score'],6)}%**、時間課金後も **{fs(sg['net_score'],6)}%**。2SE改善を満たしました。勝/分/敗は1024/27/949、WA0です。

ただし、Clangの追加確認2000件は **{fs(sc['score'],6)}%**、課金後 **{fs(sc['net_score'],6)}%** で、有意差に届きません。GCCの成功と、Clangで効果が未確定であることを分けて報告します。

検証した候補は{link('d30b-stack2/main.cpp','solutions/d30b-stack2/main.cpp')}です（最終版には取り込みません）。変更は穿孔の `cost`（9599行）と `rebuild`（9886行）にある reset 需要を、ともに `2 * demands[c]` から `6 * demands[c]` にするものです。LOCAL_BENCHの `D30B_KPERFRESET` で倍率を変えられます（既定6、2で従来倍率）。climb/rematchの色確率は2のまま、covered_gainの返却費用は0.6のままです。固定反復、CLOCK_SCALE、DesignStore、注釈・目次を維持し、時計・打切り・fallbackは追加していません。評価後の変更は説明コメントだけです。

GCC標準flagsと指定Clang flagsのビルド、20件smokeを通過しました。Clang確認には `-std=gnu++23 -O2 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero` を使用。LOCAL_BENCH/CLOCK_SCALE=1.1付きです。ローカルはClang18.1.3で、ジャッジClang21との版差は残ります。

以下の±は1SE、負のlog比が改善です。時間はCLOCK_SCALE込みのmsで、H/R/Eはhelper_end_sec / req_sec / end_sec。課金後のlog比は、得点log比に `0.0003×ΔH(ms) + 0.00055×ΔR(ms)` を加えました。

**設計モデル監査と選別**

{link('DESIGN-AUDIT.md','solutions/implb-notes/DESIGN-AUDIT.md')}に、定数・関数・行番号・注文側との対応と過去の試行を整理しました。stack1の2000件（20261109-104153_d30a-stack1）ではmodel_col=2.949、model_gc=1.361に対し、実操作dig=2.840、gen=1.214手/注文でした。ただし後処理や複数穴の共有があるため、ラベルの平均比を直接係数には代入していません。

|監査対象|モデル化する注文側の量と判断|
|---|---|
|colcostの0.5、同色pair補正、違反罰|需要で重み付けした掘り深さ。総倍率をscreen、需要2と両色制約は維持。|
|hcostのkHoleWeight=.38、gcの需要2|穴修復の限界費用、汎用層の平均移動。穴重みとgcost表の倍率をscreen。|
|initializeの.65/.04、列サイズc+1.5、余り配置.5/3|初期ペア距離、深い列への配分、色均衡。後段で再最適化されるため監査のみ。|
|climb proxy=.5、ProbabilityHead重み1/1.25|将来のfiller利益。重みをscreen。|
|climb/ProbabilityHeadのreset=2|列先頭色の確率。1.4/6をscreen。|
|穿孔の利益重み.7、reset=2|穴を足す費用とdonor/owner利益、先頭色確率。重みとresetをscreen。|
|map gobjの.5、汎用費用、.04、未成立pair罰10|窓割当前の粗いペア費用。監査のみ。|
|初期列順・候補選択|注文側需要を再利用したDP、完成候補のV最小選択。固定。Vの回帰係数・特徴量定義も変更なし。|

最初のscreenは **stack1** 上の500件、group `20261109-121144`。基準runは `_d30a-stack1`、各候補runの末尾は下表のディレクトリ名です。これはreset6上の最終結果ではありません。8系統×2値のうち、ΔVが2SE以上改善し、得点が明確に悪化していないものだけを次へ進めました。

|候補（solutions/以下）|パラメータ|log比% ± SE|勝/分/敗|Δdv_best ± SE|
|---|---|---:|---:|---:|
'''
screen=load('cost-500.json');manifest=json.loads((notes/'cost-screen.json').read_text())
for item,(name,z) in zip(manifest,screen['comparisons'].items()):
 text+=f"|{name.split('_',1)[1]}|{item['value']}|{fs(z['score'])}|{'/'.join(map(str,z['wtl']))}|{fs(z['paired_metrics']['dv_best'],5)}|\n"
text+=f'''
全arm WA0。paired時間と各armのp99は {link('COST-SCREEN.md','solutions/implb-notes/COST-SCREEN.md')}、数値原本はcost-500.jsonです。中断時点で全結果とpahcer履歴は保存済みでしたが、metadataの最終更新前だったため、得点・Vをresult/errから再集計しました。このscreenの時間差だけで採用判断はしていません。

穴重みと列倍率の大きな変更は明確に悪化し、generic倍率にはVの改善がありませんでした。climb・rematch・穿孔利益重みも通過せず。通過したのはheadreset=6とperfreset=6の二つです。

基準をreset6へ変更して500件で再確認すると、headreset=6のV改善は消えました。perfreset=6だけが残ったため、それだけをstack2に採用。最後に費用だけ6・確率2の切り分け（solutions/d30b-perfcost6）も試しましたが、stack2比で得点・Vとも悪化方向となり、500件で終了しました。

|段階|件数|log比% ± SE|勝/分/敗|ΔV ± SE|課金後% ± SE|
|---|---:|---:|---:|---:|---:|
'''
for label,b,name,z in stages:
 text+=f"|{label}|{z['n']}|{fs(z['score'])}|{'/'.join(map(str,z['wtl']))}|{fs(z['paired_metrics']['dv_best'],5)}|{fs(z['net_score'])}|\n"
text+='\n全段階WA0。R-Hはheadreset、R-Pはperfreset、Sはstack2、SCはClang、PCは費用のみ6。PC増分だけはstack2を基準にしています。\n\n'
for label,b,name,z in stages:text+=f'- {label}: `{b}` / `{name}`\n'
text+='\n|段階|ΔH ± SE|ΔR ± SE|ΔE ± SE|p99 H/R/E（基準→候補）|\n|---|---:|---:|---:|---|\n'
for label,b,name,z in stages:
 t=z['paired_ms'];q=z['arm_p99_ms'];text+='|'+label+'|'+'|'.join(fs(t[k],3) for k in ks)+'|'+' / '.join(f'{q[k][0]:.1f}→{q[k][1]:.1f}' for k in ks)+'|\n'
text+='''
この段の結果は、stack2はGCCで2SE改善、Clangは改善未確定。ユーザーの最終判定はbelow-floorです。headreset=6とperfcost6はno gainです。残る「2」を一律に「6」へ変更する根拠はありません。今回の比較で採用条件に届いたのは、穿孔の費用と確率を一緒に変更した版だけです。V改善がそのままClangの有意な得点改善にはなっていません。

**旧キュー（基準dual30）**

- different-map-elite：no gain。solutions/d30b-map-elite。修復は初版499/500、修正版497/500で成功しましたが、別候補のVは主枝に届かず、両版とも500件で悪化。解放商品数78.3→61.8へ減らす修正でも改善せず、2000件延長なし。
- tie-gap-sweep：no gain。0.2/0.4/0.5はいずれも2SE以上悪化し、0.3を維持。当時のソースはrunのsrcに保存。以後のreq-stackには含めていません。
- helper-return-menu：no gain（時間課金後）。solutions/d30b-helper-menu。初版・修正版の得点改善は−0.00339/−0.00247%ですが、注文時間+11.01/+7.09msに対し費用を回収できず、課金後+0.00267/+0.00143%。追加計画の未後処理費用の改善は、最終得点の改善を大きく上回りました。
- direct-helper-from-top：not started。前提のhelper-return-menuが不採用のため。
- retire-expanded-pass：段廃止はno gain。+0.000620±0.000199%で指定の得点条件を満たさず。二重収集だけを省く修正版 solutions/d30b-req-stack はbelow the floor。500×4列でstdoutと@paper/@opsがすべて一致しましたが、req −0.640±0.742msで有意な短縮がありません。2000件延長なし。
- mdp-types / perf-lazy：not started。ユーザー指示で中止。

旧キューのMは通常比較、T/H/Rは保存設計20261108-224255_dcomp-combo-dual30を使う500 seeds×4注文列です。以下の全比較でWA0でした。

'''
text+=(notes/'TABLES.md').read_text()
text+='\n最終的な採用ディレクトリはありません。最終版はreset6単独を維持します。最終提出への移植・コミットは行っていません。\n'
(notes/'REPORT.md').write_text(text)
print('REPORT characters:',len(text),'lines:',len(text.splitlines()))
