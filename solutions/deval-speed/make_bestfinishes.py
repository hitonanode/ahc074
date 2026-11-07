from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-headcache/main.cpp').read_text()
for name,extras in [('deval-best6',2),('deval-best8',4)]:
 s=base.replace('static constexpr int kSamples = 32;','static constexpr int kSamples = 8;',1)
 s=s.replace('auto finish = [&](Design* des,bool raw=false) {','auto finish = [&](Design* des,bool raw=false,int extra=0) {',1)
 s=s.replace('if (climb_iters > 0) des->filler_climb(1e300, climb_iters);','if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);',1)
 s=s.replace('rematch_probability(*des, std::max(1,int(2)), 1.0, 2.0);','rematch_probability(*des, extra?1:2, 1.0, 2.0);',1)
 a=s.index('    for(int i=0;i<candidates;++i) {',s.index('    const auto prefix=std::make_unique<Design>(*des);',s.index('DesignState design_papers')))
 b=s.index('    if(!finished)state.emergency=true;',a)
 s=s[:a]+'''    struct Branch { double value=1e100;int id=0;std::unique_ptr<Design> raw; };
    std::vector<Branch> branches;
    auto complete=[&](int id,int extra) {
        std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
        Design::kClimbProxyWeight=.5;
        double begin=elapsed_sec();auto candidate=finish(des.get(),false,extra);
        finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
        if(candidate.emergency)return 1e100;
        begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
        if(!finished)first=v;
        ++finished;
        if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();}
        return v;
    };
    for(int i=0;i<candidates;++i) {
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        branches.push_back({1e100,i,std::make_unique<Design>(*des)});
        branches.back().value=complete(i,0);
    }
    // Rank completed branches, retain every original completion, then spend
    // extra finishing attempts only on the two most promising raw branches.
    std::stable_sort(branches.begin(),branches.end(),[](const auto& a,const auto& b){return a.value<b.value;});
    for(int j=0;j<EXTRAS;++j) {
        const int origin=j%std::min(2,int(branches.size())),repeat=1+j/2,id=candidates+j;
        deval_salt=first_salt+id;
        des=std::make_unique<Design>(*branches[origin].raw);
        des->rng.x^=u64(repeat)*0x9E3779B97F4A7C15ULL;
        complete(id,1);
    }
'''.replace('EXTRAS',str(extras))+s[b:]
 assert len(s.encode())<=520000
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-headcache（高速化したdeval-vbranch-nofb）。

4分岐の焼きなまし・climb50k・再割当て2回を元と同じに行い、穴あけ8サンプル・穴あけ後再割当てまで全候補を完成させる。完成後のVが良い上位2分岐の焼きなまし直後へ戻り、追加で計{extras}回、固定saltを変えて仕上げる。追加分はclimb25k・再割当て1回・穴あけ8サンプル・穴あけ後再割当て1回。既存の4完成候補を残し、全部で{4+extras}完成候補の最小Vを選ぶ。

追加分の枝を、仕上げ前のVではなく完成した設計のVで選ぶ。窓割当て・焼きなましの総反復数・注文探索予算は元のまま。時間による打切りはない。DesignStoreは採用候補を保存し、@paper/@ops・目次・段の目印を保つ。
''')
 print(name,len(s.encode()))
