from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
a='        const u64 generation = ++memo_generation;'
b='''        // End values depend on the complete final order and the seed filler priority.
        // canonicalize rebuilds every level and top_d; only the old filler ID order survives.
        // Up to seven IDs fit in an exact delimiter-coded key, reusable across post calls.
        u64 generation = ++memo_generation;
        if(fillers.size()<=7) {
            generation=1;
            for(const auto& f:fillers)generation=(generation<<8)|unsigned(f.paper);
        } else generation|=u64(1)<<63;  // preserve per-call isolation for larger experimental states
'''
assert s.count(a)==1;s=s.replace(a,b)
p=r/'solutions/dcomp-endmemo-key';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-screen-replay

post_optimizeの終状態memoを、呼出し番号だけでなく、canonicalizeに渡す旧fillerの紙ID順で区別する。canonicalizeはlevelとtop_dを紙の並びから作り直し、旧fillerからは優先順だけを引き継ぐ。その順序と最終next配列が同じなら、到達可能性・canonical記録・終状態費用も同じ。7枚以下のID列を区切り付きの64bit整数で完全に符号化し、呼出し間で同じmemoを再利用する。8枚以上の実験状態は元の呼出し単位の識別を保つ。表は128のままで、hash一致だけで値を使わず全next配列も比較する。

紙・費用パラメータはSolver内で固定。探索順、採否演算、予算、ログとDesignStoreは維持する。時間fallbackなし。
''')
p=r/'solutions/dcomp-notes/task10_analyze.py';s=p.read_text().replace("'cf_value')):","'cf_value','f2_memo_')):");p.write_text(s)
