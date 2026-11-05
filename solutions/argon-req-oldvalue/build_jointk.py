from pathlib import Path
import sys
name=sys.argv[1];width=int(sys.argv[2]);p=Path('solutions')/name;p.mkdir()
s=Path('solutions/argon-req-filldp-positive/main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n','                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n','              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n','              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
 sub(line,'')
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;','long long value_filler_trials = 0;')
sub('        bool value_fillers = false;  // joint DP also tries the marginal stack value','        bool value_fillers = false;  // joint DP also tries the marginal stack value\n        int joint_rank = 0;')
sub('    void run_joint(int u, const PlanOpt& opt) {','''    std::vector<std::vector<Cand>> joint_choices;
    long long joint_extra_plans = 0, joint_extra_better = 0;
    double joint_extra_gain = 0;
    // Keep alternatives with different sets of filler papers. Levels of the same
    // paper set are optimized by the same interval recurrence, rather than taking
    // several nearby levels as separate plans.
    template<class PaperId>
    void joint_alternatives(const std::vector<std::vector<Cand>>& candidates, PaperId paper_id,
                            const std::vector<Cand>& primary) {
        struct Choice { double gain = 0; std::array<u64, 3> papers{}; std::vector<Cand> picks; };
        std::vector<std::vector<Choice>> best(H + 1);
        best[0].push_back({});
        for (int c = 0; c < H; ++c) {
            auto& list = best[c + 1];
            list = best[c];
            for (const auto& cd : candidates[c]) for (const auto& prefix : best[cd.lvl]) {
                Choice q = prefix;
                const int paper = paper_id(cd);
                q.papers[paper >> 6] |= u64(1) << (paper & 63);
                q.gain += cd.gain;
                q.picks.push_back(cd);
                bool found = false;
                for (auto& old : list) if (old.papers == q.papers) {
                    if (q.gain > old.gain + 1e-9) old = std::move(q);
                    found = true;
                    break;
                }
                if (!found) list.push_back(std::move(q));
                std::stable_sort(list.begin(), list.end(), [](const auto& a, const auto& b) { return a.gain > b.gain; });
                if (list.size() > WIDTH) list.resize(WIDTH);
            }
        }
        std::array<u64, 3> primary_papers{};
        for (const auto& cd : primary) {
            const int paper = paper_id(cd);
            primary_papers[paper >> 6] |= u64(1) << (paper & 63);
        }
        joint_choices = {primary};
        for (auto& q : best[H]) if (q.papers != primary_papers && joint_choices.size() < WIDTH) {
            std::reverse(q.picks.begin(), q.picks.end());
            joint_choices.push_back(std::move(q.picks));
        }
    }
    void run_joint(int u, const PlanOpt& opt) {'''.replace('WIDTH',str(width)))
# Cache the same candidate generation; alternate ranks all start at the identical request state.
sub('''        auto& cand = fresh_candidates();
        auto mism_level''','''        std::vector<Cand> picks;
        if (opt.joint_rank) {
            if (opt.joint_rank >= int(joint_choices.size())) { invalid = true; return; }
            picks = joint_choices[opt.joint_rank];
        } else {
        auto& cand = fresh_candidates();
        auto mism_level''')
sub('''        const auto picks = best_intervals(cand);
        std::vector<int> old_dec''','''        picks = best_intervals(cand);
        if (opt.value_fillers) joint_alternatives(cand, [&](const Cand& cd) {
            return cd.kind == 0 ? cd.idx : cd.kind == 3 ? x0 : olds[cd.idx].paper;
        }, picks);
        }
        std::vector<int> old_dec''')
sub('''        if (d != top0) opts.push_back({1, 5, true, true});''',f'''        if (d != top0) opts.push_back({{1, 5, true, true}});
        if (d != top0) for (int rank = 1; rank < {width}; ++rank) opts.push_back({{1, 5, true, true, rank}});''')
sub('q.opt.value_fillers == o.value_fillers) { repeated = &q; break; }','q.opt.value_fillers == o.value_fillers && q.opt.joint_rank == o.joint_rank) { repeated = &q; break; }')
sub('''            record_future(cost);
            if (cost < best)''','''            if (o.joint_rank) {
                ++joint_extra_plans;
                if (cost < best) ++joint_extra_better, joint_extra_gain += best - cost;
            }
            record_future(cost);
            if (cost < best)''')
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    std::cerr << "joint_extra_plans = " << solver.joint_extra_plans
              << "\\njoint_extra_better = " << solver.joint_extra_better
              << "\\njoint_extra_gain = " << solver.joint_extra_gain << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/argon-req-filldp-positive

R2の追加検証。状態価値付き共同DPの区間重みは局所差の和なので、最上位だけでなく、選ぶ紙の集合が異なる上位{width}解を作る。紙の集合が同じで配置レベルだけが違う候補は各DP位置で最良のものにまとめる。従来の最上位はそのまま残し、他の全初期計画・後処理予算も変えない。追加の共同計画には計算済みの区間集合を使い、仮配置の価値計算を繰り返さない。

各計画は従来の可視性・表示・回収可能性を検査し、完成値は従来のplan_costで選ぶ。将来の注文を参照しない。joint_extra_plans/better/gainは有効な追加計画の数、既存の最良初期値を改善した数、その改善合計。

既存のログ・スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulだけを削除する。新しい環境変数はない。
''')
