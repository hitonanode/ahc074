"""Writes a 2-second solver with the near-tie correction: solutions/legal-tie-merge (deval-helper-wide + the
merge rule) plus pooling of the complete plans of process() and the corrected final choice (tie_choice),
with the weights of tie_fit.py (--nolabels --out JSON).

Usage: python make_tie_solver.py WEIGHTS.json OUT_DIR [--margin M] [--gap G]
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "legal-tie-merge" / "main.cpp"
FEATS = ["fc", "nc", "gb", "nf", "nfb", "wtop", "wfill", "other", "len"]


def rep(src, old, new, count=1):
    n = src.count(old)
    assert n == count, (n, old[:90])
    return src.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("weights")
    ap.add_argument("out")
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--gap", type=float, default=None)
    args = ap.parse_args()
    wj = json.load(open(args.weights))
    coef = [wj["coef"].get(f, 0.0) for f in FEATS]
    const = wj["coef"].get("const", 0.0)
    gap = args.gap if args.gap is not None else wj["gap"]
    src = BASE.read_text()
    section = r'''    // ==== Near-tie correction of the final choice (tie_choice) ====

    // process() keeps the complete plans it evaluates (note: end state, moves, plan_cost; the lowest per end
    // order). At its end, the kept plans whose plan_cost is within kTieGap of the choice compete with it by
    // plan_cost plus a linear correction of end-state features, fitted on near-tie choices labelled by
    // rollouts of this policy (solutions/legal-roll/tie_fit.py, seeds 0-99 of the saved designs): the lowest
    // corrected difference below -kTieMargin wins. The features are the plan_cost terms (filler charge, next
    // cost, generic bias), the fillers (all, below the generic layer), the targets served by the lifted paper
    // and by the fillers, the demand of the other color at the column heads, and the plan length.
    static constexpr double kTieGap = @GAP@, kTieMargin = @MARGIN@, kTieConst = @CONST@;
    static constexpr std::array<double, 9> kTieCoef = {@COEF@};
    struct TieCand {
        State state;
        Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
        double value;
    };
    std::vector<TieCand> tie_pool;
    bool tie_pooling = false;
    double tie_min = 1e300;  // the lowest plan_cost noted in this request (the final choice is never above it)
    long long tie_decisions = 0, tie_switches = 0, tie_rejected = 0;
    void note(const Moves& path OP_TAG(, const std::vector<uint8_t>& tags), double value) {
        if (!tie_pooling || value >= tie_min + kTieGap) return;  // can never be within kTieGap of the choice
        tie_min = std::min(tie_min, value);
        for (auto& c : tie_pool)
            if (c.state.order == order) {
                if (value < c.value - 1e-9) c = {save(), path OP_TAG(, tags), value};
                return;
            }
        tie_pool.push_back({save(), path OP_TAG(, tags), value});
    }
    std::array<double, 9> tie_features(size_t len) const {
        GenericSplit split;
        split_generic(split);
        std::array<double, 9> f{};
        f[0] = filler_charge(split);
        f[1] = adaptive_next_cost(split);
        f[2] = generic_bias();
        f[3] = fillers.size();
        for (auto x : fillers) {
            f[4] += split.below(x.paper);
            f[6] += adaptive_weights[x.paper];
        }
        f[5] = top_d >= 0 ? adaptive_weights[top_d] : 0;
        std::array<int, 64> head;
        head.fill(-1);
        std::array<bool, K> extra{};
        if (top_d >= 0) extra[top_d] = true;
        for (auto x : fillers) extra[x.paper] = true;
        for (int k : order)
            if (col_of[k] >= 0 && !extra[k] && head[col_of[k]] < 0) head[col_of[k]] = paper[k].black >> handle[col_of[k]] & 1;
        for (int c = 0; c < H; c++)
            if (head[c] >= 0) f[7] += adaptive_holes[c][1 - head[c]];
        f[8] = len;
        return f;
    }
    Moves tie_choice(const State& st0, int u, Moves path OP_TAG(, std::vector<uint8_t>& tags)) {
        tie_pooling = false;
        const double v0 = plan_cost(path.size());
        bool any = false;
        for (const auto& c : tie_pool) any |= c.state.order != order && c.value - v0 < kTieGap;
        if (!any) return path;
        const State c0 = save();
        const auto f0 = tie_features(path.size());
        int best = -1;
        double bs = -kTieMargin;
        for (int i = 0; i < int(tie_pool.size()); i++) {
            const auto& c = tie_pool[i];
            if (c.state.order == c0.order || c.value - v0 >= kTieGap) continue;
            restore(c.state);
            const auto f = tie_features(c.path.size());
            double s = c.value - v0 + kTieConst;
            for (int j = 0; j < 9; j++) s += kTieCoef[j] * (f[j] - f0[j]);
            if (s < bs) bs = s, best = i;
        }
        tie_decisions++;
        if (best < 0) {
            restore(c0);
            return path;
        }
        const auto& c = tie_pool[best];
        // the plan once more by replay: visible papers, the end order kept, the display, fillers reachable
        bool ok = c.path.size() <= 2 * K;
        ByteOrder o = st0.order;
        for (auto [k, d] : c.path) {
            if (!ok) break;
            const int p = merge_find(o, k);
            if (!merge_visible(o, k, p)) ok = false;
            else shift_byte(o, p, d);
        }
        restore(c.state);
        if (!ok || o != order || display() != A[u] || !fillers_reachable()) {
            tie_rejected++;
            restore(c0);
            return path;
        }
        tie_switches++;
        OP_TAG(tags = c.tags;)
        return c.path;
    }

'''
    section = (section.replace("@GAP@", repr(float(gap))).replace("@MARGIN@", repr(float(args.margin)))
               .replace("@CONST@", repr(float(const))).replace("@COEF@", ", ".join(repr(float(x)) for x in coef)))
    src = rep(src, '''    // ==== Request processing (process) ====
''', section + '''    // ==== Request processing (process) ====
''')
    # pooling on for the real process (no copies run process here)
    src = rep(src, '''        init_adaptive();
        adaptive_request = u;
        const State st0 = save();''', '''        init_adaptive();
        adaptive_request = u;
        tie_pool.clear();
        tie_pooling = true;
        tie_min = 1e300;
        const State st0 = save();''')
    # the evaluation points of complete plans (as in solutions/legal-roll)
    src = rep(src, '''        const double next = plan_cost(path.size());
        const bool valid = display() == A[u] && fillers_reachable();
        value_seed_valid += valid;''', '''        const double next = plan_cost(path.size());
        const bool valid = display() == A[u] && fillers_reachable();
        if (valid) note(path OP_TAG(, tags), next);
        value_seed_valid += valid;''')
    src = rep(src, '''        auto chosen_path = post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));
''', '''        auto chosen_path = post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));
        note(chosen_path OP_TAG(, best_tags), plan_cost(chosen_path.size()));
''')
    src = rep(src, '''                post_candidate_calls++;
                double next = plan_cost(path.size());
''', '''                post_candidate_calls++;
                double next = plan_cost(path.size());
                note(path OP_TAG(, tags), next);
''')
    src = rep(src, '''        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);
''', '''        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);
        note(chosen_path OP_TAG(, best_tags), plan_cost(chosen_path.size()));
''')
    src = rep(src, '''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
''', '''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
                    note(path OP_TAG(, tags), value);
''')
    src = rep(src, '''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), cfg.plan_ejects);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
''', '''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), cfg.plan_ejects);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
                    note(path OP_TAG(, tags), value);
''')
    src = rep(src, '''                auto incumbent = save();
                double incumbent_value = plan_cost(chosen_path.size());
                if (incumbent_value < parent_value - 1e-9) {''', '''                auto incumbent = save();
                double incumbent_value = plan_cost(chosen_path.size());
                note(chosen_path OP_TAG(, best_tags), incumbent_value);
                if (incumbent_value < parent_value - 1e-9) {''')
    src = rep(src, '''                        const double value = plan_cost(path.size());
                        const bool better = value < incumbent_value - 1e-9;''', '''                        const double value = plan_cost(path.size());
                        note(path OP_TAG(, tags), value);
                        const bool better = value < incumbent_value - 1e-9;''')
    src = rep(src, '''                    incumbent_value = plan_cost(chosen_path.size());
                    f2_refine_saved += old_length - int(chosen_path.size());''', '''                    incumbent_value = plan_cost(chosen_path.size());
                    note(chosen_path OP_TAG(, best_tags), incumbent_value);
                    f2_refine_saved += old_length - int(chosen_path.size());''')
    src = rep(src, '''        merge_double_moves(st0, chosen_path OP_TAG(, op_tags));
        return chosen_path;''', '''        chosen_path = tie_choice(st0, u, std::move(chosen_path) OP_TAG(, op_tags));
        merge_double_moves(st0, chosen_path OP_TAG(, op_tags));
        return chosen_path;''')
    src = rep(src, '''    std::cerr << "merge_trials = " << solver.merge_trials''', '''    std::cerr << "tie_decisions = " << solver.tie_decisions << "\\ntie_switches = " << solver.tie_switches
              << "\\ntie_rejected = " << solver.tie_rejected << '\\n';
    std::cerr << "merge_trials = " << solver.merge_trials''')
    src = rep(src, '''//   Post-processing: a paper moved twice merged into one move (merge_double_moves)
//   Request processing (process)''', '''//   Post-processing: a paper moved twice merged into one move (merge_double_moves)
//   Near-tie correction of the final choice (tie_choice)
//   Request processing (process)''')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "main.cpp").write_text(src)
    print(f"wrote {out / 'main.cpp'}: gap {gap}, margin {args.margin}, const {const:.5f}, coef {coef}")


if __name__ == "__main__":
    main()
