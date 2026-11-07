from pathlib import Path
import re,sys
from compare_runs import main
p=Path(sys.argv[1]);runs=re.findall(r'run-id: (\S+)',p.read_text())
assert '比較が終わりました' in p.read_text(),p
for run in runs[1:]:
    name=run.split('_',1)[1]
    output=p.with_name(p.stem+'.'+name+'.json')
    sys.argv=['compare_runs.py',runs[0],run,str(output)]
    main()
