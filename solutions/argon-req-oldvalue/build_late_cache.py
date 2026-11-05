from pathlib import Path
import subprocess,sys
name=sys.argv[1];gap=sys.argv[2] if len(sys.argv)>2 else '0.5'
subprocess.run([sys.executable,'solutions/argon-req-oldvalue/build_late.py',name,gap],check=True)
p=Path('solutions')/name;s=p.joinpath('main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
sub('''        bool ready = false;
    } weighted_seed;''','''        bool ready = false;
        int stage = 0;  // 0 raw, 1 edited, 2 edited and ejected
    } weighted_seed;''')
sub('''    double late_seed_gain = 0;''','''    double late_seed_gain = 0;
    long long late_seed_cached = 0, late_seed_order_skips = 0;''')
sub('''        post_context.ready = false;  // all post-processing in this call replays the same st0''','''        if (!seed) post_context.ready = false;  // the late seed replays the same st0''')
sub('''        auto chosen_path = post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));''','''        auto chosen_path = seed && seed->stage ? std::move(best_ops)
                           : post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));''')
sub('''        post_candidate_calls++;
        const int original_length''','''        post_candidate_calls += !seed || !seed->stage;
        const int original_length''')
sub('''        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);''','''        if (!seed || seed->stage < 2)
            chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);''')
sub('''        post_secondary_saved += original_length - int(chosen_path.size());''','''        if (!seed && weighted_seed.ready) {
            const FutureCandidate raw{weighted_seed.cost, weighted_seed.state, weighted_seed.path OP_TAG(, weighted_seed.tags)};
            if (const auto* cached = find_cached_plan(raw)) {
                const auto& c = cached->edited;
                weighted_seed = {c.state, c.path OP_TAG(, c.tags), c.cost, true, cached->complete ? 2 : 1};
                ++late_seed_cached;
            }
        }
        post_secondary_saved += original_length - int(chosen_path.size());''')
sub('''        if (!weighted_seed.ready || weighted_seed.cost > value +''','''        if (weighted_seed.ready && weighted_seed.state.order == order) {
            ++late_seed_order_skips;
            return path;
        }
        if (!weighted_seed.ready || weighted_seed.cost > value +''')
sub('''    std::cerr << "late_seed_trials = "''','''    std::cerr << "late_seed_cached = " << solver.late_seed_cached
              << "\\nlate_seed_order_skips = " << solver.late_seed_order_skips << '\\n';
    std::cerr << "late_seed_trials = "''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+'''
既存のplan_cacheに対応する結果があれば、削除・挿入位置変更済み、またはeject済みの計画を引き継ぐ。既に済んだ段は繰り返さない。値の条件はこの途中結果に適用し、現在の完成結果と全紙の順序が同じ候補は追加処理しない。

late_seed_cachedは途中結果を引き継げた注文数、late_seed_order_skipsは同じ積層のため追加処理を省いた注文数。
''')
