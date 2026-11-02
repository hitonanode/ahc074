#!/usr/bin/env python3
"""基準・採用版を指定オプションでビルド。模擬計測時だけ補助紙の打ち切りを延長する。"""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('targets',nargs='*',default=['base','main'],)
p.add_argument('--sim',action='store_true')
p.add_argument('--compiler',default='g++',choices=['g++','clang++'])
a=p.parse_args()
here=pathlib.Path(__file__).resolve().parent
record=here/'build-info.json'
meta=json.loads(record.read_text()) if record.exists() else {}
for target in a.targets:
    source=here.parent/'astra-search4/main.cpp' if target=='base' else here/(target+'.cpp')
    text=source.read_text()
    name=('base' if target=='base' else target+'-bin')+('-clang' if a.compiler=='clang++' else '')+('-sim' if a.sim else '')
    source_hash=hashlib.sha256(text.encode()).hexdigest()
    if a.sim:
        old='constexpr double kHelperGiveUp = 1.55;'
        assert text.count(old)==1
        text=text.replace(old,'constexpr double kHelperGiveUp = 1000.0;')
        text=text.replace('        double tot = 0;', '        std::cerr << "sim_helper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0) << \'\\n\';\n        double tot = 0;',1)
        source=here/(name+'.cpp');source.write_text(text)
    cmd=[a.compiler,'-std=c++23','-O2','-DCLOCK_SCALE=1.1']+(['-DSIM_HARNESS'] if a.sim else [])+[str(source),'-o',str(here/name)]
    subprocess.run(cmd,check=True)
    meta[name]={'command':cmd,'source_sha256':source_hash,'compiled_source_sha256':hashlib.sha256(text.encode()).hexdigest(),'compiler':subprocess.check_output([a.compiler,'--version'],text=True).splitlines()[0]}
    record.write_text(json.dumps(meta,indent=2)+'\n')
