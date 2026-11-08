"""Combine the exact window optimization with the frozen ten-late policy."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/dcomp-nine/main.cpp').read_text()
oldten=(root/'solutions/dcomp-ten-late/main.cpp').read_text()
fast=(root/'solutions/dcomp-nine-sparsebits/main.cpp').read_text()
assert hashlib.sha256(base.encode()).hexdigest()=='2969698026bbdb76c0d345d921480068edf14bad3480c6e15fd6dc1a476b8169'
assert hashlib.sha256(oldten.encode()).hexdigest()=='48e72371220adeb4350f18d82d26914cc8566eac33389d115355f389b7abf955'
def ten(s):
    def sub(a,b):
        nonlocal s
        assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b)
    sub('if(!raw && extra!=2) {','if(!raw && extra<2) {')
    sub('if(extra==2 && !warm_state.papers.empty()) {','if(extra>=2 && !warm_state.papers.empty()) {')
    begin=oldten.index('    if(extra==3) {\n        // One additional native reassignment')
    end=oldten.index('    else perforate.template operator()<64>();',begin)
    sub('    if (solver.H <= 25) perforate.template operator()<25>();\n',oldten[begin:end])
    sub('for(int j=0;j<5;++j) {','for(int j=0;j<6;++j) {')
    sub('const bool warm=j%2==1 || j==4;','const bool warm=j%2==1 || j>=4;')
    sub('complete(id,warm?2:1);','complete(id,j==5?3:warm?2:1);')
    return s
assert ten(base)==oldten, 'The candidate extension must reproduce the frozen ten-late source byte for byte.'
for name,s in [('dcomp-nine-fast',fast),('dcomp-ten-fast',ten(fast))]:
    p=root/'solutions'/name
    assert not p.exists(),f'{p} already exists; do not overwrite a frozen candidate'
    p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('''改良元: solutions/dcomp-nine

窓探索を出力同一で高速化する。状態用・作業用のrelation費用配列について、それぞれの非ゼロ位置を保存する。試行時は作業用配列の前回の非ゼロだけを消去し、旧互換ペアのうちrelation不変の費用と、今回閉包を計算した互換ペアの費用だけ書く。受理時は配列と非ゼロ一覧を対にして交換する。その他の費用は常にゼロである。

互換ペアの一覧は、小さなbitsetに「旧互換でrelation不変」と「今回新たに互換」を入れ、番号の昇順に取り出す。元のSIMD全走査と同じ順序なので、matchingの同点処理まで保つ。近似演算やfast-mathは使わず、窓探索の乱数と反復数も不変。

'''+('''候補数は9のまま。dcomp-nineに対する出力同一性・設計高速化の確認用。
''' if name=='dcomp-nine-fast' else '''dcomp-ten-lateと同じ10候補目を追加する。既存9候補のsalt・反復数・Vと選択規則はそのまま。10候補目(id=9)は、その時点の最良の完成割当と穴を引き継ぎ、climb・前rematch・穿孔探索を省いて後段rematchとVだけを行う。追加候補がVを下げた場合だけ採用する。初期列順DPとDesignStoreは、最後に選ばれた設計に適用する。
''')+'''
map450k、gopt133k、annealと既存仕上げの予算は固定。時間による打切り、候補数変更、軽い注文処理はない。注文処理はdcomp-nineと同じlegal-tie-fast。CLOCK_SCALE、ログ、@paper/@ops、DesignStore、段の目印、実験スイッチ・プロファイラを保持する。dv_candidatesは'''+('9' if name=='dcomp-nine-fast' else '10')+'。\n')
audit={'parent_nine_sha256':hashlib.sha256(base.encode()).hexdigest(),
       'parent_ten_sha256':hashlib.sha256(oldten.encode()).hexdigest(),
       'extension_reproduces_ten_late_exactly':ten(base)==oldten,
       'nine_fast_sha256':hashlib.sha256(fast.encode()).hexdigest(),
       'ten_fast_sha256':hashlib.sha256(ten(fast).encode()).hexdigest()}
# All optimized code lies before design annealing. The design/candidate stage,
# request policy and main remain exact copies of their respective frozen parent.
marker='    // ==== Design annealing ===='
audit['nine_after_window_identical']=fast[fast.index(marker):]==base[base.index(marker):]
audit['ten_after_window_identical']=ten(fast)[ten(fast).index(marker):]==oldten[oldten.index(marker):]
assert audit['nine_after_window_identical'] and audit['ten_after_window_identical']
(root/'solutions/dcomp-notes/t9-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
