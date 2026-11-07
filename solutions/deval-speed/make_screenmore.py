from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-fast2/main.cpp').read_text()
for name,repeats,share_climb,keep in [('deval-screenmatch12',3,True,2),('deval-screenraw8',2,False,3)]:
 s=base.replace('static constexpr int kSamples = 32;','static constexpr int kSamples = 8;',1)
 s=s.replace('auto finish = [&](Design* des,bool raw=false) {','auto finish = [&](Design* des,bool raw=false,int phase=0) {',1)
 idx=s.index('auto finish = ');a=s[:idx];b=s[idx:]
 b=b.replace('    if(!raw) {','    if(phase!=2) {',1)
 b=b.replace('if (climb_iters > 0) des->filler_climb(1e300, climb_iters);','if (climb_iters > 0 && phase==0) des->filler_climb(1e300, climb_iters);',1)
 s=a+b
 a=s.index('    for(int i=0;i<candidates;++i) {',s.index('    const auto prefix=std::make_unique<Design>(*des);',s.index('DesignState design_papers')))
 b=s.index('    if(!finished)state.emergency=true;',a)
 body='''    struct Preview { double value;int id;std::unique_ptr<Design> design;std::string log; };
    std::vector<Preview> previews;
    for(int branch=0;branch<candidates;++branch) {
        deval_salt=first_salt+branch;
        des=std::make_unique<Design>(*prefix);
        if(branch)des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=branch?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        Design::kClimbProxyWeight=.5;
        SHARED_CLIMB
        const auto origin=std::make_unique<Design>(*des);
        for(int repeat=0;repeat<REPEATS;++repeat) {
            const int id=branch+candidates*repeat;
            deval_salt=first_salt+id;des=std::make_unique<Design>(*origin);
            if(repeat)des->rng.x^=u64(repeat)*0x9E3779B97F4A7C15ULL;
            std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
            std::cerr<<"colswap_tried = "<<des->colswap_tried<<"\\ncolswap_accepted = "<<des->colswap_accepted
                     <<"\\nreplace_tried = "<<des->replace_tried<<"\\nreplace_accepted = "<<des->replace_accepted<<'\\n';
            begin=elapsed_sec();auto candidate=finish(des.get(),true,PHASE);
            finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
            if(candidate.emergency)continue;
            begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
            previews.push_back({v,id,std::move(des),log.str()});
        }
    }
    std::stable_sort(previews.begin(),previews.end(),[](const auto& a,const auto& b){return a.value<b.value;});
    std::cerr<<"dv_previews = "<<previews.size()<<'\\n';
    for(int j=0;j<std::min(KEEP,int(previews.size()));++j) {
        auto& entry=previews[j];deval_salt=first_salt+entry.id;des=std::move(entry.design);
        std::ostringstream log;log<<entry.log;auto* old=std::cerr.rdbuf(log.rdbuf());
        double begin=elapsed_sec();auto candidate=finish(des.get(),false,2);
        finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
        if(candidate.emergency)continue;
        begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr<<"@deval_final "<<entry.id<<' '<<v<<'\\n';
        if(!finished)first=v;
        ++finished;
        if(v<best){best=v;chosen=entry.id;state=std::move(candidate);chosen_log=log.str();}
    }
'''
 body=body.replace('SHARED_CLIMB','begin=elapsed_sec();des->filler_climb(1e300,climb_iters);finish_sec+=elapsed_sec()-begin;' if share_climb else '// Each independent completion repeats the climb.').replace('REPEATS',str(repeats)).replace('PHASE','1' if share_climb else '0').replace('KEEP',str(keep))
 s=s[:a]+body+s[b:]
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-fast2（出力を保つ高速化を加えたdeval-vbranch-nofb）。

4分岐の焼きなましは元のまま。各分岐を{repeats}通りの固定saltで再割当て2回まで仕上げる。{'climb50kの結果を各分岐内で共有する。' if share_climb else 'climb50kもsaltごとにやり直す。'}穴あけ前のVで上位{keep}候補を残し、その候補を穴あけ8サンプル・最終再割当て1回まで完成させ、完成Vで選ぶ。

計{4*repeats}候補の前半を作り、仕上げの後半は有望な候補に使う。dv_previewsは一次候補数、dv_candidatesは完成候補数。窓・anneal・注文の予算は元のまま。時間不足による打切りはない。DesignStore、ログ、@paper/@ops、目次・段の目印を維持。
''')
 print(name,len(s.encode()))
