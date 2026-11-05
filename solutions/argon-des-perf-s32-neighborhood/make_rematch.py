"""Reassign targets after perforation, explicitly accounting for existing extra holes."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
base = (root/'argon-req-filterblocks-v2/main.cpp').read_text()
start = base.index('struct ProbabilityHead {')
end = base.index('// ==== Helper tables:', start)
s = base[start:end]

def replace(old, new):
    global s
    assert old in s, old[:120]
    s = s.replace(old, new)

replace('''    double last_value = 0;
    ProbabilityHead(Design& design, double strength_)''', '''    double last_value = 0;
    const std::vector<u64>* extra;
    std::vector<std::array<int, 2>> extended_counts;
    ProbabilityHead(Design& design, double strength_, const std::vector<u64>* extra_ = nullptr)''')
replace('''          strength(strength_) {''', '''          strength(strength_),
          extra(extra_) {''')
replace('''    void update_probability() {
        for (int c = 0; c < d.H; c++)
            prob[c] = Design::head_probability(d.hn[c][0], d.hn[c][1], strength * d.nt[c]);''', '''    u64 extra_holes(int slot) const { return extra && slot >= 0 ? (*extra)[slot] : 0; }
    const std::vector<std::array<int, 2>>& hole_counts() const { return extra ? extended_counts : d.hn; }
    double model_cost() const {
        double value = d.cur;
        if (extra) for (int c = 0; c < d.H; ++c)
            value += Design::hole_cost_of(extended_counts[c][0], extended_counts[c][1], d.reset_targets[c]) - d.hcost(c);
        return value;
    }
    void update_probability() {
        if (extra) {
            extended_counts = d.hn;
            for (int x = 0; x < d.U; ++x) {
                const auto& u = d.unit[x];
                const u64 added = (*extra)[x] & ~d.holes(u);
                for (u64 z = added; z; z &= z - 1) {
                    const int h = __builtin_ctzll(z);
                    ++extended_counts[h][d.hb[u.a] >> h & 1];
                    if (u.b >= 0) ++extended_counts[h][d.hb[u.b] >> h & 1];
                }
            }
        }
        const auto& counts = hole_counts();
        for (int c = 0; c < d.H; c++)
            prob[c] = Design::head_probability(counts[c][0], counts[c][1], strength * d.nt[c]);''')
replace('''low_bits(c + 1) & ~diff[y] & d.holes(target), wrong''',
        '''low_bits(c + 1) & ~diff[y] & (d.holes(target) | extra_holes(d.owner[t])), wrong''')
replace('''double donor(const Design::Unit& u) const''', '''double donor(const Design::Unit& u, int slot = -1) const''')
replace('''        u64 dy = u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0;
        for (int t''', '''        u64 dy = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(slot);
        for (int t''')
replace('''double target(int t, const Design::Unit& u) const''', '''double target(int t, const Design::Unit& u, int slot = -1) const''')
replace('''        u64 dx = u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0;''',
        '''        u64 dx = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(slot);''')
replace('''            diff[x] = u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0;''',
        '''            diff[x] = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(x);''')
replace('''? donor(u) : 0;''', '''? donor(u, x) : 0;''')
replace('''MatchStats rematch_probability(Design& d, int iterations, double weight, double strength)''',
        '''MatchStats rematch_probability(Design& d, int iterations, double weight, double strength,
                               const std::vector<u64>* extra = nullptr)''')
replace('''    ProbabilityHead head(d, strength);
    double initial = d.cur - weight * head.last_value, merit = initial;''',
        '''    ProbabilityHead head(d, strength, extra);
    double initial = head.model_cost() - weight * head.last_value, merit = initial;''')
replace('''        std::vector<std::array<double, 2>> gradient(d.H);
        for''', '''        std::vector<std::array<double, 2>> gradient(d.H);
        const auto& counts = head.hole_counts();
        for''')
replace('''double x = d.hn[j][0], y = d.hn[j][1]''', '''double x = counts[j][0], y = counts[j][1]''')
replace('''d.hn[j][0] + d.hn[j][1] + strength * d.nt[j]''', '''counts[j][0] + counts[j][1] + strength * d.nt[j]''')
replace('''                    profit = head.target(a, u) + head.target(b, u);
                    if (head.beta[i]) profit += head.beta[i] * head.donor(u);''',
        '''                    for (u64 z = head.extra_holes(i) & ~(d.hb[a] ^ d.hb[b]); z; z &= z - 1) {
                        const int h = __builtin_ctzll(z);
                        v += 2 * gradient[h][d.hb[b] >> h & 1];
                    }
                    profit = head.target(a, u, i) + head.target(b, u, i);
                    if (head.beta[i]) profit += head.beta[i] * head.donor(u, i);''')
old = '''                    auto& target_profit = single_target[b][c];
                    if (target_profit < 0) target_profit = head.target(b, {b, -1, c});
                    profit = target_profit;
                    if (head.beta[i]) {
                        auto& value = single_donor[b][c];
                        if (value < 0) value = head.donor(u);
                        profit += head.beta[i] * value;
                    }'''
new = '''                    if (head.extra_holes(i)) {
                        for (u64 z = head.extra_holes(i); z; z &= z - 1) {
                            const int h = __builtin_ctzll(z);
                            v += gradient[h][d.hb[b] >> h & 1];
                        }
                        profit = head.target(b, u, i);
                        if (head.beta[i]) profit += head.beta[i] * head.donor(u, i);
                    } else {
                        auto& target_profit = single_target[b][c];
                        if (target_profit < 0) target_profit = head.target(b, {b, -1, c});
                        profit = target_profit;
                        if (head.beta[i]) {
                            auto& value = single_donor[b][c];
                            if (value < 0) value = head.donor(u);
                            profit += head.beta[i] * value;
                        }
                    }'''
replace(old, new)
replace('''            double next = d.cur - weight * head.rebuild();''',
        '''            const double head_value = head.rebuild();
            double next = head.model_cost() - weight * head_value;''')
source = base[:start] + s + base[end:]

marker = 'design_papers: perforation-aware reassignment'
assert source.count('design_papers: handle perforation') == 2
source = source.replace('//   design_papers: handle perforation\n',
                        '//   design_papers: handle perforation\n//   ' + marker + '\n')
assert marker in source[:source.index('// ==== Common:')], 'TOC format changed'
needle = '''    else perforate.template operator()<64>();
    return state;'''
assert source.count(needle) == 1
stage = '''    else perforate.template operator()<64>();

    // ==== design_papers: perforation-aware reassignment ====

    // Extra holes stay attached to physical paper slots. The Hungarian step can
    // change the targets, so their colors, natural pair holes and head probabilities
    // must all be evaluated again. Columns and each slot's own handle stay fixed.
    const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", 1));
    if (late_iterations > 0) {
        const double late_start = elapsed_sec();
        std::vector<u64> extra(des->U);
        std::vector<int> slot_paper(des->U);
        for (int x = 0; x < des->U; ++x) {
            const auto& u = des->unit[x];
            const int k = slot_paper[x] = state.ded[u.a];
            extra[x] = low_bits(des->H) & ~des->holes(u) & ~solver.h_opq[k];
            assert(!(extra[x] & ~low_bits(u.c)));
        }
        const auto late = rematch_probability(*des, late_iterations, LATE_WEIGHT, 2.0, &extra);
        int remaining = 0;
        for (int x = 0; x < des->U; ++x) {
            const auto& u = des->unit[x];
            const int k = slot_paper[x];
            assert(state.columns[k] == u.c);
            u64 mask = low_bits(G) | kCapBit;
            for (int c = 0; c <= u.c; ++c) mask |= u64(1) << des->handle[c];
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            mask |= kCapBit;
            for (u64 z = extra[x]; z; z &= z - 1) mask &= ~(u64(1) << des->handle[__builtin_ctzll(z)]);
            u64 black = A[u.a] & mask;
            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;
            state.papers[k] = {mask, black};
            state.ded[u.a] = k;
            if (u.b >= 0) state.ded[u.b] = k;
            remaining += __builtin_popcountll(extra[x] & ~des->holes(u));
        }
        std::cerr << "d2_rematch_iterations = " << late.iterations
                  << "\\nd2_rematch_cycles = " << late.accepted_cycles
                  << "\\nd2_rematch_changed = " << late.changed
                  << "\\nd2_rematch_decrease = " << late.decrease
                  << "\\nd2_extra_remaining = " << remaining
                  << "\\nd2_rematch_sec = " << elapsed_sec() - late_start
                  << "\\nd2_rematch_end_sec = " << elapsed_sec() << '\\n';
    }
    return state;'''
for name, weight in [('rematch', '1.0'), ('rematchhalf', '0.5')]:
    out = root/f'argon-des-perf-{name}'
    out.mkdir()
    (out/'main.cpp').write_text(source.replace(needle, stage.replace('LATE_WEIGHT', weight)))
    (out/'README.md').write_text(f'''改良元: solutions/argon-req-filterblocks-v2

通常の穿孔を終えた紙に対し、追加穴を紙の位置に固定してHungarianによる目標再割当を行う。
追加穴の実際の色別需要を穴コスト・頭の色確率に入れ、フィラーの模様にも含める。
再割当で新しいペアが自然に同じ穴を持つ場合は二重に数えない。追加穴はその紙自身の
ハンドルより上だけなので、列と自身のハンドルは保持できる。ペアの汎用層整合も従来どおり。
列・窓割当は変更しない。再割当後の所有目標で紙を印刷し直す。未来の注文は読まない。

追加段のフィラー係数は{weight}。ARGON_D2_LATE_ITERSは追加Hungarian回数（既定1、0で同一性確認）。
元のHungarianは追加穴なしの従来モデルのまま。元のmodel/proxy/perforation指標は追加段の前。
d2_rematch_*は追加段の回数・受理cycle・変更unit数・モデル改善・時間、
d2_extra_remainingは自然なペア穴と重複しない追加穴数。
ログ・@paper/@ops・プロファイラ・予算スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStoreを保持。
新しい段の目印と目次項目design_papers: perforation-aware reassignmentを加える。
''')
