"""Share the mapper's exact poset table with V, retaining directional values.

This changes neither the existing both_of table nor V's numeric features.
The standalone verification driver checks every relabeling of all 318 classes.
"""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent

def optimize(src):
    assert 'int one_of(u64 closed)' not in src
    src=src.replace('std::vector<uint16_t> displacement, value;',
                    'std::vector<uint16_t> displacement, value, one;')
    needle='    // The canonical keys with their sums (kPosetDual), then the displacements, the largest buckets first.'
    assert needle in src
    src=src.replace(needle,'''    // Direction-specific expectation for V. The mapper still reads the original
    // sum of the two directions. Canonicalization tells which summand to use.
    __attribute__((target("bmi2"))) int one_of(u64 closed) const {
        const uint32_t packed=pack_relation(closed),key=canonical(packed);
        const unsigned i=slot(key,displacement[bucket(key)]);
        return packed==key?one[i]:value[i]-one[i];
    }
'''+needle)
    src=src.replace('std::vector<uint16_t> all_sums;','std::vector<uint16_t> all_sums, all_one;')
    src=src.replace('all_sums.reserve(65012);','all_sums.reserve(65012);all_one.reserve(65012);')
    src=src.replace('const uint32_t key = canonical(pack_relation(r));',
                    'const uint32_t packed=pack_relation(r),key=canonical(packed);')
    src=src.replace('                all_sums.push_back(sum);',
        '                all_sums.push_back(sum);\n                all_one.push_back(uint16_t(packed==key?kPosetClasses[i].sum:kPosetClasses[kPosetDual[i]].sum));')
    src=src.replace('std::vector<uint16_t> sums(start[kBuckets]);',
                    'std::vector<uint16_t> sums(start[kBuckets]),ones(start[kBuckets]);')
    src=src.replace('                sums[i] = all_sums[j];','                sums[i] = all_sums[j];ones[i]=all_one[j];')
    src=src.replace('        value.assign(1U << kSlotBits, 0);',
                    '        value.assign(1U << kSlotBits, 0);one.assign(1U << kSlotBits,0);')
    src=src.replace('for (int i = 0; i < n; i++) used[slots[i]] = 1, value[slots[i]] = sums[lo + i];',
                    'for (int i = 0; i < n; i++) {used[slots[i]]=1;value[slots[i]]=sums[lo+i];one[slots[i]]=ones[lo+i];}')
    lo=src.index('struct GenericTable {')
    mid=src.index('    __attribute__((target("popcnt"))) std::pair<double,int> cost',lo)
    src=src[:lo]+'''struct GenericTable {
    GenericTable() { (void)PosetSums::get(); }
'''+src[mid:]
    assert 'return {mean.at(relation),nr};' in src
    src=src.replace('return {mean.at(relation),nr};','return {PosetSums::get().one_of(relation)/720.,nr};')
    return src

def verifier(src):
    lo=src.index('struct PosetClass {');hi=src.index('#ifdef POSET_VERIFY',lo)
    return '''#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <numeric>
#include <vector>
#include <iostream>
using u64=std::uint64_t;
'''+src[lo:hi]+'''
int main() {
    const auto& table=PosetSums::get();
    long long checked=0,wrong=0;
    for(int i=0;i<318;++i) {
        std::array<int,6> p{0,1,2,3,4,5};
        do {
            u64 r=0;
            for(u64 z=kPosetClasses[i].relation;z;z&=z-1) {
                int bit=__builtin_ctzll(z);r|=u64(1)<<(8*p[bit/8]+p[bit%8]);
            }
            ++checked;
            wrong+=table.one_of(r)!=kPosetClasses[i].sum;
            wrong+=table.both_of(r)!=kPosetClasses[i].sum+kPosetClasses[kPosetDual[i]].sum;
        } while(std::next_permutation(p.begin(),p.end()));
    }
    std::cout<<"checked "<<checked<<" wrong "<<wrong<<'\\n';return wrong?1:0;
}
'''

if __name__=='__main__':
    source=Path(sys.argv[1]) if len(sys.argv)>1 else HERE.parent/'deval-vclean/main.cpp'
    dest=Path(sys.argv[2]) if len(sys.argv)>2 else HERE.parent/'deval-vcache'
    src=optimize(source.read_text());assert len(src.encode())<=520000
    dest.mkdir(exist_ok=True);(dest/'main.cpp').write_text(src)
    (HERE/'verify_value_table.cpp').write_text(verifier(src))
    (dest/'README.md').write_text('''# deval-vcache

改良元: `solutions/deval-vclean`。

V が重複して構築していた 130,023 通りの順序制約の期待費用表を、窓割当ての PosetSums と共有する。既存の正逆両方向の和に、正規化した向きの費用を 16 bit 配列 1 本追加し、向きごとの正確な期待費用を引く。V の数式・係数・候補作成は親と同じ。起動時の重複したハッシュ表作成と大きな表の参照を省く。

`solutions/deval-vselect/optimize_value.py` で生成する。`verify_value_table.cpp` は全 318 クラス × 720 通りの置換で、元の和と方向別の値を検査する。候補と時間ガードは親の設定を使う。
''')
    print('source bytes',len(src.encode()))
