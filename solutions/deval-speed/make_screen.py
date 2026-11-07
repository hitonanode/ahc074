from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
for count in (1,2):
    s=base.replace('auto finish = [&](Design* des,bool raw=false) {','auto finish = [&](Design* des,bool raw=false,int phase=0) {',1)
    s=s.replace('    if(!raw) {\n    if (climb_iters > 0)','    if(!raw && phase!=2) {\n    if (climb_iters > 0)',1)
    s=s.replace('    if(raw)return state;','    if(raw||phase==1)return state;',1)
    lo=s.index('    for(int i=0;i<candidates;++i) {',s.index('DesignState design_papers('))
    hi=s.index('    if(!finished)state.emergency=true;',lo)
    s=s[:lo]+f'''    struct Preview {{ double value; int id; std::unique_ptr<Design> design; std::string log; }};
    std::vector<Preview> previews;
    for(int i=0;i<candidates;++i) {{
        if(i && elapsed_sec()>env_real("DEVAL_DESIGN_LIMIT",1.12))break;
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();
        des->anneal_reheat=i?2:1.;
        des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        std::ostringstream log;
        auto* old=std::cerr.rdbuf(log.rdbuf());
        Design::kClimbProxyWeight=.5;
        begin=elapsed_sec();
        auto candidate=finish(des.get(),false,1);
        finish_sec+=elapsed_sec()-begin;
        std::cerr.rdbuf(old);
        if(candidate.emergency)continue;
        begin=elapsed_sec();
        const double v=value.from_design(candidate);
        eval_sec+=elapsed_sec()-begin;
        previews.push_back({{v,i,std::move(des),log.str()}});
    }}
    std::stable_sort(previews.begin(),previews.end(),[](const auto& a,const auto& b){{return a.value<b.value;}});
    for(int i=0;i<std::min({count},int(previews.size()));++i) {{
        if(i && elapsed_sec()>env_real("DEVAL_DESIGN_LIMIT",1.12))break;
        auto& preview=previews[i];
        deval_salt=first_salt+preview.id;
        std::ostringstream log;log<<preview.log;
        auto* old=std::cerr.rdbuf(log.rdbuf());
        double begin=elapsed_sec();
        auto candidate=finish(preview.design.get(),false,2);
        finish_sec+=elapsed_sec()-begin;
        std::cerr.rdbuf(old);
        if(candidate.emergency)continue;
        begin=elapsed_sec();
        const double v=value.from_design(candidate);
        eval_sec+=elapsed_sec()-begin;
        if(!finished)first=v;
        ++finished;
        if(v<best){{best=v;chosen=preview.id;state=std::move(candidate);chosen_log=log.str();}}
    }}
    std::cerr<<"dv_prescreen_candidates = "<<previews.size()<<'\\n';
'''+s[hi:]
    d=ROOT/f'solutions/deval-screen{count}';d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'''# deval-screen{count}

改良元: solutions/deval-vbranch-o3。

同じ4分岐を filler climb と2回の再割当てまで仕上げ、穴あけ前のVで順位をつける。上位{count}候補だけ穴あけと穴あけ後再割当てを行い、最後にVで選ぶ。探索回数・温度は元のまま。追加候補は1.12秒を超えたら止め、最初の完成設計を必ず確保する。提出時の時間ガード、LOCAL_BENCHの固定注文予算、DesignStore、診断を維持。
''')
    print(d,len(s.encode()))
for name,changes,desc in [
 ('deval-climb25', [('const int climb_env = 50000','const int climb_env = 25000')], 'filler climbの反復数を50,000から25,000に減らす'),
 ('deval-match1', [('std::max(1,int(2)), 1.0, 2.0','std::max(1,int(1)), 1.0, 2.0')], '穴あけ前の再割当てを2回から1回に減らす'),
]:
    s=base
    for a,b in changes:
        assert a in s;s=s.replace(a,b,1)
    d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{desc}。他の探索、時間ガード、DesignStore、診断を維持。\n')
