"""V16（deval-vbranch-o3 が使う V）の特徴量を出すプログラムを、このディレクトリに作る。

deval-vselect/target_qmc.py と同じ置き換え（対象ごとの固定の digital shift と、
不一致数の解析的な積分）を deval-model の surrogate.hpp に当て、features_v16 をビルドする。
出力は設計 1 件につき 142 個の double（value.hpp の kTerms の順）。
"""
from pathlib import Path
import subprocess, sys
HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / 'deval-model'
sys.path.insert(0, str(HERE.parent / 'deval-vselect'))
sys.dont_write_bytecode = True
from target_qmc import independent_samples, control_variates

src = control_variates(independent_samples((MODEL / 'surrogate.hpp').read_text()))
(HERE / 'surrogate_v16.hpp').write_text(src)
feat = (MODEL / 'design_features.hpp').read_text().replace('"surrogate.hpp"', '"surrogate_v16.hpp"')
for f in ['poset_data.hpp', 'quadrature.hpp']:
    feat = feat.replace('"' + f + '"', '"../deval-model/' + f + '"')
(HERE / 'features_v16.hpp').write_text(feat)
val = (MODEL / 'value.hpp').read_text().replace('"design_features.hpp"', '"features_v16.hpp"')
(HERE / 'value_v16.hpp').write_text(val)
(HERE / 'features_v16.cpp').write_text('''#include "value_v16.hpp"
#include <fstream>
#include <iostream>
// stdin: design state paths, one per line. stdout: 142 doubles per design (kTerms order).
int main(int argc, char** argv) {
    const int n = std::stoi(argv[1]);
    deval::GenericTable generic;
    std::string path;
    while (std::getline(std::cin, path)) {
        std::ifstream in(path);
        if (!in) return 1;
        auto state = deval::State::read(in);
        auto f = deval::static_features(state, generic);
        deval::add_stationary_features(f, state, n, 2);
        std::array<double, deval::kTerms.size()> row{};
        for (int j = 0; j < int(row.size()); ++j) row[j] = f.at(deval::kTerms[j].name);
        std::cout.write(reinterpret_cast<const char*>(row.data()), sizeof(row));
    }
}
''')
subprocess.run(['g++', '-std=c++23', '-O2', '-mpopcnt', str(HERE / 'features_v16.cpp'), '-o', str(HERE / 'features_v16')], check=True)
print('built', HERE / 'features_v16')
