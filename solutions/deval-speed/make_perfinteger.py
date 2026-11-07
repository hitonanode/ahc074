from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-geometry/main.cpp').read_text()
lo=s.index('template<int Capacity>\nstruct Perforation');hi=s.index('// ==== Design state',lo) if '// ==== Design state' in s[lo:] else s.index('struct DesignState',lo)
b=s[lo:hi]
b=b.replace('std::array<double, Capacity + 1>','std::array<int16_t, Capacity + 1>')
b=b.replace('std::array<double, Capacity> avoid','std::array<int16_t, Capacity> avoid')
b=b.replace('        double value = 0;','        int16_t value = 0;',1)
b=b.replace('int number=__builtin_popcountll(covered);','int number=5*__builtin_popcountll(covered);')
b=b.replace('const double price=1.6+(b!=int(color>>c&1));','const int price=8+5*(b!=int(color>>c&1));')
b=b.replace('const double v=number-price;','const int v=number-price;')
b=b.replace('std::max(edge[start],v)','std::max<int>(edge[start],v)')
b=b.replace('number-=int(covered>>start&1);','number-=5*int(covered>>start&1);')
b=b.replace('std::max(dp[c + 1], dp[lo] + edges[c][lo])','std::max<int>(dp[c + 1], dp[lo] + edges[c][lo])')
b=b.replace('double solve_edges(','int solve_edges(')
b=b.replace('std::max(q.backward[lo], edges[c][lo] + q.backward[c + 1])','std::max<int>(q.backward[lo], edges[c][lo] + q.backward[c + 1])')
b=b.replace('double best = -1e9;','int best = -10000;')
b=b.replace('const double v = q.forward[lo] + best;','const int v = q.forward[lo] + best;')
b=b.replace('std::max(q.avoid[c], v)','std::max<int>(q.avoid[c], v)')
b=b.replace('return sum / kSamples;','return sum / (5 * kSamples);')
b=b.replace('double changed_window_value(','int changed_window_value(')
b=b.replace('double value = q.forward[h] + q.backward[h + 1];','int value = q.forward[h] + q.backward[h + 1];')
b=b.replace('std::array<double, P * kSamples> values;','std::array<int16_t, P * kSamples> values;')
b=b.replace('double value = q.avoid[c];','int value = q.avoid[c];')
b=b.replace('double upper = sum / kSamples - profit;','double upper = sum / (5 * kSamples) - profit;')
b=b.replace('const double value = changed_window_value','const int value = changed_window_value')
b=b.replace('const double direct = value - q.value;','const int direct = value - q.value;')
b=b.replace('const double flip_new = changed_window_value','const int flip_new = changed_window_value')
b=b.replace('            double flip_old;','            int flip_old;')
b=b.replace('last_owner_raw /= kSamples;','last_owner_raw /= (5 * kSamples);')
b=b.replace('last_owner_corrected /= kSamples;','last_owner_corrected /= (5 * kSamples);')
b=b.replace('    static constexpr int kSamples = 32;','''    // All interval gains are multiples of 1/5: repaired handles cost 5,
    // placement/return 8, and a donor dig 5. Store DP values in these units.
    static constexpr int kSamples = 32;''',1)
s=s[:lo]+b+s[hi:]
d=ROOT/'solutions/deval-perfint';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-perfint

改良元: solutions/deval-geometry。

穴あけDPの利益（不一致数−1.6−掘り出し費用）を1/5操作単位のint16_tで保持する。メモリ量を1/4にし、DPの最大値・加算を整数で行う。期待値と穴コストの比較時に元の単位へ戻す。実数で定義した式は同じだが、従来のdouble丸めを変えるため、出力と8列の品質を確認して採否を決める。探索予算・時間ガードは親と同じ。
''')
print(len(s.encode()))
