#!/usr/bin/env python3
"""Reproduce assignment-only timing; the contest source is not modified."""
import hashlib,json,os,pathlib,re,subprocess,tempfile,time
here=pathlib.Path(__file__).resolve().parent
root=here.parents[1]
inputs=pathlib.Path(os.environ.get('ASTRA_INPUT_DIR', str(root/'solutions/astra-lab/cases')))
source=(here/'main.cpp').read_text()
anchor='    auto rebuild = [&]() {'
timers="""    double profile_rebuild_sec=0,profile_guide_sec=0,profile_repair_sec=0;
    struct ProfileScope {
        double& dest;
        std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
        ~ProfileScope(){dest+=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();}
    };
"""
assert source.count(anchor)==1
source=source.replace(anchor,timers+anchor+'\n        ProfileScope probe_scope{profile_rebuild_sec};')
for anchor,variable in [
 ('    auto repair=[&](State& s,const std::array<int,4>& exposed,int nexposed,int desired) {','profile_repair_sec'),
 ('    auto guide=[&](int a,int ea) {','profile_guide_sec')]:
 assert source.count(anchor)==1
 source=source.replace(anchor,anchor+'\n        ProfileScope probe_scope{'+variable+'};')
anchor='    std::cerr<<"joint_window_trials = "'
assert source.count(anchor)==1
source=source.replace(anchor,'    std::cerr<<"profile_rebuild_sec = "<<profile_rebuild_sec<<"\\nprofile_guide_sec = "<<profile_guide_sec<<"\\nprofile_repair_sec = "<<profile_repair_sec<<\'\\n\';\n'+anchor)
probe=(here/'design_probe.cpp').read_text().replace('#include "main.cpp"','#include "profile-source.cpp"')
rows=[]
with tempfile.TemporaryDirectory(prefix='ahc074-joint-profile-') as temporary:
 d=pathlib.Path(temporary)
 (d/'profile-source.cpp').write_text(source)
 (d/'probe.cpp').write_text(probe)
 subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(d/'probe.cpp'),'-o',str(d/'probe')],check=True)
 for seed in (0,1):
  data=b''.join((inputs/f'{seed:04}.txt').read_bytes().splitlines(keepends=True)[:257])
  started=time.perf_counter()
  result=subprocess.run([str(d/'probe')],input=data,capture_output=True,env=dict(os.environ,MAP_ITERS='50000',GOPT_STEPS='12500'),timeout=180,check=True)
  row={'seed':seed,'returncode':result.returncode,'wall_seconds':time.perf_counter()-started}
  for key,value in re.findall(r'^([a-z_]+) = ([-+\d.eE]+)$',result.stderr.decode(),re.M):row[key]=float(value)
  rows.append(row)
  print(row,flush=True)
(here/'profile-results.json').write_text(json.dumps({'main_sha256':hashlib.sha256((here/'main.cpp').read_bytes()).hexdigest(),'rows':rows},indent=2)+'\n')
