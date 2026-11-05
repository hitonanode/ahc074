from pathlib import Path
p=Path('solutions/argon-req-completevalue-v2');s=p.joinpath('main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
start=s.index('    long long complete_value_calls =')
end=s.index('    void run_joint(int u, const PlanOpt& opt)',start)
s=s[:start]+s[end:]
sub('''    double filler_value_increment(int c, int depth, int level, double before) {''','''    long long complete_value_calls = 0, complete_value_invalid = 0, complete_value_plans = 0;
    // With request >= 0, compare complete local plans: include the extraction
    // moves and fix the holes left uncovered. c == -1 gives the no-filler reference.
    double filler_value_increment(int c, int depth, int level, double before,
                                  int request = -1, u64 holes = 0) {''')
sub('''        u64 hh = 0;
        place_filler(c, depth, level, hh);
        const double delta = invalid ? 1e30 : plan_cost(0) - before;''','''        u64 hh = holes;
        if (c >= 0) place_filler(c, depth, level, hh);
        if (request >= 0) {
            if (!invalid) fix_handles(request, hh);
            ++complete_value_calls;
            complete_value_invalid += invalid;
        }
        const double delta = invalid ? 1e30 : plan_cost(request < 0 ? 0 : ops.size() - nops) - before;''')
sub('''opt.complete_value ? completed_filler_cost(u, hh) : 1e30''','''opt.complete_value ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30''')
sub('''gain = completed_reference - completed_filler_cost(u, hh, c, depth, lv);''','''gain = -filler_value_increment(c, depth, lv, completed_reference, u, hh);''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+'''\n仮配置の保存・復元は既存のfiller_value_incrementへ統合し、重複した処理を増やさない。追加の引数がない従来の呼び出しは、従来どおり抽出直後の将来価値差だけを返す。\n''')
