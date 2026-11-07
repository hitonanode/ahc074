from pathlib import Path
import sys,json
from compare_runs import main
P=Path(__file__).resolve().parent
pairs=[('20261107-093319_deval-vbranch-nofb','20261107-093319_deval-fast','resume-speed.deval-fast')]
for suffix in ['edit','color','prefix']:
 pairs.append(('20261107-093319_deval-fast','20261107-093319_deval-fast'+suffix,'resume-speed.fast-vs-deval-fast'+suffix))
pairs += [('20261107-094028_deval-vbranch-nofb','20261107-094028_deval-fast','resume-fast-clang.deval-fast'),('20261107-093734_deval-fast','20261107-093734_deval-fastrecip','resume-recip.deval-fastrecip')]
for x,y,out in pairs:
 sys.argv=['compare_runs.py',x,y,str(P/(out+'.json'))];main()
