"""Copy one training-selected, already tested source to its final solver directory."""
from pathlib import Path
import argparse,hashlib,json
S=Path(__file__).resolve().parents[1];N=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('slack',choices=['30','35']);a=p.parse_args()
base=S/('dcomp-t12-fund'+a.slack);d=S/('dcomp-combo-dual'+a.slack);assert not d.exists();d.mkdir()
s=(base/'main.cpp').read_bytes();(d/'main.cpp').write_bytes(s)
(d/'README.md').write_text('''改良元: solutions/dcomp-combo-dual25

中立候補として残す費用差（NEUTRAL_SLACK）を0.25から0.'''+a.slack+'''へ広げる。完成した候補の次の修復に残す選択肢を増やすための変更。設計9候補、通常計画6候補、追加親上位1個・共有6枠・3 roundsなどは親のまま。

増える要求処理の費用を、同じ注文内の通常post全体の再利用で抑える。紙順・top_d・全filler記録・操作列・処理モード・手元用ラベルが完全一致した場合だけ、完成した結果を戻す。hashの衝突はkey全体で検査する。32 entry、keyは512 bytes。大きい入力はキャッシュを使わず元の処理を実行する。neutral候補収集、trace、profileには使わない。

Clangではpostの可視性再生prefix cacheを無効化し、GCCでは元の実装を保つ。これは同じ操作の再生方法だけの違いで、探索予算は両コンパイラ共通。時計による軽量化、設計の打切り、候補数の変更はない。

- `F3_POST_MEMO=0`: whole-post再利用を無効化する実験用切替。
- `F3_PREFIX=0/1`: replay-prefixの上書き。どちらも探索結果は同じ。
- `POST_MEMO_CHECK`: hitでも元処理を実行し、終状態・操作・ラベル・採用counter差を検査するビルド用切替。
- `dp_post_memo_hits/misses`: 要求処理中のwhole-post再利用件数。外側の反復に使うeject_accepts差はhitでも再現する。他の探索回数の指標は実行した仕事を数える。

既存のCLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@ops、ログ、trace、profiler、実験switch、段の目印と目次を保持する。
''')
(N/'t12-selected.json').write_text(json.dumps({'source':str(base),'candidate':str(d),'sha256':hashlib.sha256(s).hexdigest(),'slack':a.slack},indent=2)+'\n')
print(d,hashlib.sha256(s).hexdigest())
