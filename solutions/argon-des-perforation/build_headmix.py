"""Broaden the design-stage filler objective while leaving perforation unchanged."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent;out=root/'argon-des-headmix'
assert not out.exists()
out.mkdir();s=(root/'esw-slim/main.cpp').read_text()
old='    static constexpr double kClimbProxyWeight = 0.5;'
s=s.replace(old,old+'''
    static double secondary_head_rate() {
        static const double rate = [] {
            const char* value = std::getenv("ARGON_D2_HEAD_RATE");
            return value && *value ? std::atof(value) : 0.0625;
        }();
        return rate;
    }''')
start=s.index('    void filler_climb(');end=s.index('// ==== Head-aware reassignment',start)
part=s[start:end]
old='''        auto eligible = [&](int x) {
            const Unit& u = unit[x];
            return weight(u) == max_weight[u.c][color(u, u.c)];
        };'''
assert old in part;part=part.replace(old,'        auto eligible = [](int) { return true; };')
startcv=part.index('        auto column_value =');endcv=part.index('        double proxy =',startcv)
part=part[:startcv]+'''        auto column_value = [&](int c) {
            std::array<std::array<int, 2>, 2> top{{{-1,-1},{-1,-1}}};
            auto better = [&](int y, int z) {
                if (z < 0) return true;
                if (weight(unit[y]) != weight(unit[z])) return weight(unit[y]) > weight(unit[z]);
                return utility[y] > utility[z];
            };
            for (int y : members[c]) {
                auto& t = top[color(unit[y], c)];
                if (better(y, t[0])) t[1] = t[0], t[0] = y;
                else if (better(y, t[1])) t[1] = y;
            }
            double value = 0;
            for (int b = 0; b < 2; ++b) if (top[b][0] >= 0) {
                const double rate = top[b][1] >= 0 ? secondary_head_rate() : 0;
                value += color_probability[c][b] * ((1-rate)*utility[top[b][0]] +
                    (top[b][1] >= 0 ? rate*utility[top[b][1]] : 0));
            }
            return value;
        };
'''+part[endcv:]
s=s[:start]+part+s[end:]
start=s.index('struct ProbabilityHead {');end=s.index('// Reassign mobile targets',start)
part=s[start:end]
part=part.replace('std::vector<double> utility, beta;', 'std::vector<double> utility, beta, conditional_beta;')
part=part.replace('          beta(d.U),','          beta(d.U),\n          conditional_beta(d.U),')
part=part.replace('''        const auto selected = heads();
        for (int c = 0; c < d.H; c++) gradient[c] = utility[selected[c][1]] - utility[selected[c][0]];''','''        for (int y : active_heads) {
            const int c = d.unit[y].c, b = d.color(d.unit[y], c);
            gradient[c] += (b ? 1 : -1) * conditional_beta[y] * utility[y];
        }''')
part=part.replace('utility[x] = d.weight(u) == max_weight[u.c][d.color(u, u.c)] ? donor(u) : 0;','utility[x] = donor(u);')
startbeta=part.index('        const auto best = heads();');endbeta=part.index('        active_heads.clear();',startbeta)
part=part[:startbeta]+'''        const auto best = heads();
        std::fill(beta.begin(), beta.end(), 0);
        std::fill(conditional_beta.begin(), conditional_beta.end(), 0);
        double sum = 0;
        for (int c = 0; c < d.H; c++) for (int b = 0; b < 2; b++) {
            const int y = best[c][b];
            int second = -1;
            for (int x = 0; x < d.U; ++x) {
                const auto u = d.unit[x];
                if (x == y || u.c != c || d.color(u, c) != b) continue;
                if (second < 0 || d.weight(u) > d.weight(d.unit[second]) ||
                    (d.weight(u) == d.weight(d.unit[second]) && utility[x] > utility[second])) second = x;
            }
            const double rate = second >= 0 ? Design::secondary_head_rate() : 0;
            conditional_beta[y] = 1-rate;
            beta[y] = prob[c][b] * (1-rate);
            sum += beta[y] * utility[y];
            if (second >= 0) {
                conditional_beta[second] = rate;
                beta[second] = prob[c][b] * rate;
                sum += beta[second] * utility[second];
            }
        }
'''+part[endbeta:]
s=s[:start]+part+s[end:]
(out/'main.cpp').write_text(s)
(out/'README.md').write_text('''改良元: solutions/esw-slim

D2の設計段の拡張。穿孔処理は基準と同じ。
filler_climbとProbabilityHeadのフィラー効用を、列・色ごとの第1候補と第2候補の混合にする。
順位は頻度、次にフィラー効用。第2候補への確率はARGON_D2_HEAD_RATE（既定0.0625）。
Hungarianの効用の勾配にも同じ混合を入れ、全紙の効用を更新する。
保存出力の列頭の観測頻度を参考にした全ケース共通の定数で、未来の注文は読まない。

指標と予算スイッチは基準と同じ。proxy_before/afterとmatch_decreaseは混合目的の値になる。
既存ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を維持する。
検証の記録はsolutions/argon-des-perforation/REPORT.md。
''')
