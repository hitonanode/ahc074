"""A completed-design neighborhood that moves entire columns and their handles."""
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vcol'

def remove_function(src,name):
    lo=src.index('int '+name+'(');start=src.index('{',lo);level=1;i=start+1
    while level:
        level+=(src[i]=='{')-(src[i]=='}');i+=1
    return src[:lo]+src[i:]

def stripped_source():
    src=(HERE.parent/'deval-vtarget/main.cpp').read_text()
    src=remove_function(src,'deval_refine')
    lo=src.index('    // ==== design_papers: accept assignment cycles by V ====')
    hi=src.index('    std::cerr << chosen_log;',lo)
    src=src[:lo]+src[hi:]
    src=re.sub(r'^.*best_design.*\n','',src,flags=re.M)
    src=src.replace('std::function<double(const Design&)> deval_match_merit;\n','')
    src=src.replace('deval_match_merit?deval_match_merit(d):','')
    src=src.replace('        if(deval_match_merit && elapsed_sec()>1.2)break;\n','')
    src=src.replace('env_int("DEVAL_CANDIDATES"):2','env_int("DEVAL_CANDIDATES"):1')
    return src

COL_CODE='''// ==== V: completed column-order refinement ====
// Reorder whole columns together with their handle windows. Pair compatibility
// and both own-handle colors remain valid. Rebuild masks, retain current extra
// perforations, and renumber papers so the initial stack is again in column order.
DesignState reorder_columns(const DesignState& s,const std::vector<int>& sequence) {
    auto out=s;
    std::array<std::vector<int>,K> owners;
    for(int t=0;t<P;++t)owners[s.ded[t]].push_back(t);
    std::array<u64,K> extra{};
    for(int k=0;k<K;++k)if(s.columns[k]>=0) {
        u64 mask=low_bits(s.G)|kCapBit;
        for(int c=0;c<=s.columns[k];++c)mask|=u64(1)<<s.handle[c];
        if(owners[k].size()==2)mask&=~(s.A[owners[k][0]]^s.A[owners[k][1]]);
        mask|=kCapBit;
        extra[k]=mask&~s.papers[k].opaque;
    }
    int next=s.M+1;
    u64 prefix=low_bits(s.G)|kCapBit;
    for(int c=0;c<s.H;++c) {
        const int oldcol=sequence[c];
        out.handle[c]=s.handle[oldcol];prefix|=u64(1)<<out.handle[c];
        for(int k=0;k<K;++k)if(s.columns[k]==oldcol) {
            const auto& ts=owners[k];
            u64 mask=prefix;
            if(ts.size()==2)mask&=~(s.A[ts[0]]^s.A[ts[1]]);
            mask=(mask&~extra[k])|kCapBit;
            u64 black=s.A[ts[0]]&mask;
            if(ts.size()==2&&((s.A[ts[0]]^s.A[ts[1]])&kCapBit))black&=~kCapBit;
            out.papers[next]={mask,black};out.columns[next]=c;
            for(int t:ts)out.ded[t]=next;
            ++next;
        }
    }
    assert(next==K);
    return out;
}
int refine_columns(DesignState& state,const deval::DesignValue& value,double& best,int trials) {
    XorShift rng{0x95d2b7a2106c31ULL};
    int accepted=0;
    for(int it=0;it<trials;++it) {
        if(elapsed_sec()>1.2)break;
        const int a=rng.below(state.H);
        int b=rng.below(state.H);
        if(it%4)b=std::clamp(a+(rng.below(2)?1:-1)*(1+rng.below(3)),0,state.H-1);
        if(a==b)continue;
        std::vector<int> sequence(state.H);std::iota(sequence.begin(),sequence.end(),0);
        if(it&1) {
            if(a<b)std::rotate(sequence.begin()+a,sequence.begin()+a+1,sequence.begin()+b+1);
            else std::rotate(sequence.begin()+b,sequence.begin()+a,sequence.begin()+a+1);
        } else std::swap(sequence[a],sequence[b]);
        auto candidate=reorder_columns(state,sequence);
        const double v=value.from_design(candidate);
        if(v<best)best=v,state=std::move(candidate),++accepted;
    }
    return accepted;
}
'''

def refresh_contents(src):
    lo=src.index('// Contents (');hi=src.index('#include',lo)
    # Keep any compiler macro definitions that precede the first include.
    defines=src[src.index('#ifndef DEVAL_REQUEST_LIMIT',lo):hi] if '#ifndef DEVAL_REQUEST_LIMIT' in src[lo:hi] else ''
    sections=re.findall(r'^\s*// ==== (.*?) ====\s*$',src,re.M)
    return src[:lo]+'// Contents (section markers below):\n'+''.join('//   '+s+'\n' for s in sections)+defines+src[hi:]

def main():
    src=stripped_source()
    src=src.replace('// ==== Design iteration counts ====',COL_CODE+'\n// ==== Design iteration counts ====')
    src=src.replace('    std::cerr << chosen_log;', '''    const double col_begin=elapsed_sec();
    const int col_accepted=state.emergency?0:refine_columns(state,value,best,int(env_real("DEVAL_COL_REFINE",24)));
    std::cerr << "dv_col_accepted = " << col_accepted << "\\ndv_col_sec = " << elapsed_sec()-col_begin << '\\n';
    std::cerr << chosen_log;''')
    src=refresh_contents(src)
    DEST.mkdir(exist_ok=True)
    (DEST/'main.cpp').write_text(src)
    assert len(src.encode())<=520000,len(src.encode())
    (DEST/'README.md').write_text('''# deval-vcol

改良元: `solutions/deval-vtarget`（SOTA からの設計評価器統合版）。

通常の設計を完成させた後、列全体と専用 handle を同時に並べ替える近傍を 24 回試す。ペアの組合せと各列の両色を保つ。紙の prefix の印刷範囲を再計算し、列順に紙を番号付けし直すため、初期のスタックも正しい列順になる。V が下がった変更だけを採用する。

V は対象ごとの digital shift と解析的な不一致数補正を使う 16 点モデル。学習は seed 0–499。`DEVAL_COL_REFINE` は試行数（既定 24）。追加設計は経過 1.2 秒で止める。リクエストの軽量化は提出時のみ 1.72 秒から有効。LOCAL_BENCH では無効。

`dv_col_accepted` は採用数、`dv_col_sec` はその計算時間。その他の記録、@paper/@ops、DesignStore は親と共通。生成は `solutions/deval-vselect/make_col.py`。
''')
    print('source bytes',len(src.encode()))
if __name__=='__main__':main()
