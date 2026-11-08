from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n修復は同じ終状態に到達する合法な操作列への短縮だけ。固定予算を両コンパイラで共用し、時刻による切替なし。既存ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
x='''            F3_DIAG(fp_legal[fp_op]++;)
            if (neutral_collect && cfg.collect) {''';assert B.count(x)==1
for name,condition in [('merge-near','value < best_score+1.01'),('merge-collect','neutral_collect && value < best_score+1.35'),('merge-win','value < best_score+1e-8')]:
 s=B.replace(x,'''            // Repair a repeated move before evaluating or discarding its legal plan.
            // The repair preserves the exact end stack and all future-cost terms.
            if('''+condition+''') {
                const auto previous_size=path.size();
                merge_double_moves(initial,path OP_TAG(,path_tags));
                if(path.size()!=previous_size) {
                    // Preserve the left-to-right arithmetic of the original value model.
                    value=memo ? path.size()+memo->charge+memo->next_cost : plan_cost(path.size());
                }
            }
'''+x)
 write('dcomp-t11-'+name,s,'post_optimizeの合法候補に対し、二重移動の同終状態への結合を費用比較の前に行う。適用条件: '+condition+'。候補の終状態・将来費用は同じで、操作数だけ正確に減る。prefixの再生記録は修復前のまま保持する。')
