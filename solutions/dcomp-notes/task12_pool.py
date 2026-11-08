from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
old='''                    if (!found)
                        neutral_candidates.push_back({save(), path OP_TAG(, path_tags), value, signature, trial_operator, repeats, hides});'''
new='''                    // The pool is already sorted. Do not materialize a new state/path
                    // that is strictly worse than its last entry at full capacity.
                    // Duplicate signatures must be handled first: their replacement rule
                    // compares value alone and may deliberately change the priority tuple.
                    const int pool_width=secondary_neutral?1:neutral_width;
                    auto last_is_better = [&] {
                        const auto& a=neutral_candidates.back();
                        if(cfg.candidate_priority) {
                            if(a.path.size()!=path.size())return a.path.size()<path.size();
                            if(cfg.hidden_rank && a.hides!=hides)return a.hides>hides;
                            if(a.repeats!=repeats)return a.repeats>repeats;
                        }
                        return a.value<value;
                    };
                    if (!found && !(neutral_candidates.size()==size_t(pool_width) && last_is_better()))
                        neutral_candidates.push_back({save(), path OP_TAG(, path_tags), value, signature, trial_operator, repeats, hides});'''
assert b.count(old)==1;b=b.replace(old,new)
d=S/'dcomp-t12-poolprune';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(b)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\n整列済みの中立候補poolが満杯なら、末尾より厳密に優先順位が低い新候補のState・操作列のcopyを省く。同じsignatureの置換は先に元どおり処理し、同点は元のsortへ渡す。poolのsortと本探索の順は保持する。追加親にも同じ処理を使う。\n\n固定予算、コンパイラ共通の探索量、時計での切替なし。ログ・実験switch・段と目次・DesignStoreを保持する。\n')
