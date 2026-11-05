"""Reproduce D2 changes from the current esw-slim base, without editing it."""
from pathlib import Path
here=Path(__file__).resolve().parent
source=(here.parent/'esw-slim/main.cpp').read_text()
start=source.index('struct Perforation {');end=source.index('// ==== Design state:',start)
s=source[start:end]
def replace(old,new):
    global s
    assert old in s,old[:100]
    s=s.replace(old,new)

replace('    int trials = 0, accepted = 0;', '''    int trials = 0, accepted = 0;
    bool wide = false;
    int secondary_trials = 0, secondary_viable = 0, secondary_accepted = 0;
    double secondary_cost = 0, secondary_profit = 0;
    std::array<std::vector<int>, 128> ranked;
    std::vector<std::array<int, 128>> sample_head;
    std::vector<double> exposure;
    // The same-color runner-up can be exposed by a dig or by taking the usual head out.
    // Its probability is deliberately separate from the handle's color probability.
    double secondary_rate = env_real("ARGON_D2_RATE", 0.125);
    int secondary_width = std::max(2, int(env_real("ARGON_D2_WIDTH", 2)));

    void prepare_secondary() {
        for (int k = kFirst; k < K; ++k) {
            utility[k] = 0;
            for (int u = 0; u < P; ++u) utility[k] += gain(u, k);
            const int c = columns[k], b = int(colors[k] >> c & 1);
            ranked[2*c+b].push_back(k);
        }
        for (int c = 0; c < H; ++c) for (int b = 0; b < 2; ++b) {
            auto& list = ranked[2*c+b];
            std::stable_sort(list.begin(), list.end(), [&](int a, int z) {
                if (a == heads[c][b] || z == heads[c][b]) return a == heads[c][b] && z != heads[c][b];
                if (frequency[a] != frequency[z]) return frequency[a] > frequency[z];
                return utility[a] > utility[z];
            });
            if (int(list.size()) > secondary_width) list.resize(secondary_width);
        }
    }
    void enable_secondary() {
        wide = true;
        exposure.assign(K, 0);
        std::mt19937_64 random(0xa279ba31ULL);
        sample_head.resize(P * kSamples);
        for (int c = 0; c < H; ++c) for (int b = 0; b < 2; ++b) {
            const auto& list = ranked[2*c+b];
            double rate = list.size() > 1 ? secondary_rate : 0;
            exposure[list[0]] = 1 - rate;
            for (int j = 1; j < int(list.size()); ++j) exposure[list[j]] = rate / (list.size()-1);
            for (auto& row : sample_head) {
                const double x = (random() >> 11) * 0x1.0p-53;
                int j = x < 1-rate ? 0 : 1 + std::min(int(list.size())-2, int((x-(1-rate))/rate*(list.size()-1)));
                row[2*c+b] = list[j];
            }
        }
        rebuild();
    }
    int sampled_head(int sample, int c, int b) const {
        return wide ? sample_head[sample][2*c+b] : heads[c][b];
    }
''')
replace('        for (int c = 0; c < H; c++)\n            for (int b = 0; b < 2; b++) sum += probability[c][b] * utility[heads[c][b]];', '''        if (wide) {
            for (int k : donors) sum += probability[columns[k]][colors[k] >> columns[k] & 1] * exposure[k] * utility[k];
        } else {
            for (int c = 0; c < H; c++)
                for (int b = 0; b < 2; b++) sum += probability[c][b] * utility[heads[c][b]];
        }''')
replace('u64 edge_column(int u, u64 color, int c, std::array<double, 65>& edge) const',
        'u64 edge_column(int u, u64 color, int c, std::array<double, 65>& edge, int sample) const')
replace('            int k = heads[c][b];\n            assert(k >= 0);','            int k = sampled_head(sample, c, b);\n            assert(k >= 0);')
replace('    Edges make_edges(int u, u64 color) const {','    Edges make_edges(int u, u64 color, int sample) const {')
replace('edge_column(u, color, c, edges[c])','edge_column(u, color, c, edges[c], sample)')
replace('make_edges(u, samples[i])','make_edges(u, samples[i], i)')
replace('edge_column(u, samples[i], c, edge)','edge_column(u, samples[i], c, edge, i)')
replace('''            for (int b = 0; b < 2; b++)
                same[u] = same[u] && (signature(heads[c][b], opacity) == signature(heads[c][b], cache_opacity));''', '''            if (wide) {
                for (int b = 0; b < 2; ++b) for (int y : ranked[2*c+b])
                    same[u] = same[u] && (signature(y, opacity) == signature(y, cache_opacity));
            } else {
                for (int b = 0; b < 2; b++)
                    same[u] = same[u] && (signature(heads[c][b], opacity) == signature(heads[c][b], cache_opacity));
            }''')
replace('''            if (heads.empty() ? frequency[k] != max_frequency[c][b] : k != heads[c][b]) continue;''', '''            if (wide ? exposure[k] == 0 : (heads.empty() ? frequency[k] != max_frequency[c][b] : k != heads[c][b])) continue;''')
replace('''            if (k == heads[columns[k]][colors[k] >> columns[k] & 1]) donors.push_back(k);''', '''            if (wide ? exposure[k] > 0 : k == heads[columns[k]][colors[k] >> columns[k] & 1]) donors.push_back(k);''')
replace('''            if (k != heads[c][b]) continue;
            for (u64 bits''','''            if (wide ? (exposure[k] == 0 || k == heads[c][b]) : k != heads[c][b]) continue;
            for (u64 bits''')
replace('''            trials++;
            const u64 bit''','''            trials++;
            if (wide) ++secondary_trials;
            const u64 bit''')
replace('''            const double next = viable ? total_profit(k) : profit;''','''            if (wide && viable) ++secondary_viable;
            const double next = viable ? total_profit(k) : profit;''')
replace('''                hole_cost += delta;
                profit = next;''','''                if (wide) {
                    ++secondary_accepted;
                    secondary_cost += delta;
                    secondary_profit += next - profit;
                }
                hole_cost += delta;
                profit = next;''')
source=source[:start]+s+source[end:]
old='''    Perforation perforation(solver);
    perforation.run(0.5);
    perforation.install();'''
new='''    Perforation perforation(solver);
    perforation.prepare_secondary();
    perforation.run(0.5);
    const double d2_start = elapsed_sec();
    perforation.enable_secondary();
    perforation.run(0.5);
    std::cerr << "d2_trials = " << perforation.secondary_trials
              << "\\nd2_viable = " << perforation.secondary_viable
              << "\\nd2_accepted = " << perforation.secondary_accepted
              << "\\nd2_cost_delta = " << perforation.secondary_cost / P
              << "\\nd2_profit_delta = " << perforation.secondary_profit / P
              << "\\nd2_sec = " << elapsed_sec() - d2_start << '\\n';
    perforation.install();'''
assert old in source;source=source.replace(old,new)
(here/'main.cpp').write_text(source)
