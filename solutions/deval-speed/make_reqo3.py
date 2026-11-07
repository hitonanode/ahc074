from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-climbcache/main.cpp').read_text()
a='// ==== Solver: papers, handles and the generic look-ahead ===='
b='// ==== Emergency design ===='
s=s.replace(a,'''#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC push_options
#pragma GCC optimize("O3")
#endif
'''+a,1)
s=s.replace(b,'''#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options
#endif
'''+b,1)
d=R/'solutions/deval-reqo3';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-reqo3

改良元: solutions/deval-climbcache。

設計段と同様に、GCCで注文処理の関数群をO3で最適化する。fast-mathは使わず、浮動小数点の既定の規則を維持する。Clangは元のコンパイラ設定を使う。アルゴリズム・探索予算は同じで、GCCの全出力を比較する。

時間不足の切替えはない。ログ、DesignStore、@paper/@ops、目次と段の目印を維持。
''')
print(len(s.encode()))
