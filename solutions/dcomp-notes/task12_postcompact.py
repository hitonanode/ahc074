from pathlib import Path
S=Path(__file__).resolve().parents[1];s=(S/'dcomp-t12-postmemo/main.cpp').read_text()
s=s.replace('std::array<uint8_t,12*K+32> key','std::array<uint8_t,512> key')
x='input_ops.size()>2*K ||';assert s.count(x)==1
s=s.replace(x,'input_ops.size()>64 || fillers.size()>32 OP_TAG(||tags.size()>64) ||')
s=s.replace('// state, path and labels are compared; counters used by the outer repair loops','// state, path and labels are compared; counters used by the outer repair loops')
s=s.replace('''    struct PostMemoEntry {''','''    // The key needs at most 489 bytes for 64 moves and 32 filler records.
    // Larger exact inputs bypass this optional cache and execute the same pass.
    struct PostMemoEntry {''')
d=S/'dcomp-t12-postcompact';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-t12-postmemo\n\nwhole-post memoのkey bufferを2336から512 bytesへ縮め、32entryの常用部分をcacheへ収めやすくする。64操作または32 fillerを超える入力はキャッシュを使わず元の同一処理を実行する。最大key489 bytesのため切捨てや衝突共有はない。探索結果・探索回数は変えず、時計で切り替えない。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。\n')
