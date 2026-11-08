改良元: solutions/dcomp-t11-stack-pc6

探索方針・予算を保ったまま、dcomp-t11-fast-lateの出力同一高速化へ更新する。end-memoを合法性再生の後へ移し、修復区間を二つの端点から直接求める。Clangでは不要リンクと解決済みfirst-color検査も省く。GCC/Clangの探索予算は同一。

要求探索は通常post候補6個、区間DPの広い同点選択、family選別前の二重移動結合、完成ALTの追加親一つの1→1修復、共有neutral枠6個。追加親も共有6枠へ入れる。設計は親と同じ9候補。

既存ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。
