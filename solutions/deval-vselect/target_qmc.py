"""Independent digital Sobol shifts per target; fit/validate on seeds below 500.

Run this whole program under runs/.lock, including its compilation.
"""
from pathlib import Path
import os,sys,json,subprocess,re
import numpy as np
HERE=Path(__file__).resolve().parent
MODEL=HERE.parent/'deval-model'
sys.path.insert(0,str(MODEL))
from prepare import state_file
from fit import linear_fit,group_metrics,summarize

def independent_samples(source):
    lo=source.index('    std::vector<U64> color_masks(nSample);')
    hi=source.index('    // A target\'s donor intervals',lo)
    source=source[:lo]+'''    std::array<std::uint32_t,MaxH> threshold{};
    for(int c=0;c<s.H;++c)threshold[c]=std::uint32_t(std::clamp(prob[c],0.,1.)*1073741824.);
    static const auto shifts=[] {
        std::array<std::array<std::uint32_t,MaxH>,P> shifts{};
        for(int t=0;t<P;++t)for(int c=0;c<MaxH;++c) {
            std::uint32_t h=0x9e3779b9U*(1+t*MaxH+c);
            h^=h>>16;h*=0x7feb352dU;h^=h>>15;h*=0x846ca68bU;h^=h>>16;
            shifts[t][c]=h&0x3fffffffU;
        }
        return shifts;
    }();
    std::vector<std::array<std::uint32_t,MaxH>> draws(nSample);
    for(int i=0;i<nSample;++i)for(int c=0;c<s.H;++c)
        draws[i][c]=std::uint32_t(samples[i*s.H+c]*1073741824.);
'''+source[hi:]
    source=source.replace('            const U64 colors=color_masks[sample];','''            U64 colors=0;
            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;''')
    return source

def control_variates(source):
    """Integrate the uncoupled mismatch exactly; sample only donor coverage."""
    source=source.replace('        const U64 holes=all&~s.op[own];','''        const U64 holes=all&~s.op[own];
        double exact_raw=0;
        for(U64 z=holes;z;z&=z-1) {
            const int c=std::countr_zero(z),b=s.hb[t]>>c&1;
            const double mismatch=b?1-prob[c]:prob[c];
            exact_raw+=mismatch;ans.flips[c][b]+=mismatch;
        }''')
    source=source.replace('row{double(raw),raw-dp[s.H],double(fixes),',
                          'row{exact_raw,exact_raw-dp[s.H],exact_raw-(raw-fixes),')
    source=source.replace('for(U64 z=left;z;z&=z-1)', 'for(U64 z=wrong&covered;z;z&=z-1)')
    source=source.replace('ans.flips[c][s.hb[t]>>c&1]+=1./nSample;', 'ans.flips[c][s.hb[t]>>c&1]-=1./nSample;')
    source=source.replace('    return ans;','    for(auto& f:ans.flips)for(double& x:f)x=std::max(0.,x);\n    return ans;')
    return source

def main():
    source=(MODEL/'surrogate.hpp').read_text()
    shared=os.environ.get('QMC_SHARED')=='1'
    control=os.environ.get('QMC_CONTROL')=='1'
    if not shared:source=independent_samples(source)
    if control:source=control_variates(source)
    prefix=('shared' if shared else 'target')+('_cv' if control else '')+'_qmc'
    (HERE/'surrogate_target.hpp').write_text(source)
    features=(MODEL/'design_features.hpp').read_text().replace('"surrogate.hpp"','"surrogate_target.hpp"')
    for f in ['poset_data.hpp','quadrature.hpp']: features=features.replace('"'+f+'"','"../deval-model/'+f+'"')
    (HERE/'features_target.hpp').write_text(features)
    value=(MODEL/'value.hpp').read_text().replace('"design_features.hpp"','"features_target.hpp"')
    (HERE/'value_target.hpp').write_text(value)
    (HERE/'features_target.cpp').write_text('''#include "value_target.hpp"
#include <fstream>
#include <iostream>
int main(int argc,char** argv) {
    const int n=std::stoi(argv[1]);deval::GenericTable generic;
    std::string path;
    while(std::getline(std::cin,path)) {
        std::ifstream in(path);if(!in)return 1;
        auto state=deval::State::read(in);
        auto f=deval::static_features(state,generic);
        deval::add_stationary_features(f,state,n,2);
        std::array<double,deval::kTerms.size()> row{};
        for(int j=0;j<int(row.size());++j)row[j]=f.at(deval::kTerms[j].name);
        std::cout.write(reinterpret_cast<const char*>(row.data()),sizeof(row));
    }
}
''')
    subprocess.run(['g++','-std=c++23','-O2','-mpopcnt',str(HERE/'features_target.cpp'),'-o',str(HERE/'features_target')],check=True)
    manifest=[l.split('\t') for l in (MODEL/'runs.tsv').read_text().splitlines() if l!='done']
    paths=[str(state_file(row[1],s)) for s in range(500) for row in manifest]
    d=np.load(MODEL/'models/final_predictions.npz')
    Y=d['Y'][:500];tags=d['variants'].tolist()
    names=[v[0] for v in re.findall(r'\{"([^"]+)",([^}]+)\}',value)]
    reference=json.loads((MODEL/'models/stationary32_all.metrics.json').read_text())
    print('original validation',reference['models']['stationary32_all']['all']['r'],flush=True)
    out=[]
    for n in [16,32] if control else [8,16,32]:
        cache=HERE/f'{prefix}_{n}.npz'
        if cache.exists(): X=np.load(cache)['X']
        else:
            binary=subprocess.run([str(HERE/'features_target'),str(n)],input=('\n'.join(paths)+'\n').encode(),capture_output=True,check=True).stdout
            X=np.frombuffer(binary,dtype=np.float64).reshape(500,7,len(names))
            np.savez_compressed(cache,X=X,Y=Y,names=names)
        best=(-1,None)
        for alpha in [.01,.1,1.,10.,100.,1000.,10000.]:
            coef,bias=linear_fit(X[:400],Y[:400].mean(axis=2),alpha)
            metrics=group_metrics(X[400:]@coef+bias,Y[400:],tags)
            r=metrics['all']['r']
            if r>best[0]:best=(r,(alpha,coef,bias,metrics))
        alpha,coef,bias,metrics=best[1]
        print('points',n,'alpha',alpha,summarize('target_qmc',metrics),flush=True)
        spec={'experiment':f'{prefix}_{n}','n_samples':n,'coefficients':coef.tolist(),'intercept':bias,'feature_names':names,
              'shared':shared,'control':control,
              'training_seeds':'0-399','validation_seeds':'400-499','alpha':alpha,'metrics':metrics}
        (HERE/f'{prefix}_{n}.validation.json').write_text(json.dumps(spec,indent=2))
        out.append(spec)
    (HERE/f'{prefix}_summary.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
