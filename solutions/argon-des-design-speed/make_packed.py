"""独立に局所短縮を確認した距離表と穿孔配列の変更を組み合わせる。"""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
s=(root/'solutions/argon-des-perf-compact/main.cpp').read_text()
orbit=(root/'solutions/argon-des-comparator-orbit/main.cpp').read_text()
def part(text):
    start=text.index('    void build_tables() {')
    end=text.index('    // The orders (indices of perms)',start)
    return start,end
lo,hi=part(s);a,b=part(orbit)
s=s[:lo]+orbit[a:b]+s[hi:]
dest=root/'solutions/argon-des-design-packed';dest.mkdir()
(dest/'main.cpp').write_text(s)
(dest/'README.md').write_text('''改良元: solutions/argon-des-perf-stratacut

設計の出力を保つ2つの高速化を組み合わせる。
Comparatorの距離表は、紙番号を付け替えても合法な操作が同じことを利用し、
恒等順序からの1回のBFSと辞書順で先に求めた行の置換で作る。
perms・next・belowと全距離の値・経路の同点処理は同じ。

穿孔の区間DPとキャッシュは、H≤25で25窓の容量を使い、末尾の未使用領域を省く。
H>25では64窓の同じ処理を使う。計算式・順序・候補・採否・乱数・標本数は同じ。
全ログ・@paper/@ops・profiler・予算スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持する。新しいスイッチや指標はない。
''')
print(dest)
