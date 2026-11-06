"""Use one cheap Hungarian round to screen a wider set of late branches."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vscreen'
src=(HERE.parent/'deval-vpipeline/main.cpp').read_text()
src=src.replace('env_real("DEVAL_BRANCHES",8)),1,8)','env_real("DEVAL_BRANCHES",12)),1,16)')
src=src.replace('if (climb_iters > 0&&phase!=2)', 'if (climb_iters > 0&&phase!=1)')
src=src.replace('    std::vector<Design>* elite_states=nullptr;',
    '    double anneal_reheat=1.,reheat_start=.5;\n    std::vector<Design>* elite_states=nullptr;')
needle='                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);'
assert needle in src
src=src.replace(needle,needle+'\n                    temp*=std::pow(D.anneal_reheat,(1-p0-(p1-p0)*progress)/(1-D.reheat_start));')
needle='            des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;'
assert needle in src
src=src.replace(needle,needle+'\n            des->anneal_reheat=std::pow(env_real("DEVAL_REHEAT",1.),branch%3);des->reheat_start=shared/4.;')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vscreen

改良元: `solutions/deval-vpipeline`。

前半 2 段を共有した 12 分岐から、再割当て 1 回だけを行った状態の V16 で上位 2 候補を選ぶ。選んだ候補だけ filler climb 50,000 回、再割当て 1 回、穴あけと最終再割当てまで仕上げて V16 で決定する。予備選別の全候補で filler climb を省くことで候補数を増やす。

`DEVAL_REHEAT` を z とすると、分岐開始時の温度倍率は 1, z, z² の繰り返しで、終端では全て 1 に戻す。既定 z=1。総反復数、時間ガード、保存形式は親と同じ。生成は `solutions/deval-vselect/make_screen.py`。
''')
print('source bytes',len(src.encode()))
