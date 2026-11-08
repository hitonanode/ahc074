from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(s,a,b,n=1):assert s.count(a)==n,(s.count(a),a[:80]);return s.replace(a,b)
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n設計・要求予算は固定、両コンパイラ共通。既存ログ・実験スイッチ・profiler・目次・段とDesignStoreを保持し、時計で探索を変えない。\n')
s=rep(B,'    mutable std::vector<std::vector<Cand>> cand_scratch;','    mutable std::vector<std::vector<Cand>> cand_scratch;\n    int interval_tie_mode=0;')
s=rep(s,'                if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9) {','''                if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9 ||
                    (interval_tie_mode && std::abs(best[cand[c][i].lvl]+cand[c][i].gain-best[c+1])<=1e-9)) {''')
s=rep(s,'        bool complete_value = false;\n    };','        bool complete_value = false;\n        int interval_tie=0;\n    };')
s=rep(s,'''        if (opt.fret_mode == 5) {
            run_joint(u, opt);
            return;
        }''','''        if (opt.fret_mode == 5) {
            const int previous=interval_tie_mode;interval_tie_mode=opt.interval_tie;
            run_joint(u, opt);interval_tie_mode=previous;
            return;
        }''')
s=rep(s,'                        q.opt.value_fillers == o.value_fillers && q.opt.complete_value == o.complete_value) { repeated = &q; break; }',
'''                        q.opt.value_fillers == o.value_fillers && q.opt.complete_value == o.complete_value &&
                        q.opt.interval_tie == o.interval_tie) { repeated = &q; break; }''')
x='        if (d != top0) opts.push_back({1, 5, true, true, true});'
add=rep(s,x,x+'\n        if(d!=top0)opts.push_back({1,5,true,false,false,1});')
write('dcomp-t11-interval-add',add,'joint filler選択の区間DPには整数の同点が多い。元の計画を保ち、同じ最適DP値で後に列挙された区間を選ぶ計画を1個追加する。元の費用関数とpost修復で完成計画を選ぶ。DPの探索目的・固定候補数は変えない。')
replace=rep(s,'            run_joint(u, opt);interval_tie_mode=previous;','            if(!opt.value_fillers)interval_tie_mode=1;\n            run_joint(u, opt);interval_tie_mode=previous;')
write('dcomp-t11-interval-replace',replace,'unweighted joint filler選択の区間DPを、同じ最適値なら後に列挙された区間を選ぶ規則へ置換する。新しい計画の生成は増やさず、同点選択が完成計画へ与える効果を測る対照。')
