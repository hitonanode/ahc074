from pathlib import Path
import sys
name=sys.argv[1]
base=sys.argv[2] if len(sys.argv)>2 else 'argon-req-filldp-positive'
p=Path('solutions')/name
assert p.is_dir()
s=Path('solutions',base,'main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n',
             '                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n',
             '              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n',
             '              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
    s=s.replace(line,'',1)
s=s.replace('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;',
            'long long value_filler_trials = 0;',1)
sub('''    long long post_alternate = 0, post_candidate_calls = 0, post_secondary_saved = 0;''','''    long long post_alternate = 0, post_candidate_calls = 0, post_secondary_saved = 0;
    long long reserve_added = 0, reserve_processed = 0, reserve_better = 0;
    double reserve_gain = 0;''')
sub('''            OP_TAG(std::vector<uint8_t> tags;)  // the labels of path
        };''','''            OP_TAG(std::vector<uint8_t> tags;)  // the labels of path
            bool reserved = false;
        };''')
sub('''        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;''','''        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates, reserved_candidates;''')
sub('''        auto record_future = [&](double cost) {
''','''        auto record_future = [&](double cost, bool extra = false) {
            if (!extra) collect_future(reserved_candidates, kPostCandidates, cost);
''')
condition = 'o.old_value != 0' if 'int old_value = 0;' in s else 'o.value_fillers'
sub('''            record_future(cost);
            if (cost < best)''',f'''            record_future(cost, {condition});
            if (cost < best)''')
sub('''        if (source == 1) chain_selected++, chain_papers += chain_count;''','''        // Preserve a distinct family that would have reached post-processing
        // without the new weighted plan. Existing families need no extra slot.
        for (auto& candidate : reserved_candidates) {
            const bool present = std::any_of(future_candidates.begin(), future_candidates.end(), [&](const auto& c) {
                return c.state.order == candidate.state.order || same_family(c.path, candidate.path);
            });
            if (present) continue;
            candidate.reserved = true;
            future_candidates.push_back(std::move(candidate));
            ++reserve_added;
        }
        std::sort(future_candidates.begin(), future_candidates.end(), by_cost);
        if (source == 1) chain_selected++, chain_papers += chain_count;''')
sub('''                double next = plan_cost(path.size());
                if (next < value - 1e-9)''','''                double next = plan_cost(path.size());
                if (candidate.reserved) {
                    ++reserve_processed;
                    if (next < value) ++reserve_better, reserve_gain += value - next;
                }
                if (next < value - 1e-9)''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "reserve_added = " << solver.reserve_added
              << "\\nreserve_processed = " << solver.reserve_processed
              << "\\nreserve_better = " << solver.reserve_better
              << "\\nreserve_gain = " << solver.reserve_gain << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(f'''改良元: solutions/{base}

R2の後処理候補の押し出しを検証する。追加の状態価値DPがない場合の上位候補を別にも記録し、追加後の上位候補から消えた異なる操作紙の系列だけ後処理に戻す。同じ最終積層または同じ操作紙の系列が既にある場合は追加しない。後処理する候補数が増えた場合の費用を測る。

設計・目的関数・既存スイッチ・分析ログ・プロファイラを維持する。基準の常に0のvalue_filler_zero/value_filler_zero_usefulだけはユーザー指示に従い削除。

reserve_added/processed/better/gainは救い戻した初期候補の数、後処理した数、後処理時の最良値を改善した数、その評価値改善の和。新規環境変数はない。
''')
