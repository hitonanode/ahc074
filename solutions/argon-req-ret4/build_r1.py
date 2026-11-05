from pathlib import Path
base=Path('solutions/esw-slim/main.cpp').read_text()
s=base
s=s.replace('    struct PlanOpt {', '''    // ARGON_R1_PROBE=1 measures extra keep plans without selecting them.
#ifndef ARGON_R1_PROBE
#define ARGON_R1_PROBE 0
#endif
#ifndef ARGON_R1_NEW_ONLY
#define ARGON_R1_NEW_ONLY 0
#endif
    long long r1_requests = 0, r1_previous = 0, r1_generic_ok = 0, r1_color_ok = 0, r1_new_gate = 0;
    long long r1_trials = 0, r1_legal = 0, r1_valid = 0, r1_valid_requests = 0;
    long long r1_new_states = 0, r1_new_requests = 0, r1_better_requests = 0, r1_base_keep_requests = 0;
    long long r1_selected = 0, r1_extension_valid = 0, r1_extension_better = 0;
    double r1_raw_gain = 0;
    bool can_keep_previous(int u) const {
        const int d = ded[u];
        return top_d >= 0 && d >= 0 && top_d != d &&
               !(~paper[d].opaque & paper[top_d].opaque & (paper[top_d].black ^ A[u]));
    }
    struct PlanOpt {''',1)
s=s.replace('''        u64 pre_cov = 0;
        if (top_d >= 0 && opt.ret_mode == 3) {''','''        u64 pre_cov = 0;
        if (opt.ret_mode == 4) {
            if (!can_keep_previous(u)) {
                invalid = true;
                return;
            }
            const int kept = top_d;
            const auto olds = fillers;
            top_d = -1;
            // Register it before returning other fillers, so it is never treated as in-column.
            fillers.push_back({kept, 0, col_of[kept]});
            pre_cov = paper[kept].opaque & ~paper[ded[u]].opaque & (gmask | hmask);
            if (opt.fret_mode == 4) {
                std::vector<Filler> placed;
                refill_or_return(u, olds, pre_cov, placed);
                for (const auto& f : placed) fillers.push_back(f);
            } else {
                return_visible_fillers(olds, u, opt.fret_mode);
            }
            run_plan_tail(u, opt, pre_cov);
            return;
        }
        if (top_d >= 0 && opt.ret_mode == 3) {''',1)
s=s.replace('''        set_generic(u, holes);
        u64 hh = holes & ~gmask & ~pre_cov;''','''        // pre_cov normally contains handles; keep plans also cover correct generic holes.
        set_generic(u, holes & ~pre_cov);
        u64 hh = holes & ~gmask & ~pre_cov;''',1)
s=s.replace('''        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
''','''        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
        ++r1_requests;
        const bool r1_color_safe = can_keep_previous(u);
        const bool r1_extension = r1_color_safe && (gmask & ~paper[d].opaque & paper[top0].opaque);
        const bool r1_eligible = r1_color_safe && (!ARGON_R1_NEW_ONLY || r1_extension);
        if (prev_ok) {
            ++r1_previous;
            const u64 covered = ~paper[d].opaque & paper[top0].opaque;
            r1_generic_ok += !(covered & gmask & (paper[top0].black ^ A[u]));
            r1_color_ok += r1_color_safe;
            r1_new_gate += r1_extension;
        }
#if ARGON_R1_PROBE
        std::vector<std::array<uint8_t, K>> r1_base_orders;
        bool r1_base_kept = false;
#endif
''',1)
s=s.replace('''        auto record_future = [&](double cost) {
''','''        auto record_future = [&](double cost) {
#if ARGON_R1_PROBE
            if (r1_eligible) {
                r1_base_orders.push_back(order);
                r1_base_kept |= is_filler(top0) && index_of(top0) < generic_bottom();
            }
#endif
''',1)
needle='''        if (source == 1) chain_selected++, chain_papers += chain_count;
        if (best > 1e17) {'''
replacement='''        if (source == 1) chain_selected++, chain_papers += chain_count;
        if (r1_eligible) {
            const double prior_best = best;
            double keep_best = 1e18;
            bool any_valid = false;
#if ARGON_R1_PROBE
            bool any_new = false;
            r1_base_keep_requests += r1_base_kept;
#endif
            for (int fm : fms) {
                start_plan(st0);
                ++r1_trials;
                run_plan(u, {4, fm, true});
                if (invalid || ops.size() > 2 * K) continue;
                ++r1_legal;
                if (display() != A[u] || !fillers_reachable()) continue;
                ++r1_valid;
                any_valid = true;
                const double cost = plan_cost(ops.size());
                keep_best = std::min(keep_best, cost);
#if ARGON_R1_PROBE
                const bool fresh = std::find(r1_base_orders.begin(), r1_base_orders.end(), order) == r1_base_orders.end();
                r1_new_states += fresh;
                any_new |= fresh;
#else
                record_future(cost);
                if (cost < best) {
                    best = cost;
                    best_ops = ops;
                    OP_TAG(best_tags = op_tags;)
                    best_state = save();
                }
#endif
            }
            r1_valid_requests += any_valid;
            r1_extension_valid += r1_extension && any_valid;
#if ARGON_R1_PROBE
            r1_new_requests += any_new;
#endif
            if (keep_best + 1e-9 < prior_best) {
                ++r1_better_requests;
                r1_extension_better += r1_extension;
                r1_raw_gain += prior_best - keep_best;
            }
#if !ARGON_R1_PROBE
            r1_selected += best < prior_best;
#endif
        }
        if (best > 1e17) {'''
assert needle in s
s=s.replace(needle,replacement,1)
s=s.replace('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "r1_requests = " << solver.r1_requests << "\\nr1_previous = " << solver.r1_previous
              << "\\nr1_generic_ok = " << solver.r1_generic_ok << "\\nr1_color_ok = " << solver.r1_color_ok
              << "\\nr1_new_gate = " << solver.r1_new_gate << "\\nr1_trials = " << solver.r1_trials
              << "\\nr1_legal = " << solver.r1_legal << "\\nr1_valid = " << solver.r1_valid
              << "\\nr1_valid_requests = " << solver.r1_valid_requests << "\\nr1_new_states = " << solver.r1_new_states
              << "\\nr1_new_requests = " << solver.r1_new_requests << "\\nr1_base_keep_requests = " << solver.r1_base_keep_requests
              << "\\nr1_better_requests = " << solver.r1_better_requests << "\\nr1_raw_gain = " << solver.r1_raw_gain
              << "\\nr1_extension_valid = " << solver.r1_extension_valid
              << "\\nr1_extension_better = " << solver.r1_extension_better
              << "\\nr1_selected = " << solver.r1_selected << '\\n';
''',1)
assert s != base
Path('solutions/argon-req-ret4/main.cpp').write_text(s.replace('#define ARGON_R1_NEW_ONLY 0', '#define ARGON_R1_NEW_ONLY 1'))
Path('solutions/argon-req-ret4-all/main.cpp').write_text(s)
Path('solutions/argon-req-ret4-probe/main.cpp').write_text('#define ARGON_R1_PROBE 1\n'+s)
readme='''改良元: solutions/esw-slim

R1: 前の商品紙を残す計画を、今回の商品紙の全ての穴で色が正しい場合だけ追加する。正しく覆う汎用窓は比較層の並べ替えの対象から除く。ハンドルの穴も全て色を検査し、既存の可視性・表示・フィラー回収可能性の検査を通した候補だけを使う。設計・目的関数・探索予算は変更しない。

`ARGON_R1_PROBE=1` は測定専用。候補を採用せず、現在の計画と同じ開始状態で比較する。既存スイッチ・ログ・プロファイラ・DesignStoreは維持する。

追加指標（全注文の累積）:
- `r1_requests / r1_previous`: 注文数 / 前の商品紙と今回の商品紙が異なる注文数。
- `r1_generic_ok / r1_color_ok`: 汎用窓だけ / 全ての穴で据え置き可能な注文数。
- `r1_new_gate`: 全ての穴で色が合い、旧判定なら汎用窓の不透明部分だけで排除された注文数。
- `r1_trials / r1_legal / r1_valid`: 追加試行数 / 操作が合法 / 表示と回収も正しい試行数。
- `r1_valid_requests`: 有効な追加候補のある注文数。
- `r1_new_states / r1_new_requests`: 測定版で既存の全初期候補とは最終積層が異なる候補数 / 注文数。
- `r1_base_keep_requests`: 測定版で既存候補にも前の商品紙を比較層より上に残すものがあった注文数。
- `r1_better_requests / r1_raw_gain`: 追加候補が後処理前の最良値を改善した注文数 / plan_cost改善量の合計。
- `r1_selected`: 追加候補が後処理前の最良計画になった注文数。

全件の結果と採否はREPORT.md。
'''
Path('solutions/argon-req-ret4/README.md').write_text(readme+'\nこの版はARGON_R1_NEW_ONLY=1。旧ret_mode=4でも試せた候補を増やさず、正しい色の汎用窓を前の商品紙が覆う場合だけ追加する。r1_extension_valid / r1_extension_better はこの拡張による有効候補 / 後処理前改善の注文数。\n')
Path('solutions/argon-req-ret4-all/README.md').write_text(readme+'\nこの版はARGON_R1_NEW_ONLY=0。旧ret_mode=4で試せた場合も含め、全ての色安全な据え置き候補を追加する。\n')
Path('solutions/argon-req-ret4-probe/README.md').write_text(readme+'\nこのディレクトリはARGON_R1_PROBE=1を固定した測定版。候補の選択は基準のまま。\n')
