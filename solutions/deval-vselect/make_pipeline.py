"""Successive finishing: rank after climb/matching, then perforate finalists."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vpipeline'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
src=src.replace('env_real("DEVAL_MODE",1)','env_real("DEVAL_MODE",5)')
src=src.replace('env_int("DEVAL_CANDIDATES"):4','env_int("DEVAL_CANDIDATES"):2')
src=src.replace('env_real("DEVAL_BRANCHES",4)','env_real("DEVAL_BRANCHES",8)')
src=src.replace('env_real("DEVAL_ELITES",8)),0,32)','env_real("DEVAL_ELITES",0)),0,32)')
needle='    auto finish = [&](Design* des,bool raw=false) {'
assert needle in src
src=src.replace(needle,'    auto finish = [&](Design* des,bool raw=false,int phase=0) {')
src=src.replace('if (climb_iters > 0) des->filler_climb(1e300, climb_iters);',
                'if (climb_iters > 0&&phase!=2) des->filler_climb(1e300, climb_iters);')
src=src.replace('rematch_probability(*des, std::max(1,int(env_real("DEVAL_MATCH_ITERS",kMatchIterations))), 1.0, 2.0);',
                'rematch_probability(*des, phase?1:std::max(1,int(env_real("DEVAL_MATCH_ITERS",kMatchIterations))), 1.0, 2.0);')
src=src.replace('    if(raw)return state;','    if(raw||phase==1)return state;')
lo=src.index('    if(mode==3||mode==5) {\n        if(mode==3)elites.push_back(*des);')
hi=src.index('    for(int i=0;i<candidates;++i)',lo)
part=src[lo:hi]
part=part.replace('        const double begin=elapsed_sec();',
                    '        const double begin=elapsed_sec();\n        double preview_work=0;')
part=part.replace('            auto raw=finish(&elites[i],true);',
    '''            if(i>=2&&elapsed_sec()>env_real("DEVAL_PREVIEW_LIMIT",1.08))break;
            deval_salt=first_salt+i;
            const double stage_begin=elapsed_sec();
            auto raw=finish(&elites[i],false,1);
            preview_work+=elapsed_sec()-stage_begin;''')
part=part.replace('ranked.emplace_back(prescreen_value(raw,value),i);',
                    'ranked.emplace_back(value.from_design(raw),i);')
part=part.replace('        eval_sec+=elapsed_sec()-begin;',
    '        finish_sec+=preview_work;\n        eval_sec+=elapsed_sec()-begin-preview_work;')
src=src[:lo]+part+src[hi:]
src=src.replace('            des=std::make_unique<Design>(elites[elite_order[i]]);',
    '            des=std::make_unique<Design>(elites[elite_order[i]]);\n            deval_salt=first_salt+elite_order[i];')
src=src.replace('        auto candidate=finish(des.get());','        auto candidate=finish(des.get(),false,2);')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vpipeline

改良元: `solutions/deval-vclean`。

前半 2 段を共有し、後半 2 段を 8 分岐（各 1/8 の反復数）する。全 8 候補に filler climb 50,000 回と再割当て 1 回を実施し、穴あけ前の完成した紙を V16 で評価する。上位 2 候補だけ再割当てをもう 1 回、穴あけ、最終再割当てまで実施し、再度 V16 で選ぶ。焼きなましの合計反復数は SOTA と同じ。

途中選別に実際の注文処理は使わない。候補数は `DEVAL_BRANCHES`、最終候補数は `DEVAL_CANDIDATES`。前半の仕上げは経過 1.08 秒で追加を止め、最終候補は 1.12 秒で追加を止める。提出時の注文処理の時間ガード、保存形式、既存診断は親と同じ。

生成は `solutions/deval-vselect/make_pipeline.py`。
''')
print('source bytes',len(src.encode()))
