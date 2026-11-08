# Task 11: 出力同一変更の根拠

最終の高速化単独版は `solutions/dcomp-combo-fast11`（検証runの `dcomp-t11-fast-late` と同一ソース）。親は `solutions/dcomp-combo-alt1`。コンパイラごとに同じコンパイラ・同じflagsの親とstdoutの全byteを照合する。GCCとClang相互の一致は要求しない。計算の近似・fast-math・時計による予算変更は使わない。以下は実装の根拠であり、採用・不採用と実測はREPORT11に記す。

- **anchor固定配列**: 列挙するのは `-1` と紙IDで、重複を除き動かす紙自身を除く。容量K+1で十分。追加順は元のvectorと同じ。
- **anchorize遅延**: 各anchor走査中に使うeditsは元から固定。途中の勝者から作るchosenは最後にしか読まれない。最後に受理したbest_opsを一回だけanchorizeすれば、次の走査に渡すeditsは同じ。
- **部分MDP cache**: 列MDPの対象列は最大15枚。紙ID列を2個の64bit語と長さへ可逆に詰める。元の順で加算したone-stepのdoubleと、元の列挙indexで引いたMDP値のfloatを保存する。hole項と列間の加算順は元のまま。ハッシュだけでなく完全なキーを比較する。全列を覆うケースは旧経路のまま。PARTIAL_MDP_CHECKは元の関数も実行し、doubleの全bitを比較する。
- **next_costの不要初期化**: prefix cache hitが上書きするrank/first/codeを直前に初期化しない。miss時は元と同じ0/-1/1を、実際に参照するH/2Hの範囲へ設定する。coveredとavailableも参照範囲だけ初期化する。NEXT_PREFIX_CHECKは元の関数とdoubleの全bitを比較する。
- **end-memo hash/無効化**: ハッシュ変更は置換するslotだけを変える。memo hitは完全な後続リンク配列の比較で確定し、合法性再生は毎回行う。memoを無効化しても同じ関数・加算順で費用を再計算する。cacheのhit/miss counterは変わる。
- **合法性再生後のend-memo**: 呼出し内のseed（canonicalizeが保存するfiller優先順）を固定し、完成順序192byteをkeyとする。世代はpost呼出しごとに更新する。key全体を照合し、合法性とcap順序を検査してから値を共有する。不合法な試行ではhashとslot破棄を省ける。latememo-checkはhitごとにcanonicalizeとplan_costを再計算し、fillerの全属性、top_d、double全bitを照合する。
- **Clangのリンク省略**: 可換screenが完成表示を証明済みで、memoが後段または無効なら、前段のリンク配列はcap順序の早期検査にしか使わない。後段の正確なordにも同じcap検査があるため、リンクを省いても受理される候補は変わらない。prefix cacheのhit数や棄却の時点は変わる。SCREEN_REPLAY_CHECKは全screen候補を旧可視性再生と照合する。速度差が確認できたClangだけで使う。
- **Clangのfirst-color scan**: その列に印刷された色の全てについてfirstが埋まった後は、後続の紙でfirstを更新する条件は必ず偽になる。残りの費用加算とMDP符号化は元の紙順で全件行う。NEXT_PREFIX_CHECKで旧next_costのdouble全bitも検査した。
- **挿入区間の直接計算**: kを除いた順序で、bad窓のどれかへ最初に触れる紙の位置がhiとなる。wrong窓それぞれの最初のownerの最大位置に1を加えたものがloとなる。元のtop-two-layer prefixは、一枚だけ抜いた後の全てのfirst ownerを含む。抜くkがprefixより深ければ、prefix内の位置はずれない。ownerが存在しないwrong窓は必ず区間を空にする。DIRECT_GEOMETRY_CHECKとEJECT_GEOM_CHECKで、区間の有無および全ての非空区間の端点を元の表・完全な紙順序と照合する。空区間の数値そのものは以後参照されない。
- **同じneutral端点の重複除去**: 浅い端・深い端のgap組が一致した時は、同じtail列・同じ再生になる。二回目は一回目より良い費用や別の署名を生成しない。実際の出力一致を別途検証する。
- **handle商の表引き**: n0/n1は0〜256の整数カウント。resetは2×列target数の整数でsegment中は固定。元のqfで各商を生成し、Qだけを置換する。n0/n1の更新とdifの加算順は元のまま。HOLE_QUOTIENT_CHECKは各laneの元SIMD除算結果と全bitを比較する。表の生成・gatherが割に合うかは別の速度試験で判断する。

性能が悪かった案の例: 空maskの圧縮store省略、少数bitでの圧縮、推移閉包が同じ辺集合の再利用は、整数的には同じ結果でもbranchやcache費用が増える。数学的な同一性だけで採用しない。
