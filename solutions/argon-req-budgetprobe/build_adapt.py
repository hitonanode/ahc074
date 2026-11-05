from pathlib import Path
p=Path('solutions/argon-req-budget-adapt');assert not p.exists()
s=Path('solutions/argon-des-perf-latew105/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b,1)
sub('''    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return config;
    }''','''    inline static const SearchConfig* request_budget = nullptr;
    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return request_budget ? *request_budget : config;
    }
    // Default budgets remain overridable by the existing F3_* experiment switches.
    static bool adaptive_budget() {
        static const bool enabled = [] {
            const char* s = std::getenv("ARGON_ADAPT");
            return !s || std::atoi(s) != 0;
        }();
        return enabled && search_config().mode == 1;
    }
    inline static long long budget_requests = 0, budget_triples = 0;''')
sub('''        CF_SCOPE(process);
        post_context.ready = false;''','''        CF_SCOPE(process);
        SearchConfig budget = search_config();
        const bool adapt = adaptive_budget();
        if (adapt) {
            static const bool default_plans = !search_env("POST_CANDIDATES");
            static const bool default_shortlist = !search_env("PLAN_SHORTLIST");
            static const bool default_repeat = !search_env("REPEAT_MIN");
            if (default_plans) budget.post_candidates = 4;
            if (default_shortlist) budget.plan_shortlist = 0;
            if (default_repeat) budget.repeat_min = .05;
            ++budget_requests;
        }
        request_budget = &budget;
        struct BudgetReset { ~BudgetReset() { request_budget = nullptr; } } budget_reset;
        post_context.ready = false;''')
sub('''        if (neutral_enabled) {
            const auto& cfg = search_config();''','''        if (neutral_enabled) {
            // Long edit paths make triples costly; use the common ordinary result,
            // known before the extra-plan and neutral stages, to choose this budget.
            static const bool default_triples = !search_env("NS_TRIPLES");
            if (adapt && default_triples) budget.triples = chosen_path.size() <= 11;
            budget_triples += adapt && budget.triples;
            const auto& cfg = search_config();''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "budget_requests = " << Solver::budget_requests << '\\n'
              << "budget_triples = " << Solver::budget_triples << '\\n';
''')
p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-des-perf-latew105

R5の探索時間配分。1周の評価改善が0.05未満なら中立探索を打ち切り、その時間を追加計画4本（短い経路だけに限定しない）と3削除へ回す。3削除は通常の編集・eject終了時の経路が11手以下の注文だけに使う。測定では長い経路の3削除は時間に比べて利得が小さかったため。目的関数、設計、候補生成器、他の予算は変更しない。時計・未来注文を探索判断に使わない。

ARGON_ADAPT=0で新しい配分を無効にする。MODE=0/2のプリセットは従来通り。F3_POST_CANDIDATES、F3_PLAN_SHORTLIST、F3_REPEAT_MIN、F3_NS_TRIPLESを明示した場合は個別指定を優先し、他のF3_*、全てのログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・節と目次も維持する。

追加指標budget_requestsは新配分の注文数、budget_triplesはそのうち3削除を有効にした注文数。既存指標は従来の意味を保つ。
''')
