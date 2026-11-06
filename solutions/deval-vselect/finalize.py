"""Freeze a measured training configuration and install the tested reserve guard.

This does not fit a model or read evaluation scores. Use before final test runs.
"""
from pathlib import Path
import argparse,hashlib,json,re
from make_col import refresh_contents
from optimize_value import optimize
from strip_branch import strip_branch
from compiler_options import design_o3
HERE=Path(__file__).resolve().parent

def replace_calls(src,fun,name,value):
    needle=fun+'("'+name+'"'
    while needle in src:
        lo=src.index(needle);i=lo+len(fun);depth=0
        while i<len(src):
            if src[i]=='(':depth+=1
            elif src[i]==')':
                depth-=1
                if depth==0:break
            i+=1
        src=src[:lo]+str(value)+src[i+1:]
    return src

def reserve_guard(src):
    src=src.replace('#define DEVAL_REQUEST_LIMIT 1.72','#define DEVAL_REQUEST_LIMIT 1.90')
    if 'int processed_requests=0;' not in src:
        src=src.replace('    Moves process(int u) {','    int processed_requests=0;\n    Moves process(int u) {\n        const double remaining=std::max(0.,(1024.-processed_requests++)/1024.);')
    src=src.replace('light=now>DEVAL_REQUEST_LIMIT?2:now>1.84?1:0;',
                    'light=now>DEVAL_REQUEST_LIMIT-.30*remaining?2:now>1.84-.12*remaining?1:0;')
    assert 'DEVAL_REQUEST_LIMIT-.30*remaining' in src
    # Each loop exits through its existing best-state restoration. These are
    # submission-only emergency caps, so ordinary benchmark designs stay fixed.
    if '// Submission-only absolute design caps.' not in src:
        needle='            if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;'
        assert needle in src
        src=src.replace(needle,needle+'''\n#ifndef LOCAL_BENCH
            // Submission-only absolute design caps.
            if(elapsed_sec()>.85)break;
#endif''')
        needle='            stats.climb_steps = it + 1;'
        assert needle in src
        src=src.replace(needle,'''#ifndef LOCAL_BENCH
            if((it&15)==0&&elapsed_sec()>.90)break;
#endif
'''+needle)
        needle='                    if (progress >= 1 || elapsed >= seconds) break;'
        assert needle in src
        src=src.replace(needle,needle+'''\n#ifndef LOCAL_BENCH
                    if(elapsed_sec()>1.15)break;
#endif''')
        needle='            if (fixedIterations > 0 ? it >= fixedIterations : ((it & 63) == 0 && scaled_since(start) >= seconds)) break;'
        assert needle in src
        src=src.replace(needle,needle+'''\n#ifndef LOCAL_BENCH
            if((it&63)==0&&elapsed_sec()>1.25)break;
#endif''')
    return src

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source');p.add_argument('destination')
    p.add_argument('--settings',default='{}');p.add_argument('--share-table',action='store_true')
    p.add_argument('--prune-branch',action='store_true')
    p.add_argument('--o3-design',action='store_true')
    a=p.parse_args();settings=json.loads(a.settings)
    original=(Path(a.source)/'main.cpp').read_text();src=original
    for name,value in settings.items():
        if name=='DEVAL_CANDIDATES':
            src=re.sub(r'    const int candidates=.*?;\n',f'    const int candidates={int(value)};\n',src,count=1)
        elif name=='DEVAL_BRANCHES':
            src=re.sub(r'    const int branches=.*?;\n',f'    const int branches={int(value)};\n',src,count=1)
        else:
            for fun in ['env_int','env_real']:src=replace_calls(src,fun,name,value)
    src=reserve_guard(src)
    if a.share_table:src=optimize(src)
    if a.prune_branch:src=strip_branch(src,settings.get('DEVAL_SHARED',2))
    if a.o3_design:src=design_o3(src)
    src=src.replace('// ==== V: swaps of completed target assignments ====\n','')
    src=refresh_contents(src)
    assert len(src.encode())<=520000
    dest=Path(a.destination);dest.mkdir(exist_ok=True)
    (dest/'main.cpp').write_text(src)
    spec=dict(parent=a.source,settings=settings,share_table='int one_of(u64 closed)' in src,
              prune_branch='prescreen_value(' not in src,o3_design=a.o3_design,
              parent_sha256=hashlib.sha256(original.encode()).hexdigest(),
              source_sha256=hashlib.sha256(src.encode()).hexdigest(),source_bytes=len(src.encode()),
              training_seeds='0-499',final_test_seeds='500-999',
              value_model='solutions/deval-vtarget/V.json',request_guard='reserve_v1',
              design_guard='submission_absolute_caps_v1')
    (dest/'FROZEN.json').write_text(json.dumps(spec,indent=2)+'\n')
    print(json.dumps(spec,indent=2))

if __name__=='__main__':main()
