改良元: solutions/dcomp-combo-alt1

出力同一の要求高速化を合成する。anchor候補は固定配列にし、最後の勝者だけanchorizeする。部分MDPの列内紙ID列を正確なkeyでcacheし、prefix hitで不要な初期化をしない。end-memoは合法性再生を通った後で検索し、完成順序の192byteを全照合する。修復区間の端点はtop-two-layer prefixから直接求める。

Clangだけでは、表示検査済みの候補の不要なリンク配列構築を省き、next_costで既に見つかった色を再検査しない。両方ともGCCでは元の実装を使う。コンパイラで探索の件数や予算は変えない。加算順・候補順・出力は保持する。MEMO/LATE_MEMOと検証用の旧経路を残す。

設計9候補、要求方針・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。
