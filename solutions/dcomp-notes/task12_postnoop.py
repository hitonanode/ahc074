from pathlib import Path
S=Path(__file__).resolve().parents[1];s=(S/'dcomp-t12-postmemo/main.cpp').read_text()
def rep(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90]);s=s.replace(a,b)
rep('''        int op=0;
    };
    struct PostMemoTable''','''        int op=0; bool unchanged=false;
    };
    bool last_post_unchanged=false;
    inline static long long post_memo_noops=0;
    struct PostMemoTable''')
rep('''#else
            post_saved+=int(input_ops.size())-int(entry.path.size());''','''#else
            last_post_unchanged=entry.unchanged;
            if(entry.unchanged) {
                ++post_memo_noops;eject_accepts+=entry.eject_delta;last_post_operator=entry.op;
                return input_ops;
            }
            post_saved+=int(input_ops.size())-int(entry.path.size());''')
rep('''        entry.state=save();entry.path=result;OP_TAG(entry.tags=tags;)
        entry.eject_delta''','''        entry.unchanged=last_post_unchanged;
        if(!entry.unchanged
#ifdef POST_MEMO_CHECK
           || true
#endif
        ) {entry.state=save();entry.path=result;OP_TAG(entry.tags=tags;)}
        entry.eject_delta''')
rep('''        double best_score = plan_cost(best_ops.size());
        int trial_operator''','''        double best_score = plan_cost(best_ops.size());
        bool best_unchanged=true;
        int trial_operator''')
rep('''            best_score = value;
            best_operator = trial_operator;''','''            best_score = value;
            best_unchanged=false;
            best_operator = trial_operator;''')
rep('''        last_post_operator = best_operator;
        OP_TAG(tags = std::move(best_tags);)''','''        last_post_operator = best_operator;
        last_post_unchanged=best_unchanged;
        OP_TAG(tags = std::move(best_tags);)''')
rep('''    cf_report();''','''    std::cerr<<"dp_post_memo_noops = "<<solver.post_memo_noops<<'\\n';
    cf_report();''')
for suffix,check in [('postnoop',False),('postnoop-check',True)]:
 d=S/('dcomp-t12-'+suffix);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(('#define POST_MEMO_CHECK 1\n'if check else'')+s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t12-postmemo\n\npostが一度もbestを更新しなかった場合、終状態・操作・ラベルは呼出し入力そのものなので、結果のcopyを保存せずunchanged bitで記録する。hitでも入力をそのまま返す。入力key全体の一致とeject_accepts差の再現は保持。'+('検証版はno-opでも元処理と全出力を照合する。'if check else'')+'\n\n探索・選択は変えず、時計で切り替えない。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。\n')
