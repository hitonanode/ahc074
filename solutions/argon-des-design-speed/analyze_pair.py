"""同時比較の集計と出力一致検査を1つの外部ロック内で順に実行する。"""
import argparse
import subprocess
import sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('base');p.add_argument('candidate');p.add_argument('prefix');p.add_argument('--end',type=int,default=500)
a=p.parse_args();here=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(here/'summarize.py'),a.base,a.candidate,'--end',str(a.end),
                '--output',a.prefix+'.json'],check=True)
subprocess.run([sys.executable,str(here/'identity.py'),a.base,a.candidate,'--end',str(a.end),
                '--output',a.prefix+'-identity.json'],check=True)
