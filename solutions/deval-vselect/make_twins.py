"""Spend the anneal budget on fewer branches and diversify their finishing."""
from pathlib import Path
from make_col import refresh_contents
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vtwins'
src=(HERE.parent/'deval-vcompact/main.cpp').read_text()
src=src.replace('    const int candidates=4;',
    '''    const int raw_branches=std::clamp(int(env_real("DEVAL_RAW_BRANCHES",2)),1,4);
    const int finishes=std::clamp(int(env_real("DEVAL_FINISHES",2)),1,4);
    const int candidates=raw_branches*finishes;''')
src=src.replace('    const int climb_env = 50000,','    const int climb_env = env_int("CLIMB_ITERS"),')
src=src.replace('std::max(1,int(2)), 1.0, 2.0','std::max(1,int(env_real("DEVAL_MATCH_ITERS",2))), 1.0, 2.0')
needle='    const auto prefix=std::make_unique<Design>(*des);\n'
assert needle in src
src=src.replace(needle,needle+'''    // ==== design_papers: paired completions of longer branches ====
    std::vector<Design> raw;
    for(int branch=0;branch<raw_branches;++branch) {
        des=std::make_unique<Design>(*prefix);
        des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;
        des->anneal_reheat=branch?env_real("DEVAL_REHEAT",2.):1.;
        des->reheat_start=shared/4.;
        const double begin=elapsed_sec();
        des->anneal(1e300,anneal_iters/raw_branches,shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        raw.push_back(*des);
    }
''')
lo=src.index('        des=std::make_unique<Design>(*prefix);',src.index('    for(int i=0;i<candidates;++i)'))
hi=src.index('        std::ostringstream log;',lo)
src=src[:lo]+'''        des=std::make_unique<Design>(raw[i/finishes]);
        des->rng.x^=u64(i%finishes)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();
'''+src[hi:]
src=refresh_contents(src)
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vtwins

改良元: `solutions/deval-vcompact`。

前半2段を共有し、後半は2分岐へ半分ずつ反復数を配る。それぞれを異なる固定saltで2回仕上げ、計4候補をV16で選ぶ。焼きなましの合計反復数と仕上げ回数は4分岐案と同じだが、各分岐を長くして、その後の仕上げで多様性を得る。

`DEVAL_RAW_BRANCHES`は焼きなましの分岐数（既定2）、`DEVAL_FINISHES`は各分岐の仕上げ回数（既定2）。`CLIMB_ITERS`と`DEVAL_MATCH_ITERS`は仕上げ予算。後発分岐の温度倍率は2。Vの表共有、提出時のガード、ログと保存は親と同じ。生成は `solutions/deval-vselect/make_twins.py`。
''')
print('source bytes',len(src.encode()))
