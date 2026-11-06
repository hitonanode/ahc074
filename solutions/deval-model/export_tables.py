"""Copy the solver's exact poset costs and freeze design-independent quadrature.
Run under flock. Only this directory is written.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import re
from features import qmc_samples
HERE=Path(__file__).resolve().parent
src=(HERE.parent/'argon-des-perf-latew105/main.cpp').read_text()
body=src.split('constexpr PosetClass kPosetClasses[318] = {',1)[1].split('};',1)[0]
data=re.findall(r'\{0x([0-9a-f]+)ULL, (\d+)\}',body)
text='#pragma once\n#include <array>\n#include <cstdint>\nnamespace deval {\nstruct PosetClass { std::uint64_t relation; int sum; };\ninline constexpr std::array<PosetClass,318> kClasses{{\n'
text+=''.join(f'    {{0x{k}ULL,{v}}},\n' for k,v in data)
text+='}};\n}\n'
(HERE/'poset_data.hpp').write_text(text)
text='#pragma once\n#include <array>\n#include <stdexcept>\nnamespace deval {\n'
for H in [25,31,35]:
    a=qmc_samples(H,128)
    text+=f'inline constexpr std::array<double,{a.size}> kSamples{H}{{\n'
    text+=''.join('    '+','.join(format(x,'.17g') for x in row)+',\n' for row in a)
    text+='};\n'
text+='inline const double* samples_for(int H) {\n'
for H in [25,31,35]:text+=f'    if(H=={H})return kSamples{H}.data();\n'
text+='    throw std::runtime_error("Unsupported H: export a Sobol table for this H");\n}\n}\n'
(HERE/'quadrature.hpp').write_text(text)
print('exported 318 exact poset classes and fixed Sobol tables')
