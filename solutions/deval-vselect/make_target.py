"""Freeze the target-specific, control-variate V on seeds 0-499 and integrate it."""
from pathlib import Path
import json,re,sys
import numpy as np
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vtarget'
sys.path.insert(0,str(HERE.parent/'deval-model'))
from fit import linear_fit
from target_qmc import independent_samples,control_variates

def main():
    spec=json.loads((HERE/'target_cv_qmc_16.validation.json').read_text())
    data=np.load(HERE/'target_cv_qmc_16.npz')
    coef,bias=linear_fit(data['X'],data['Y'].mean(axis=2),spec['alpha'])
    spec.update(coefficients=coef.tolist(),intercept=bias,training_seeds='0-499')
    DEST.mkdir(exist_ok=True)
    (DEST/'V.json').write_text(json.dumps(spec,indent=2))
    src=(HERE/'main.cpp').read_text()
    lo=src.index('__attribute__((target("popcnt"))) inline CoverResult expectation(')
    hi=src.index('} // namespace deval',lo)
    src=src[:lo]+control_variates(independent_samples(src[lo:hi]))+src[hi:]
    src=re.sub(r'inline constexpr double kIntercept=[^;]+;',f'inline constexpr double kIntercept={bias:.17g};',src)
    lo=src.index('inline constexpr std::array<ModelTerm,142> kTerms{{')
    hi=src.index('\n}};',lo)+4
    terms='inline constexpr std::array<ModelTerm,142> kTerms{{\n'+''.join('    {"%s",%.17g},\n'%(n,c) for n,c in zip(spec['feature_names'],coef))+'}};'
    src=src[:lo]+terms+src[hi:]
    src=src.replace('int nSamples=32','int nSamples=16')
    src=src.replace('batch==1?32:screen_samples','batch==1?16:screen_samples')
    src=src.replace('env_real("DEVAL_ELITE_SAMPLES",32)','env_real("DEVAL_ELITE_SAMPLES",16)')
    src=src.replace('// V selects completed designs;', '// V16 with target-specific Sobol shifts and exact mismatch control variates selects designs;')
    assert len(src.encode())<=520000,len(src.encode())
    (DEST/'main.cpp').write_text(src)
    readme=(HERE/'README.md').read_text().replace('# deval-vselect','# deval-vtarget',1)
    readme=readme.replace('改良元: `solutions/argon-des-perf-latew105`。評価関数は `solutions/deval-model` の固定済み V。',
        '改良元: `solutions/deval-vselect`（その親は `solutions/argon-des-perf-latew105`）。V の積分を改良した比較実験用の解法。')
    readme=readme.replace('V は固定した 32 個の Sobol 積分点、列上端色の平均場更新 2 回、142 特徴量の線形結合。積分点は XOR 基底から復元する。評価関数の係数は Task 1 の学習 seed 0–499 で固定したものを使う。',
        'V は 16 個の Sobol 点を対象ごとに固定 digital shift して使う。不一致数の単独期待値は解析的に積分し、filler の被覆効果だけを数値積分する。平均場更新は 2 回、142 特徴量の線形結合。学習は seed 0–399、選択は 400–499、係数の最終推定は 0–499。テスト seed 500–999 は使用していない。')
    readme+='\n生成は `solutions/deval-vselect/make_target.py`。元の実験用インターフェースを保ち、V の係数と積分方法だけを変更する。`V.json` が固定したモデルの定義。\n'
    (DEST/'README.md').write_text(readme)
    print('source bytes',len(src.encode()))
if __name__=='__main__':main()
