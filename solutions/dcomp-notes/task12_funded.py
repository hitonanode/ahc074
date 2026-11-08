from pathlib import Path
S=Path(__file__).resolve().parents[1]
for v in ['30','35']:
 s=(S/('dcomp-t12-memo'+v)/'main.cpp').read_text()
 old='''        bool prefix = get("PREFIX", 1);''';assert s.count(old)==1
 new='''#if defined(__clang__)
        bool prefix = get("PREFIX", 0);  // same replay, avoiding prefix-copy overhead on Clang
#else
        bool prefix = get("PREFIX", 1);
#endif'''
 s=s.replace(old,new);d=S/('dcomp-t12-fund'+v);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t12-memo'+v+'（方策はdual25のslackを0.'+v+'へ拡大）\n\n512byte-key whole-post memoに加え、Clangだけpostの可視性再生prefix cacheを無効化する。元の初期状態から同じ操作を再生するため、探索候補・計算値・出力・予算は変わらない。GCCは元のprefixを使い、両コンパイラで同じ通常6候補・第二親1個・共有6枠・3roundsを探索する。\n\n時計による切替なし。F3_PREFIXで計測用の上書きを残す。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。\n')
