"""Attribute the apparent profit to donor versus owner target changes."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
s=(root/'argon-des-perforation/main.cpp').read_text()
s=s.replace('double secondary_cost = 0, secondary_profit = 0;', 'double secondary_cost = 0, secondary_profit = 0, secondary_owner_profit = 0, last_owner_delta = 0;')
start=s.index('    double total_profit(int k) {',s.index('struct Perforation {'));end=s.index('    // Everything from the current opacity',start)
p=s[start:end]
p=p.replace('        double sum = 0;', '        double sum = 0, owner_delta = 0;')
p=p.replace('''                    sum += solve_edges(make_edges(u, samples[i], i));''','''                    const double value = solve_edges(make_edges(u, samples[i], i));
                    sum += value;
                    owner_delta += value - q.value;''')
p=p.replace('        return sum / kSamples;', '        last_owner_delta = owner_delta / kSamples;\n        return sum / kSamples;')
s=s[:start]+p+s[end:]
s=s.replace('                    secondary_profit += next - profit;', '                    secondary_profit += next - profit;\n                    secondary_owner_profit += last_owner_delta;')
s=s.replace('''            if (wide ? (exposure[k] == 0 || k == heads[c][b]) : k != heads[c][b]) continue;''','''            if (wide ? (k == heads[c][b] || std::find(ranked[2*c+b].begin(), ranked[2*c+b].end(), k) == ranked[2*c+b].end()) : k != heads[c][b]) continue;''')
s=s.replace('''              << "\\nd2_sec = " << elapsed_sec() - d2_start''','''              << "\\nd2_owner_profit = " << perforation.secondary_owner_profit / P
              << "\\nd2_donor_profit = " << (perforation.secondary_profit-perforation.secondary_owner_profit) / P
              << "\\nd2_sec = " << elapsed_sec() - d2_start''')
for name,rate in [('argon-des-perf-audit',0.125),('argon-des-perf-zero',0.0)]:
    out=root/name;assert not out.exists();out.mkdir()
    (out/'main.cpp').write_text(s.replace('env_real("ARGON_D2_RATE", 0.125)',f'env_real("ARGON_D2_RATE", {rate})'))
    (out/'README.md').write_text(f'''改良元: solutions/esw-slim

D2の利益分解。追加穿孔は同色第2候補、8標本、露出率{rate}。
露出率0でも候補を残し、その紙を他の注文のフィラーとして使う利益を無くした対照も調べる。
d2_owner_profitは変更紙自身の目標での区間DP利益増加、d2_donor_profitは他の目標での増加。
その他の指標・私有スイッチはargon-des-perforationと同じ。
既存のログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印を維持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。
''')
