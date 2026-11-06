"""Branch a shared anneal; screen snapshots with the fitted cheap head features."""
from pathlib import Path
import json,re
from make_col import stripped_source,refresh_contents
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vbeam'

def main():
    src=stripped_source()
    assert 'const double temperature_floor=env_real("DEVAL_TEMP_FLOOR",0);' in src
    src=src.replace('const double temperature_floor=env_real("DEVAL_TEMP_FLOOR",0);',
        'const double temperature_floor=env_real("DEVAL_TEMP_FLOOR",0.);\n            const double temperature_start=env_real("DEVAL_TEMP_START",2.0),temperature_end=env_real("DEVAL_TEMP_END",.015);')
    src=src.replace('2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress)',
                    'temperature_start * std::pow(temperature_end / temperature_start, p0 + (p1 - p0) * progress)')
    spec=json.loads((HERE/'prescreen_head_state.final.json').read_text())
    n=len(spec['coefficients'])
    names=re.findall(r'\{"([^"]+)",[^}]+\}',src[src.index('inline constexpr std::array<ModelTerm,142>'):])[:142]
    assert names[:n]==spec['feature_names']
    lo=src.index('    template<class DesignState> FeatureMap features_from_design(')
    end=src.index('\n    }',lo)+6
    method=src[lo:end].replace('features_from_design','head_features_from_design')
    method=method.replace('add_stationary_features(features,s,nSamples,2);',
        'const auto p=s.probabilities(2.); const Donors donors(s,p); features["f_s2_headutility"]=donors.head_utility(s,p);')
    src=src[:end]+'\n'+method+src[end:]
    code='''// ==== Cheap prediction of the completed design from a snapshot ====
// Fitted only on seeds 0-499. The inputs are static state properties and the
// analytic value of the column heads; no quadrature or request planner is used.
double prescreen_value(const DesignState& state,const deval::DesignValue& model) {
'''
    code+=f'    static constexpr std::array<double,{n}> weights{{'+','.join(f'{c:.17g}' for c in spec['coefficients'])+'};\n'
    code+=f'    double value={spec["intercept"]:.17g};\n'
    code+='''    const auto features=model.head_features_from_design(state);
    for(int i=0;i<int(weights.size());++i)value+=weights[i]*features.at(deval::kTerms[i].name);
    return value;
}
'''
    src=src.replace('// ==== Design iteration counts ====',code+'\n// ==== Design iteration counts ====')
    src=src.replace('const int mode=env_int("DEVAL_MODE");','const int mode=int(env_real("DEVAL_MODE",5));')
    src=src.replace('env_int("DEVAL_CANDIDATES"):1','env_int("DEVAL_CANDIDATES"):2')
    src=src.replace('const int shared=mode>=2?4:', 'const int branches=std::clamp(int(env_real("DEVAL_BRANCHES",4)),1,8);\n    const int shared=(mode>=2&&mode!=5)?4:')
    src=src.replace('env_real("DEVAL_BRANCH_SCALE",1.0/candidates)', 'env_real("DEVAL_BRANCH_SCALE",1.0/(mode==5?branches:candidates))')
    src=src.replace('    if(mode==4) {','''    if(mode==5) {
        double begin=elapsed_sec();
        des->anneal(1e300,anneal_iters,0,shared);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        const auto common=std::make_unique<Design>(*des);
        for(int branch=0;branch<branches;++branch) {
            des=std::make_unique<Design>(*common);
            des->rng.x^=u64(branch)*0x9E3779B97F4A7C15ULL;
            const int direction=branch==0?0:(branch&1)?(branch+1)/2:-branch/2;
            des->local_objective=direction*env_real("DEVAL_BRANCH_OBJECTIVE",0.);
            std::vector<Design> tail;
            des->elite_limit=std::clamp(int(env_real("DEVAL_ELITES",8)),0,32);
            des->elite_start=shared/4.;des->elite_end=1.;des->elite_current=true;
            des->elite_states=des->elite_limit?&tail:nullptr;
            begin=elapsed_sec();
            des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
            anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
            des->elite_states=nullptr;
            for(auto& snapshot:tail)elites.push_back(std::move(snapshot));
            elites.push_back(*des);
        }
        prefix=std::make_unique<Design>(*des);
    } else if(mode==4) {''')
    # The first mode==3 initializes capture for the single trajectory. The later
    # block screens a completed pool, and the candidate loop uses its ranking.
    src=src.replace('    if(mode==3) {\n        elites.push_back(*des);',
                    '    if(mode==3||mode==5) {\n        if(mode==3)elites.push_back(*des);')
    src=src.replace('ranked.emplace_back(value.from_design(raw,std::clamp(int(env_real("DEVAL_ELITE_SAMPLES",16)),1,32)),i);',
                    'ranked.emplace_back(prescreen_value(raw,value),i);')
    src=src.replace('env_real("DEVAL_KEEP_FINAL",1)', 'env_real("DEVAL_KEEP_FINAL",0)')
    src=src.replace('        if(mode==3) {\n            if(i>=int(elite_order.size()))',
                    '        if(mode==3||mode==5) {\n            if(i>=int(elite_order.size()))')
    src=src.replace('(mode==3?elite_order[i]:i)', '((mode==3||mode==5)?elite_order[i]:i)')
    src=refresh_contents(src)
    assert len(src.encode())<=520000,len(src.encode())
    DEST.mkdir(exist_ok=True)
    (DEST/'main.cpp').write_text(src)
    (DEST/'prescreen.json').write_text(json.dumps(spec,indent=2))
    (DEST/'README.md').write_text('''# deval-vbeam

改良元: `solutions/deval-vtarget`。焼きなまし途中の状態を安く選別するモデルを追加する。

既定では最初の 2 段を共有し、後半 2 段を 4 通りの乱数 salt で分岐する。各分岐の反復数は元の 1/4 で、合計反復数は SOTA と同じ。各分岐から途中の現在状態 8 個と目的値最良の最終状態を集める。

各状態を列・穴・ペアなどの静的特徴と先頭 filler の解析的価値で順位付けし、上位 2 個を仕上げる。選別器は seed 0–399 で学習し、400–499 で検証した後、0–499 で再推定。入力は設計状態だけで、将来の注文や焼きなましの進行度を使わない。最終的には対象ごとの積分点と解析的な補正を使う V16 で選ぶ。

`DEVAL_BRANCHES` は分岐数、`DEVAL_SHARED` は共有段数、`DEVAL_BRANCH_SCALE` は分岐の反復数倍率。`DEVAL_CANDIDATES` は仕上げる候補数。`DEVAL_ELITES` は分岐ごとの途中状態数。通常の段の反復数は親と同じ。

設計が遅い場合は追加候補を省略する。提出時は 1.72 秒から軽量リクエスト処理に切り替える（LOCAL_BENCH では無効）。DesignStore と @paper/@ops を維持する。生成は `solutions/deval-vselect/make_beam.py`、選別器は `prescreen.json`。
''')
    print('source bytes',len(src.encode()))
if __name__=='__main__':main()
