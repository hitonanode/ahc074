"""Diversify late branches by a temperature bump that decays to zero."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vreheat'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
src=src.replace('    std::vector<Design>* elite_states=nullptr;',
    '    double anneal_reheat=1.,reheat_start=.5;\n    std::vector<Design>* elite_states=nullptr;')
needle='                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);'
assert needle in src
src=src.replace(needle,needle+'\n                    temp*=std::pow(D.anneal_reheat,(1-p0-(p1-p0)*progress)/(1-D.reheat_start));')
needle='        if(mode==1)des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);'
assert needle in src
src=src.replace(needle,'''        if(mode==1) {
            des->anneal_reheat=i?env_real("DEVAL_REHEAT",4.):1.;
            des->reheat_start=shared/4.;
            des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        }''')
needle='            des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;'
src=src.replace(needle,needle+'\n            des->anneal_reheat=branch?env_real("DEVAL_REHEAT",4.):1.;des->reheat_start=shared/4.;')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vreheat

改良元: `solutions/deval-vclean`。

後半を分岐する際、候補 0 は元の温度を保ち、その他は温度を一時的に上げる。開始温度の倍率 `DEVAL_REHEAT` は既定 4 で、最後の温度は親と同じ 0.015 になるよう指数的に倍率を 1 へ戻す。目的関数と総反復数は同じ。V16 で完成候補を選択する。

候補数、仕上げ、時間ガード、保存形式は親と同じ。生成は `solutions/deval-vselect/make_reheat.py`。
''')
print('source bytes',len(src.encode()))
