"""Diversify late branches with generic cost tables, without hot-path branches."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vmix'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
src=src.replace('    std::vector<Design>* elite_states=nullptr;',
    '    double anneal_reheat=1.,reheat_start=.5;\n    std::vector<Design>* elite_states=nullptr;')
needle='                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);'
assert needle in src
src=src.replace(needle,needle+'\n                    temp*=std::pow(D.anneal_reheat,(1-p0-(p1-p0)*progress)/(1-D.reheat_start));')
needle='        if(mode==1)des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);'
assert needle in src
src=src.replace(needle,'''        if(mode==1) {
            const int direction=i==0?0:(i&1)?(i+1)/2:-i/2;
            const double scale=1+direction*env_real("DEVAL_GENERIC_SPREAD",.15);
            if(i)for(auto& row:des->gcost)for(auto& cost:row)cost*=scale;
            des->anneal_reheat=i?env_real("DEVAL_REHEAT",1.):1.;
            des->reheat_start=shared/4.;
            des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
            des->gcost=prefix->gcost;
            des->refresh_reset();
        }''')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vmix

改良元: `solutions/deval-vclean`。

後半 4 分岐の generic ペア費用をそれぞれ 1.0 / 1.15 / 0.85 / 1.30 倍として、違う傾向の候補を作る。倍率は開始時に費用表へ掛けるため、焼きなまし内側の更新処理は親と同じ。仕上げの前に元の表を正確に戻し、V16 で完成候補を選ぶ。`DEVAL_GENERIC_SPREAD` は倍率間隔（既定 0.15）。`DEVAL_REHEAT` は第 2 候補以降の開始温度倍率で、最後に 1 へ戻す（既定 1）。

反復数・仕上げ・時間ガード・保存形式は親と同じ。生成は `solutions/deval-vselect/make_mix.py`。
''')
print('source bytes',len(src.encode()))
