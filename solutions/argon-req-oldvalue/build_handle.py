from pathlib import Path
p=Path('solutions/argon-req-handlevalue')
s=Path('solutions/argon-req-filldp-positive/main.cpp').read_text()
def sub(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b,1)
for line in ['                        value_filler_zero += raw_gain == 0;\n',
             '                        value_filler_zero_useful += raw_gain == 0 && gain > 0;\n',
             '              << "\\nvalue_filler_zero = " << solver.value_filler_zero\n',
             '              << "\\nvalue_filler_zero_useful = " << solver.value_filler_zero_useful\n']:
    sub(line,'')
sub('long long value_filler_trials = 0, value_filler_zero = 0, value_filler_zero_useful = 0;',
    'long long value_filler_trials = 0;')
sub('''    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {
        auto fix''','''    bool value_handles = false;
    long long value_handle_intervals = 0, value_handle_plans = 0;
    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) {
        const double before = value_handles ? plan_cost(0) : 0;
        auto fix''')
sub('''                int gain = save - kFillerCost - depth;
                if (gain > 0) cand[c].push_back({lvl, (double)gain, c, depth});''','''                double gain = save - kFillerCost - depth;
                if (value_handles && gain > 0) {
                    ++value_handle_intervals;
                    gain -= filler_value_increment(c, depth, lvl, before);
                }
                if (gain > 0) cand[c].push_back({lvl, gain, c, depth});''')
sub('''            keep(plan_cost(ops.size()));
        };
        for (const auto& item : pair_picks) {''','''            value_handle_plans += value_handles;
            keep(plan_cost(ops.size()));
        };
        for (const auto& item : pair_picks) for (int variant = 0; variant < 2; variant++) {
            value_handles = variant;''')
sub('''        for (const auto& item : picks) {
            restore(clean);''','''        for (const auto& item : picks) for (int variant = 0; variant < 2; variant++) {
            value_handles = variant;
            restore(clean);''')
sub('''            run_interleave(u, item.second);
            finish();
        }
    }''','''            run_interleave(u, item.second);
            finish();
        }
        value_handles = false;
    }''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "value_handle_intervals = " << solver.value_handle_intervals
              << "\\nvalue_handle_plans = " << solver.value_handle_plans << '\\n';
''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text('''改良元: solutions/argon-req-filldp-positive

R2の継続検証。ヘルパー配置後のハンドル修正DPにも、新規フィラー抽出後の状態価値を使う計画を追加する。元のヘルパー計画を保ち、その各配置について重み付きDPでも完成まで実行する。即時利得1以上の閾値、設計、目的関数、後処理の予算は変えない。

既存スイッチ・ログ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは指示に従って削除する。新規環境変数はない。

value_handle_intervalsは状態価値を評価したフィラー区間数、value_handle_plansは有効な追加ヘルパー計画数。両方とも後処理前の数。
''')
