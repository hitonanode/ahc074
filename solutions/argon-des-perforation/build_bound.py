"""Exact early rejection before evaluating owner-target conditional differences."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent;out=root/'argon-des-perf-condbound'
assert not out.exists();out.mkdir()
s=(root/'argon-des-perf-condfast/main.cpp').read_text()
s=s.replace('    double last_owner_raw = 0, last_owner_corrected = 0;', '''    double last_owner_raw = 0, last_owner_corrected = 0;
    bool last_profit_possible = true;
    int owner_bound_checks = 0, owner_bound_skips = 0;''')
a=s.index('    double total_profit(int k) {',s.index('struct Perforation {'));b=s.index('    // Everything from the current opacity',a)
p=s[a:b].replace('double total_profit(int k)', 'double total_profit(int k, double required_gain)')
p=p.replace('        last_owner_raw = last_owner_corrected = 0;', '        last_owner_raw = last_owner_corrected = 0;\n        last_profit_possible = true;')
loop=p.index('        double sum = 0;')
owner_start=p.index('                if (s.ded[u] == k) {',loop)
def block(text,start):
    opening=text.index('{',start);depth=1;i=opening+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[opening+1:i-1],i
owner,oe=block(p,owner_start)
other,ne=block(p,p.index('else {',oe))
owner=owner.replace('                    sum += value;', '                    values[i] = value;')
other=other.replace('                    sum += value;', '                    values[i] = value;')
tail=p[p.index('        last_owner_raw /= kSamples;',ne):]
p=p[:loop]+'''        std::array<double, P * kSamples> values;
        double sum = 0;
        for (int u = 0; u < P; ++u) for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;
            const auto& q = cache[i];
            if (s.ded[u] == k || same[u]) values[i] = q.value;
            else {'''+other+'''
            }
            sum += values[i];
        }
        if (cache_opacity[k] & changed) {
            // Adding this hole can only restrict the old donor intervals. Its extra
            // reward is at most one repaired error, and disjoint intervals count it
            // at most once. Conditioning the color bounds the owner gain by P(error).
            double upper = sum / kSamples - profit;
            for (int u : owners[k]) upper += probability[changed_handle][(target[u] >> changed_handle & 1) ^ 1];
            ++owner_bound_checks;
            if (upper < required_gain - 1e-8) {
                ++owner_bound_skips;
                last_profit_possible = false;
                return profit;
            }
        }
        for (int u : owners[k]) for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;
            const auto& q = cache[i];'''+owner+'''
        }
        // Retain the original order of floating-point additions.
        sum = 0;
        for (double value : values) sum += value;
'''+tail
s=s[:a]+p+s[b:]
s=s.replace('const double next = viable ? total_profit(k) : profit;', 'const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;')
s=s.replace('if (viable && delta - weight * (next - profit + correction)', 'if (viable && last_profit_possible && delta - weight * (next - profit + correction)')
s=s.replace('''    std::cerr << "perf_owner_raw = "''','''    std::cerr << "perf_owner_bound_checks = " << perforation.owner_bound_checks
              << "\\nperf_owner_bound_skips = " << perforation.owner_bound_skips << '\\n';
    std::cerr << "perf_owner_raw = "''')
(out/'main.cpp').write_text(s)
(out/'README.md').write_text((root/'argon-des-perf-condfast/README.md').read_text()+'''
他目標の差分を先に計算する。追加穴が自目標で生むDP利益は、その窓の誤色確率以下。
この上限を加えても穴費用を回収できない候補は、自目標の条件付きDPを計算せず棄却する。
元の浮動小数点加算順序を維持し、境界には1e-8の余裕を持たせる。
perf_owner_bound_checks / skipsは上限を調べた数と、重い評価を省いた数。
''')
