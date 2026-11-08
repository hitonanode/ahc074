"""Repair the late tie choice; optionally preserve its learned terminal ranking."""
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n予算は両コンパイラ共通の固定回数。選別はseed0–499、時計による変更なし。既存のログ・trace・profiler・実験スイッチ、段の目印と目次、DesignStoreを保持する。\n')
for name,rounds,veto,edit in [('tie-eject',1,False,False),('tie-eject-value',1,True,False),('tie-edit-value',1,True,True),('tie-polish-value',2,True,False)]:
 s=B
 x='    long long tie_decisions = 0, tie_switches = 0, tie_rejected = 0;';assert s.count(x)==1
 s=s.replace(x,x+'\n    long long tie_repair_calls=0,tie_repair_changes=0,tie_repair_kept=0,tie_repair_moves=0;')
 x='''        chosen_path = tie_choice(st0, u, std::move(chosen_path) OP_TAG(, op_tags));
        merge_double_moves(st0, chosen_path OP_TAG(, op_tags));''';assert s.count(x)==1
 action=''
 if edit:action+='            chosen_path=post_optimize(st0,std::move(chosen_path),u OP_TAG(,op_tags),false);\n'
 action+=f'            chosen_path=polish_ejects(st0,std::move(chosen_path),u OP_TAG(,op_tags),{rounds});\n'
 s=s.replace(x,'''        const auto before_tie=tie_switches;
        chosen_path = tie_choice(st0, u, std::move(chosen_path) OP_TAG(, op_tags));
        if(tie_switches!=before_tie) {
            ++tie_repair_calls;
            const auto before_state=save();const auto before_path=chosen_path;
            OP_TAG(const auto before_tags=op_tags;)
            const double before_value=plan_cost(chosen_path.size());
            const auto before_features=tie_features(chosen_path.size());
            F3_DIAG(f3_stage=30;f3_round=0;)
'''+action+'''            tie_repair_changes+=chosen_path!=before_path;
            bool keep=true;
'''+('''            const auto after_features=tie_features(chosen_path.size());
            double difference=plan_cost(chosen_path.size())-before_value;
            for(int j=0;j<9;++j)difference+=kTieCoef[j]*(after_features[j]-before_features[j]);
            keep=difference<-1e-9;
''' if veto else '')+'''            if(keep) {
                tie_repair_kept+=chosen_path!=before_path;
                tie_repair_moves+=int(before_path.size())-int(chosen_path.size());
            } else {
                restore(before_state);chosen_path=before_path;OP_TAG(op_tags=before_tags;)
            }
        }
        merge_double_moves(st0, chosen_path OP_TAG(, op_tags));''')
 x='    cf_report();';assert s.count(x)==1
 s=s.replace(x,'''    std::cerr<<"tie_repair_calls = "<<solver.tie_repair_calls<<"\\ntie_repair_changes = "<<solver.tie_repair_changes
             <<"\\ntie_repair_kept = "<<solver.tie_repair_kept<<"\\ntie_repair_moves = "<<solver.tie_repair_moves<<'\\n';
'''+x)
 # main owns the solver under the existing name sol, checked below during generation.
 if 'Solver solver' not in s:
  s=s.replace('<<solver.tie_repair','<<sol.tie_repair')
 desc=f'最後のtie_choiceが別の計画を選んだ注文だけ、'+('通常の編集の後に' if edit else '')+f'2→1修復を最大{rounds}回行う。'+('修復前後を既存の近接選択と同じ線形補正付き費用で比べ、改善するときだけ採る。' if veto else '修復は既存plan_costを下げた結果を採る。')+'追加指標tie_repair_*は呼出し、変更、採用、手数減少。'
 write('dcomp-t11-'+name,s,desc)

for gap in [.5,1.0]:
 x='static constexpr double kTieGap = 0.3,';assert B.count(x)==1
 write('dcomp-t11-tiegap'+str(gap).replace('.',''),B.replace(x,f'static constexpr double kTieGap = {gap},'),
       f'完了した計画を終端の線形補正で比較する範囲kTieGapを0.3から{gap}へ広げる。追加の計画生成や修復は行わない。学習済み係数は変えず、外挿の良否を実replayで検証する。')
