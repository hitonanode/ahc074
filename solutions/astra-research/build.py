#!/usr/bin/env python3
"""Regenerate the self-contained submission from the baseline and exact table."""
from pathlib import Path

here = Path(__file__).resolve().parent
base = (here.parent / 'astra-search4' / 'main.cpp').read_text()
generator = (here / 'generate_posets.cpp').read_text()
canon = generator[generator.index('u64 canonical7('):generator.index('\nint main(')]
module = (here / 'assignment7.inc').read_text()
module = module.replace('// @CANONICAL7@', canon)
module = module.replace('// @POSET7_TABLE@', (here / 'posets7.inc').read_text())
begin = base.index('// Closure of a relation bit matrix')
end = base.index('// kBitLanes[v][i]')
source = base[:begin] + module + '\n' + base[end:]
source = source.replace('int M = 6, G = 36;\n    Comparator comp;', '''#ifndef RESEARCH_G
#define RESEARCH_G 38
#endif
    int M = 7, G = RESEARCH_G;
    Comparator comp;''')
source = source.replace('return PosetSums::get().both_of(r) / 1440.0;',
                        'return (Poset7Costs::get().cost(r) - 1) / 10080.0;')
source = '// astra-research: seven generic sheets, exact legal-distance costs for all 7-element posets.\n' + source
(here / 'main.cpp').write_text(source)
