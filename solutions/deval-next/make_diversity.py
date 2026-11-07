"""Task 4: fixed refinish diversification, retaining the first four candidates."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-seven-wide/main.cpp').read_text()
configs={
 'mix-climb':dict(cw=[.25,.75,1.25]),
 'mix-match':dict(mw=[.7,1.3,1.6]),
 'mix-perf':dict(pw=[.35,1.,1.4]),
 'mix-finish':dict(cw=[.25,.75,1.25],mw=[.7,1.2,1.5],pw=[.4,1.,1.3]),
 'kick2':dict(kick=2),
 'kick6':dict(kick=6),
 'beam-finish':dict(beam=True),
}
def arr(values):return 'std::array<double,3>{'+','.join(map(str,values))+'}'
for name,cfg in configs.items():
 s=base.replace('auto finish = [&](Design* des,bool raw=false,int extra=0)', 'auto finish = [&](Design* des,bool raw=false,int refine=0)',1)
 s=s.replace('extra?25000:climb_iters','refine?25000:climb_iters',1)
 mw=cfg.get('mw',[1.,1.,1.]);pw=cfg.get('pw',[.7,.7,.7]);cw=cfg.get('cw',[.5,.5,.5])
 s=s.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0)',f'rematch_probability(*des, refine?1:2, refine?{arr(mw)}[refine-1]:1.0, 2.0)',1)
 s=s.replace('perforation.run(0.7);',f'perforation.run(refine?{arr(pw)}[refine-1]:.7);',1)
 s=s.replace('rematch_probability(*des, late_iterations, 1.05, 2.0, &extra)',f'rematch_probability(*des, late_iterations, refine?{arr([1.05*x for x in mw])}[refine-1]:1.05, 2.0, &extra)',1)
 s=s.replace('Design::kClimbProxyWeight=.5;',f'Design::kClimbProxyWeight=extra?{arr(cw)}[extra-1]:.5;',1)
 s=s.replace('complete(id,1);','complete(id,j+1);',1)
 if cfg.get('kick'):
  kick=cfg['kick']
  needle='        complete(id,j+1);'
  code=f'''        // A fixed number of feasible unit exchanges; no clock or request list is used.
        int kicked=0;
        for(int trial=0;trial<4096 && kicked<{kick};++trial) {{
            const int x=des->rng.below(des->U),y=des->rng.below(des->U);
            auto a=des->unit[x],b=des->unit[y];
            if(a.c==b.c || (a.b>=0)!=(b.b>=0))continue;
            if(!des->valid(a,b.c)||!des->valid(b,a.c))continue;
            if(des->color(a,b.c)!=des->color(b,b.c)||des->color(b,a.c)!=des->color(a,a.c))continue;
            std::swap(des->unit[x].c,des->unit[y].c);++kicked;
        }}
        des->rebuild();
'''
  s=s.replace(needle,code+needle,1)
 if cfg.get('beam'):
  s=s.replace('std::unique_ptr<Design> best_assignment;','std::unique_ptr<Design> best_assignment,second_assignment;\n    double second_value=1e100;',1)
  needle='        if(v<best){best=v;'
  s=s.replace(needle,'''        if(v<best && best_assignment){second_value=best;second_assignment=std::make_unique<Design>(*best_assignment);}
        else if(v>=best && v<second_value){second_value=v;second_assignment=std::make_unique<Design>(*des);}
'''+needle,1)
  s=s.replace('des=std::make_unique<Design>(*best_assignment);','des=std::make_unique<Design>(*(j==1&&second_assignment?second_assignment:best_assignment));',1)
 d=R/'solutions'/('deval-'+name);d.mkdir(exist_ok=False)
 assert len(s.encode())<=520000
 (d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# deval-{name}

改良元: solutions/deval-seven-wide。

最初の4完成候補は基準と同じ。追加3回の仕上げだけを変え、完成V16で選ぶ。固定設定: {cfg}。

cwはclimbのfiller利益の重み（基準0.5）、mwは再割当てのfiller重み（基準1.0、穴あけ後はその1.05倍）、pwは穴あけの利益の重み（基準0.7）。配列は追加候補の順。kickは同じ種類・交換先でも同じ色になる有効な2ユニットの列交換を指定数だけ試し、その後に通常の仕上げで修復する。beamは2番目の完成配置も保持し、追加2回目をそこから始める。

追加候補のclimbは25k、再割当て1回、穴あけ8サンプル、最終再割当て1回。焼きなまし・窓・注文探索の予算は基準と同じ。時間による打切りや軽量化はない。DesignStore、@paper/@ops、ログ、目次・段の目印を維持する。
''')
 print(d.name,len(s.encode()))
