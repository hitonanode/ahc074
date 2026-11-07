from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/deval-seven-wide/main.cpp').read_text()
def put(name,code,desc):
 p=root/'solutions'/name;p.mkdir(exist_ok=True)
 (p/'main.cpp').write_text(code)
 (p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n'+desc+'\n\n探索回数、乱数、候補、浮動小数点演算は共通です。時間不足による切り替えはありません。\n')
 print(name,len(code.encode()))
a=base.index('        const __m256i f =',base.index('__m256i closure4('))
b=base.index('        const __m256i ones =',a)
gather='''        const __m128i rs = _mm_set_epi32(int(r3),int(r2),int(r1),int(r0));
        const __m128i mask = _mm_set1_epi32(255);
        __m256i c = _mm256_i32gather_epi64((const long long*)expand[0].data(),_mm_and_si128(rs,mask),8);
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[1].data(),_mm_and_si128(_mm_srli_epi32(rs,8),mask),8));
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[2].data(),_mm_and_si128(_mm_srli_epi32(rs,16),mask),8));
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[3].data(),_mm_srli_epi32(rs,24),8));
'''
put('deval-map-gather',base[:a]+gather+base[b:],'窓割り当ての4組の閉包計算で、関係行列の展開を既存の整数表から gather します。')
scalar='''        const auto expand_one = [&](uint32_t r) { return expand[0][r&255] | expand[1][(r>>8)&255] | expand[2][(r>>16)&255] | expand[3][r>>24]; };
        __m256i c = _mm256_set_epi64x((long long)expand_one(r3),(long long)expand_one(r2),(long long)expand_one(r1),(long long)expand_one(r0));
'''
put('deval-map-expand',base[:a]+scalar+base[b:],'窓割り当ての4組の閉包計算で、関係行列の展開に既存の整数表を使います。')
old='''            found |= u64(unsigned(_mm256_movemask_ps(_mm256_castsi256_ps(hit)))) << (8 * i);'''
new='''            const unsigned bits = unsigned(_mm256_movemask_ps(_mm256_castsi256_ps(hit)));
            if(bits) return triangles[8*i+__builtin_ctz(bits)];'''
assert old in base
put('deval-map-triangle',base.replace(old,new),'窓割り当ての非互換性の証拠を探す際、最初の三角閉路が見つかった時点で返します。選ぶ証拠は同じです。')
key=base.replace('    std::vector<uint32_t> pair_tail(np);','''    std::vector<int> handle_key(np);
    u64 keyed_handles = ~hm;
    auto refresh_keys = [&] __attribute__((target("popcnt"))) {
        if(keyed_handles == hm) return;
        keyed_handles = hm;
        for(int p=0;p<np;++p) handle_key[p] = 1800*__builtin_popcountll(pairs.diff[p]&hm)+full144[p];
    };
    std::vector<uint32_t> pair_tail(np);''')
key=key.replace('        const int size = nvalid;\n        for (int i = 0; i < size; i++) {','        const int size = nvalid;\n        refresh_keys();\n        for (int i = 0; i < size; i++) {',1)
oldkey='1800 * __builtin_popcountll(pairs.diff[p] & handle_mask) + 5 * int(rel[p] - 1) + full144[p]'
assert oldkey in key
key=key.replace(oldkey,'(handle_mask==hm ? handle_key[p] : 1800 * __builtin_popcountll(pairs.diff[p] & handle_mask) + full144[p]) + 5 * int(rel[p] - 1)',1)
put('deval-map-key',key,'窓割り当てのマッチングで、現在のハンドル集合の整数コストをキャッシュします。集合が変わったときだけ更新します。')
put('deval-next-prof','#define DESIGN_PROFILE 3\n#define COLFAST_PROFILE 1\n#define AF_PROFILE 1\n'+base,'既存の窓割り当て・焼きなまし・注文処理の計測を有効にした調査用です。')
