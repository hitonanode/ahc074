#!/usr/bin/env python3
"""計測用コピーだけ診断出力・補助紙の打ち切りを変更する。"""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('targets', nargs='+')
p.add_argument('--sim', action='store_true')
p.add_argument('--plain', action='store_true', help='提出ソースを変更せずビルドする')
p.add_argument('--compiler', choices=['g++','clang++'], default='g++')
a=p.parse_args(); assert not (a.sim and a.plain)
here=pathlib.Path(__file__).resolve().parent
meta_path=here/'build-info.json'
meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
for target in a.targets:
    source=here.parent/'imp-s2hd/main.cpp' if target=='base' else here/(target+'.cpp')
    original=source.read_text(); text=original
    anchor='    std::cerr << "anneal_iters = "'
    assert text.count(anchor)==1
    if not a.plain: text=text.replace(anchor, '    std::cerr.precision(12);\n    std::cerr << "anneal_cost = " << des->cur << \'\\n\';\n'+anchor)
    if a.sim:
        text=text.replace('constexpr double kHelperGiveUp = 1.55;', 'constexpr double kHelperGiveUp = 1000.0;')
        text=text.replace('        double tot = 0;', '        std::cerr << "sim_helper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0) << \'\\n\';\n        double tot = 0;',1)
    name=target+('-clang' if a.compiler=='clang++' else '')+('-sim' if a.sim else '-plain' if a.plain else '-normal')
    src=source if a.plain else here/(name+'-measure.cpp')
    if not a.plain: src.write_text(text)
    cmd=[a.compiler,'-std=c++23','-O2','-DCLOCK_SCALE=1.1']+(['-DSIM_HARNESS'] if a.sim else [])+[str(src),'-o',str(here/name)]
    subprocess.run(cmd, check=True)
    meta[name]={'command':cmd,'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'compiled_sha256':hashlib.sha256(text.encode()).hexdigest(),'compiler':subprocess.check_output([a.compiler,'--version'],text=True).splitlines()[0]}
    meta_path.write_text(json.dumps(meta,indent=2)+'\n')
    print(name,flush=True)
