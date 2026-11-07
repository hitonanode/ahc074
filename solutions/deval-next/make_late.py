from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-warm9/main.cpp').read_text()
for name,count,expr in [('deval-late9',5,'j>=3?3:1'),('deval-late12',8,'j>=3?3:1'),('deval-latemix10',6,'j>=3?3:(j==1?2:1)')]:
 s=b.replace('if(!raw && extra!=2)','if(!raw && extra<2)',1).replace('if(extra==2 && !warm_state.papers.empty())','if(extra>=2 && !warm_state.papers.empty())',1)
 needle='''    if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();'''
 replacement='''    if(extra==3) {
        state.papers=solver.paper;
        int holes=0;for(int k=M+1;k<K;++k)holes+=__builtin_popcountll(natural_opacity[k]&~solver.h_opq[k]);
        std::cerr<<"perforation_holes = "<<holes<<"\\nperforation_trials = 0\\nperforation_accepts = 0\\nperforation_sec = 0\\n";
    } else {
'''+needle+'\n    }'
 assert needle in s;s=s.replace(needle,replacement,1)
 s=s.replace('for(int j=0;j<5;++j)',f'for(int j=0;j<{count};++j)',1)
 needle='''        const bool warm=j>=3;
        if(warm)warm_state=state;
        complete(id,warm?2:1);'''
 assert needle in s;s=s.replace(needle,f'''        const int mode={expr};
        if(mode>=2)warm_state=state;
        complete(id,mode);''',1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text(f'改良元: `solutions/deval-seven-wide`（deval-warm9の穴保存を使用）。\n\n完成した配置と物理穴を保ち、穴あけ後のHungarian再割当て1回だけを別saltで行う候補を追加する。V16で最良を選び、改善しなければ次も最良配置から始める。\n\n最初の4分岐は同じ。追加候補{count}回で、0起算jに対するmodeは `{expr}`。1は元の仕上げ、2は穴を保存した穴あけと再割当て、3は穴を固定した再割当てのみ。固定予算で、時間による切り替えはない。\n');print(name,len(s.encode()))
