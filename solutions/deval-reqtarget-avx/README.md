改良元: `solutions/deval-trim6b`。

Solverの関数群にtarget("avx2,popcnt")を明示する。後処理のビット数集計をハードウェア命令で行い、配列コピーにもAVX2命令を使えるようにする。FMAとfast-mathを新たに有効化しない。GCCは既存のpush/pop_options内、Clangはattribute push/popで範囲を限定する。探索予算・乱数・演算の式・実験スイッチ・ログは維持する。出力一致と通常24並列のcompareで効果を確認する実験。
