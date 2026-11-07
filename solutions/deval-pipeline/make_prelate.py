from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,all_passes,chain in [('deval-prelate10',False,False),('deval-prelate16',True,False),('deval-prelate-chain',False,True)]:
 s=b.replace('''    DesignState warm_state;
    auto finish''','''    DesignState warm_state;
    struct FinishedSnapshot { DesignState state; std::string log; int id; };
    std::vector<FinishedSnapshot> before_late;
    std::unique_ptr<Design> before_late_assignment;
    std::ostringstream* finish_capture=nullptr;
    int finish_id=0;
    auto finish''',1)
 marker='''    // ==== design_papers: perforation-aware reassignment ====
'''
 code=f'''    // The perforated state is already a valid complete design. Keep it
    // eligible without changing the original finishing trajectory.
    if({'true' if all_passes else 'extra==2'}) {{
        before_late.push_back({{state,finish_capture->str()+"dv_pre_late = 1\\n",100+finish_id}});
        {'before_late_assignment=std::make_unique<Design>(*des);' if chain else ''}
    }}

'''
 assert marker in s;s=s.replace(marker,marker+code,1)
 s=s.replace('''        std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());''','''        std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
        finish_capture=&log;finish_id=id;''',1)
 if chain:
  s=s.replace('''        if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);}
        return v;''','''        if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);}
        if(extra==2) {
            auto& pre=before_late.back();begin=elapsed_sec();
            const double pv=value.from_design(pre.state);eval_sec+=elapsed_sec()-begin;++finished;
            if(pv<best){best=pv;chosen=pre.id;state=std::move(pre.state);chosen_log=pre.log;best_assignment=std::move(before_late_assignment);}
            before_late.pop_back();
        }
        return v;''',1)
 else:
  s=s.replace('''    if(!finished)state.emergency=true;''','''    for(auto& pre:before_late) {
        const double begin=elapsed_sec(),v=value.from_design(pre.state);
        eval_sec+=elapsed_sec()-begin;++finished;
        if(v<best){best=v;chosen=pre.id;state=std::move(pre.state);chosen_log=pre.log;}
    }
    if(!finished)state.emergency=true;''',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n'+('全8仕上げ' if all_passes else '穴を保存する2仕上げ')+'について、穴あけ直後・最終再割当て前の完成設計も保存し、V16で選択できるようにする。'+('その中間設計が最良なら次の再仕上げの出発点にもする。' if chain else '既存8候補の仕上げの連鎖は変えず、中間候補との比較は全ての仕上げが終わってから行う。')+'追加仕上げはなく、追加費用は主にVの評価。中間候補はdv_chosenに元の番号+100、dv_pre_late=1と記録する。DesignStoreは選ばれた設計を保存する。全予算固定、時間不足の切り替えなし。\n')
 print(name,len(s.encode()))
