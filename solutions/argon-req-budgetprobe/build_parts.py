from pathlib import Path
p=Path('solutions/argon-req-budgetparts')
assert not p.exists()
s=Path(__file__).with_name('main.cpp').read_text()
start=s.index('    Solver::SearchConfig budget_light =')
end=s.index('    double budget_base_sec =', start)
s=s[:start]+'''    Solver::SearchConfig budget_control = Solver::search_config();
    Solver::SearchConfig budget_rounds = budget_control;
    budget_rounds.rounds = 3;
    Solver::SearchConfig budget_plans = budget_control;
    budget_plans.post_candidates = 8;
    budget_plans.plan_shortlist = 0;
    Solver::SearchConfig budget_refine = budget_control;
    budget_refine.refine_best = 1;
    Solver::SearchConfig budget_triples = budget_control;
    budget_triples.triples = true;
    Solver::SearchConfig budget_interior = budget_control;
    budget_interior.interior = 4;
    Solver::SearchConfig budget_stop = budget_control;
    budget_stop.repeat_min = .05;
    const std::array<const Solver::SearchConfig*,7> budget_configs = {
        &budget_control,&budget_rounds,&budget_plans,&budget_refine,
        &budget_triples,&budget_interior,&budget_stop};
    std::array<double,7> budget_sec{}, budget_gain{}, budget_moves{};
    std::array<long long,7> budget_invalid{};
'''+s[end:]
s=s.replace('mode<3','mode<7')
p.mkdir()
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-des-perf-latew105

R5の予算別測定版。各注文の基準出力を保ち、同じ開始積層から7予算を解き直す。0は同じ基準（再実行の計時対照）、1は中立3周、2は追加計画8・短い計画への限定なし、3は最良計画再編集1回、4は3削除、5は内部深さ4、6は周回継続に0.05以上の利得を要求する。他の予算・目的関数は基準のまま。複数の重い機能をまとめた測定では時間効率の原因を分けられなかったため、個別に測る。

#budgetとbudget_<番号>_sec/gain/moves/invalidの意味・形式は../argon-req-budgetprobe/README.mdと同じ。出力・積層を必ず基準に戻す。全ての既存ログ・スイッチ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・目次・節を維持する。未来注文を読まない。

固定設計の時間超過測定専用。通常評価なら--no-recordを使う。
''')
