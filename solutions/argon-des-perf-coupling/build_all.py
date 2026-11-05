"""Check one new source at a time; yield the evaluation lock between source directories."""
import argparse,subprocess,json,shlex
from pathlib import Path
here=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('directories',nargs='+');a=p.parse_args()
idle='/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/tools/whenidle.sh'
for directory in a.directories:
 command=shlex.join(['flock','-x','/home/sato/ahc074/runs/.lock','python3',str(here/'check_builds.py'),directory])
 print('Checking',directory,flush=True)
 result=subprocess.run([idle,command])
 print('Finished',directory,result.returncode,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
