"""Remove unused candidate-generation experiments from a frozen mode-1 solver."""
import re

def strip_branch(src,shared=2):
    lo=src.index('// ==== Cheap prediction of the completed design from a snapshot ====')
    hi=src.index('// ==== Design iteration counts ====',lo)
    src=src[:lo]+src[hi:]
    src=src.replace('// Generic compatibility is unchanged. Keep each slot\'s perforations, require\n// the unit to agree on its own handle, and preserve both colors in every column.\n','')
    lo=src.index('                    if(D.elite_states')
    i=src.index('{',lo);depth=1;i+=1
    while depth:
        depth+=(src[i]=='{')-(src[i]=='}');i+=1
    src=src[:lo]+src[i:]
    for name in ['elite_states','elite_limit','elite_start','elite_end','elite_current']:
        src=re.sub(r'^    [^\n]*\b'+name+r'[^\n]*;\n','',src,flags=re.M)
    lo=src.index('    auto initialize = [&](Design& d) {',src.index('DesignState design_papers('))
    hi=src.index('    for(int i=0;i<candidates;++i)',lo)
    src=src[:lo]+'''    // Share the first segments. Every branch starts from this same
    // best state, with a deterministic salt for its remaining random moves.
    const double prefix_begin=elapsed_sec();
    des->anneal(1e300,anneal_iters,0,shared);
    anneal_sec+=elapsed_sec()-prefix_begin;
    total_iters+=des->anneal_iters;
    const auto prefix=std::make_unique<Design>(*des);
'''+src[hi:]
    lo=src.index('        if(mode==3||mode==5) {',src.index('    for(int i=0;i<candidates;++i)'))
    hi=src.index('        double begin=elapsed_sec();',lo)
    src=src[:lo]+'''        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
'''+src[hi:]
    lo=src.index('        // Checkpoints are 256 moves per segment.')
    hi=src.index('        if(mode==1)',lo)
    src=src[:lo]+src[hi:]
    src=src.replace('        if(mode==1) {','        {')
    src=src.replace('        if(mode<2)total_iters+=des->anneal_iters;','        total_iters+=des->anneal_iters;')
    src=src.replace('((mode==3||mode==5)?elite_order[i]:i)','i')
    src=re.sub(r'    const int mode=.*?\n','',src,count=1)
    src=re.sub(r'    const int branches=.*?\n','',src,count=1)
    src=re.sub(r'    const int shared=.*?\n',f'    const int shared={int(shared)};\n',src,count=1)
    assert 'mode==' not in src[src.index('DesignState design_papers('):src.index('struct DesignStore')]
    assert 'elite_states' not in src
    return src
