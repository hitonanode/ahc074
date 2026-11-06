"""Share the expensive front of finishing and select perforation variants."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vperf'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
src=src.replace('env_real("DEVAL_MODE",1)','env_real("DEVAL_MODE",7)')
src=src.replace('kClimbIters = int(50000 * ITER_SCALE), kMatchIterations = 2',
                'kClimbIters = int(154000 * ITER_SCALE), kMatchIterations = 4')
needle='    auto finish = [&](Design* des,bool raw=false) {'
assert needle in src
src=src.replace(needle,'''    std::unique_ptr<Design> finished_front;
    double perforation_weight=.7;
    auto finish = [&](Design* des,bool raw=false,bool skip_front=false) {''')
src=src.replace('    if(!raw) {\n    if (climb_iters > 0)',
                '    if(!raw&&!skip_front) {\n    if (climb_iters > 0)')
src=src.replace('    if(raw)return state;','    if(raw)return state;\n    if(!skip_front)finished_front=std::make_unique<Design>(*des);')
src=src.replace('perforation.run(0.7);','perforation.run(perforation_weight);')
needle='        } else if(mode) {\n            des=std::make_unique<Design>(*prefix);'
assert needle in src
src=src.replace(needle,'''        } else if(mode==7&&i) {
            des=std::make_unique<Design>(*finished_front);
        } else if(mode) {
            des=std::make_unique<Design>(*prefix);''')
needle='        auto candidate=finish(des.get());'
assert needle in src
src=src.replace(needle,'''        static constexpr double weights[]{.7,.4,1.,1.3};
        perforation_weight=env_real("DEVAL_PERF_GRID",1)?weights[i%4]:.7;
        auto candidate=finish(des.get(),false,mode==7&&i);''')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vperf

改良元: `solutions/deval-vclean`。

焼きなましと filler climb 154,000 回、再割当て 4 回を共有し、穴あけと最終再割当てだけを 4 通り試す。穴あけの filler 利益の重みは 0.7 / 0.4 / 1.0 / 1.3、乱数 salt は 0–3。`DEVAL_PERF_GRID=0` は重みを全て 0.7 にする。V16 で完成状態を選ぶ。既定の mode は 7。

時間ガード、DesignStore、診断は親と同じ。生成は `solutions/deval-vselect/make_perfselect.py`。
''')
print('source bytes',len(src.encode()))
