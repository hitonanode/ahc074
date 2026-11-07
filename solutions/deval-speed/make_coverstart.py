from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-fast/main.cpp').read_text()
a=s.index('    static double covered_gain(');b=s.index('    // The expected saving',a);v=s[a:b]
old='''        double p0 = 1, p1 = 0, expected = 0;
        for (u64 z = covered; z; z &= z - 1) {'''
new='''        if(!covered)return 0;
        // The first Bernoulli step starts at (p0,p1,mean)=(1,0,0).
        // Multiplication by 0/1 and addition to +0 are exact for these
        // finite nonnegative probabilities. Seed it directly, retaining every
        // later multiply/add and the final subtraction order.
        const double first=probability(__builtin_ctzll(covered));
        double p0=1-first,p1=first,expected=first;
        for (u64 z = covered & (covered-1); z; z &= z - 1) {'''
assert old in v;v=v.replace(old,new,1);s=s[:a]+v+s[b:]
d=R/'solutions/deval-coverstart';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-coverstart

改良元: solutions/deval-fast。

fillerの期待節約を計算する確率多項式の最初の1項を、p0=1-p、p1=p、期待値=pで初期化する。元の初期状態はp0=1、p1=0、期待値=0なので、有限の非負確率に対する0/1倍と0加算を省くだけ。2項目以降と最後の減算は元の順序を保つ。空集合は元と同じ正の0。

探索予算・固定乱数・時間による打切りの不在は親と同じ。
''')
print(len(s.encode()))
