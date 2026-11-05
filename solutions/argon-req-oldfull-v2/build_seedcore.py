from pathlib import Path


def add_seed_core(s):
    def sub(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:100])
        s = s.replace(old, new, 1)

    sub('    Moves process(int u) {\n        CF_SCOPE(process);', '''    struct ProcessSeed {
        State state;
        Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
        int stage = 0;  // 0 raw, 1 edited, 2 ejected
    };
    // A supplied seed uses the same completion pipeline from the same initial
    // stack, without generating the ordinary plans again.
    Moves process(int u, const ProcessSeed* seed = nullptr, bool* seed_ok = nullptr) {
        CF_SCOPE(process);
        if (seed_ok) *seed_ok = false;''')
    sub('        post_context.ready = false;  // all post-processing in this call replays the same st0',
        '        if (!seed) post_context.ready = false;  // seed completion replays the same st0')
    sub('        OP_TAG(if (neutral_enabled) ++request_counter;)',
        '        OP_TAG(if (neutral_enabled && !seed) ++request_counter;)')
    sub('        double best = 1e18, best_normal = 1e18;',
        '        if (seed) opts = {{1, 5, true}};\n        double best = 1e18, best_normal = 1e18;')
    sub('            const RepeatedPlan* repeated = nullptr;', '''            if (seed) {
                restore(seed->state);
                ops = seed->path;
                OP_TAG(op_tags = seed->tags;)
                placement_chains.clear();
            } else {
            const RepeatedPlan* repeated = nullptr;''')
    sub('''            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double cost = plan_cost(ops.size());''', '''            }
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double cost = plan_cost(ops.size());''')
    sub('        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {',
        '        if (!seed && interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {')
    sub('''        if (best > 1e17) {
            plan_failures++;''', '''        if (best > 1e17) {
            if (seed) return {};
            plan_failures++;''')
    sub('''        check_vis = false;
        restore(best_state);''', '''        if (seed_ok) *seed_ok = true;
        check_vis = false;
        restore(best_state);''')
    sub('        auto chosen_path = post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));',
        '''        auto chosen_path = seed && seed->stage ? std::move(best_ops)
            : post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));''')
    sub('        post_candidate_calls++;\n        const int original_length',
        '        post_candidate_calls += !seed || !seed->stage;\n        const int original_length')
    sub('        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);',
        '''        if (!seed || seed->stage < 2)
            chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);''')
    # Only the outer request emits a final-path trace. Exploratory completions
    # cannot claim to be the final path when the incumbent is later retained.
    start = s.index('    Moves process(int u, const ProcessSeed* seed')
    end = s.index('// ==== Emergency design ====', start)
    part = s[start:end]
    for token in ['cfg.trace', 'cfg.predict', 'cfg.plan_trace']:
        part = part.replace('if ('+token+')', 'if (!seed && '+token+')')
    s = s[:start]+part+s[end:]
    return s


if __name__ == '__main__':
    p = Path('solutions/argon-req-seedcore')
    assert not p.exists()
    p.mkdir()
    source = Path('solutions/argon-req-ejectstats-v2/main.cpp').read_text()
    (p/'main.cpp').write_text(add_seed_core(source))
    (p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

測定用の計画単独仕上げを共通のprocessで行えるようにする切り出し確認版。既定の呼び出しでは元の全計画・順序・予算・出力を保つ。別計画を渡す呼び出しはこの版では使用しない。

ProcessSeedのstageは0:未編集、1:編集済み、2:eject済み。既に終えた段を繰り返さず、以後の処理を共通実装で行う。測定中の仮の完成経路を最終経路としてtraceへ出さない。既存のログ・スイッチ・プロファイラ・設計・目的関数・乱数・CLOCK_SCALE・LOCAL_BENCH・DesignStore・目次と節名は維持する。新規の指標・環境変数はない。
''')
