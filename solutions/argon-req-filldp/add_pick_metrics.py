from pathlib import Path
import sys
p=Path('solutions')/sys.argv[1]
s=p.joinpath('main.cpp').read_text()
s=s.replace('''        bool post = false;
    };
    // Weighted interval scheduling''','''        bool post = false;
        bool zero_gain = false;  // a new filler with no immediate move saving
    };
    // Weighted interval scheduling''',1)
s=s.replace('''    long long value_filler_plans = 0, value_filler_better = 0;''','''    long long value_filler_plans = 0, value_filler_better = 0;
    long long value_filler_zero_picks = 0, value_filler_zero_better = 0;
    bool value_filler_has_zero = false;''',1)
s=s.replace('''cand[c].push_back({lv, gain, c, 0, 0, f, post});''','''cand[c].push_back({lv, gain, c, 0, 0, f, post, raw_gain == 0});''',1)
s=s.replace('''        const auto picks = best_intervals(cand);
        std::vector<int> old_dec''','''        const auto picks = best_intervals(cand);
        if (opt.value_fillers) {
            const int zeros = std::count_if(picks.begin(), picks.end(), [](const Cand& x) { return x.zero_gain; });
            value_filler_zero_picks += zeros;
            value_filler_has_zero = zeros > 0;
        }
        std::vector<int> old_dec''',1)
s=s.replace('''                if (cost < best) ++value_filler_better, value_filler_gain += best - cost;''','''                if (cost < best) {
                    ++value_filler_better;
                    value_filler_zero_better += value_filler_has_zero;
                    value_filler_gain += best - cost;
                }''',1)
s=s.replace('''              << "\\nvalue_filler_plans = " << solver.value_filler_plans''','''              << "\\nvalue_filler_zero_picks = " << solver.value_filler_zero_picks
              << "\\nvalue_filler_zero_better = " << solver.value_filler_zero_better
              << "\\nvalue_filler_plans = " << solver.value_filler_plans''',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+'''
`value_filler_zero_picks` は追加DPが選んだ即時利得0の新規フィラー数、`value_filler_zero_better` はそのような紙を含み、最良の既存初期計画より良くなった追加計画数。
''')
