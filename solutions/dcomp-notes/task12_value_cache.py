from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
def make(name,s,desc):
 d=S/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s);(d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\n'+desc+'\n\n完全キーを比較するexact cacheだけの変更。計算順・探索・出力を変えない。CLOCK_SCALE・ログ・実験switch・段・DesignStoreを保持する。\n')
x='mutable std::array<NextValueEntry, 256> next_value_cache;';assert b.count(x)==1
make('dcomp-t12-value1024',b.replace(x,'mutable std::array<NextValueEntry, 1024> next_value_cache;'),'next_costのexact value cacheを256から1024 slotへ拡大し、修復候補間の追い出しを減らす。キーとdouble値は元のまま。')
x='''    struct NextValueEntry {
        std::array<uint8_t, 3 * K + 8> key;
        int size = 0;
        double value = 0;
    };''';assert b.count(x)==1
v='''    struct NextValueEntry {
        // In-place papers + delimiter + two bytes per below-generic filler.
        // Distinct filler papers are excluded from the in-place sequence:
        // key_size <= K + number_of_fillers + 1 <= 2*K+1.
        int size = 0;
        double value = 0;
        std::array<uint8_t, 2 * K + 8> key;
    };'''
make('dcomp-t12-valuecompact',b.replace(x,v),'next_costのcache entryを詰め、sizeとvalueをkeyより前へ置く。in-placeとfillerが排他的なのでkeyは最大2K+1 byteで、2K+8 byteの領域で足りる。key生成用の一時領域は元のまま。')
