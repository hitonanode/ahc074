"""Separate visited-potential updates from the vectorizable slack subtraction."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
start=s.index('std::vector<int> hungarian(');end=s.index('// The filler value of the column heads',start)
b=s[start:end]
b=b.replace('    std::vector<uint8_t> used(n + 1);','    std::vector<uint8_t> used(n + 1);\n    std::vector<int> visited(n + 1);',1)
b=b.replace('        int j0 = 0;','        int j0 = 0, visited_count = 0;',1)
b=b.replace('            used[j0] = true;','            used[j0] = true;\n            visited[visited_count++]=j0;',1)
old='''            for (int j = 0; j <= n; j++)
                if (used[j])
                    u[p[j]] += delta, v[j] -= delta;
                else
                    minv[j] -= delta;'''
new='''            for(int q=0;q<visited_count;++q) {
                const int j=visited[q];
                u[p[j]]+=delta;v[j]-=delta;
            }
            // A visited column is never read from minv again in this search.
            // Updating its dead slack too permits a branch-free vector loop;
            // every live slack has exactly the original subtraction sequence.
            for(int j=1;j<=n;++j)minv[j]-=delta;'''
assert old in b
b=b.replace(old,new)
s=s[:start]+b+s[end:]
d=ROOT/'solutions/deval-hungarian';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-hungarian

改良元: solutions/deval-vbranch-o3。

Hungarian法で訪問済み列のリストを持ち、ポテンシャルの更新とminvの一括減算を分離する。訪問済み列のminvはその探索では二度と読まれないため、そこにも減算して分岐をなくす。使われる値の演算順、最小値の同点処理、割当ては同じ。探索回数と時間ガードは元のまま。
''')
print(d,len(s.encode()))
