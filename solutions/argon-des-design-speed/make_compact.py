"""基準を新しい候補ディレクトリへコピーし、穿孔の配列容量を特殊化する。"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / 'solutions/argon-des-perf-stratacut/main.cpp'
dest = root / 'solutions/argon-des-perf-compact'
dest.mkdir()
s = base.read_text()
lo = s.index('struct Perforation {')
hi = s.index('// ==== Design state:', lo)
part = s[lo:hi]
part = part.replace('struct Perforation {', 'template<int Capacity>\nstruct Perforation {')
part = part.replace('std::array<double, 65>', 'std::array<double, Capacity + 1>')
part = part.replace('std::array<double, 64>', 'std::array<double, Capacity>')
part = part.replace('std::array<std::array<double, Capacity + 1>, 64>',
                    'std::array<std::array<double, Capacity + 1>, Capacity>')
part = part.replace('std::array<u64, 64> starts{}, ends{};',
                    'std::array<u64, Capacity> starts{}, ends{};')
part = part.replace('          utility(K) {', '          utility(K) {\n        assert(H <= Capacity);')
s = s[:lo] + part + s[hi:]
lo = s.index('    Perforation perforation(solver);')
hi = s.index('    return state;', lo)
part = s[lo:hi].replace('Perforation perforation(solver);', 'Perforation<Capacity> perforation(solver);')
s = (s[:lo] + '    // Only the H live entries are read. Specialize the common 25-handle layout;\n'
     '    // the full capacity also supports the retry designs and experimental maps.\n'
     '    auto perforate = [&]<int Capacity>() {\n'
     + ''.join('    ' + line if line.strip() else line for line in part.splitlines(True))
     + '    };\n'
     '    if (solver.H <= 25) perforate.template operator()<25>();\n'
     '    else perforate.template operator()<64>();\n' + s[hi:])
(dest / 'main.cpp').write_text(s)
(dest / 'README.md').write_text('''改良元: solutions/argon-des-perf-stratacut

穿孔の区間DPとキャッシュの配列容量を、通常の25ハンドルに合わせて特殊化する。
H以下の添字だけを使う不変条件を保ち、これまで使わなかった末尾の領域を減らす。
25を超えるハンドルの設計は同じアルゴリズムを64要素の配列で実行する。
計算の式・走査順・乱数・標本数・候補の採否は変えない。

新しいスイッチ・指標はない。全ログ・@paper/@ops・profiler・予算スイッチ、
CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
変更はHandle perforationと、その呼び出しの容量の選択だけ。
''')
print(dest)
