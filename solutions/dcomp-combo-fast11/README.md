改良元: solutions/dcomp-combo-alt1

要求処理の出力を変えない高速化だけをまとめる。main.cppはTask 11のdcomp-t11-fast-lateと全byteが同じ。探索予算・選択規則・設計は親のまま。

- anchor候補を固定配列で作り、anchorizeは走査の最後の勝者だけへ遅延する。
- 列MDPが部分被覆のケースでは、対象列の正確な紙ID列でone-step値とMDP値をcacheする。キー全体を照合する。
- next_costでprefix cache hitが上書きする初期化を省く。
- end-memoを合法性再生後に引き、完成紙順192byteを照合する。不合法な試行によるhash計算とcache追い出しを避ける。
- eject修復の挿入区間端点を、既にある上2層のprefixから直接求める。
- Clangだけ、検査済み候補のリンク構築と、既に色が確定した列の探索を省く。GCCとの探索量は変えない。

浮動小数の加算順は維持する。時刻での切替・打切りなし。CLOCK_SCALE、DesignStore、@paper/@ops、ログ・metrics・trace・profiler・実験スイッチ、段と目次を保持する。

同一性の根拠は ../dcomp-notes/EXACTNESS11.md、測定条件と採否は ../dcomp-notes/REPORT11.md を参照。
