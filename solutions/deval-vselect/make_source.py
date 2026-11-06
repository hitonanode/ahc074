"""Integrate the frozen V and candidate selection; never modify the parent solver."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MODEL = ROOT / 'solutions/deval-model'
src = (ROOT / 'solutions/argon-des-perf-latew105/main.cpp').read_text()

def strip_header(name):
    s = (MODEL / name).read_text()
    return re.sub(r'^#(?:pragma once|include[^\n]*)\n', '', s, flags=re.M)

# Sobol samples form an affine binary map of the sample index. Keep its shift
# and five basis vectors instead of 128 floating-point points for each H.
original = (MODEL / 'quadrature.hpp').read_text()
quad = ['namespace deval {\n// ==== V: compact fixed quadrature ====\n']
for h in (25, 31, 35):
    body = re.search(r'kSamples%d\{(.*?)\};' % h, original, re.S).group(1)
    samples = [float(x) for x in body.replace('\n', '').split(',') if x.strip()]
    values = [[round(x * (1 << 30)) for x in samples[i*h:(i+1)*h]] for i in range(32)]
    basis = [values[0]] + [[values[1 << b][j] ^ values[0][j] for j in range(h)] for b in range(5)]
    for i in range(32):
        for j in range(h):
            v = basis[0][j]
            for b in range(5):
                if i >> b & 1: v ^= basis[b+1][j]
            assert v / (1 << 30) == samples[i*h+j]
    quad.append('inline constexpr std::uint32_t kBasis%d[6][%d]={\n' % (h, h))
    quad.extend('    {' + ','.join(map(str, row)) + '},\n' for row in basis)
    quad.append('};\n')
quad.append('''inline const double* samples_for(int H) {
    static std::array<double,32*35> samples{};
    static int cachedH=0;
    if(cachedH!=H) {
        assert(H==25||H==31||H==35);
        const std::uint32_t* basis=H==25?&kBasis25[0][0]:H==31?&kBasis31[0][0]:&kBasis35[0][0];
        for(int i=0;i<32;++i) for(int j=0;j<H;++j) {
            auto v=basis[j];
            for(int b=0;b<5;++b)if(i>>b&1)v^=basis[(b+1)*H+j];
            samples[i*H+j]=double(v)/1073741824.;
        }
        cachedH=H;
    }
    return samples.data();
}
} // namespace deval
''')
surrogate = strip_header('surrogate.hpp')
lo = surrogate.index('    static State read(')
hi = surrogate.index('    std::array<double,MaxH> probabilities', lo)
surrogate = surrogate[:lo] + surrogate[hi:]
features = strip_header('design_features.hpp').replace('kClasses', 'kPosetClasses')
value = strip_header('value.hpp')
value = value.replace('double operator()(State state) const', 'double operator()(State state,int nSamples=32) const')
value = value.replace('add_stationary_features(features,state,32,2)', 'add_stationary_features(features,state,nSamples,2)')
value = value.replace('from_design(const DesignState& d) const', 'from_design(const DesignState& d,int nSamples=32) const')
value = value.replace('return (*this)(s);', 'return (*this)(s,nSamples);')
adapter=value[value.index('    template<class DesignState>'):value.index('\n};\n} // namespace deval')]
feature_adapter=adapter.replace('double from_design(', 'FeatureMap features_from_design(')
feature_adapter=feature_adapter.replace('return (*this)(s,nSamples);',
    's.prepare(); auto features=static_features(s,generic_); add_stationary_features(features,s,nSamples,2); return features;')
value=value.replace('\n};\n} // namespace deval','\n'+feature_adapter+'\n};\n} // namespace deval')
vcode = surrogate + ''.join(quad) + features + value
# The problem's x86 judge supports POPCNT. Keep floating-point arithmetic
# unchanged; only compile the bit-mask kernels with the hardware instruction.
vcode = vcode.replace('inline CoverResult expectation(', '__attribute__((target("popcnt"))) inline CoverResult expectation(')
vcode = vcode.replace('inline FeatureMap static_features(', '__attribute__((target("popcnt"))) inline FeatureMap static_features(')
vcode = vcode.replace('    std::pair<double,int> cost(', '    __attribute__((target("popcnt"))) std::pair<double,int> cost(')
vcode += '''
// ==== V: swaps of completed target assignments ====
// A proposal exchanges complete single/pair target units between physical slots.
// Generic compatibility is unchanged. Keep each slot's perforations, require
// the unit to agree on its own handle, and preserve both colors in every column.
int deval_refine(DesignState& state,const deval::DesignValue& value,double& best,int trials) {
    std::array<std::vector<int>,K> owners;
    std::array<u64,K> extra{};
    std::array<std::array<int,2>,64> counts{};
    std::vector<int> slots;
    auto natural_mask=[&](const std::vector<int>& targets,int c) {
        u64 mask=low_bits(state.G)|kCapBit;
        for(int j=0;j<=c;++j)mask|=u64(1)<<state.handle[j];
        if(targets.size()==2)mask&=~(state.A[targets[0]]^state.A[targets[1]]);
        return mask|kCapBit;
    };
    for(int t=0;t<P;++t)owners[state.ded[t]].push_back(t);
    for(int k=0;k<K;++k)if(state.columns[k]>=0) {
        const int c=state.columns[k];slots.push_back(k);
        extra[k]=natural_mask(owners[k],c)&~state.papers[k].opaque;
        ++counts[c][state.A[owners[k][0]]>>state.handle[c]&1];
    }
    XorShift rng{0x1fa734c53a2921ULL};
    const int batch=std::clamp(int(env_real("DEVAL_REFINE_BATCH",1)),1,32);
    const int screen_samples=std::clamp(int(env_real("DEVAL_SCREEN_SAMPLES",8)),1,32);
    int accepted=0;
    for(int it=0;it<trials;++it) {
        if(elapsed_sec()>1.2)break;
        DesignState selected;
        double selected_value=1e100;
        int selected_a=-1,selected_b=-1;
        for(int proposal=0;proposal<batch;++proposal) {
        int a=-1,b=-1,ca=0,cb=0,aa=0,ab=0,ba=0,bb=0;
        bool found=false;
        for(int attempt=0;attempt<40;++attempt) {
            a=slots[rng.below(slots.size())];b=slots[rng.below(slots.size())];
            if(a==b)continue;
            ca=state.columns[a];cb=state.columns[b];
            if((it&1)&&std::abs(ca-cb)>4)continue;
            const auto& x=owners[a];const auto& y=owners[b];
            if((x.size()==2&&((state.A[x[0]]^state.A[x[1]])>>state.handle[cb]&1))||
               (y.size()==2&&((state.A[y[0]]^state.A[y[1]])>>state.handle[ca]&1)))continue;
            aa=state.A[x[0]]>>state.handle[ca]&1;ab=state.A[x[0]]>>state.handle[cb]&1;
            ba=state.A[y[0]]>>state.handle[ca]&1;bb=state.A[y[0]]>>state.handle[cb]&1;
            if(ca!=cb&&((aa!=ba&&counts[ca][aa]==1)||(ab!=bb&&counts[cb][bb]==1)))continue;
            found=true;break;
        }
        if(!found)continue;
        auto candidate=state;
        auto install=[&](int slot,const std::vector<int>& targets) {
            const u64 mask=natural_mask(targets,state.columns[slot])&~extra[slot];
            u64 black=state.A[targets[0]]&mask;
            if(targets.size()==2&&((state.A[targets[0]]^state.A[targets[1]])&kCapBit))black&=~kCapBit;
            candidate.papers[slot]={mask,black};
            for(int t:targets)candidate.ded[t]=slot;
        };
        install(a,owners[b]);install(b,owners[a]);
        const double v=value.from_design(candidate,batch==1?32:screen_samples);
        if(v<selected_value) {
            selected_value=v;selected=std::move(candidate);selected_a=a;selected_b=b;
        }
        }
        if(selected_a<0)continue;
        const double v=batch==1?selected_value:value.from_design(selected);
        if(v<best) {
            const int a=selected_a,b=selected_b;
            const int ca=state.columns[a],cb=state.columns[b];
            const int aa=state.A[owners[a][0]]>>state.handle[ca]&1,ab=state.A[owners[a][0]]>>state.handle[cb]&1;
            const int ba=state.A[owners[b][0]]>>state.handle[ca]&1,bb=state.A[owners[b][0]]>>state.handle[cb]&1;
            best=v;state=std::move(selected);++accepted;
            --counts[ca][aa];++counts[ca][ba];--counts[cb][bb];++counts[cb][ab];
            std::swap(owners[a],owners[b]);
        }
    }
    return accepted;
}
'''
src = src.replace('#include <algorithm>', '#include <algorithm>\n#include <bit>\n#include <map>\n#include <unordered_map>\n#include <stdexcept>\n#include <sstream>\n#include <functional>')
src = src.replace('// ==== Design iteration counts ====','// ==== V: design-only expected moves ====\n' + vcode + '\n// ==== Design iteration counts ====')
src = src.replace('struct MatchStats {', '''// Empty for ordinary finishing. The final design-only search can accept a
// complete Hungarian cycle using V instead of its linear proposal model.
std::function<double(const Design&)> deval_match_merit;
struct MatchStats {''')
src = src.replace('    double initial = head.model_cost() - weight * head.last_value, merit = initial;',
                  '    double initial = deval_match_merit?deval_match_merit(d):head.model_cost() - weight * head.last_value, merit = initial;')
src = src.replace('        std::vector<int> anchor(d.U, -1), mobile(d.U), color(d.U);',
                  '        if(deval_match_merit && elapsed_sec()>1.2)break;\n        std::vector<int> anchor(d.U, -1), mobile(d.U), color(d.U);')
src = src.replace('            double next = head.model_cost() - weight * head_value;',
                  '            double next = deval_match_merit?deval_match_merit(d):head.model_cost() - weight * head_value;')

# Run any consecutive schedule segments while keeping their original temperatures.
src = src.replace('void anneal(double seconds, int fixedIterations = 0) {',
                  'void anneal(double seconds, int fixedIterations = 0, int firstSegment = 0, int endSegment = 4) {')
src = src.replace('for (int s = 0; s < kAnnealSegments; s++) {',
                  'for (int s = firstSegment; s < endSegment; s++) {')
src = src.replace('    double cur = 0;\n    int anneal_iters', '''    double cur = 0;
    double local_objective=0;
    std::vector<Design>* elite_states=nullptr;
    int elite_limit=16;
    double elite_start=.5;
    double elite_end=1;
    bool elite_current=false;
    int anneal_iters''')
# Interpolate toward the seven-term local fit, normalized to the old column
# coefficient. Only annealing uses this objective; finishing uses its own model.
src = src.replace('    double hcost(int j) const { return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]); }', '''    double hcost(int j) const {
        const double q=hole_cost_of(hn[j][0],hn[j][1],reset_targets[j]);
        if(!local_objective)return q;
        const double x=hn[j][0],y=hn[j][1],b=std::min(x,y)/std::max(1.,x+y);
        const double f=(2./(.4850075367537387*1.52))*(.6983460212096222+.18884350564854607*j/(H-1.)
                       -.35141093906333204*(j==H-1)-1.5883383903008574*b+1.9585634975419637*b*b);
        return q*(1+local_objective*(f-1));
    }''')
src = src.replace('gcost[u.a][u.b] * 2; }', 'gcost[u.a][u.b] * 2 * (1+local_objective*(.7096096589540385/.4850075367537387-1)); }')
src = src.replace('        std::vector<ColRow> rows;', '''        alignas(32) float local_base[L]={};
        float local_b1=0,local_b2=0;
        std::vector<ColRow> rows;''')
src = src.replace('ANNEAL_TARGET static float qf(float a, float b, float reset) {\n            const float s = a + b + reset;\n            return (a * b + .5f * reset * std::min(a, b)) / (s > 1.f ? s : 1.f);', '''ANNEAL_TARGET float qf(float a, float b, float reset,int j) const {
            const float s = a + b + reset;
            float q=(a * b + .5f * reset * std::min(a,b))/(s>1.f?s:1.f);
            if(D.local_objective) {
                const float balance=std::min(a,b)/std::max(1.f,a+b);
                q*=local_base[j]+balance*(local_b1+balance*local_b2);
            }
            return q;''')
src = src.replace('qf(n0[j], n1[j], reset[j])','qf(n0[j], n1[j], reset[j],j)')
src = src.replace('qf(na0, na1, reset[a])','qf(na0, na1, reset[a],a)').replace('qf(nb0, nb1, reset[b])','qf(nb0, nb1, reset[b],b)')
src = src.replace('                Q[r] = _mm256_div_ps(numerator, s);', '''                Q[r] = _mm256_div_ps(numerator, s);
                if(D.local_objective) {
                    const __m256 b=_mm256_div_ps(_mm256_min_ps(N0[r],N1[r]),_mm256_max_ps(one,_mm256_add_ps(N0[r],N1[r])));
                    const __m256 f=_mm256_add_ps(_mm256_load_ps(local_base+8*r),_mm256_mul_ps(b,
                        _mm256_add_ps(_mm256_set1_ps(local_b1),_mm256_mul_ps(b,_mm256_set1_ps(local_b2)))));
                    Q[r]=_mm256_mul_ps(Q[r],f);
                }''')
src = src.replace('            for (int j = 0; j < H; j++) {\n                reset[j]', '''            const double local_scale=D.local_objective*2./(.4850075367537387*1.52);
            local_b1=float(local_scale*-1.5883383903008574);local_b2=float(local_scale*1.9585634975419637);
            for (int j = 0; j < H; j++) {
                local_base[j]=float(1-D.local_objective+local_scale*(.6983460212096222+.18884350564854607*j/(H-1.)-.35141093906333204*(j==H-1)));
                reset[j]''')
needle='                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);'
assert needle in src
src = src.replace(needle,'                    temp = std::max(temperature_floor,2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress));'+'''
                    if(D.elite_states && int(D.elite_states->size())<D.elite_limit &&
                       p0+(p1-p0)*progress >= D.elite_start+(D.elite_end-D.elite_start)*D.elite_states->size()/D.elite_limit) {
                        D.elite_states->push_back(D);
                        auto& out=D.elite_states->back();
                        out.elite_states=nullptr;
                        if(!D.elite_current) {out.unit=best;out.handle=bestHandle;}
                        for(int t=0;t<256;++t) {
                            out.hb[t]=0;
                            for(int c=0;c<H;++c)out.hb[t]|=((out.A[t]>>out.handle[c])&1)<<c;
                        }
                        out.rebuild();
                    }''')
src = src.replace('            double progress = 0;\n            // Handle exchanges',
                  '            double progress = 0;\n            const double temperature_floor=env_real("DEVAL_TEMP_FLOOR",0);\n            // Handle exchanges')

# Fixed salts are shared by initialization, annealing, reassignment and perforation.
salt = '''double env_real(const char* name,double fallback);
// Candidate salt is set only while constructing a design, never by requests.
u64 deval_salt=0;
u64 deval_seed_salt() { return deval_salt*0x9E3779B97F4A7C15ULL; }
'''
src = src.replace('struct XorShift {', salt + '\nstruct XorShift {')
src = src.replace('static constexpr double kClimbProxyWeight = 0.5;', 'inline static double kClimbProxyWeight = 0.5;')
for old,new in [
    ('0x6176abcd1349ULL}', '0x6176abcd1349ULL ^ deval_seed_salt()}'),
    ('rng(0x181ba71c83ULL)', 'rng(0x181ba71c83ULL ^ deval_seed_salt())'),
    ('random(731000003)', 'random(731000003 ^ deval_seed_salt())'),
    ('rng(0xc9a513a1ULL)', 'rng(0xc9a513a1ULL ^ deval_seed_salt())')]:
    assert old in src, old
    src = src.replace(old,new)

start = src.index('DesignState design_papers(')
end = src.index('\n#ifdef LOCAL_BENCH\n// ==== Saving',start)
fn = src[start:end]
head_end = fn.index('    // ==== design_papers: design annealing')
finish_start = fn.index('    if (climb_iters > 0)')
finisher = fn[finish_start:fn.rindex('\n}')]
finisher = finisher.replace('kMatchIterations, 1.0', 'std::max(1,int(env_real("DEVAL_MATCH_ITERS",kMatchIterations))), 1.0')
finish_match=finisher.index('    if (climb_iters > 0)')
finish_cap=finisher.index('    // Restore the cap bit')
finisher=finisher[:finish_match]+'    if(!raw) {\n'+finisher[finish_match:finish_cap]+'    }\n'+finisher[finish_cap:]
finisher=finisher.replace('    // ==== design_papers: handle perforation ====',
                        '    if(raw)return state;\n    // ==== design_papers: handle perforation ====')
head = fn[:head_end]
head = head.replace('    DesignState state;', '''    deval_salt=std::max(0,env_int("DEVAL_SALT"));
    const u64 first_salt=deval_salt;
    const int candidates=std::clamp(env_int("DEVAL_CANDIDATES",2),1,32);
    const int mode=env_int("DEVAL_MODE"); // 0 split, 1 branch, 2 finishing, 3 elites, 4 guided segments
    const int shared=mode>=2?4:std::clamp(int(env_real("DEVAL_SHARED",2)),0,3);
    const double branch_scale=env_real("DEVAL_BRANCH_SCALE",1.0/candidates);
    DesignState state;''')
# env_int in this source accepts one argument, unlike env_real.
head = head.replace('env_int("DEVAL_CANDIDATES",2)', '(std::getenv("DEVAL_CANDIDATES")?env_int("DEVAL_CANDIDATES"):2)')
body = '''    // ==== design_papers: finish each candidate and select by V ====
    auto finish = [&](Design* des,bool raw=false) {
        if(des->local_objective) {des->local_objective=0;des->refresh_reset();}
        DesignState state;
        auto A=des->A;
FINISH
    };
    deval::DesignValue value;
    double best=1e100,first=0,anneal_sec=0,finish_sec=0,eval_sec=0;
    int chosen=-1,finished=0,total_iters=0;
    std::string chosen_log;
    std::unique_ptr<Design> best_design;
    auto initialize = [&](Design& d) {
        auto estimate = [&](u64 a,u64 b) {
            const auto reach=comp.closure(a,a^b);
            u64 r=0;
            for(int s=0;s<M;++s)r|=u64(reach[s])<<(8*s);
            return PosetSums::get().both_of(r)/1440.;
        };
        return d.initialize([&](u64 a,u64 b){return comp.compatible(a,b);},estimate,[](){return false;});
    };
    std::unique_ptr<Design> prefix;
    std::vector<Design> elites;
    std::vector<int> elite_order;
    if(mode==3) {
        des->elite_limit=std::clamp(int(env_real("DEVAL_ELITES",16)),1,64);
        des->elite_start=env_real("DEVAL_ELITE_START",.5);
        des->elite_current=env_int("DEVAL_ELITE_CURRENT")!=0;
        elites.reserve(des->elite_limit+1);
        des->elite_states=&elites;
    }
    if(mode==4) {
        double begin=elapsed_sec();
        des->anneal(1e300,anneal_iters,0,2);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        for(int segment=2;segment<4;++segment) {
            elites.clear();
            des->elite_limit=std::clamp(int(env_real("DEVAL_ELITES",8)),1,64);
            des->elite_start=segment/4.;des->elite_end=(segment+1)/4.;
            des->elite_current=true;des->elite_states=&elites;
            begin=elapsed_sec();
            des->anneal(1e300,anneal_iters,segment,segment+1);
            anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
            des->elite_states=nullptr;elites.push_back(*des);
            begin=elapsed_sec();
            int selected=int(elites.size())-1;
            double merit=1e100;
            std::ostringstream discard;
            auto* old=std::cerr.rdbuf(discard.rdbuf());
            for(int i=0;i<int(elites.size());++i) {
                const auto raw=finish(&elites[i],true);
                if(raw.emergency)continue;
                const double v=value.from_design(raw);
                if(v<merit)merit=v,selected=i;
            }
            std::cerr.rdbuf(old);
            eval_sec+=elapsed_sec()-begin;
            des=std::make_unique<Design>(elites[selected]);
        }
        prefix=std::make_unique<Design>(*des);
    } else if(mode) {
        const double begin=elapsed_sec();
        des->local_objective=env_real("DEVAL_LOCAL_OBJECTIVE",0);
        des->anneal(1e300,anneal_iters,0,shared);
        anneal_sec+=elapsed_sec()-begin;
        total_iters+=des->anneal_iters;
        des->elite_states=nullptr;
        prefix=std::make_unique<Design>(*des);
    }
    if(mode==3) {
        elites.push_back(*des);
        const double begin=elapsed_sec();
        std::vector<std::pair<double,int>> ranked;
        std::ostringstream discard;
        auto* old=std::cerr.rdbuf(discard.rdbuf());
        for(int i=0;i<int(elites.size());++i) {
            auto raw=finish(&elites[i],true);
            if(!raw.emergency)ranked.emplace_back(value.from_design(raw,std::clamp(int(env_real("DEVAL_ELITE_SAMPLES",32)),1,32)),i);
            if(!raw.emergency && env_int("DEVAL_DUMP_FEATURES")) {
                const auto f=value.features_from_design(raw);
                std::ostream diag(old);
                diag.precision(17);diag << "@deval_raw " << i;
                for(const auto& term:deval::kTerms)diag << ' ' << f.at(term.name);
                diag << '\\n';
            }
        }
        std::cerr.rdbuf(old);
        eval_sec+=elapsed_sec()-begin;
        std::sort(ranked.begin(),ranked.end());
        const int final=int(elites.size())-1;
        if(env_real("DEVAL_KEEP_FINAL",1)!=0)elite_order.push_back(final);
        for(auto [v,i]:ranked)if(elite_order.empty()||i!=elite_order[0])elite_order.push_back(i);
    }
    for(int i=0;i<candidates;++i) {
        // Leave enough time for helpers and requests. The first valid design is
        // always finished; a late case keeps its best completed candidate.
        if(i && elapsed_sec()>env_real("DEVAL_DESIGN_LIMIT",1.12))break;
        deval_salt=first_salt+i;
        if(mode==3) {
            if(i>=int(elite_order.size()))break;
            des=std::make_unique<Design>(elites[elite_order[i]]);
        } else if(mode) {
            des=std::make_unique<Design>(*prefix);
            if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        } else if(i) {
            des=std::make_unique<Design>(A,M,G);
            if(!initialize(*des))continue;
        }
        double begin=elapsed_sec();
        des->local_objective=env_real("DEVAL_LOCAL_OBJECTIVE",0);
        // Checkpoints are 256 moves per segment. Align divided budgets so the
        // half-budget experiment uses exactly ANNEAL_ITERS=5587968.
        const int divided=candidates==1?anneal_iters:((anneal_iters/candidates/4+255)/256)*1024;
        if(mode==0)des->anneal(1e300,divided);
        if(mode==1)des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;
        if(mode<2)total_iters+=des->anneal_iters;
        std::ostringstream log;
        auto* old=std::cerr.rdbuf(log.rdbuf());
        Design::kClimbProxyWeight=env_real("DEVAL_CLIMB_WEIGHT",.5)+(env_int("DEVAL_CLIMB_GRID")?.3*i:0.);
        std::cerr << "colswap_tried = " << des->colswap_tried << "\\ncolswap_accepted = " << des->colswap_accepted
                  << "\\nreplace_tried = " << des->replace_tried << "\\nreplace_accepted = " << des->replace_accepted << '\\n';
        begin=elapsed_sec();
        auto candidate=finish(des.get());
        finish_sec+=elapsed_sec()-begin;
        std::cerr.rdbuf(old);
        if(candidate.emergency)continue;
        begin=elapsed_sec();
        const double v=value.from_design(candidate);
        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr << "@deval_final " << (mode==3?elite_order[i]:i) << ' ' << v << '\\n';
        eval_sec+=elapsed_sec()-begin;
        if(!finished)first=v;
        ++finished;
        if(v<best) {
            best=v;chosen=i;state=std::move(candidate);chosen_log=log.str();
            best_design=std::make_unique<Design>(*des);
        }
    }
    if(!finished)state.emergency=true;
    // ==== design_papers: accept assignment cycles by V ====
    const double vmatch_begin=elapsed_sec();
    int vmatch_calls=0,vmatch_accepts=0;
    if(best_design && env_int("DEVAL_VMATCH")>0) {
        auto& d=*best_design;
        std::vector<u64> extra(d.U);
        std::vector<int> slot(d.U);
        for(int x=0;x<d.U;++x) {
            slot[x]=state.ded[d.unit[x].a];
            u64 shown=0;
            for(int c=0;c<d.H;++c)shown|=((state.papers[slot[x]].opaque>>d.handle[c])&1)<<c;
            extra[x]=low_bits(d.H)&~d.holes(d.unit[x])&~shown;
        }
        auto materialize=[&](const Design& next) {
            auto s=state;
            for(int x=0;x<next.U;++x) {
                const auto& u=next.unit[x];const int k=slot[x];
                u64 mask=low_bits(next.G)|kCapBit;
                for(int c=0;c<=u.c;++c)mask|=u64(1)<<next.handle[c];
                if(u.b>=0)mask&=~(s.A[u.a]^s.A[u.b]);
                mask|=kCapBit;
                for(u64 z=extra[x];z;z&=z-1)mask&=~(u64(1)<<next.handle[__builtin_ctzll(z)]);
                u64 black=s.A[u.a]&mask;
                if(u.b>=0&&((s.A[u.a]^s.A[u.b])&kCapBit))black&=~kCapBit;
                s.papers[k]={mask,black};s.ded[u.a]=k;if(u.b>=0)s.ded[u.b]=k;
            }
            return s;
        };
        deval_match_merit=[&](const Design& next) {
            if(vmatch_calls && elapsed_sec()>1.2)return 1e100;
            ++vmatch_calls;
            return value.from_design(materialize(next));
        };
        const auto changed=rematch_probability(d,env_int("DEVAL_VMATCH"),env_real("DEVAL_VMATCH_WEIGHT",1.05),2.,&extra);
        vmatch_accepts=changed.accepted_cycles;
        deval_match_merit={};
        state=materialize(d);
        best=value.from_design(state);
    }
    std::cerr << "dv_vmatch_calls = " << vmatch_calls << "\\ndv_vmatch_accepted = " << vmatch_accepts
              << "\\ndv_vmatch_sec = " << elapsed_sec()-vmatch_begin << '\\n';
    const double refine_begin=elapsed_sec();
    const int refined=state.emergency?0:deval_refine(state,value,best,env_int("DEVAL_REFINE"));
    std::cerr << "dv_refine_accepted = " << refined << "\\ndv_refine_sec = " << elapsed_sec()-refine_begin << '\\n';
    std::cerr << chosen_log;
    std::cerr << "anneal_iters = " << total_iters << "\\nanneal_end_sec = " << elapsed_sec()
              << "\\ndv_candidates = " << finished << "\\ndv_chosen = " << chosen
              << "\\ndv_first = " << first << "\\ndv_best = " << best
              << "\\ndv_anneal_sec = " << anneal_sec << "\\ndv_finish_sec = " << finish_sec
              << "\\ndv_eval_sec = " << eval_sec << '\\n';
    return state;
}
'''.replace('FINISH',finisher)
src = src[:start] + head + body + src[end:]

# A bounded request mode: accept the first valid ordinary plan. On a rare
# invalid ordinary plan continue the same safe search until a valid one exists.
src = src.replace('    Moves process(int u) {', '''    long long light_requests=0,hard_light_requests=0;
    Moves process(int u) {
        int light=0;
#ifndef LOCAL_BENCH
        const double now=elapsed_sec();
        light=now>DEVAL_REQUEST_LIMIT?2:now>1.84?1:0;
#endif
        light_requests+=light>0;
        hard_light_requests+=light==2;''')
src = src.replace('static const bool neutral_enabled = [] {','static const bool neutral_config = [] {')
src = src.replace('        OP_TAG(if (neutral_enabled) ++request_counter;)',
                  '        const bool neutral_enabled=neutral_config && light==0;\n        OP_TAG(if (neutral_enabled) ++request_counter;)')
needle = '            double cost = plan_cost(ops.size());\n            if (o.value_fillers)'
assert needle in src
src = src.replace(needle,'''            if(light==2) {
                tail_cache_on=false;
                check_vis=false;
                canonicalize();
                return ops;
            }
''' + needle)
src = src.replace('    std::cerr << "value_seed_trials', '    std::cerr << "light_requests = " << solver.light_requests << "\\nhard_light_requests = " << solver.hard_light_requests << \'\\n\';\n    std::cerr << "value_seed_trials')
src = src.replace('// (argon-des-perf-latew105)', '// (deval-vselect)')
# Preserve the parent's table of contents and add all new section names.
sections = re.findall(r'^\s*// ==== (.*?) ====\s*$',src,re.M)
firstinclude = src.index('#include')
prefix = src[:firstinclude]
tocstart = prefix.index('// Contents (') if '// Contents (' in prefix else -1
if tocstart >= 0:
    src = src[:tocstart] + '// Contents (section markers below):\n' + ''.join('//   '+s+'\n' for s in sections) + '\n' + src[firstinclude:]
src = src.replace('// Time-shortage fallback was intentionally removed in PR #117; restore it before final submission.',
                  '// V selects completed designs; near the deadline requests use one valid ordinary plan.')
src = src.replace('#include <algorithm>', '#ifndef DEVAL_REQUEST_LIMIT\n#define DEVAL_REQUEST_LIMIT 1.90\n#endif\n#include <algorithm>')
assert len(src.encode()) <= 520000, len(src.encode())
(HERE/'main.cpp').write_text(src)
print('source bytes',len(src.encode()))
