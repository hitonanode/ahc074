from pathlib import Path
import subprocess,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
subprocess.run([sys.executable,str(P/'compose.py'),'deval-sixpolish','deval-sixpolish2','--features','colrun','gainprob','--nofb'],check=True)
base=(R/'solutions/deval-sixpolish2/main.cpp').read_text()
for name,branches,climb,screen in [('deval-twins8',4,25000,False),('deval-twins6',3,50000,False),('deval-twins8screen',4,50000,True)]:
 s=base.replace('const int candidates=6;',f'const int candidates={branches};',1).replace('const double branch_scale=0.25;',f'const double branch_scale=1.0/{branches};',1)
 s=s.replace('const int climb_env = 25000',f'const int climb_env = {climb}',1)
 s=s.replace('if (climb_iters > 0) des->filler_climb','if (climb_iters > 0 && phase!=2) des->filler_climb',1)
 s=s.replace('rematch_probability(*des, phase?1:2, 1.0, 2.0);','rematch_probability(*des, 1, 1.0, 2.0);',1)
 a=s.index('    struct Preview { double value; int id;',s.index('DesignState design_papers'))
 b=s.index('    if(!finished)state.emergency=true;',a)
 body='''    struct Preview { double value; int id; std::unique_ptr<Design> design; std::string log; };
    std::vector<Preview> previews;
    // Two independently salted completions share each annealed branch.
    for(int branch=0;branch<candidates;++branch) {
        deval_salt=first_salt+branch;
        des=std::make_unique<Design>(*prefix);
        if(branch)des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();
        des->anneal_reheat=branch?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        const auto raw=std::make_unique<Design>(*des);
        for(int twin=0;twin<2;++twin) {
            const int id=2*branch+twin;
            deval_salt=first_salt+id;
            des=std::make_unique<Design>(*raw);
            if(twin)des->rng.x^=u64(twin)*0x9E3779B97F4A7C15ULL;
            std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
            Design::kClimbProxyWeight=.5;
            begin=elapsed_sec();auto candidate=finish(des.get(),false,PHASE);
            finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
            if(candidate.emergency)continue;
            begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
            ADD_RESULT
        }
    }
'''.replace('PHASE','1' if screen else '0')
 full='''if(!finished)first=v;
            ++finished;
            if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();}'''
 body=body.replace('ADD_RESULT','previews.push_back({v,id,std::move(des),log.str()});' if screen else full)
 if screen:
  sort_begin=base.index('    std::stable_sort(previews.begin()',base.index('DesignState design_papers'))
  sort_end=base.index('    if(!finished)state.emergency=true;',sort_begin)
  oldloop=base[sort_begin:sort_end]
  body+=oldloop
 s=s[:a]+body+s[b:]
 assert len(s.encode())<=520000 and 'DEVAL_DESIGN_LIMIT' not in s
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-sixpolish2（設計・注文の元はdeval-vbranch-nofb）。

焼きなまし前半2段を共有し、後半を{branches}分岐へ分ける。各分岐の予算は1/{branches}で、合計は元とほぼ同じ。各分岐を固定saltを変えて2回仕上げる。filler climbは各{climb:,}回、再割当て1回、穴あけ8サンプル、穴あけ後の再割当て1回。

{'climbと再割当ての後にVで上位2候補を選び、その2候補に再割当て1回を加え、穴あけ以降を行って最終Vで選ぶ。' if screen else f'{2*branches}候補すべてを完成させ、Vで選ぶ。'} Hungarian SIMD、穴あけ整数DPと差分更新、filler列の内部保持、列の連続区間走査、丸めた確率差分の共有を使う。

固定予算・固定乱数で、時間不足による探索削減はない。DesignStoreは選ばれた設計を保存し、@paper/@ops・目次・段の目印を保つ。
''')
 print(name,len(s.encode()))
