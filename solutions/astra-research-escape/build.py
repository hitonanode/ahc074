#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
source = (here.parent / 'astra-research-look' / 'main.cpp').read_text()
old = '''            if(no_accept>=(climb?2048:1024)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
'''
assert old in source
source = source.replace(old, '', 1)
new = '''            no_accept++;
            if(no_accept>=(climb?2048:1024)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                escapes++;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
'''
needle = '            int ia=rng.mod(g),ib=rng.mod(g),a=order[ia],b=order[ib];'
assert needle in source
source = source.replace(needle, new + needle, 1)
source = source.replace('pol=oldpol;no_accept++;', 'pol=oldpol;', 1)
source = source.replace('long long full=0;', 'long long full=0,escapes=0;', 1)
source = source.replace('std::cerr<<"map_full_evaluations = "<<full',
                        'std::cerr<<"map_escapes = "<<escapes<<"\\nmap_full_evaluations = "<<full', 1)
(here / 'main.cpp').write_text(source)
